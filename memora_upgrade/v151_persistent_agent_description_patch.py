from pathlib import Path
import os

# Agents: description and prompt are separate persistent fields. The automatic
# prompt generator reads the saved/editable description and writes the prompt;
# the generated prompt remains persisted until the user edits/regenerates it.
p = Path('lib/agent_page.dart')
s = p.read_text()

# Model + persistence.
s = s.replace("    required this.name,\n    required this.prompt,", "    required this.name,\n    this.description = '',\n    required this.prompt,", 1)
s = s.replace("  final String name;\n  final String prompt;", "  final String name;\n  final String description;\n  final String prompt;", 1)
s = s.replace("    String? name,\n    String? prompt,", "    String? name,\n    String? description,\n    String? prompt,", 1)
s = s.replace("        name: name ?? this.name,\n        prompt: prompt ?? this.prompt,", "        name: name ?? this.name,\n        description: description ?? this.description,\n        prompt: prompt ?? this.prompt,", 1)
s = s.replace("        'name': name,\n        'prompt': prompt,", "        'name': name,\n        'description': description,\n        'prompt': prompt,", 1)
s = s.replace("      name: json['name']?.toString() ?? 'Agente',\n      prompt: json['prompt']?.toString() ?? '',", "      name: json['name']?.toString() ?? 'Agente',\n      description: json['description']?.toString() ?? '',\n      prompt: json['prompt']?.toString() ?? '',", 1)

s = s.replace(
    "    final promptDescription = TextEditingController();",
    "    final promptDescription = TextEditingController(text: existing?.description ?? '');",
    1,
)

needle = "                    name: name.text.trim(),\n                    prompt: prompt.text.trim(),"
replacement = "                    name: name.text.trim(),\n                    description: promptDescription.text.trim(),\n                    prompt: prompt.text.trim(),"
if needle not in s:
    raise RuntimeError('agent save profile anchor not found')
s = s.replace(needle, replacement, 1)

s = s.replace("    name.dispose();\n    prompt.dispose();", "    name.dispose();\n    promptDescription.dispose();\n    prompt.dispose();", 1)
s = s.replace("activeAgent!.prompt.trim().isEmpty\n                                    ? 'No description has been added for this agent yet.'\n                                    : activeAgent!.prompt.trim()", "activeAgent!.description.trim().isEmpty\n                                    ? 'Todavía no se ha añadido una descripción para este agente.'\n                                    : activeAgent!.description.trim()", 1)
s = s.replace("'Description'", "'Descripción'", 1)
p.write_text(s)

p = Path('lib/tutor_page.dart')
t = p.read_text()
t = t.replace("'Description'", "'Descripción'", 1)
t = t.replace("'No description has been added for this tutor yet.'", "'Todavía no se ha añadido una descripción para este tutor.'", 1)
p.write_text(t)

print('Persistent agent descriptions and description-driven prompt generation enabled')

_v152=Path(os.environ['GITHUB_WORKSPACE'])/'memora_upgrade'/'v152_agent_tutor_response_parity_patch.py'
exec(compile(_v152.read_text(),str(_v152),'exec'))
