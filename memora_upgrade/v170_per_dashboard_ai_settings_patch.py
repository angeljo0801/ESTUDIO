from pathlib import Path
import re

# v170: isolate AI Settings and response routing per dashboard.
# Each dashboard can keep a different provider/model/API configuration.
# Missing scoped values inherit the existing global value, so upgrades are seamless.

# ---------------------------------------------------------------------------
# LlmSettingsPage: add a dashboard scope and store all LLM settings under it.
# ---------------------------------------------------------------------------
p = Path('lib/llm_settings_page.dart')
s = p.read_text()

old = """class LlmSettingsPage extends StatefulWidget {
  const LlmSettingsPage({super.key});
  @override
  State<LlmSettingsPage> createState() => _LlmSettingsPageState();
}
"""
new = """class LlmSettingsPage extends StatefulWidget {
  const LlmSettingsPage({
    super.key,
    this.scope = 'global',
    this.scopeLabel = 'Memora',
  });

  final String scope;
  final String scopeLabel;

  @override
  State<LlmSettingsPage> createState() => _LlmSettingsPageState();
}
"""
if old not in s:
    raise SystemExit('v170 settings constructor anchor missing')
s = s.replace(old, new, 1)

anchor = "class _LlmSettingsPageState extends State<LlmSettingsPage> {\n"
helpers = """class _LlmSettingsPageState extends State<LlmSettingsPage> {
  String _prefKey(String base) =>
      widget.scope == 'global' ? base : 'memora_dashboard_${widget.scope}_$base';

  String? _readPref(SharedPreferences prefs, String base) =>
      prefs.getString(_prefKey(base)) ?? prefs.getString(base);

  Future<void> _writePref(
    SharedPreferences prefs,
    String base,
    String value,
  ) =>
      prefs.setString(_prefKey(base), value);

"""
if anchor not in s:
    raise SystemExit('v170 settings state anchor missing')
s = s.replace(anchor, helpers, 1)

keys = [
    'llm_provider',
    'device_model_mode',
    'gemini_key',
    'openai_base_url',
    'openai_model',
    'openai_key',
    'local_base_url',
    'local_model',
    'local_key',
    'device_model_path',
    'shared_model_uri',
    'shared_model_name',
    'ai_task_exam',
    'ai_task_explanation',
    'ai_task_guide',
    'ai_task_prompt',
]
for key in keys:
    s = s.replace(f"p.getString('{key}')", f"_readPref(p, '{key}')")
    s = s.replace(f"await p.setString('{key}', ", f"await _writePref(p, '{key}', ")

# Keep private GGUF copies physically separate when a dashboard imports its own model.
s = s.replace(
    "      final modelDir = Directory('${dir.path}/models');\n",
    "      final modelDir = Directory(widget.scope == 'global' ? '${dir.path}/models' : '${dir.path}/models/${widget.scope}');\n",
    1,
)

s = s.replace(
    "        appBar: AppBar(title: const Text('Ajustes de IA')),\n",
    "        appBar: AppBar(title: Text(widget.scope == 'global' ? 'Ajustes de IA' : 'Ajustes de IA · ${widget.scopeLabel}')),\n",
    1,
)

heading = """                  const Text(
                    'Elige qué cerebro usará Memora',
                    style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                  ),
"""
heading_new = """                  Text(
                    widget.scope == 'global'
                        ? 'Elige qué cerebro usará Memora'
                        : 'Elige qué cerebro usará ${widget.scopeLabel}',
                    style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                  ),
                  if (widget.scope != 'global') ...[
                    const SizedBox(height: 6),
                    const Text(
                      'Estos ajustes pertenecen solo a este dashboard. Cambiar su IA o modelo no modifica los demás.',
                    ),
                  ],
"""
if heading in s:
    s = s.replace(heading, heading_new, 1)

p.write_text(s)

# ---------------------------------------------------------------------------
# AiService: read provider/model/key/url settings through an optional scope.
# ---------------------------------------------------------------------------
p = Path('lib/ai_service.dart')
s = p.read_text()

anchor = "class AiService {\n"
helpers = """class AiService {
  static String _scopeKey(String base, String? scope) =>
      scope == null || scope.isEmpty || scope == 'global'
          ? base
          : 'memora_dashboard_${scope}_$base';

  static String _scopePref(
    SharedPreferences prefs,
    String base,
    String? scope, {
    String fallback = '',
  }) =>
      prefs.getString(_scopeKey(base, scope)) ??
      prefs.getString(base) ??
      fallback;

"""
if anchor not in s:
    raise SystemExit('v170 AiService class anchor missing')
s = s.replace(anchor, helpers, 1)

# v144 task-specific provider helper.
old = """  static Future<String> providerForTask(String task) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('ai_task_$task') ?? 'gemini';
  }
"""
new = """  static Future<String> providerForTask(
    String task, {
    String? settingsScope,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    return _scopePref(
      prefs,
      'ai_task_$task',
      settingsScope,
      fallback: 'gemini',
    );
  }
"""
if old in s:
    s = s.replace(old, new, 1)

# askCascade gets and forwards the dashboard scope.
start = s.find("  static Future<String> askCascade({")
if start >= 0:
    end = s.find("  static Future<String> askConfigured({", start)
    block = s[start:end]
    block = block.replace(
        "    String? preferredProvider,\n    String responseMode = 'normal',\n",
        "    String? preferredProvider,\n    String? settingsScope,\n    String responseMode = 'normal',\n",
        1,
    )
    block = block.replace(
        "? await providerForTask(task)",
        "? await providerForTask(task, settingsScope: settingsScope)",
        1,
    )
    block = block.replace(
        "          providerOverride: provider,\n",
        "          providerOverride: provider,\n          settingsScope: settingsScope,\n",
        1,
    )
    s = s[:start] + block + s[end:]

# askConfigured signature.
start = s.find("  static Future<String> askConfigured({")
if start < 0:
    raise SystemExit('v170 askConfigured missing')
end_candidates = [x for x in [
    s.find("  static bool looksLikeTask(", start),
    s.find("  static Future<String> askTaskConfigured({", start),
    s.find("  static Future<String> askGemini({", start),
] if x >= 0]
end = min(end_candidates)
block = s[start:end]
block = block.replace(
    "    String? providerOverride,\n    String responseMode = 'normal',\n",
    "    String? providerOverride,\n    String? settingsScope,\n    String responseMode = 'normal',\n",
    1,
)

# taskHint routing must preserve scope.
block = block.replace(
    "        providerOverride: providerOverride,\n        responseMode: responseMode,\n",
    "        providerOverride: providerOverride,\n        settingsScope: settingsScope,\n        responseMode: responseMode,\n",
    1,
)

# Resolve the selected provider per dashboard.
block = block.replace(
    "? (prefs.getString('llm_provider') ?? 'gemini')",
    "? _scopePref(prefs, 'llm_provider', settingsScope, fallback: 'gemini')",
)

# Resolve provider details per dashboard.
replacements = {
    "prefs.getString('gemini_key')?.trim() ?? ''":
        "_scopePref(prefs, 'gemini_key', settingsScope).trim()",
    "prefs.getString('openai_key')?.trim() ?? ''":
        "_scopePref(prefs, 'openai_key', settingsScope).trim()",
    "prefs.getString('openai_model')?.trim() ?? ''":
        "_scopePref(prefs, 'openai_model', settingsScope).trim()",
    "prefs.getString('openai_base_url')?.trim() ??\n          'https://api.openai.com/v1'":
        "_scopePref(prefs, 'openai_base_url', settingsScope, fallback: 'https://api.openai.com/v1').trim()",
    "prefs.getString('local_base_url')?.trim() ??\n          'http://127.0.0.1:11434/v1'":
        "_scopePref(prefs, 'local_base_url', settingsScope, fallback: 'http://127.0.0.1:11434/v1').trim()",
    "prefs.getString('local_model')?.trim() ?? ''":
        "_scopePref(prefs, 'local_model', settingsScope).trim()",
    "prefs.getString('local_key')?.trim() ?? ''":
        "_scopePref(prefs, 'local_key', settingsScope).trim()",
}
for old_text, new_text in replacements.items():
    block = block.replace(old_text, new_text)

# All device calls get the scope.
block = block.replace(
    "        onPartial: onPartial,\n      );",
    "        onPartial: onPartial,\n        settingsScope: settingsScope,\n      );",
)
s = s[:start] + block + s[end:]

# askTaskConfigured also gets/forwards scope.
start = s.find("  static Future<String> askTaskConfigured({")
if start >= 0:
    end = s.find("  static Future<String> askGemini({", start)
    block = s[start:end]
    block = block.replace(
        "    String? providerOverride,\n    String responseMode = 'normal',\n",
        "    String? providerOverride,\n    String? settingsScope,\n    String responseMode = 'normal',\n",
        1,
    )
    block = block.replace(
        "? (prefs.getString('llm_provider') ?? 'gemini')",
        "? _scopePref(prefs, 'llm_provider', settingsScope, fallback: 'gemini')",
    )
    block = block.replace(
        "        onPartial: onPartial,\n      );",
        "        onPartial: onPartial,\n        settingsScope: settingsScope,\n      );",
    )
    block = block.replace(
        "      imagePaths: imagePaths,\n    );",
        "      imagePaths: imagePaths,\n      settingsScope: settingsScope,\n    );",
    )
    s = s[:start] + block + s[end:]

p.write_text(s)

# ---------------------------------------------------------------------------
# DeviceLlmService: the dashboard scope chooses its own GGUF mode/path/URI.
# ---------------------------------------------------------------------------
p = Path('lib/device_llm_service.dart')
s = p.read_text()

anchor = "class DeviceLlmService {\n"
helpers = """class DeviceLlmService {
  static String _scopeKey(String base, String? scope) =>
      scope == null || scope.isEmpty || scope == 'global'
          ? base
          : 'memora_dashboard_${scope}_$base';

  static String _scopePref(
    SharedPreferences prefs,
    String base,
    String? scope, {
    String fallback = '',
  }) =>
      prefs.getString(_scopeKey(base, scope)) ??
      prefs.getString(base) ??
      fallback;

"""
if anchor not in s:
    raise SystemExit('v170 DeviceLlmService class anchor missing')
s = s.replace(anchor, helpers, 1)

s = s.replace(
    "  static Future<String> _resolvePrivateModel(SharedPreferences p) async {\n"
    "    final path = p.getString('device_model_path') ?? '';\n",
    "  static Future<String> _resolvePrivateModel(\n"
    "    SharedPreferences p, {\n"
    "    String? settingsScope,\n"
    "  }) async {\n"
    "    final path = _scopePref(p, 'device_model_path', settingsScope);\n",
    1,
)
s = s.replace(
    "  static Future<String> _openSharedModel(SharedPreferences p) async {\n"
    "    final uriText = p.getString('shared_model_uri') ?? '';\n",
    "  static Future<String> _openSharedModel(\n"
    "    SharedPreferences p, {\n"
    "    String? settingsScope,\n"
    "  }) async {\n"
    "    final uriText = _scopePref(p, 'shared_model_uri', settingsScope);\n",
    1,
)

old = """  static Future<void> _ensureLoaded({
    required SharedPreferences prefs,
    required String mode,
  }) async {
    final normalizedMode = mode == 'shared' ? 'shared' : 'private';
    final isShared = normalizedMode == 'shared';
    final sharedUri = prefs.getString('shared_model_uri') ?? '';
    final privatePath = prefs.getString('device_model_path') ?? '';
"""
new = """  static Future<void> _ensureLoaded({
    required SharedPreferences prefs,
    required String mode,
    String? settingsScope,
  }) async {
    final normalizedMode = mode == 'shared' ? 'shared' : 'private';
    final isShared = normalizedMode == 'shared';
    final sharedUri = _scopePref(prefs, 'shared_model_uri', settingsScope);
    final privatePath = _scopePref(prefs, 'device_model_path', settingsScope);
"""
if old not in s:
    raise SystemExit('v170 device ensureLoaded anchor missing')
s = s.replace(old, new, 1)
s = s.replace(
    "    final path = isShared ? await _openSharedModel(prefs) : await _resolvePrivateModel(prefs);\n",
    "    final path = isShared\n"
    "        ? await _openSharedModel(prefs, settingsScope: settingsScope)\n"
    "        : await _resolvePrivateModel(prefs, settingsScope: settingsScope);\n",
    1,
)

# Add settingsScope to public device methods and pass it to _askInternal.
for method in ['ask', 'askWithMode', 'askTask', 'askTaskWithMode']:
    marker = f"  static Future<String> {method}("
    start = s.find(marker)
    if start < 0:
        continue
    next_positions = [
        x for x in [
            s.find("  static Future<String> askWithMode(", start + 1),
            s.find("  static Future<String> askTask(", start + 1),
            s.find("  static Future<String> askTaskWithMode(", start + 1),
            s.find("  static Future<String> _askInternal(", start + 1),
        ] if x > start
    ]
    end = min(next_positions) if next_positions else len(s)
    block = s[start:end]
    if "String? settingsScope," not in block:
        block = block.replace(
            "    void Function(String text)? onPartial,\n",
            "    void Function(String text)? onPartial,\n    String? settingsScope,\n",
            1,
        )
    block = block.replace(
        "    final mode = prefs.getString('device_model_mode') ?? 'private';",
        "    final mode = _scopePref(prefs, 'device_model_mode', settingsScope, fallback: 'private');",
    )
    block = block.replace(
        "      onPartial: onPartial,\n    );",
        "      onPartial: onPartial,\n      settingsScope: settingsScope,\n    );",
    )
    block = block.replace(
        "          onPartial: onPartial,\n        ));",
        "          onPartial: onPartial,\n          settingsScope: settingsScope,\n        ));",
    )
    block = block.replace(
        "          onPartial: onPartial,\n        );",
        "          onPartial: onPartial,\n          settingsScope: settingsScope,\n        );",
    )
    s = s[:start] + block + s[end:]

# _askInternal receives the scope and loads the correct dashboard model.
start = s.find("  static Future<String> _askInternal(")
if start < 0:
    raise SystemExit('v170 device _askInternal missing')
end = s.find("  static Future<void> stopCurrent()", start)
block = s[start:end]
if "String? settingsScope," not in block:
    block = block.replace(
        "    void Function(String text)? onPartial,\n",
        "    void Function(String text)? onPartial,\n    String? settingsScope,\n",
        1,
    )
block = block.replace(
    "      await _ensureLoaded(prefs: prefs, mode: mode);",
    "      await _ensureLoaded(prefs: prefs, mode: mode, settingsScope: settingsScope);",
)
s = s[:start] + block + s[end:]
p.write_text(s)

# ---------------------------------------------------------------------------
# Each dashboard opens its own AI Settings profile and routes its own AI calls.
# ---------------------------------------------------------------------------
dashboards = {
    'lib/general_ai_chat_page.dart': ('chat', 'Chat IA'),
    'lib/tutor_page.dart': ('tutor', 'Tutor'),
    'lib/agent_page.dart': ('agents', 'Agentes'),
    'lib/agent_orchestrator_page.dart': ('agents', 'Agentes'),
    'lib/daily_exam_page.dart': ('exam', 'Examen'),
    'lib/study_plan_page.dart': ('plan', 'Plan'),
}

for filename, (scope, label) in dashboards.items():
    p = Path(filename)
    if not p.exists():
        continue
    s = p.read_text()

    s = s.replace(
        "const LlmSettingsPage()",
        f"LlmSettingsPage(scope:'{scope}', scopeLabel:'{label}')",
    )
    s = s.replace(
        "LlmSettingsPage()",
        f"LlmSettingsPage(scope:'{scope}', scopeLabel:'{label}')",
    )

    # Scope every AI request initiated from this dashboard.
    for call in [
        'AiService.askConfigured(',
        'AiService.askTaskConfigured(',
        'AiService.askCascade(',
    ]:
        s = s.replace(call, f"{call}settingsScope:'{scope}',")

    p.write_text(s)

print('v170 applied: every dashboard now owns an independent AI/model configuration')
