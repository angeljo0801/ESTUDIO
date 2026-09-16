from pathlib import Path


def required(text: str, old: str, new: str, label: str, count: int = 1) -> str:
    if old not in text:
        raise RuntimeError(f'{label} anchor not found')
    return text.replace(old, new, count)


# -----------------------------------------------------------------------------
# Tutor: instant greetings, compact guide lookups, visible thinking state, and
# small-context fast routing for short/simple questions.
# -----------------------------------------------------------------------------
p = Path('lib/tutor_page.dart')
s = p.read_text()

helper_anchor = "  bool _isBroadGuideRequest(String value) {\n"
quick_helpers = r'''  bool _isQuickGreeting(String value) {
    final text = value.toLowerCase().trim();
    if (text.isEmpty || text.length > 70) return false;
    return RegExp(
      r'^(?:hola|hello|hi|hey|buenas|buenos días|buenas tardes|buenas noches|qué tal|que tal)[!,.?\s]*$',
      caseSensitive: false,
    ).hasMatch(text);
  }

  bool _isSimpleTutorRequest(String value) {
    final text = value.toLowerCase().trim();
    if (text.isEmpty || text.length > 180 || AiService.looksLikeTask(text)) return false;
    if (RegExp(
      r'\b(step by step|in detail|deeply|compare and contrast|analyze|analysis|paso a paso|en detalle|profundamente|compara y contrasta|analiza|análisis)\b',
      caseSensitive: false,
    ).hasMatch(text)) return false;
    final words = RegExp(r"[A-Za-zÀ-ÿ0-9']+").allMatches(text).length;
    return words <= 28;
  }

'''
if '_isQuickGreeting(' not in s:
    s = required(s, helper_anchor, quick_helpers + helper_anchor, 'Tutor quick-request helpers')

old_guard = """    final attachments = _extrasKey.currentState?.attachments ?? const <QueryAttachment>[];
    if ((question.isEmpty && attachments.isEmpty) || busy) return;
    if (guides.isEmpty && attachments.isEmpty) {
"""
new_guard = """    final attachments = _extrasKey.currentState?.attachments ?? const <QueryAttachment>[];
    if ((question.isEmpty && attachments.isEmpty) || busy) return;
    final isGreeting = attachments.isEmpty && _isQuickGreeting(question);
    if (guides.isEmpty && attachments.isEmpty && !isGreeting) {
"""
s = required(s, old_guard, new_guard, 'Tutor greeting guard')

old_history = """    final token = ++_turnToken;
    _cancelRequested = false;
    final history = _conversationHistory();
    final shownQuestion = question.isEmpty ? 'Analyze the attached content.' : question;
"""
new_history = """    final token = ++_turnToken;
    _cancelRequested = false;
    final shownQuestion = question.isEmpty ? 'Analyze the attached content.' : question;
    final broadRequest = attachments.isEmpty && _isBroadGuideRequest(shownQuestion);
    final simpleRequest = attachments.isEmpty && _isSimpleTutorRequest(shownQuestion);
    final history = (broadRequest || simpleRequest)
        ? current.conversationContext(maxChars: 700, maxMessages: 4)
        : _conversationHistory();
"""
s = required(s, old_history, new_history, 'Tutor compact fast history')

old_busy = """    q.clear();
    if (mounted) setState(() => busy = true);

    try {
      final tutor = activeTutor;
      final limits = _retrievalLimits();
"""
new_busy = """    q.clear();
    if (mounted) setState(() => busy = true);
    if (!isGreeting) {
      _updateAssistantBubble(
        pending.id,
        broadRequest ? 'Reading the guide…' : 'Thinking…',
        token,
      );
    }

    try {
      if (isGreeting) {
        final spanish = RegExp(
          r'\b(hola|buenas|buenos|qué tal|que tal)\b',
          caseSensitive: false,
        ).hasMatch(shownQuestion);
        await _finishGroundedReply(
          pending,
          spanish
              ? '¡Hola! Soy ${activeTutor.name}. ¿Qué quieres repasar o preguntar?'
              : 'Hi! I’m ${activeTutor.name}. What would you like to review or ask about?',
          token,
          notify: false,
        );
        return;
      }

      final tutor = activeTutor;
      final baseLimits = _retrievalLimits();
"""
s = required(s, old_busy, new_busy, 'Tutor visible thinking and instant greeting')

old_context = """      final attachmentText = QueryAttachmentService.buildTextContext(attachments);
      final broad = _isBroadGuideRequest(shownQuestion) && attachments.isEmpty;
      var context = broad
          ? _randomGuideContext(guides, maxChars: limits.$1)
          : KnowledgeRetriever.buildContext(
              guides: guides,
              query: '$question\\n$attachmentText',
              maxChars: limits.$1,
              maxChunks: limits.$2,
              allowUnmatchedFallback: false,
            );
      if (!broad && context.startsWith('(No matching evidence found')) {
        context = KnowledgeRetriever.buildCoverageContext(
          guides: guides,
          maxChars: limits.$1,
          maxChunks: limits.$2,
        );
      }
"""
new_context = """      final attachmentText = QueryAttachmentService.buildTextContext(attachments);
      final broad = broadRequest;
      final simple = simpleRequest;
      final contextChars = broad
          ? 1200
          : (simple && responseMode == 'fast' ? 2400 : baseLimits.$1);
      final contextChunks = broad
          ? 2
          : (simple && responseMode == 'fast' ? 2 : baseLimits.$2);
      var context = broad
          ? _randomGuideContext(guides, maxChars: contextChars)
          : KnowledgeRetriever.buildContext(
              guides: guides,
              query: '$question\\n$attachmentText',
              maxChars: contextChars,
              maxChunks: contextChunks,
              allowUnmatchedFallback: false,
            );
      if (!broad && context.startsWith('(No matching evidence found')) {
        context = KnowledgeRetriever.buildCoverageContext(
          guides: guides,
          maxChars: simple && responseMode == 'fast' ? 3600 : baseLimits.$1,
          maxChunks: simple && responseMode == 'fast' ? 4 : baseLimits.$2,
        );
      }
"""
s = required(s, old_context, new_context, 'Tutor compact source context')

old_style = """      final answerStyle = responseMode == 'fast'
          ? 'Answer directly in 1-3 concise sentences. No preamble and no unnecessary repetition.'
          : responseMode == 'deep'
              ? 'Give a thorough but focused explanation, connecting the relevant ideas in the guide.'
              : 'Give a clear, concise explanation with enough context to understand the answer.';
"""
new_style = """      final answerStyle = broad
          ? 'Answer in 1-2 concise sentences. Pick one concrete point from the supplied guide excerpt and explain it directly.'
          : responseMode == 'fast'
              ? 'Answer directly in 1-3 concise sentences. No preamble and no unnecessary repetition.'
              : responseMode == 'deep'
                  ? 'Give a thorough but focused explanation, connecting the relevant ideas in the guide.'
                  : 'Give a clear, concise explanation with enough context to understand the answer.';
"""
s = required(s, old_style, new_style, 'Tutor broad-response style')

old_mode = """        providerOverride: tutor.modelSource == 'global' ? 'global' : tutor.modelSource,
        responseMode: responseMode,
        imagePaths: imagePaths,
"""
new_mode = """        providerOverride: tutor.modelSource == 'global' ? 'global' : tutor.modelSource,
        responseMode: broad || (simple && responseMode == 'fast') ? 'fast' : responseMode,
        imagePaths: imagePaths,
"""
s = required(s, old_mode, new_mode, 'Tutor fast response mode')

# If the user cancels while only the temporary status text is visible, replace it
# with the existing stopped-response text rather than leaving "Thinking…" behind.
s = s.replace(
    "if (messages.last.text.trim().isEmpty) {",
    "if (messages.last.text.trim().isEmpty || messages.last.text == 'Thinking…' || messages.last.text == 'Reading the guide…') {",
    1,
)
p.write_text(s)


# -----------------------------------------------------------------------------
# OpenAI-compatible transports (including Ollama / local server): stream tokens
# instead of waiting for the entire response. The model remains server-managed;
# direct GGUF already keeps its controller loaded between normal tutor messages.
# -----------------------------------------------------------------------------
p = Path('lib/ai_service.dart')
s = p.read_text()

stream_helper_anchor = "  static Future<String> askGemini({\n"
stream_helper = r'''  static int _networkMaxTokens(String mode) {
    switch (mode) {
      case 'fast':
        return 260;
      case 'deep':
        return 2400;
      default:
        return 1400;
    }
  }

  static Future<String> askOpenAiCompatibleStreaming({
    required http.Client client,
    required String baseUrl,
    required String apiKey,
    required String model,
    required String prompt,
    required String responseMode,
    void Function(String text)? onPartial,
    List<String> imagePaths = const [],
  }) async {
    final cleanBase = baseUrl.replaceAll(RegExp(r'/+$'), '');
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (apiKey.isNotEmpty) headers['Authorization'] = 'Bearer $apiKey';

    dynamic userContent = prompt;
    if (imagePaths.isNotEmpty) {
      final content = <Map<String, dynamic>>[
        {'type': 'text', 'text': prompt},
      ];
      for (final path in imagePaths.take(4)) {
        final file = File(path);
        if (!await file.exists()) continue;
        final bytes = await file.readAsBytes();
        if (bytes.isEmpty) continue;
        content.add({
          'type': 'image_url',
          'image_url': {
            'url': 'data:${_imageMime(path)};base64,${base64Encode(bytes)}',
          },
        });
      }
      userContent = content;
    }

    final request = http.Request(
      'POST',
      Uri.parse('$cleanBase/chat/completions'),
    );
    request.headers.addAll(headers);
    request.body = jsonEncode({
      'model': model,
      'messages': [
        {
          'role': 'system',
          'content':
              'You are Memora AI. Follow the specific instructions in the request carefully.',
        },
        {'role': 'user', 'content': userContent},
      ],
      'temperature': 0.25,
      'stream': true,
      'max_tokens': _networkMaxTokens(responseMode),
    });

    final response = await client.send(request).timeout(const Duration(seconds: 45));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final body = await response.stream.bytesToString();
      throw Exception('The model returned ${response.statusCode}: ${_message(body)}');
    }

    final buffer = StringBuffer();
    var lastUiUpdate = DateTime.fromMillisecondsSinceEpoch(0);
    await for (final rawLine
        in response.stream.transform(utf8.decoder).transform(const LineSplitter())) {
      var line = rawLine.trim();
      if (line.isEmpty || line.startsWith('event:')) continue;
      if (line.startsWith('data:')) line = line.substring(5).trim();
      if (line == '[DONE]') break;
      try {
        final data = jsonDecode(line);
        if (data is! Map) continue;
        final choices = data['choices'];
        if (choices is! List || choices.isEmpty || choices.first is! Map) continue;
        final choice = choices.first as Map;
        final delta = choice['delta'];
        final message = choice['message'];
        final piece = delta is Map
            ? delta['content']?.toString()
            : message is Map
                ? message['content']?.toString()
                : choice['text']?.toString();
        if (piece == null || piece.isEmpty) continue;
        buffer.write(piece);
        final now = DateTime.now();
        if (onPartial != null &&
            now.difference(lastUiUpdate) >= const Duration(milliseconds: 55)) {
          onPartial(buffer.toString());
          lastUiUpdate = now;
        }
      } catch (_) {
        // Ignore non-JSON keepalive lines from compatible local servers.
      }
    }

    final text = buffer.toString().trim();
    if (text.isEmpty) {
      throw Exception('The model completed without returning text.');
    }
    onPartial?.call(text);
    return text;
  }

'''
if 'askOpenAiCompatibleStreaming({' not in s:
    s = required(s, stream_helper_anchor, stream_helper + stream_helper_anchor, 'Streaming AI helper')

old_openai = """      final result = await _runOnline((client, _) => askOpenAiCompatible(
            client: client,
            baseUrl: baseUrl,
            apiKey: key,
            model: model,
            prompt: prompt,
            imagePaths: imagePaths,
          ));
      onPartial?.call(result);
      return result;
"""
new_openai = """      return _runOnline((client, _) => askOpenAiCompatibleStreaming(
            client: client,
            baseUrl: baseUrl,
            apiKey: key,
            model: model,
            prompt: prompt,
            responseMode: responseMode,
            onPartial: onPartial,
            imagePaths: imagePaths,
          ));
"""
s = required(s, old_openai, new_openai, 'OpenAI streaming route')

old_local = """      final result = await _runOnline((client, _) => askOpenAiCompatible(
            client: client,
            baseUrl: baseUrl,
            apiKey: key,
            model: model,
            prompt: prompt,
          ));
      onPartial?.call(result);
      return result;
"""
new_local = """      return _runOnline((client, _) => askOpenAiCompatibleStreaming(
            client: client,
            baseUrl: baseUrl,
            apiKey: key,
            model: model,
            prompt: prompt,
            responseMode: responseMode,
            onPartial: onPartial,
          ));
"""
s = required(s, old_local, new_local, 'Ollama/local streaming route')
p.write_text(s)

print('Memora v1.25 fast tutor response patch applied successfully')
