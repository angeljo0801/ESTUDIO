from pathlib import Path
import re

# Memora v1.22
# - AI-only study cards, default target 50, using the system AI (including Ollama/GGUF).
# - One-time removal of legacy parser cards and no automatic regex-card rebuilds.
# - System AI/model labels stay synchronized with AI Settings.
# - Tutor grounding gets a broader second retrieval pass instead of failing too early.
# - AI exams generate in validated batches and keep good batches while retrying missing items.
# - English cleanup for the screens touched by recent patches.


def required(text, old, new, label, count=1):
    if old not in text:
        raise RuntimeError(f'Pattern not found for {label}')
    return text.replace(old, new, count)


def regex_required(text, pattern, replacement, label):
    out, n = re.subn(pattern, lambda _m: replacement, text, count=1, flags=re.S)
    if n != 1:
        raise RuntimeError(f'Pattern not found for {label}: {n}')
    return out


def replace_all(path, pairs):
    p = Path(path)
    s = p.read_text()
    for old, new in pairs:
        s = s.replace(old, new)
    p.write_text(s)


# -----------------------------------------------------------------------------
# New guides never receive parser/regex cards. AI generation owns study cards.
# -----------------------------------------------------------------------------
p = Path('lib/study_engine.dart')
s = p.read_text()
s = required(
    s,
    '      cards: buildCards(clean),',
    '      cards: const [],',
    'StudyEngine AI-only guide cards',
)
p.write_text(s)


# -----------------------------------------------------------------------------
# GuideStore: one-time removal of all pre-v1.22 generated cards. Do not rebuild
# empty guides from StudyEngine; empty means "waiting for the configured AI".
# -----------------------------------------------------------------------------
p = Path('lib/guide_store.dart')
s = p.read_text()
import_anchor = "import 'package:path_provider/path_provider.dart';\n"
if "shared_preferences.dart" not in s:
    s = required(
        s,
        import_anchor,
        import_anchor + "import 'package:shared_preferences/shared_preferences.dart';\n",
        'GuideStore SharedPreferences import',
    )

migration = """      final prefs = await SharedPreferences.getInstance();
      var repaired = false;
      final migratedToAiCards = prefs.getBool('memora_ai_cards_v1_migrated') ?? false;
      if (!migratedToAiCards) {
        for (final guide in guides) {
          if (guide.cards.isNotEmpty) {
            guide.cards = <StudyCard>[];
            repaired = true;
          }
        }
        await prefs.setBool('memora_ai_cards_v1_migrated', true);
      }

      guides.sort"""
s = regex_required(
    s,
    r"      var repaired = false;\n      for \(final guide in guides\) \{.*?\n      \}\n\n      guides\.sort",
    migration,
    'GuideStore one-time AI card migration',
)
p.write_text(s)


# -----------------------------------------------------------------------------
# Retrieval: add light morphological matching and a coverage fallback that samples
# the assigned guide(s) evenly when the user's wording does not share exact words.
# -----------------------------------------------------------------------------
p = Path('lib/knowledge_retriever.dart')
s = p.read_text()
old_score = """        for (final term in terms) {
          if (title.contains(term)) score += 3;
          final matches = term.allMatches(lower).length;
          if (matches > 0) score += 1 + matches.clamp(0, 4).toDouble();
        }
"""
new_score = """        final chunkWords = RegExp(r'[a-záéíóúüñ0-9]{3,}')
            .allMatches(lower)
            .map((m) => m.group(0)!)
            .toSet();
        for (final term in terms) {
          if (title.contains(term)) score += 3;
          final matches = term.allMatches(lower).length;
          if (matches > 0) {
            score += 1 + matches.clamp(0, 4).toDouble();
          } else if (term.length >= 5) {
            final prefix = term.substring(0, 5);
            if (chunkWords.any((word) => word.length >= 5 && word.startsWith(prefix))) {
              score += .8;
            }
          }
        }
"""
s = required(s, old_score, new_score, 'KnowledgeRetriever fuzzy term scoring')
coverage_anchor = "  static List<String> _chunk(String text, int size) {\n"
coverage_method = r'''  static String buildCoverageContext({
    required List<StudyGuide> guides,
    int maxChars = 7000,
    int maxChunks = 7,
  }) {
    final candidates = <_Chunk>[];
    for (final guide in guides) {
      final normalized = guide.text.replaceAll('\r\n', '\n').trim();
      if (normalized.isEmpty) continue;
      final parts = _chunk(normalized, 900);
      if (parts.isEmpty) continue;
      final take = maxChunks.clamp(1, parts.length).toInt();
      if (take == 1) {
        candidates.add(_Chunk(guide: guide, text: parts.first, score: 1));
      } else {
        for (var i = 0; i < take; i++) {
          final index = ((parts.length - 1) * i / (take - 1)).round();
          candidates.add(_Chunk(guide: guide, text: parts[index], score: 1));
        }
      }
    }
    if (candidates.isEmpty) return '(The assigned guides contain no usable text)';

    final out = StringBuffer();
    var used = 0;
    for (final chunk in candidates.take(maxChunks)) {
      final header = '\n=== ${chunk.guide.title} [${chunk.guide.sourceType}] ===\n';
      final remaining = maxChars - used - header.length;
      if (remaining <= 180) break;
      final body = chunk.text.length <= remaining
          ? chunk.text
          : chunk.text.substring(0, remaining);
      out.write(header);
      out.write(body);
      used += header.length + body.length;
      if (used >= maxChars) break;
    }
    return out.toString().trim();
  }

'''
if "static String buildCoverageContext" not in s:
    s = required(s, coverage_anchor, coverage_method + coverage_anchor, 'coverage retrieval helper')
p.write_text(s)


# -----------------------------------------------------------------------------
# Home/Library: automatically ask the configured system AI for 50 cards after a
# new guide is imported, pasted, photographed, or merged. No model => no fake cards.
# -----------------------------------------------------------------------------
p = Path('lib/home_page.dart')
s = p.read_text()
if "ai_card_service.dart" not in s:
    s = required(
        s,
        "import 'guide_creator_page.dart';\n",
        "import 'ai_card_service.dart';\nimport 'completion_notification_service.dart';\nimport 'guide_creator_page.dart';\n",
        'Home AI-card imports',
    )
state_anchor = "  bool _busy = false;\n"
s = required(
    s,
    state_anchor,
    state_anchor + "  String _busyMessage = 'Processing…';\n",
    'Home busy message state',
)
helper_anchor = "  Future<void> _importFile() async {\n"
home_helper = r'''  Future<void> _generateCardsFor(StudyGuide guide) async {
    final systemAi = await AiCardService.systemAi();
    if (!systemAi.ready) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Guide imported. Study cards are pending until a system AI/model is configured.',
          ),
        ),
      );
      return;
    }

    if (mounted) {
      setState(() {
        _busy = true;
        _busyMessage = 'Generating AI cards… 0/${AiCardService.defaultTarget}';
      });
    }
    try {
      final cards = await AiCardService.generateCards(
        guide,
        target: AiCardService.defaultTarget,
        onProgress: (generated, target) {
          if (!mounted) return;
          setState(() => _busyMessage = 'Generating AI cards… $generated/$target');
        },
      );
      guide.cards = cards;
      await widget.store.update(guide);
      await CompletionNotificationService.show(
        title: 'Study cards ready',
        body: '${guide.title}: ${cards.length} AI-generated cards with ${systemAi.label}.',
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${cards.length} AI study cards created with ${systemAi.label}.')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'The guide was imported, but cards are still pending: ${AiService.userFacingError(e)}',
          ),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
          _busyMessage = 'Processing…';
        });
      }
    }
  }

'''
# Home already indirectly imports AiService in older builds only through other pages;
# add it explicitly for user-facing errors.
if "import 'ai_service.dart';" not in s:
    s = required(s, "import 'ai_card_service.dart';\n", "import 'ai_card_service.dart';\nimport 'ai_service.dart';\n", 'Home AiService import')
if "Future<void> _generateCardsFor" not in s:
    s = required(s, helper_anchor, home_helper + helper_anchor, 'Home card-generation helper')

# Every normal guide variable added from Home should get AI cards. v1.4 also adds
# image/OCR guides using the same variable name.
s = s.replace(
    "      await widget.store.add(guide);\n",
    "      await widget.store.add(guide);\n      await _generateCardsFor(guide);\n",
)
s = s.replace(
    "    await widget.store.add(guide);\n",
    "    await widget.store.add(guide);\n    await _generateCardsFor(guide);\n",
)
s = s.replace(
    "    await widget.store.add(merged);\n",
    "    await widget.store.add(merged);\n    await _generateCardsFor(merged);\n",
    1,
)
# Avoid duplicate insertion if indentation variants overlapped.
s = s.replace("await _generateCardsFor(guide);\n      await _generateCardsFor(guide);", "await _generateCardsFor(guide);")
s = s.replace("await _generateCardsFor(guide);\n    await _generateCardsFor(guide);", "await _generateCardsFor(guide);")

s = s.replace(
    "label: Text(_busy ? 'Processing…' : 'Add / create'),",
    "label: Text(_busy ? _busyMessage : 'Add / create'),",
)
p.write_text(s)


# -----------------------------------------------------------------------------
# Guide detail: regeneration is now AI-only, targets 50, and empty migrated guides
# automatically start generation when a configured model is ready.
# -----------------------------------------------------------------------------
p = Path('lib/guide_detail_page.dart')
s = p.read_text()
if "ai_card_service.dart" not in s:
    s = required(
        s,
        "import 'guide_file_service.dart';\n",
        "import 'ai_card_service.dart';\nimport 'ai_service.dart';\nimport 'completion_notification_service.dart';\nimport 'guide_file_service.dart';\n",
        'Guide detail AI-card imports',
    )
class_anchor = "class _GuideDetailPageState extends State<GuideDetailPage> {\n"
state_block = r'''class _GuideDetailPageState extends State<GuideDetailPage> {
  bool _generatingCards = false;
  int _cardProgress = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _autoGenerateCards());
  }

  Future<void> _autoGenerateCards() async {
    if (!mounted || widget.guide.cards.isNotEmpty || _generatingCards) return;
    final ai = await AiCardService.systemAi();
    if (!ai.ready || !mounted) return;
    await _regenerate(automatic: true);
  }

'''
s = required(s, class_anchor, state_block, 'Guide detail card state')
new_regenerate = r'''  Future<void> _regenerate({bool automatic = false}) async {
    if (_generatingCards) return;
    final ai = await AiCardService.systemAi();
    if (!ai.ready) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Configure a system AI/model before generating study cards.'),
        ),
      );
      return;
    }
    setState(() {
      _generatingCards = true;
      _cardProgress = 0;
    });
    try {
      final cards = await AiCardService.generateCards(
        widget.guide,
        target: AiCardService.defaultTarget,
        onProgress: (generated, _) {
          if (mounted) setState(() => _cardProgress = generated);
        },
      );
      setState(() => widget.guide.cards = cards);
      await _save();
      await CompletionNotificationService.show(
        title: 'Study cards ready',
        body: '${widget.guide.title}: ${cards.length} cards generated with ${ai.label}.',
      );
      if (!mounted || automatic) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${cards.length} AI study cards generated.')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Card generation failed: ${AiService.userFacingError(e)}')),
      );
    } finally {
      if (mounted) setState(() => _generatingCards = false);
    }
  }

'''
s = regex_required(
    s,
    r"  Future<void> _regenerate\(\) async \{.*?\n  \}\n\n  Future<void> _export",
    new_regenerate + "  Future<void> _export",
    'Guide detail AI regenerate method',
)
s = s.replace("Text('Regenerate questions')", "Text('Regenerate 50 AI cards')")
# Insert a visible generation control after the translation button added in v1.19.
card_ui_anchor = """          const SizedBox(height: 12),
          Row(
            children: [
"""
card_ui = """          const SizedBox(height: 12),
          if (_generatingCards || guide.cards.isEmpty) ...[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _generatingCards
                          ? 'Generating study cards… $_cardProgress/${AiCardService.defaultTarget}'
                          : 'No AI-generated study cards yet.',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 10),
                    if (_generatingCards)
                      LinearProgressIndicator(
                        value: (_cardProgress / AiCardService.defaultTarget).clamp(0.0, 1.0),
                      )
                    else
                      FilledButton.icon(
                        onPressed: () => _regenerate(),
                        icon: const Icon(Icons.auto_awesome_rounded),
                        label: const Text('Generate 50 AI cards'),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
          ],
          Row(
            children: [
"""
# v1.19 inserted Translate guide before this first stats row. Use last occurrence
# near stats by replacing the first exact post-translation occurrence if available.
if card_ui_anchor in s:
    s = s.replace(card_ui_anchor, card_ui, 1)
p.write_text(s)


# -----------------------------------------------------------------------------
# AI-created guides and translated guides also receive system-AI cards. Card
# failure must never delete or invalidate an otherwise successfully-created file.
# -----------------------------------------------------------------------------
for filename, variable in [
    ('lib/guide_creator_page.dart', 'guide'),
    ('lib/guide_translation_page.dart', 'translatedGuide'),
]:
    p = Path(filename)
    s = p.read_text()
    if "ai_card_service.dart" not in s:
        s = required(
            s,
            "import 'ai_service.dart';\n",
            "import 'ai_card_service.dart';\nimport 'ai_service.dart';\n",
            f'{filename} AI-card import',
        )
    add_line = f"      await widget.store.add({variable});\n"
    generation = f"""      await widget.store.add({variable});
      try {{
        final systemAi = await AiCardService.systemAi();
        if (systemAi.ready) {{
          final cards = await AiCardService.generateCards(
            {variable},
            target: AiCardService.defaultTarget,
          );
          {variable}.cards = cards;
          await widget.store.update({variable});
        }}
      }} catch (_) {{
        // The guide/file remains valid; cards can be generated later from its detail page.
      }}
"""
    s = required(s, add_line, generation, f'{filename} post-create AI cards')
    p.write_text(s)


# -----------------------------------------------------------------------------
# Best-available ordering respects the user's configured System AI first.
# -----------------------------------------------------------------------------
p = Path('lib/tutor_context_service.dart')
s = p.read_text()
priority_anchor = "    return providers;\n  }\n\n  static Future<String?> bestAvailableProvider()"
priority = """    final selected = (prefs.getString('llm_provider') ?? '').trim();
    var preferred = selected;
    if (selected == 'ollama') preferred = 'local';
    if (selected == 'device') {
      preferred = preferredMode == 'shared' ? 'shared' : 'private';
    }
    if (providers.remove(preferred)) providers.insert(0, preferred);

    return providers;
  }

  static Future<String?> bestAvailableProvider()"""
s = required(s, priority_anchor, priority, 'System AI priority in best available')
p.write_text(s)


# -----------------------------------------------------------------------------
# Tutor UI: show the exact system provider/model, refresh after AI Settings,
# broaden grounding before saying "not found", and make Fast genuinely concise.
# -----------------------------------------------------------------------------
p = Path('lib/tutor_page.dart')
s = p.read_text()
if "ai_card_service.dart" not in s:
    s = required(
        s,
        "import 'ai_service.dart';\n",
        "import 'ai_card_service.dart';\nimport 'ai_service.dart';\n",
        'Tutor system-AI import',
    )
state_anchor = "  String globalProvider = 'gemini';\n"
s = required(
    s,
    state_anchor,
    state_anchor + "  String systemAiDisplay = 'Gemini • 2.5 Flash';\n",
    'Tutor exact system AI state',
)
load_anchor = "    globalProvider = prefs.getString('llm_provider') ?? 'gemini';\n"
s = required(
    s,
    load_anchor,
    load_anchor + "    systemAiDisplay = (await AiCardService.systemAi()).label;\n",
    'Tutor system AI load',
)
label_anchor = "  String _tutorAiLabel(String source) {\n"
refresh_method = r'''  Future<void> _refreshSystemAi() async {
    final prefs = await SharedPreferences.getInstance();
    final descriptor = await AiCardService.systemAi();
    if (!mounted) return;
    setState(() {
      globalProvider = prefs.getString('llm_provider') ?? 'gemini';
      globalLocalModel = prefs.getString('local_model') ?? '';
      systemAiDisplay = descriptor.label;
    });
  }

'''
if "Future<void> _refreshSystemAi()" not in s:
    s = required(s, label_anchor, refresh_method + label_anchor, 'Tutor system AI refresh helper')
s = s.replace(
    "if (source == 'global') return 'System general AI • ${_sourceLabel(globalProvider)}';",
    "if (source == 'global') return 'System general AI • $systemAiDisplay';",
)
s = s.replace(
    "subtitle: Text('Follow AI Settings: ${_sourceLabel(globalProvider)}'),",
    "subtitle: Text('Follow AI Settings: $systemAiDisplay'),",
)
s = s.replace(
    "  Future<void> _openQuickAiSelector() async {\n    final selected =",
    "  Future<void> _openQuickAiSelector() async {\n    await _refreshSystemAi();\n    if (!mounted) return;\n    final selected =",
    1,
)
# The top-right AI Settings button must refresh the Tutor screen when it returns.
old_settings = """            IconButton(
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const LlmSettingsPage()),
              ),
              icon: const Icon(Icons.tune),
            ),
"""
new_settings = """            IconButton(
              onPressed: () async {
                await Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const LlmSettingsPage()),
                );
                await _refreshSystemAi();
              },
              icon: const Icon(Icons.tune),
            ),
"""
if old_settings in s:
    s = s.replace(old_settings, new_settings, 1)

# Recommended model actions already save llm_provider=local. Keep the label exact
# immediately instead of waiting for a full reload.
s = s.replace(
    "globalLocalModel = model;\n",
    "globalLocalModel = model;\n            systemAiDisplay = 'Ollama • $model';\n",
)

# Strict first retrieval, then evenly-sampled guide coverage before refusing.
s = s.replace(
    "      final context = broad\n",
    "      var context = broad\n",
    1,
)
coverage_insert_anchor = """            );
      final attachmentContext = QueryAttachmentService.buildTextContext(
"""
coverage_insert = """            );
      if (!broad && context.startsWith('(No matching evidence found')) {
        context = KnowledgeRetriever.buildCoverageContext(
          guides: guides,
          maxChars: limits.$1,
          maxChunks: limits.$2,
        );
      }
      final attachmentContext = QueryAttachmentService.buildTextContext(
"""
s = required(s, coverage_insert_anchor, coverage_insert, 'Tutor second-pass guide retrieval')

style_anchor = """      final sourceRule = broad
          ? 'The user asked for a random point. Choose ONE meaningful fact or concept explicitly present in SOURCE EVIDENCE and explain it. Do not repeat the user request.'
          : 'Answer only when SOURCE EVIDENCE or CURRENT ATTACHMENTS explicitly support the answer.';

      final result = await AiService.askConfigured(
"""
style_new = """      final sourceRule = broad
          ? 'The user asked for a random point. Choose ONE meaningful fact or concept explicitly present in SOURCE EVIDENCE and explain it. Do not repeat the user request.'
          : 'Answer only when SOURCE EVIDENCE or CURRENT ATTACHMENTS support the answer. The wording may be paraphrased; it does not need to be a literal sentence match.';
      final answerStyle = responseMode == 'fast'
          ? 'Answer directly in 1-3 concise sentences. No preamble and no unnecessary repetition.'
          : responseMode == 'deep'
              ? 'Give a thorough but focused explanation, connecting the relevant ideas in the guide.'
              : 'Give a clear, concise explanation with enough context to understand the answer.';

      final result = await AiService.askConfigured(
"""
s = required(s, style_anchor, style_new, 'Tutor response style')
s = s.replace(
    "- Keep the conversation natural and use the history only for conversational continuity, never as evidence that overrides the guides.\n",
    "- Keep the conversation natural and use the history only for conversational continuity, never as evidence that overrides the guides.\n- $answerStyle\n",
    1,
)
p.write_text(s)


# -----------------------------------------------------------------------------
# AI Settings: choosing a provider immediately becomes the System AI; Save still
# persists keys/model fields. This removes the stale Gemini selection behavior.
# -----------------------------------------------------------------------------
p = Path('lib/llm_settings_page.dart')
s = p.read_text()
choice_anchor = "  Widget _choice(String value, IconData icon, String title, String subtitle) =>\n"
select_method = r'''  Future<void> _selectProvider(String? value) async {
    final selected = value ?? 'gemini';
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('llm_provider', selected);
    if (mounted) setState(() => provider = selected);
  }

'''
if "Future<void> _selectProvider" not in s:
    s = required(s, choice_anchor, select_method + choice_anchor, 'AI Settings immediate provider method')
s = s.replace(
    "onChanged: (v) => setState(() => provider = v ?? 'gemini'),",
    "onChanged: _selectProvider,",
    1,
)
p.write_text(s)


# -----------------------------------------------------------------------------
# Daily exams: explicit AI modes generate in small batches until the selected
# question count is reached. No literal-evidence requirement and no generic
# parser fallback. Instant mode uses stored AI cards only.
# -----------------------------------------------------------------------------
p = Path('lib/daily_exam_page.dart')
s = p.read_text()
if "ai_card_service.dart" not in s:
    s = required(
        s,
        "import 'ai_service.dart';\n",
        "import 'ai_card_service.dart';\nimport 'ai_service.dart';\n",
        'Exam system-AI import',
    )
state_anchor = "  int examElapsedSeconds = 0;\n"
s = required(
    s,
    state_anchor,
    state_anchor + "  int examGeneratedQuestions = 0;\n  int examTargetQuestions = 0;\n",
    'Exam batch progress state',
)
# v1.18's instant/indexed helper currently recreates parser cards from raw text.
parser_loop = """    for (final guide in guides) {
      // Regenerate cards from the original text so old imports also benefit
      // from current parser fixes without forcing the user to re-import PDFs.
      for (final card in StudyEngine.buildCards(guide.text)) {
        addCandidate(guide, card);
      }
      for (final card in guide.cards) {
"""
stored_only = """    for (final guide in guides) {
      // v1.22: instant mode may reuse stored AI cards, but it never creates
      // parser/regex questions from raw guide fragments.
      for (final card in guide.cards) {
"""
if parser_loop in s:
    s = s.replace(parser_loop, stored_only, 1)

helper_start = s.find("  List<ExamQuestionData> _parseAiQuestions(")
helper_end = s.find("  Future<TutorExamSession> _buildExam(", helper_start)
if helper_start < 0 or helper_end < 0:
    raise RuntimeError('Exam AI helper block not found')
exam_helpers = r'''  List<ExamQuestionData> _parseAiQuestions(
    String raw, {
    required List<StudyGuide> guides,
    required List<String> avoidQuestions,
  }) {
    final out = <ExamQuestionData>[];

    void addMap(Map<dynamic, dynamic> map) {
      final q = (map['question'] ?? map['pregunta'] ?? map['q'])?.toString().trim() ?? '';
      final a = (map['answer'] ?? map['respuesta'] ?? map['a'])?.toString().trim() ?? '';
      final source = (map['source'] ?? map['fuente'] ?? map['topic'])?.toString().trim() ?? '';
      if (_lowQualityQuestion(q) || a.length < 10 || _looksIncomplete(a)) return;
      if (avoidQuestions.any((old) => _nearDuplicate(old, q))) return;
      if (out.any((old) => _nearDuplicate(old.question, q))) return;

      final combined = guides.map((g) => g.text.toLowerCase()).join('\n');
      final meaningful = _matchWords('$q $a')
          .where((word) => word.length >= 5)
          .where((word) => !const {
                'question','answer','which','their','there','about','could','would','should',
                'guide','content','using','because','where','when','what','does'
              }.contains(word))
          .take(14)
          .toList();
      if (meaningful.isNotEmpty && !meaningful.any(combined.contains)) return;

      var sourceTitle = source;
      if (sourceTitle.isEmpty) sourceTitle = guides.first.title;
      out.add(ExamQuestionData(question: q, answer: a, sourceTitle: sourceTitle));
    }

    final start = raw.indexOf('[');
    final end = raw.lastIndexOf(']');
    if (start >= 0 && end > start) {
      try {
        final decoded = jsonDecode(raw.substring(start, end + 1));
        if (decoded is List) {
          for (final item in decoded.whereType<Map>()) addMap(item);
          if (out.isNotEmpty) return out;
        }
      } catch (_) {}
    }

    for (final match in RegExp(r'\{[^{}]*\}', dotAll: true).allMatches(raw)) {
      try {
        final decoded = jsonDecode(match.group(0)!);
        if (decoded is Map) addMap(decoded);
      } catch (_) {}
    }
    return out;
  }

  List<String> _examContentChunks(List<StudyGuide> guides, int maxChars) {
    final chunks = <String>[];
    for (final guide in guides) {
      final paragraphs = guide.text
          .replaceAll('\r', '')
          .split(RegExp(r'\n{2,}'))
          .map((e) => e.trim())
          .where((e) => e.isNotEmpty)
          .toList();
      var buffer = StringBuffer('=== ${guide.title} ===\n');
      for (final paragraph in paragraphs) {
        if (paragraph.length > maxChars) {
          final existing = buffer.toString().trim();
          if (existing.length > guide.title.length + 8) chunks.add(existing);
          for (var start = 0; start < paragraph.length; start += maxChars) {
            final end = min(start + maxChars, paragraph.length);
            chunks.add('=== ${guide.title} ===\n${paragraph.substring(start, end)}');
          }
          buffer = StringBuffer('=== ${guide.title} ===\n');
          continue;
        }
        if (buffer.length + paragraph.length + 2 > maxChars) {
          chunks.add(buffer.toString().trim());
          buffer = StringBuffer('=== ${guide.title} ===\n');
        }
        buffer.writeln(paragraph);
        buffer.writeln();
      }
      final remaining = buffer.toString().trim();
      if (remaining.length > guide.title.length + 8) chunks.add(remaining);
    }
    return chunks;
  }

  Future<List<ExamQuestionData>> _generateAiExamQuestions({
    required TutorContextProfile tutor,
    required List<StudyGuide> guides,
    required int count,
    required String difficulty,
    required String provider,
    required bool localish,
    required List<String> recentQuestions,
  }) async {
    final chunks = _examContentChunks(guides, localish ? 4200 : 8500);
    if (chunks.isEmpty) return const [];
    final out = <ExamQuestionData>[];
    final batchSize = localish ? 4 : 6;
    final maxAttempts = max(8, (count / batchSize).ceil() + 8).clamp(8, 28).toInt();
    var attempt = 0;

    if (mounted) {
      setState(() {
        examGeneratedQuestions = 0;
        examTargetQuestions = count;
      });
    }

    while (out.length < count && attempt < maxAttempts) {
      final chunk = chunks[attempt % chunks.length];
      final needed = count - out.length;
      final askFor = min(batchSize + 2, needed + 2);
      final avoid = <String>[
        ...recentQuestions.take(18),
        ...out.map((q) => q.question),
      ];
      final raw = await AiService.askTaskConfigured(
        providerOverride: provider,
        responseMode: localish ? 'normal' : 'deep',
        prompt: '''Create $askFor NEW high-quality exam questions using ONLY the assigned MATERIAL below.
Difficulty: $difficulty.

RULES:
- Test understanding, application, cause/effect, comparison, decision-making, formulas, or calculations when supported by the material.
- You MAY paraphrase and combine directly related ideas from the material. Do not require literal wording.
- Do NOT use outside knowledge or facts absent from the material.
- Do NOT create isolated-word vocabulary trivia or vague fragment questions.
- Questions must make sense on their own and answers must be complete enough to grade.
- Avoid every recent/already accepted question below, including close rephrasings.
- Return ONLY a JSON array with no Markdown.
- Exact item format: {"question":"...","answer":"...","source":"guide/topic"}.

QUESTIONS TO AVOID:
${avoid.isEmpty ? '(none)' : avoid.map((q) => '- $q').join('\n')}

MATERIAL:
$chunk''',
      );
      final parsed = _parseAiQuestions(
        raw,
        guides: guides,
        avoidQuestions: avoid,
      );
      for (final item in parsed) {
        if (out.length >= count) break;
        if (out.any((old) => _nearDuplicate(old.question, item.question))) continue;
        out.add(item);
        if (mounted) setState(() => examGeneratedQuestions = out.length);
      }
      attempt++;
    }
    return out;
  }

'''
s = s[:helper_start] + exam_helpers + s[helper_end:]

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
    var generatorLabel = 'Instant • stored AI cards';

    if (generatorMode == 'instant') {
      questions = _cardQuestions(
        guides,
        count,
        avoidQuestions: recentQuestions,
      );
      if (questions.isEmpty) {
        throw Exception(
          'This tutor has no AI-generated study cards yet. Generate the guide cards first or choose an AI exam generator.',
        );
      }
    } else {
      String provider;
      String displayLabel;
      if (generatorMode == 'best') {
        final systemAi = await AiCardService.systemAi();
        if (!systemAi.ready) {
          throw Exception('The configured System AI is not ready for exam generation.');
        }
        provider = 'global';
        displayLabel = systemAi.label;
      } else {
        provider = tutor.modelSource;
        if (provider == 'global') {
          final systemAi = await AiCardService.systemAi();
          if (!systemAi.ready) {
            throw Exception('The configured System AI is not ready for exam generation.');
          }
          displayLabel = systemAi.label;
        } else {
          displayLabel = TutorContextService.sourceLabel(provider);
        }
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

      generatorLabel = generatorMode == 'best'
          ? 'System AI • $displayLabel'
          : '${tutor.name} • $displayLabel';
      questions = await _generateAiExamQuestions(
        tutor: tutor,
        guides: guides,
        count: count,
        difficulty: difficulty,
        provider: provider,
        localish: localish,
        recentQuestions: recentQuestions,
      );

      if (questions.length < count) {
        throw Exception(
          'The AI generated ${questions.length} of $count usable questions. Memora kept the good batches but could not complete the requested exam yet.',
        );
      }
    }

    if (questions.length > count) questions = questions.take(count).toList();
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
s = regex_required(
    s,
    r"  Future<TutorExamSession> _buildExam\(\{.*?\n  \}\n\n  Future<void> _openExam",
    new_build_exam + "  Future<void> _openExam",
    'Exam batched AI builder',
)

# Stopwatch remains informational and now also shows question-generation progress.
s = s.replace(
    "'Preparing… ${examElapsedSeconds}s'",
    "'Preparing… ${examElapsedSeconds}s${examTargetQuestions > 0 ? ' • $examGeneratedQuestions/$examTargetQuestions' : ''}'",
)
s = s.replace(
    "'Creating exam… ${examElapsedSeconds}s'",
    "'Creating exam… ${examElapsedSeconds}s${examTargetQuestions > 0 ? ' • $examGeneratedQuestions/$examTargetQuestions' : ''}'",
)
# Reset batch counters with the existing timer lifecycle.
s = s.replace(
    "        examElapsedSeconds = 0;\n",
    "        examElapsedSeconds = 0;\n        examGeneratedQuestions = 0;\n        examTargetQuestions = 0;\n",
    1,
)
# _endExamWork has a second identical elapsed reset; replace that occurrence too.
end_marker = """        busyTutorId = null;
        examElapsedSeconds = 0;
"""
if end_marker in s:
    s = s.replace(
        end_marker,
        """        busyTutorId = null;
        examElapsedSeconds = 0;
        examGeneratedQuestions = 0;
        examTargetQuestions = 0;
""",
        1,
    )
p.write_text(s)


# -----------------------------------------------------------------------------
# English cleanup after v1.21 reintroduced several Spanish labels.
# -----------------------------------------------------------------------------
replace_all('lib/tutor_page.dart', [
    ("'Tutores con IA'", "'AI Tutors'"),
    ("'Tutor activo'", "'Active tutor'"),
    ("'Modelos recomendados'", "'Recommended models'"),
    ("'Toca uno para usarlo como modelo general Ollama'", "'Tap a model to manage, download, or use it with Ollama'"),
    ("'Modelo general Ollama: $globalLocalModel'", "'System Ollama model: $globalLocalModel'"),
    ("'El selector cambia el modelo general de Ollama; no descarga el modelo automáticamente.'", "'Tap a recommended model to use, download, delete, or manage it.'"),
    ("'Editar tutor / recomendaciones'", "'Edit tutor / recommendations'"),
    ("'Rápido'", "'Fast'"),
    ("'Profundo'", "'Deep'"),
    ("'Motor GGUF: $accelerationLabel'", "'GGUF engine: $accelerationLabel'"),
    ("'Biblioteca de este tutor'", "\"This tutor's library\""),
    ("'${activeGuides.length} guía(s) asignada(s)'", "'${activeGuides.length} guide(s) assigned'"),
    ("'Todavía no tiene guías asignadas.'", "'No guides assigned yet.'"),
    ("'Asignar / quitar guías'", "'Assign / remove guides'"),
    ("'Pregunta a ${activeTutor.name}…'", "'Ask ${activeTutor.name}…'"),
    ("'Detener generación'", "'Stop generation'"),
    ("'Enviar'", "'Send'"),
    ("'Mis tutores'", "'My tutors'"),
    ("'Editar activo'", "'Edit active'"),
    ("'Eliminar'", "'Delete'"),
    ("'Administrar tutores'", "'Manage tutors'"),
    ("' guía(s)'", "' guide(s)'"),
])

replace_all('lib/daily_exam_page.dart', [
    ("'Exámenes'", "'Exams'"),
    ("'Examen diario'", "'Daily exam'"),
    ("'Crear examen'", "'Create exam'"),
    ("'Elige un tutor. Memora usará exclusivamente el contenido asignado a ese tutor.'", "'Choose a tutor. Memora will use only the content assigned to that tutor.'"),
    ("'Tutor / contenido del examen'", "'Tutor / exam content'"),
    ("'Selecciona un tutor.'", "'Select a tutor.'"),
    ("'${tutor.name} no tiene guías asignadas.'", "'${tutor.name} has no assigned guides.'"),
    ("'${guides.length} guía(s) disponibles para este examen.'", "'${guides.length} guide(s) available for this exam.'"),
    ("'Número de preguntas'", "'Number of questions'"),
    ("Text('$n preguntas')", "Text('$n questions')"),
    ("'Cómo redactar las preguntas'", "'How to generate the questions'"),
    ("'✨ Mejor IA disponible'", "'✨ System AI'"),
    ("'🧑‍🏫 IA del tutor'", "'🧑‍🏫 Tutor AI'"),
    ("'⚡ Instantáneo (sin IA)'", "'⚡ Instant (stored AI cards)'"),
    ("'Exámenes diarios por tutor'", "'Daily exams by tutor'"),
    ("'Cada tutor te examina únicamente de sus propias guías. El examen de hoy se guarda y no se vuelve a generar al abrir esta pantalla.'", "'Each tutor tests you only on its assigned guides. Today\'s exam is saved and is not regenerated just by reopening this screen.'"),
    ("'Generador de exámenes diarios'", "'Daily exam generator'"),
    ("'Pendiente'", "'Pending'"),
    ("'Completado • ${exam.correct}/${exam.questions.length}'", "'Completed • ${exam.correct}/${exam.questions.length}'"),
    ("'En progreso • ${exam.currentIndex}/${exam.questions.length}'", "'In progress • ${exam.currentIndex}/${exam.questions.length}'"),
    ("'${guides.length} guía(s) • $status'", "'${guides.length} guide(s) • $status'"),
    ("'Este tutor todavía no tiene material para examinarte.'", "'This tutor does not have exam material yet.'"),
    ("'Crear examen de hoy'", "\"Create today's exam\""),
    ("'Abrir examen'", "'Open exam'"),
    ("'Regenerar examen de hoy'", "\"Regenerate today's exam\""),
    ("'Dificultad'", "'Difficulty'"),
    ("'Fácil'", "'Easy'"),
    ("'Media'", "'Medium'"),
    ("'Difícil'", "'Hard'"),
    ("'Adaptativa'", "'Adaptive'"),
])

replace_all('lib/llm_settings_page.dart', [
    ("'Ajustes de IA'", "'AI Settings'"),
    ("'Elige qué cerebro usará Memora'", "'Choose the system AI Memora will use'"),
    ("'Rápido y sencillo con una clave de Google AI Studio.'", "'Fast online option using a Google AI Studio key.'"),
    ("'LLM online compatible'", "'Online compatible LLM'"),
    ("'OpenAI o cualquier API compatible con /chat/completions.'", "'OpenAI or any API compatible with /chat/completions.'"),
    ("'LLM local'", "'Local LLM / Ollama'"),
    ("'Ollama, LM Studio u otro servidor compatible, sin nube.'", "'Ollama, LM Studio, or another compatible local server.'"),
    ("'GGUF en este teléfono'", "'GGUF on this phone'"),
    ("'Memora puede usar su modelo privado o un modelo compartido con otras APK.'", "'Memora can use its private model or a GGUF shared with other apps.'"),
    ("'Clave de Gemini'", "'Gemini key'"),
    ("'URL del LLM local'", "'Local LLM URL'"),
    ("'Nombre del modelo'", "'Model name'"),
    ("'Clave opcional'", "'Optional key'"),
    ("'Guardar y usar esta opción'", "'Save and use this option'"),
    ("'Configuración de IA guardada'", "'AI settings saved'"),
])

print('Memora v1.22 AI cards, system AI sync, tutor grounding, and batched exam patch applied successfully')
