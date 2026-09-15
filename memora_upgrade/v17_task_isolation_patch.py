from pathlib import Path

# -----------------------------------------------------------------------------
# Device GGUF: isolated one-shot task sessions
# -----------------------------------------------------------------------------
p = Path('lib/device_llm_service.dart')
s = p.read_text()
anchor = "  static Future<String> _askInternal(\n"
insert = r'''  static Future<String> askTask(
    String prompt, {
    String responseMode = 'normal',
    void Function(String text)? onPartial,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final mode = prefs.getString('device_model_mode') ?? 'private';
    return askTaskWithMode(
      prompt,
      mode: mode,
      responseMode: responseMode,
      onPartial: onPartial,
    );
  }

  static Future<String> askTaskWithMode(
    String prompt, {
    required String mode,
    String responseMode = 'normal',
    void Function(String text)? onPartial,
  }) {
    final requestId = ++_requestSerial;
    return _enqueue(() async {
      // A task never reuses the controller/context left by a chat.
      await _disposeController();
      try {
        return await _askInternal(
          requestId,
          prompt,
          mode: mode,
          responseMode: responseMode,
          onPartial: onPartial,
        );
      } finally {
        // Always close the task context, even after cancellation/error.
        await _disposeController();
      }
    });
  }

'''
if anchor not in s:
    raise RuntimeError('Device task isolation anchor not found')
s = s.replace(anchor, insert + anchor, 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# AI routing: task detection + isolated task API
# -----------------------------------------------------------------------------
p = Path('lib/ai_service.dart')
s = p.read_text()
method_anchor = "  static Future<String> askConfigured({\n"
if method_anchor not in s:
    raise RuntimeError('AiService askConfigured anchor not found')

# Add taskHint to normal chat requests. If the user's current message is a
# creation/analysis task, route it through a clean one-shot session.
old_sig = """    String responseMode = 'normal',\n    void Function(String text)? onPartial,\n    List<String> imagePaths = const [],\n  }) async {\n    final prefs = await SharedPreferences.getInstance();\n"""
new_sig = """    String responseMode = 'normal',\n    void Function(String text)? onPartial,\n    List<String> imagePaths = const [],\n    String? taskHint,\n  }) async {\n    if (taskHint != null && looksLikeTask(taskHint)) {\n      return askTaskConfigured(\n        prompt: prompt,\n        deviceModeOverride: deviceModeOverride,\n        providerOverride: providerOverride,\n        responseMode: responseMode,\n        onPartial: onPartial,\n        imagePaths: imagePaths,\n      );\n    }\n    final prefs = await SharedPreferences.getInstance();\n"""
if old_sig not in s:
    raise RuntimeError('AiService signature anchor not found')
s = s.replace(old_sig, new_sig, 1)

insert_anchor = "  static Future<String> askGemini({\n"
helper = r'''  static bool looksLikeTask(String text) {
    final value = text.toLowerCase().trim();
    if (value.isEmpty) return false;
    final action = RegExp(
      r'\b(crea|crear|créame|creame|genera|generar|haz|hacer|prepara|preparar|elabora|elaborar|construye|construir|convierte|convertir|exporta|exportar|analiza|analizar)\b',
      caseSensitive: false,
    );
    final output = RegExp(
      r'\b(examen|exámenes|examenes|prueba|test|quiz|plan|guía|guia|pdf|excel|xlsx|documento|archivo|resumen|tabla|informe|reporte|presentación|presentacion)\b',
      caseSensitive: false,
    );
    return action.hasMatch(value) && output.hasMatch(value);
  }

  static Future<String> askTaskConfigured({
    required String prompt,
    String? deviceModeOverride,
    String? providerOverride,
    String responseMode = 'normal',
    void Function(String text)? onPartial,
    List<String> imagePaths = const [],
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final explicit = providerOverride?.trim();

    if (explicit == 'private' || explicit == 'shared') {
      return DeviceLlmService.askTaskWithMode(
        prompt,
        mode: explicit!,
        responseMode: responseMode,
        onPartial: onPartial,
      );
    }
    if (deviceModeOverride == 'private' || deviceModeOverride == 'shared') {
      return DeviceLlmService.askTaskWithMode(
        prompt,
        mode: deviceModeOverride!,
        responseMode: responseMode,
        onPartial: onPartial,
      );
    }

    final provider = (explicit == null || explicit.isEmpty || explicit == 'global')
        ? (prefs.getString('llm_provider') ?? 'gemini')
        : explicit;

    if (provider == 'device') {
      return DeviceLlmService.askTask(
        prompt,
        responseMode: responseMode,
        onPartial: onPartial,
      );
    }

    // Online/Ollama HTTP calls are stateless per request already. Use the
    // normal transport, but without a taskHint so this cannot recurse.
    return askConfigured(
      prompt: prompt,
      deviceModeOverride: deviceModeOverride,
      providerOverride: provider,
      responseMode: responseMode,
      onPartial: onPartial,
      imagePaths: imagePaths,
    );
  }

'''
if insert_anchor not in s:
    raise RuntimeError('AiService task helper anchor not found')
s = s.replace(insert_anchor, helper + insert_anchor, 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# Large one-shot features always use isolated task routing.
# -----------------------------------------------------------------------------
for filename in (
    'lib/study_plan_page.dart',
    'lib/daily_exam_page.dart',
    'lib/guide_creator_page.dart',
    'lib/ai_study_guide_page.dart',
):
    p = Path(filename)
    text = p.read_text()
    if 'AiService.askConfigured(' not in text:
        raise RuntimeError(f'No task AI call found in {filename}')
    text = text.replace('AiService.askConfigured(', 'AiService.askTaskConfigured(')
    p.write_text(text)

# -----------------------------------------------------------------------------
# Tutor/Agent chat: automatically isolate explicit creation tasks while keeping
# ordinary conversation on the normal persistent chat route.
# -----------------------------------------------------------------------------
p = Path('lib/tutor_page.dart')
s = p.read_text()
needle = "        responseMode: responseMode,\n        imagePaths: imagePaths,\n        onPartial: (partial) {"
replacement = "        responseMode: responseMode,\n        imagePaths: imagePaths,\n        taskHint: shownQuestion,\n        onPartial: (partial) {"
if needle not in s:
    raise RuntimeError('Tutor taskHint anchor not found')
s = s.replace(needle, replacement, 1)
p.write_text(s)

p = Path('lib/agent_page.dart')
s = p.read_text()
needle = "        responseMode: responseMode,\n        imagePaths: imagePaths,\n        onPartial: (partial) {"
replacement = "        responseMode: responseMode,\n        imagePaths: imagePaths,\n        taskHint: request.isEmpty ? 'Analiza el archivo adjunto' : request,\n        onPartial: (partial) {"
if needle not in s:
    raise RuntimeError('Agent taskHint anchor not found')
s = s.replace(needle, replacement, 1)
p.write_text(s)

print('Memora v1.7 isolated task sessions applied successfully')
