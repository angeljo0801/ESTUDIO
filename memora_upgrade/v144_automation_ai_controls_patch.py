from pathlib import Path
import os

# Memora v1.44 foundation: task-specific AI defaults/cascade + randomized exam fallback.
p = Path('lib/ai_service.dart')
s = p.read_text()
anchor = "  static Future<String> askConfigured({\n"
helper = r'''  static const List<String> defaultCascade = <String>[
    'gemini',
    'openai',
    'local',
    'device',
  ];

  static Future<String> providerForTask(String task) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('ai_task_$task') ?? 'gemini';
  }

  static Future<String> askCascade({
    required String prompt,
    String task = 'chat',
    String? preferredProvider,
    String responseMode = 'normal',
    void Function(String text)? onPartial,
    List<String> imagePaths = const [],
  }) async {
    final preferred = (preferredProvider == null ||
            preferredProvider.trim().isEmpty ||
            preferredProvider == 'global')
        ? await providerForTask(task)
        : preferredProvider.trim();
    final order = <String>[preferred, ...defaultCascade]
        .where((e) => e.isNotEmpty)
        .toSet()
        .toList();
    Object? lastError;
    for (final provider in order) {
      try {
        return await askConfigured(
          prompt: prompt,
          providerOverride: provider,
          responseMode: responseMode,
          onPartial: onPartial,
          imagePaths: imagePaths,
        );
      } catch (e) {
        lastError = e;
      }
    }
    throw Exception('No AI provider in the cascade is available. ${lastError ?? ''}');
  }

'''
if 'static const List<String> defaultCascade' not in s:
    if anchor not in s: raise RuntimeError('v1.44 AiService anchor not found')
    s = s.replace(anchor, helper + anchor, 1)
p.write_text(s)

# AI Settings: task-specific providers, Gemini on fresh install.
p = Path('lib/llm_settings_page.dart')
s = p.read_text()
field_anchor = "  String provider = 'gemini';\n"
fields = """  String examProvider = 'gemini';
  String explanationProvider = 'gemini';
  String guideProvider = 'gemini';
  String promptProvider = 'gemini';
"""
if "String examProvider = 'gemini';" not in s:
    s = s.replace(field_anchor, field_anchor + fields, 1)
load_anchor = "    provider = p.getString('llm_provider') ?? 'gemini';\n"
load = """    examProvider = p.getString('ai_task_exam') ?? 'gemini';
    explanationProvider = p.getString('ai_task_explanation') ?? 'gemini';
    guideProvider = p.getString('ai_task_guide') ?? 'gemini';
    promptProvider = p.getString('ai_task_prompt') ?? 'gemini';
"""
if "p.getString('ai_task_exam')" not in s:
    s = s.replace(load_anchor, load_anchor + load, 1)
save_anchor = "    await p.setString('llm_provider', provider);\n"
save = """    await p.setString('ai_task_exam', examProvider);
    await p.setString('ai_task_explanation', explanationProvider);
    await p.setString('ai_task_guide', guideProvider);
    await p.setString('ai_task_prompt', promptProvider);
"""
if "p.setString('ai_task_exam'" not in s:
    s = s.replace(save_anchor, save_anchor + save, 1)
ui_anchor = "                  const SizedBox(height: 22),\n                  FilledButton.icon(\n                    onPressed: _save,"
ui = r'''                  const SizedBox(height: 22),
                  const Divider(),
                  const SizedBox(height: 10),
                  const Text('AI by task', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 6),
                  const Text('Each task starts with its selected AI. If unavailable, Memora falls back: Gemini → OpenAI → Ollama → on-phone model.'),
                  const SizedBox(height: 12),
                  for (final task in <(String, String, String)>[
                    ('Exam creation', 'exam', examProvider),
                    ('Exam explanations', 'explanation', explanationProvider),
                    ('Guide creation', 'guide', guideProvider),
                    ('Prompt generation', 'prompt', promptProvider),
                  ])
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: DropdownButtonFormField<String>(
                        value: task.$3,
                        decoration: InputDecoration(labelText: task.$1),
                        items: const [
                          DropdownMenuItem(value: 'gemini', child: Text('Gemini')),
                          DropdownMenuItem(value: 'openai', child: Text('OpenAI')),
                          DropdownMenuItem(value: 'local', child: Text('Ollama')),
                          DropdownMenuItem(value: 'device', child: Text('On-phone model')),
                        ],
                        onChanged: (value) {
                          final v = value ?? 'gemini';
                          setState(() {
                            if (task.$2 == 'exam') examProvider = v;
                            if (task.$2 == 'explanation') explanationProvider = v;
                            if (task.$2 == 'guide') guideProvider = v;
                            if (task.$2 == 'prompt') promptProvider = v;
                          });
                        },
                      ),
                    ),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: _save,'''
if 'AI by task' not in s:
    if ui_anchor not in s: raise RuntimeError('v1.44 AI settings UI anchor not found')
    s = s.replace(ui_anchor, ui, 1)
p.write_text(s)

# Exams: AI primary; randomized cards only fill missing slots.
p = Path('lib/daily_exam_page.dart')
s = p.read_text()
start = s.find('  List<ExamQuestionData> _cardQuestions(')
parse_anchor = s.find('  List<ExamQuestionData> _parseAiQuestions(', start)
if start < 0 or parse_anchor < 0: raise RuntimeError('v1.44 card fallback block not found')
block = s[start:parse_anchor]
sort_start = block.find('    pool.sort((a, b) {')
return_start = block.find('    return pool', sort_start)
if sort_start >= 0 and return_start >= 0:
    block = block[:sort_start] + "    pool.shuffle(Random(DateTime.now().microsecondsSinceEpoch));\n" + block[return_start:]
    s = s[:start] + block + s[parse_anchor:]
s = s.replace('final raw = await AiService.askConfigured(\n', "final raw = await AiService.askCascade(\n          task: 'exam',\n")
p.write_text(s)

# Tutor prompt generator.
p = Path('lib/tutor_page.dart')
s = p.read_text()
method_anchor = '  Future<TutorProfile?> _editTutorDialog({TutorProfile? existing}) async {\n'
method = r'''  Future<String> _generateTutorPrompt(String description) async {
    if (description.trim().isEmpty) return '';
    return AiService.askCascade(
      task: 'prompt',
      responseMode: 'fast',
      prompt: """Create a concise, production-ready system prompt for a study tutor in Memora from this user description:
$description
Include role, teaching behavior, response style, use of assigned study guides, uncertainty handling, and useful learning rules. Return only the prompt.""",
    );
  }

'''
if '_generateTutorPrompt(' not in s:
    if method_anchor not in s: raise RuntimeError('v1.44 tutor dialog anchor not found')
    s = s.replace(method_anchor, method + method_anchor, 1)
target = """                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: source,"""
button = r'''                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: () async {
                    final generated = await _generateTutorPrompt(description.text);
                    if (generated.isNotEmpty) {
                      instructions.text = generated;
                      setDialogState(() {});
                    }
                  },
                  icon: const Icon(Icons.auto_awesome),
                  label: const Text('Generate prompt from description'),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: source,'''
pos = s.find(method_anchor)
idx = s.find(target, pos)
if idx >= 0 and 'Generate prompt from description' not in s[pos:idx+1000]:
    s = s[:idx] + s[idx:].replace(target, button, 1)
p.write_text(s)

# Agent prompt generator.
p = Path('lib/agent_page.dart')
s = p.read_text()
agent_anchor = '  Future<AgentProfile?> _agentDialog({AgentProfile? existing}) async {\n'
agent_method = r'''  Future<String> _generateAgentPrompt(String description) async {
    if (description.trim().isEmpty) return '';
    return AiService.askCascade(
      task: 'prompt',
      responseMode: 'fast',
      prompt: """Create a concise, production-ready system prompt for a Memora agent from this user description:
$description
Define role, objectives, behavior, response format, use of assigned knowledge bases, boundaries and uncertainty handling. Return only the prompt.""",
    );
  }

'''
if '_generateAgentPrompt(' not in s:
    if agent_anchor not in s: raise RuntimeError('v1.44 agent dialog anchor not found')
    s = s.replace(agent_anchor, agent_method + agent_anchor, 1)
old = "    final prompt = TextEditingController(text: existing?.prompt ?? '');\n"
if 'final promptDescription = TextEditingController' not in s:
    s = s.replace(old, old + "    final promptDescription = TextEditingController();\n", 1)
prompt_field = """                TextField(
                  controller: prompt,
                  minLines: 5,"""
insert = r'''                TextField(
                  controller: promptDescription,
                  minLines: 2,
                  maxLines: 4,
                  decoration: const InputDecoration(
                    labelText: 'Describe what this agent should do',
                    hintText: 'Example: Analyze my assigned finance guides and answer with practical steps.',
                  ),
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: () async {
                    final generated = await _generateAgentPrompt(promptDescription.text);
                    if (generated.isNotEmpty) {
                      prompt.text = generated;
                      setDialogState(() {});
                    }
                  },
                  icon: const Icon(Icons.auto_awesome),
                  label: const Text('Generate prompt with AI'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: prompt,
                  minLines: 5,'''
if 'Describe what this agent should do' not in s:
    if prompt_field not in s: raise RuntimeError('v1.44 agent prompt field anchor not found')
    s = s.replace(prompt_field, insert, 1)
p.write_text(s)

# Version bump and continue chain.
p = Path('pubspec.yaml')
s = p.read_text().replace('version: 1.43.0+56', 'version: 1.44.0+57')
p.write_text(s)
print('Memora v1.44 automation + AI controls patch applied successfully')
_v145 = Path(os.environ['GITHUB_WORKSPACE']) / 'memora_upgrade' / 'v145_remaining_improvements_patch.py'
exec(compile(_v145.read_text(), str(_v145), 'exec'))
