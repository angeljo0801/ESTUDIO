from pathlib import Path
import re

# Memora v1.21
# - Per-tutor Quick AI selector with an explicit System general AI option.
# - Strict guide grounding + random-guide requests that use real source text.
# - Tutor reply notifications.
# - Exam stopwatch becomes display-only; AI exams wait for AI and never silently
#   switch to indexed/generic questions.
# - Plan depth selector.
# - Recommended Ollama model download/use/delete actions.
# - Downloaded-model management entry in AI Settings.


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f'Pattern not found for {label}')
    return text.replace(old, new, 1)


def replace_regex(text, pattern, replacement, label):
    out, n = re.subn(pattern, lambda _m: replacement, text, count=1, flags=re.S)
    if n != 1:
        raise RuntimeError(f'Pattern not found for {label}: {n}')
    return out

# -----------------------------------------------------------------------------
# Tutor page: restore per-tutor quick override while retaining System general AI.
# -----------------------------------------------------------------------------
p = Path('lib/tutor_page.dart')
s = p.read_text()

if "import 'dart:math';\n" not in s:
    s = replace_once(s, "import 'dart:convert';\n", "import 'dart:convert';\nimport 'dart:math';\n", 'tutor dart math import')

for anchor, extra, label in [
    ("import 'ai_service.dart';\n", "import 'completion_notification_service.dart';\n", 'tutor notification import'),
    ("import 'llm_settings_page.dart';\n", "import 'local_model_manager.dart';\nimport 'model_manager_page.dart';\n", 'tutor model imports'),
]:
    if extra.strip().split('\n')[0] not in s:
        s = replace_once(s, anchor, anchor + extra, label)

# v1.14 used to erase every saved tutor override at load time. Keep existing
# source assignments now; new tutors still default to global/system AI.
s = s.replace(
    "        tutor.copyWith(\n          modelSource: 'global',\n          recommendedModels:",
    "        tutor.copyWith(\n          recommendedModels:",
    1,
)

# Recommended model chips now open an action sheet instead of silently changing
# the global model. Ollama provides the online download/delete transport.
new_recommended = r'''  Future<void> _useRecommendedModel(String recommendation) async {
    final model = _modelTag(recommendation);
    final action = await showModalBottomSheet<String>(
      context: context,
      builder: (sheetContext) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(8, 10, 8, 18),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(Icons.memory_outlined),
                title: Text(model, style: const TextStyle(fontWeight: FontWeight.bold)),
                subtitle: const Text('Recommended model for this tutor'),
              ),
              ListTile(
                leading: const Icon(Icons.check_circle_outline),
                title: const Text('Use this Ollama model'),
                subtitle: const Text('Select it for this tutor and as the configured local model.'),
                onTap: () => Navigator.pop(sheetContext, 'use'),
              ),
              ListTile(
                leading: const Icon(Icons.download_rounded),
                title: const Text('Download with Ollama'),
                subtitle: const Text('Ask the Ollama server configured in AI Settings to download it.'),
                onTap: () => Navigator.pop(sheetContext, 'download'),
              ),
              ListTile(
                leading: const Icon(Icons.delete_outline),
                title: const Text('Delete from Ollama'),
                subtitle: const Text('Remove this model from the configured Ollama server.'),
                onTap: () => Navigator.pop(sheetContext, 'delete'),
              ),
              ListTile(
                leading: const Icon(Icons.folder_open_outlined),
                title: const Text('Manage downloaded models'),
                onTap: () => Navigator.pop(sheetContext, 'manage'),
              ),
            ],
          ),
        ),
      ),
    );
    if (action == null) return;

    if (action == 'manage') {
      await Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => const ModelManagerPage()),
      );
      final prefs = await SharedPreferences.getInstance();
      if (mounted) {
        setState(() {
          globalProvider = prefs.getString('llm_provider') ?? 'gemini';
          globalLocalModel = prefs.getString('local_model') ?? '';
        });
      }
      return;
    }

    if (action == 'use') {
      await LocalModelManager.useOllamaModel(model);
      await _setTutorAiSource('local');
      if (!mounted) return;
      setState(() {
        globalProvider = 'local';
        globalLocalModel = model;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$model selected for ${activeTutor.name}.')),
      );
      return;
    }

    if (action == 'download') {
      if (!mounted) return;
      final progress = ValueNotifier<String>('Connecting to Ollama…');
      showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (dialogContext) => PopScope(
          canPop: false,
          child: AlertDialog(
            title: Text('Downloading $model'),
            content: ValueListenableBuilder<String>(
              valueListenable: progress,
              builder: (_, value, __) => Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const LinearProgressIndicator(),
                  const SizedBox(height: 14),
                  Text(value),
                ],
              ),
            ),
          ),
        ),
      );
      try {
        await LocalModelManager.pullOllamaModel(
          model,
          onProgress: (status, completed, total) {
            final suffix = total > 0
                ? ' ${(completed * 100 / total).clamp(0, 100).toStringAsFixed(0)}%'
                : '';
            progress.value = '$status$suffix';
          },
        );
        await LocalModelManager.useOllamaModel(model);
        await _setTutorAiSource('local');
        final prefs = await SharedPreferences.getInstance();
        if (mounted) {
          setState(() {
            globalProvider = prefs.getString('llm_provider') ?? 'local';
            globalLocalModel = model;
          });
        }
        if (mounted) Navigator.of(context, rootNavigator: true).pop();
        progress.dispose();
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$model downloaded and selected.')),
        );
      } catch (e) {
        if (mounted) Navigator.of(context, rootNavigator: true).pop();
        progress.dispose();
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not download $model: $e')),
        );
      }
      return;
    }

    if (action == 'delete') {
      final yes = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Delete Ollama model?'),
          content: Text('Delete $model from the configured Ollama server?'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
            FilledButton.icon(
              onPressed: () => Navigator.pop(context, true),
              icon: const Icon(Icons.delete_outline),
              label: const Text('Delete'),
            ),
          ],
        ),
      );
      if (yes != true) return;
      try {
        await LocalModelManager.deleteOllamaModel(model);
        final prefs = await SharedPreferences.getInstance();
        if (mounted) {
          setState(() {
            globalProvider = prefs.getString('llm_provider') ?? globalProvider;
            globalLocalModel = prefs.getString('local_model') ?? '';
          });
        }
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$model deleted from Ollama.')),
        );
      } catch (e) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not delete $model: $e')),
        );
      }
    }
  }

'''
s = replace_regex(
    s,
    r"  Future<void> _useRecommendedModel\(String recommendation\) async \{.*?\n  \}\n\n",
    new_recommended,
    'recommended model menu',
)

new_selector = r'''  String _tutorAiLabel(String source) {
    if (source == 'global') return 'System general AI • ${_sourceLabel(globalProvider)}';
    return _sourceLabel(source);
  }

  Future<void> _setTutorAiSource(String source) async {
    final index = tutors.indexWhere((t) => t.id == activeTutorId);
    if (index < 0) return;
    final copy = List<TutorProfile>.from(tutors);
    copy[index] = copy[index].copyWith(modelSource: source);
    if (mounted) setState(() => tutors = copy);
    await _saveTutors();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('${activeTutor.name}: ${_tutorAiLabel(source)}')),
    );
  }

  Future<void> _openQuickAiSelector() async {
    final selected = await showModalBottomSheet<String>(
      context: context,
      builder: (sheetContext) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(8, 12, 8, 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                title: const Text(
                  'Quick AI selector',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 19),
                ),
                subtitle: Text('Choose the AI used by ${activeTutor.name}.'),
              ),
              ListTile(
                leading: const Icon(Icons.settings_suggest_outlined),
                title: const Text('System general AI'),
                subtitle: Text('Follow AI Settings: ${_sourceLabel(globalProvider)}'),
                trailing: activeTutor.modelSource == 'global'
                    ? const Icon(Icons.check_circle)
                    : null,
                onTap: () => Navigator.pop(sheetContext, 'global'),
              ),
              for (final option in const [
                ('gemini', Icons.cloud_outlined, 'Gemini online'),
                ('openai', Icons.public, 'OpenAI / compatible'),
                ('local', Icons.smartphone, 'Ollama / local server'),
                ('device', Icons.memory, 'On-phone GGUF'),
              ])
                ListTile(
                  leading: Icon(option.$2),
                  title: Text(option.$3),
                  trailing: activeTutor.modelSource == option.$1
                      ? const Icon(Icons.check_circle)
                      : null,
                  onTap: () => Navigator.pop(sheetContext, option.$1),
                ),
              const SizedBox(height: 4),
              OutlinedButton.icon(
                onPressed: () {
                  Navigator.pop(sheetContext);
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const LlmSettingsPage()),
                  ).then((_) async {
                    final prefs = await SharedPreferences.getInstance();
                    if (!mounted) return;
                    setState(() {
                      globalProvider = prefs.getString('llm_provider') ?? 'gemini';
                      globalLocalModel = prefs.getString('local_model') ?? '';
                    });
                  });
                },
                icon: const Icon(Icons.tune),
                label: const Text('Full AI settings'),
              ),
            ],
          ),
        ),
      ),
    );
    if (selected != null) await _setTutorAiSource(selected);
  }

'''
s = replace_regex(
    s,
    r"  Future<void> _setGlobalProvider\(String provider\) async \{.*?\n  Future<void> _selectTutor",
    new_selector + "  Future<void> _selectTutor",
    'per tutor quick selector',
)

# Quick selector card + manager/editor wording.
s = s.replace("title: const Text('General tutor AI'),", "title: const Text('Quick AI selector'),", 1)
s = s.replace("subtitle: Text(_sourceLabel(globalProvider)),", "subtitle: Text(_tutorAiLabel(activeTutor.modelSource)),", 1)
s = s.replace(
    "'Memora general AI • ${tutor.guideIds.length} guide(s)'",
    "'${_tutorAiLabel(tutor.modelSource)} • ${tutor.guideIds.length} guide(s)'",
)
s = s.replace(
    "'This tutor uses Memora general AI. You can change it instantly from the quick selector.'",
    "'This tutor uses the system general AI by default. You can override it from the Quick AI selector.'",
)

# Preserve a tutor's quick override when editing its other properties.
s = s.replace(
    "                    modelSource: 'global',",
    "                    modelSource: existing?.modelSource ?? 'global',",
    1,
)

# Grounding helpers and replacement chat request.
new_ask = r'''  bool _isBroadGuideRequest(String value) {
    final text = value.toLowerCase();
    return RegExp(
      r'\b(random|anything|something|any fact|any concept|from the guide|from my guide|de la guía|de mi guía|algo random|algo al azar|cualquier cosa|mencióname algo|menciona algo)\b',
      caseSensitive: false,
    ).hasMatch(text);
  }

  String _randomGuideContext(List<StudyGuide> guides, {int maxChars = 4500}) {
    final usable = guides.where((g) => g.text.trim().isNotEmpty).toList();
    if (usable.isEmpty) return '';
    final rng = Random(DateTime.now().microsecondsSinceEpoch);
    final guide = usable[rng.nextInt(usable.length)];
    final paragraphs = guide.text
        .replaceAll('\r', '')
        .split(RegExp(r'\n{2,}'))
        .map((e) => e.replaceAll(RegExp(r'\s+'), ' ').trim())
        .where((e) => e.length >= 60)
        .toList();
    String body;
    if (paragraphs.isNotEmpty) {
      final start = rng.nextInt(paragraphs.length);
      final buffer = StringBuffer();
      for (var offset = 0; offset < paragraphs.length; offset++) {
        final paragraph = paragraphs[(start + offset) % paragraphs.length];
        if (buffer.isNotEmpty && buffer.length + paragraph.length + 2 > maxChars) break;
        if (buffer.isNotEmpty) buffer.writeln();
        buffer.write(paragraph);
        if (buffer.length >= maxChars) break;
      }
      body = buffer.toString();
    } else {
      final text = guide.text.replaceAll(RegExp(r'\s+'), ' ').trim();
      body = text.length <= maxChars ? text : text.substring(0, maxChars);
    }
    return '=== ${guide.title} [${guide.sourceType}] ===\n$body';
  }

  String _groundedFallback(String context) {
    final clean = context
        .split('\n')
        .where((line) => !line.trim().startsWith('==='))
        .join(' ')
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();
    if (clean.isEmpty) return 'I could not find that in the assigned guides.';
    final sentences = clean
        .split(RegExp(r'(?<=[.!?])\s+'))
        .map((e) => e.trim())
        .where((e) => e.length >= 45)
        .toList();
    final fact = sentences.isNotEmpty
        ? sentences.first
        : (clean.length <= 340 ? clean : '${clean.substring(0, 340)}…');
    return 'One concrete point from the assigned guide is: $fact';
  }

  bool _looksLikeEcho(String question, String result) {
    String key(String value) => value
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-z0-9áéíóúüñ]+'), ' ')
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();
    final qKey = key(question);
    final rKey = key(result);
    if (qKey.isEmpty || rKey.isEmpty) return false;
    if (qKey == rKey) return true;
    if (rKey.length <= (qKey.length * 1.35) &&
        (rKey.contains(qKey) || qKey.contains(rKey))) return true;
    final words = rKey.split(' ').where((e) => e.isNotEmpty).toList();
    if (words.length >= 8 && words.toSet().length / words.length < .38) return true;
    return false;
  }

  Future<void> _finishGroundedReply(
    ChatSession pending,
    String text,
    int token, {
    bool notify = true,
  }) async {
    _updateAssistantBubble(pending.id, text, token);
    final finished = _chatById(pending.id);
    if (finished != null) await ChatStore.save(finished);
    if (notify) {
      final body = text.length <= 150 ? text : '${text.substring(0, 150)}…';
      await CompletionNotificationService.show(
        title: '${activeTutor.name} replied',
        body: body,
      );
    }
  }

  Future<void> _ask() async {
    final question = q.text.trim();
    final guides = activeGuides;
    final attachments = _extrasKey.currentState?.attachments ?? const <QueryAttachment>[];
    if ((question.isEmpty && attachments.isEmpty) || busy) return;
    if (guides.isEmpty && attachments.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Assign a guide or attach a PDF, photo, or screenshot before asking.')),
      );
      return;
    }
    final current = _activeChat;
    if (current == null) return;

    final token = ++_turnToken;
    _cancelRequested = false;
    final history = _conversationHistory();
    final shownQuestion = question.isEmpty ? 'Analyze the attached content.' : question;
    final attachmentNames = attachments.map((a) => a.name).toList();
    final now = DateTime.now();
    final title = current.messages.isEmpty
        ? ChatSession.titleFrom(
            shownQuestion,
            fallback: attachmentNames.isEmpty ? 'New chat' : attachmentNames.first,
          )
        : current.title;
    final pending = current.copyWith(
      title: title,
      updatedAt: now,
      messages: [
        ...current.messages,
        ChatMessage(role: 'user', text: shownQuestion, createdAt: now, attachments: attachmentNames),
        ChatMessage(role: 'assistant', text: '', createdAt: now),
      ],
    );
    _putChat(pending);
    await ChatStore.save(pending);
    q.clear();
    if (mounted) setState(() => busy = true);

    try {
      final tutor = activeTutor;
      final limits = _retrievalLimits();
      final attachmentText = QueryAttachmentService.buildTextContext(attachments);
      final broad = _isBroadGuideRequest(shownQuestion) && attachments.isEmpty;
      final context = broad
          ? _randomGuideContext(guides, maxChars: limits.$1)
          : KnowledgeRetriever.buildContext(
              guides: guides,
              query: '$question\n$attachmentText',
              maxChars: limits.$1,
              maxChunks: limits.$2,
              allowUnmatchedFallback: false,
            );
      final attachmentContext = QueryAttachmentService.buildTextContext(
        attachments,
        maxChars: responseMode == 'fast' ? 4500 : responseMode == 'deep' ? 10000 : 7000,
      );
      final imagePaths = <String>[
        ...guides
            .where((g) => g.sourceType == 'image' && g.filePath != null)
            .map((g) => g.filePath!)
            .take(3),
        ...QueryAttachmentService.imagePaths(attachments),
      ].take(4).toList();

      final noEvidence = context.startsWith('(No matching evidence found');
      if (noEvidence && attachmentContext.isEmpty && imagePaths.isEmpty) {
        await _finishGroundedReply(
          pending,
          'I could not find that in the assigned guides.',
          token,
        );
        if (mounted) _extrasKey.currentState?.clearAttachments();
        return;
      }

      final sourceRule = broad
          ? 'The user asked for a random point. Choose ONE meaningful fact or concept explicitly present in SOURCE EVIDENCE and explain it. Do not repeat the user request.'
          : 'Answer only when SOURCE EVIDENCE or CURRENT ATTACHMENTS explicitly support the answer.';

      final result = await AiService.askConfigured(
        providerOverride: tutor.modelSource == 'global' ? 'global' : tutor.modelSource,
        responseMode: responseMode,
        imagePaths: imagePaths,
        taskHint: shownQuestion,
        onPartial: (partial) {
          if (partial.isNotEmpty) _updateAssistantBubble(pending.id, partial, token);
        },
        prompt: '''You are ${tutor.name}, one of Memora's tutors.
YOUR STYLE: ${tutor.description}
INSTRUCTIONS: ${tutor.instructions}

STRICT SOURCE RULES:
- $sourceRule
- Never invent a fact that is not supported by SOURCE EVIDENCE or CURRENT ATTACHMENTS.
- If the answer is not explicitly supported, reply exactly: I could not find that in the assigned guides.
- Do not echo or restate the user's request as the answer.
- Do not manufacture a definition for an isolated word.
- Prefer a concrete concept, relationship, formula, cause/effect, comparison, or application from the source.
- Keep the conversation natural and use the history only for conversational continuity, never as evidence that overrides the guides.
- Answer in the language of the assigned guide unless the user explicitly asks for another language.

CONVERSATION HISTORY:
$history

SOURCE EVIDENCE FROM ASSIGNED GUIDES:
$context

CURRENT ATTACHMENTS:
${attachmentContext.isEmpty ? '(No temporary attachments)' : attachmentContext}

CURRENT USER MESSAGE:
$shownQuestion''',
      );
      if (token != _turnToken || _cancelRequested) return;

      var finalResult = result.trim();
      if (finalResult.isEmpty || _looksLikeEcho(shownQuestion, finalResult)) {
        finalResult = broad
            ? _groundedFallback(context)
            : 'I could not find that in the assigned guides.';
      }
      await _finishGroundedReply(
        pending,
        finalResult,
        token,
        notify: !AiService.looksLikeTask(shownQuestion),
      );
      if (mounted) {
        setState(() => accelerationLabel = AiService.localAccelerationLabel);
        _extrasKey.currentState?.clearAttachments();
      }
    } catch (e) {
      if (token != _turnToken || _cancelRequested) return;
      final text = 'I could not consult ${_tutorAiLabel(activeTutor.modelSource)}: ${AiService.userFacingError(e)}';
      _updateAssistantBubble(pending.id, text, token);
      final failed = _chatById(pending.id);
      if (failed != null) await ChatStore.save(failed);
    } finally {
      if (mounted && token == _turnToken) setState(() => busy = false);
    }
  }

'''
s = replace_regex(
    s,
    r"  Future<void> _ask\(\) async \{.*?\n  \}\n\n  Future<TutorProfile\?> _editTutorDialog",
    new_ask + "  Future<TutorProfile?> _editTutorDialog",
    'grounded tutor chat',
)

p.write_text(s)

# TutorContextService must honor the saved per-tutor quick override rather than
# forcing all profiles back to global at read time.
p = Path('lib/tutor_context_service.dart')
s = p.read_text()
factory_anchor = """      emoji: json['emoji']?.toString() ?? '🧠',
      modelSource: 'global',
      guideIds:"""
factory_new = """      emoji: json['emoji']?.toString() ?? '🧠',
      modelSource: json['modelSource']?.toString() ?? 'global',
      guideIds:"""
if factory_anchor not in s:
    raise RuntimeError('TutorContext forced-global factory anchor not found')
s = s.replace(factory_anchor, factory_new, 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# AI Settings: central model-management/delete page.
# -----------------------------------------------------------------------------
p = Path('lib/llm_settings_page.dart')
s = p.read_text()
if "import 'model_manager_page.dart';\n" not in s:
    if "import 'fast_model_setup_page.dart';\n" not in s:
        raise RuntimeError('AI settings fast model import anchor not found')
    s = s.replace(
        "import 'fast_model_setup_page.dart';\n",
        "import 'fast_model_setup_page.dart';\nimport 'model_manager_page.dart';\n",
        1,
    )

method_anchor = "  Future<void> _openFastModelSetup() async {"
manager_method = r'''  Future<void> _openModelManager() async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const ModelManagerPage()),
    );
    if (!mounted) return;
    await _load();
  }

'''
if method_anchor not in s:
    raise RuntimeError('AI settings model method anchor not found')
if "Future<void> _openModelManager()" not in s:
    s = s.replace(method_anchor, manager_method + method_anchor, 1)

ui_anchor = "                  if (provider == 'device') ...[\n"
manage_card = """                  Card(
                    child: ListTile(
                      leading: const Icon(Icons.storage_outlined),
                      title: const Text('Manage / delete downloaded models'),
                      subtitle: const Text('View private GGUF and Ollama models stored for Memora.'),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: _openModelManager,
                    ),
                  ),
                  const SizedBox(height: 12),
"""
if ui_anchor not in s:
    raise RuntimeError('AI settings device UI anchor not found')
if "Manage / delete downloaded models" not in s:
    s = s.replace(ui_anchor, manage_card + ui_anchor, 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# Daily exam: stopwatch is informational only. AI mode waits for the AI and does
# not silently replace its output with indexed/generic cards.
# -----------------------------------------------------------------------------
p = Path('lib/daily_exam_page.dart')
s = p.read_text()

new_build_exam = r'''  Future<TutorExamSession> _buildExam({
    required TutorContextProfile tutor,
    required int count,
    required String difficulty,
    required String generatorMode,
    required bool daily,
  }) async {
    final guides = TutorContextService.guidesFor(widget.store, tutor);
    if (guides.isEmpty) {
      throw Exception('${tutor.name} does not have assigned material for an exam yet.');
    }

    final recentQuestions = _recentQuestions(tutor.id);
    var questions = <ExamQuestionData>[];
    var generatorLabel = 'Instant • indexed content';

    if (generatorMode == 'instant') {
      questions = _cardQuestions(
        guides,
        count,
        avoidQuestions: recentQuestions,
      );
    } else {
      String? provider;
      if (generatorMode == 'best') {
        provider = await TutorContextService.bestAvailableProvider();
        if (provider == null) {
          throw Exception('No configured AI is currently available for this exam.');
        }
        generatorLabel = 'Best available AI • ${TutorContextService.sourceLabel(provider)}';
      } else {
        provider = tutor.modelSource;
        generatorLabel = '${tutor.name} • ${TutorContextService.sourceLabel(provider)}';
      }

      final prefs = await SharedPreferences.getInstance();
      final resolvedProvider = provider == 'global'
          ? (prefs.getString('llm_provider') ?? 'gemini')
          : provider;
      final localish = resolvedProvider == 'private' ||
          resolvedProvider == 'shared' ||
          resolvedProvider == 'device' ||
          resolvedProvider == 'local' ||
          resolvedProvider == 'ollama';
      final requested = count + (count >= 10 ? 4 : 2);
      final content = TutorContextService.contentForGuides(
        guides,
        maxChars: localish ? 6500 : 18000,
      );

      final raw = await AiService.askTaskConfigured(
        providerOverride: provider,
        responseMode: localish ? 'normal' : 'deep',
        prompt: '''Create $requested high-quality exam questions using ONLY the assigned material for ${tutor.name}.
Difficulty: $difficulty.

RULES:
- Test actual understanding, application, cause/effect, comparison, decision-making, formulas, or calculations when the source supports them.
- Do NOT create vocabulary trivia from isolated words.
- Do NOT ask generic questions such as "What does X mean?" unless X is explicitly defined as a technical concept in the source.
- Each question must be answerable from the supplied content alone.
- Every item MUST include an evidence field copied exactly from the supplied content that supports the answer.
- Keep answers complete enough to grade; never use sentence fragments such as "part of the career".
- Avoid repeating recent questions listed below.
- Return ONLY a valid JSON array with no Markdown.
- Exact object format: {"question":"...","answer":"...","evidence":"exact supporting text","source":"guide or topic"}.

RECENT QUESTIONS TO AVOID:
${recentQuestions.take(18).map((q) => '- $q').join('\n')}

ASSIGNED CONTENT:
$content''',
      );
      questions = _parseAiQuestions(
        raw,
        content: content,
        guides: guides,
        avoidQuestions: recentQuestions,
      );
      if (questions.isEmpty) {
        throw Exception(
          'The AI did not return any valid grounded exam questions. Memora did not replace them with generic questions.',
        );
      }
      if (questions.length > count) questions = questions.take(count).toList();
      if (questions.length < count) {
        generatorLabel = '$generatorLabel • ${questions.length}/$count validated questions';
      }
    }

    if (questions.isEmpty) {
      throw Exception('I could not create valid questions from the assigned material.');
    }

    final now = DateTime.now();
    return TutorExamSession(
      id: 'exam_${now.microsecondsSinceEpoch}',
      tutorId: tutor.id,
      tutorName: tutor.name,
      tutorEmoji: tutor.emoji,
      createdAt: now,
      dateKey: daily ? today : '',
      isDaily: daily,
      difficulty: difficulty,
      generatorLabel: generatorLabel,
      questions: questions,
    );
  }

'''
s = replace_regex(
    s,
    r"  Future<TutorExamSession> _buildExam\(\{.*?\n  \}\n\n  Future<void> _openExam",
    new_build_exam + "  Future<void> _openExam",
    'wait-for-AI exam builder',
)

# Remove obsolete timeout explanations left by v1.13/v1.18.
s = s.replace(
    'The AI writes part of the exam and Memora completes the rest with verified tutor content. The AI has a 20-second limit; after that the exam finishes automatically without waiting longer.',
    'When an AI generator is selected, Memora waits for that AI. The stopwatch only shows how long generation is taking; it does not force a fallback to indexed questions.',
)
s = s.replace(
    'La IA redacta una parte y Memora completa el resto con contenido verificado del tutor. La IA tiene un máximo de 20 segundos; después el examen termina automáticamente sin seguir esperando.',
    'When an AI generator is selected, Memora waits for that AI. The stopwatch only shows how long generation is taking; it does not force a fallback to indexed questions.',
)
# Any now-unreachable 20-second generator-label strings are harmless, but keep
# the UI clean if they remain after older patches.
s = s.replace(' • 20 s limit; completed with verified content', '')
s = s.replace(' • límite 20 s; completado con contenido verificado', '')
p.write_text(s)

# -----------------------------------------------------------------------------
# Study plan: selectable depth, including a much more detailed mode.
# -----------------------------------------------------------------------------
p = Path('lib/study_plan_page.dart')
s = p.read_text()

state_anchor = "  String intensity = 'Normal';\n"
if state_anchor not in s:
    # English-only migration keeps the internal value names in some builds.
    state_anchor = "  String intensity = 'Normal';\n"
if state_anchor not in s:
    raise RuntimeError('Study plan intensity state anchor not found')
s = s.replace(state_anchor, state_anchor + "  String planDepth = 'standard';\n", 1)

helper_anchor = "  static bool _isLocalPlanProvider(String provider) {"
plan_helpers = r'''  String _planDepthLabel() {
    switch (planDepth) {
      case 'concise':
        return 'Concise';
      case 'detailed':
        return 'Detailed';
      case 'maximum':
        return 'Maximum depth';
      default:
        return 'Standard';
    }
  }

  String _planDepthPrompt() {
    switch (planDepth) {
      case 'concise':
        return 'Keep the plan compact: major phases, daily focus, review cadence, and advancement criteria.';
      case 'detailed':
        return '''Make the plan substantially detailed. For each phase/week, specify daily objectives, exact study blocks, approximate minutes per activity, active-recall tasks, practice problems, spaced reviews, checkpoints, and what evidence of mastery is required before advancing.''';
      case 'maximum':
        return '''Create an extremely detailed operational learning plan. Break the material into ordered phases, weeks, and daily sessions. For each session specify exact objective, source/topic, approximate minutes, learning action, retrieval practice, application exercise, review items, expected output, mastery criterion, and what to do if the criterion is missed. Include weekly cumulative tests, spaced-repetition intervals, monthly milestones, dependency/prerequisite order, catch-up rules, and a concrete progression path. Do not pad with generic motivational text.''';
      default:
        return 'Create a practical, structured plan with concrete daily actions, reviews, tests, milestones, and clear advancement criteria.';
    }
  }

  String _planResponseMode() {
    switch (planDepth) {
      case 'concise':
        return 'fast';
      case 'detailed':
      case 'maximum':
        return 'deep';
      default:
        return 'normal';
    }
  }

'''
if helper_anchor not in s:
    raise RuntimeError('Study plan helper anchor not found')
if "String _planDepthLabel()" not in s:
    s = s.replace(helper_anchor, plan_helpers + helper_anchor, 1)

# Add depth requirements to the final English prompt. Fall back to the Spanish
# anchor in case a future migration changes ordering.
if "\nInclude:\n" in s:
    s = s.replace(
        "\nInclude:\n",
        "\nPlan depth: ${_planDepthLabel()}.\nDEPTH REQUIREMENTS:\n${_planDepthPrompt()}\n\nInclude:\n",
        1,
    )
elif "\nIncluye:\n" in s:
    s = s.replace(
        "\nIncluye:\n",
        "\nPlan depth: ${_planDepthLabel()}.\nDEPTH REQUIREMENTS:\n${_planDepthPrompt()}\n\nIncluye:\n",
        1,
    )
else:
    raise RuntimeError('Study plan prompt include anchor not found')

# Only the plan generation AI call should use the selected output depth.
call_index = s.find('AiService.askTaskConfigured(')
if call_index < 0:
    raise RuntimeError('Study plan task AI call not found')
mode_index = s.find("responseMode: 'normal',", call_index)
if mode_index < 0:
    raise RuntimeError('Study plan response mode anchor not found')
s = s[:mode_index] + s[mode_index:].replace(
    "responseMode: 'normal',",
    "responseMode: _planResponseMode(),",
    1,
)

# Add depth selector immediately after Intensity dropdown.
intensity_pattern = re.compile(
    r"(                  DropdownButtonFormField<String>\(\n"
    r"                    initialValue: intensity,.*?"
    r"decoration: const InputDecoration\(labelText: 'Intensity'\),\n"
    r"                  \),\n)",
    re.S,
)
match = intensity_pattern.search(s)
if not match:
    # Some builds still contain the pre-translation label at this point.
    intensity_pattern = re.compile(
        r"(                  DropdownButtonFormField<String>\(\n"
        r"                    initialValue: intensity,.*?"
        r"decoration: const InputDecoration\(labelText: 'Intensidad'\),\n"
        r"                  \),\n)",
        re.S,
    )
    match = intensity_pattern.search(s)
if not match:
    raise RuntimeError('Study plan intensity dropdown block not found')

depth_ui = r'''                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: planDepth,
                    decoration: const InputDecoration(
                      labelText: 'Plan depth',
                      prefixIcon: Icon(Icons.account_tree_outlined),
                    ),
                    items: const [
                      DropdownMenuItem(value: 'concise', child: Text('Concise')),
                      DropdownMenuItem(value: 'standard', child: Text('Standard')),
                      DropdownMenuItem(value: 'detailed', child: Text('Detailed')),
                      DropdownMenuItem(value: 'maximum', child: Text('Maximum depth')),
                    ],
                    onChanged: busy ? null : (value) => setState(() => planDepth = value ?? 'standard'),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    planDepth == 'maximum'
                        ? 'Maximum depth creates a session-by-session plan with time blocks, mastery criteria, catch-up rules, tests, and spaced reviews.'
                        : planDepth == 'detailed'
                            ? 'Detailed adds daily objectives, time allocation, retrieval practice, checkpoints, and mastery criteria.'
                            : planDepth == 'concise'
                                ? 'Concise keeps only the essential schedule and milestones.'
                                : 'Standard balances detail and speed.',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
'''
s = s[:match.end()] + depth_ui + s[match.end():]

# Include selected depth in exported plan metadata when the v1.12 PDF helper is present.
for old in (
    "Intensity: $intensity\n",
    "Intensidad: $intensity\n",
):
    if old in s:
        s = s.replace(old, old + "Plan depth: ${_planDepthLabel()}\n", 1)
        break

p.write_text(s)

print('Memora v1.21 tutor grounding, per-tutor AI, exam wait, plan depth and model management applied successfully')
