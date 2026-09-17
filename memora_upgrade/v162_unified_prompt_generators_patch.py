from pathlib import Path

# v162: restore consistent description-driven automatic prompt generation for
# Tutors, Agents and Orchestrators after the v159 directory rewrite.
# Descriptions stay separate from prompts and are persisted.

p = Path('lib/agent_profiles.dart')
s = p.read_text()

repls = [
    (
        "    required this.name,\n    required this.prompt,",
        "    required this.name,\n    this.description = '',\n    required this.prompt,",
    ),
    (
        "  final String name;\n  final String prompt;",
        "  final String name;\n  final String description;\n  final String prompt;",
    ),
    (
        "  AgentProfile copyWith({String? name, String? prompt, String? modelSource, List<String>? guideIds}) => AgentProfile(",
        "  AgentProfile copyWith({String? name, String? description, String? prompt, String? modelSource, List<String>? guideIds}) => AgentProfile(",
    ),
    (
        "    name: name ?? this.name,\n    prompt: prompt ?? this.prompt,",
        "    name: name ?? this.name,\n    description: description ?? this.description,\n    prompt: prompt ?? this.prompt,",
    ),
    (
        "    'id': id, 'name': name, 'prompt': prompt,",
        "    'id': id, 'name': name, 'description': description, 'prompt': prompt,",
    ),
    (
        "      name: json['name']?.toString() ?? 'Agente',\n      prompt: json['prompt']?.toString() ?? '',",
        "      name: json['name']?.toString() ?? 'Agente',\n      description: json['description']?.toString() ?? '',\n      prompt: json['prompt']?.toString() ?? '',",
    ),
]
for old, new in repls:
    if old not in s:
        raise SystemExit('v162 agent profile anchor missing: ' + old[:70])
    s = s.replace(old, new, 1)
p.write_text(s)

p = Path('lib/agent_page.dart')
s = p.read_text()

anchor = "  Future<AgentProfile?> _agentDialog({AgentProfile? existing}) async {\n"
method = r"""  Future<String> _generateAgentPrompt(String description) async {
    if (description.trim().isEmpty) return '';
    return AiService.askCascade(
      task: 'prompt',
      responseMode: 'fast',
      prompt: '''Crea un prompt de sistema conciso y listo para producción para un agente de Memora a partir de esta descripción del usuario:
$description

Define claramente: rol, objetivos, comportamiento, formato de respuesta, cómo usar sus bases de conocimiento asignadas, límites, manejo de incertidumbre y cuándo debe decir que no tiene información suficiente.
Devuelve solamente el prompt final.''',
    );
  }

  Future<String> _generateOrchestratorPrompt(String description) async {
    if (description.trim().isEmpty) return '';
    return AiService.askCascade(
      task: 'prompt',
      responseMode: 'fast',
      prompt: '''Crea un prompt de sistema conciso y listo para producción para un orquestador de Memora a partir de esta descripción del usuario:
$description

Define claramente: misión del orquestador, cómo coordinar agentes autorizados, cómo dividir trabajos, cómo pasar contexto entre agentes, cómo integrar resultados, cómo manejar contradicciones e incertidumbre y que nunca debe crear ni activar agentes sin decisión explícita del usuario.
Devuelve solamente el prompt final.''',
    );
  }

"""
if '_generateAgentPrompt(String description)' not in s:
    if anchor not in s:
        raise SystemExit('v162 agent dialog anchor missing')
    s = s.replace(anchor, method + anchor, 1)

old = """    final name = TextEditingController(text: existing?.name ?? '');
    final prompt = TextEditingController(text: existing?.prompt ?? '');
    var source = existing?.modelSource ?? 'global';
"""
new = """    final name = TextEditingController(text: existing?.name ?? '');
    final description = TextEditingController(text: existing?.description ?? '');
    final prompt = TextEditingController(text: existing?.prompt ?? '');
    var source = existing?.modelSource ?? 'global';
"""
if old not in s:
    raise SystemExit('v162 agent controllers anchor missing')
s = s.replace(old, new, 1)

old = """          TextField(controller:name,decoration:const InputDecoration(labelText:'Nombre del agente')),
          const SizedBox(height:12),
          TextField(controller:prompt,minLines:5,maxLines:10,decoration:const InputDecoration(labelText:'Prompt / función',alignLabelWithHint:true)),
"""
new = """          TextField(controller:name,decoration:const InputDecoration(labelText:'Nombre del agente')),
          const SizedBox(height:12),
          TextField(
            controller:description,
            minLines:2,
            maxLines:5,
            decoration:const InputDecoration(
              labelText:'Descripción',
              hintText:'Ej. Analiza mis guías de finanzas y responde con pasos prácticos.',
              alignLabelWithHint:true,
            ),
          ),
          const SizedBox(height:8),
          OutlinedButton.icon(
            onPressed:() async {
              if(description.text.trim().isEmpty){
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content:Text('Escribe primero la descripción del agente.')),
                );
                return;
              }
              try{
                final generated=await _generateAgentPrompt(description.text);
                if(generated.isNotEmpty){prompt.text=generated;setD((){});}
              }catch(e){
                if(context.mounted)ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content:Text('No pude generar el prompt: ${AiService.userFacingError(e)}')),
                );
              }
            },
            icon:const Icon(Icons.auto_awesome),
            label:const Text('Generar prompt automáticamente'),
          ),
          const SizedBox(height:12),
          TextField(controller:prompt,minLines:5,maxLines:10,decoration:const InputDecoration(labelText:'Prompt / función',alignLabelWithHint:true)),
"""
if old not in s:
    raise SystemExit('v162 agent dialog fields anchor missing')
s = s.replace(old, new, 1)

old = """            if(name.text.trim().isEmpty||prompt.text.trim().isEmpty)return;
            Navigator.pop(dc,AgentProfile(
              id:existing?.id??'agent_${DateTime.now().microsecondsSinceEpoch}',
              name:name.text.trim(),prompt:prompt.text.trim(),modelSource:source,
"""
new = """            if(name.text.trim().isEmpty||description.text.trim().isEmpty||prompt.text.trim().isEmpty)return;
            Navigator.pop(dc,AgentProfile(
              id:existing?.id??'agent_${DateTime.now().microsecondsSinceEpoch}',
              name:name.text.trim(),description:description.text.trim(),prompt:prompt.text.trim(),modelSource:source,
"""
if old not in s:
    raise SystemExit('v162 agent save anchor missing')
s = s.replace(old, new, 1)

old = "    name.dispose(); prompt.dispose(); return result;\n  }\n\n  Future<OrchestratorProfile?> _orchestratorDialog"
new = "    name.dispose(); description.dispose(); prompt.dispose(); return result;\n  }\n\n  Future<OrchestratorProfile?> _orchestratorDialog"
if old not in s:
    raise SystemExit('v162 agent dispose anchor missing')
s = s.replace(old, new, 1)

old = """          TextField(controller:description,minLines:2,maxLines:4,decoration:const InputDecoration(labelText:'Descripción')),
          const SizedBox(height:12),
          TextField(controller:prompt,minLines:4,maxLines:8,decoration:const InputDecoration(labelText:'Instrucciones del orquestador',alignLabelWithHint:true)),
"""
new = """          TextField(controller:description,minLines:2,maxLines:5,decoration:const InputDecoration(labelText:'Descripción',alignLabelWithHint:true)),
          const SizedBox(height:8),
          OutlinedButton.icon(
            onPressed:() async {
              if(description.text.trim().isEmpty){
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content:Text('Escribe primero la descripción del orquestador.')),
                );
                return;
              }
              try{
                final generated=await _generateOrchestratorPrompt(description.text);
                if(generated.isNotEmpty){prompt.text=generated;setD((){});}
              }catch(e){
                if(context.mounted)ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content:Text('No pude generar el prompt: ${AiService.userFacingError(e)}')),
                );
              }
            },
            icon:const Icon(Icons.auto_awesome),
            label:const Text('Generar prompt automáticamente'),
          ),
          const SizedBox(height:12),
          TextField(controller:prompt,minLines:4,maxLines:8,decoration:const InputDecoration(labelText:'Instrucciones del orquestador',alignLabelWithHint:true)),
"""
if old not in s:
    raise SystemExit('v162 orchestrator directory fields anchor missing')
s = s.replace(old, new, 1)

old = """            if(name.text.trim().isEmpty)return;
            Navigator.pop(dc,OrchestratorProfile(
"""
new = """            if(name.text.trim().isEmpty||description.text.trim().isEmpty||prompt.text.trim().isEmpty)return;
            Navigator.pop(dc,OrchestratorProfile(
"""
if old not in s:
    raise SystemExit('v162 orchestrator save anchor missing')
s = s.replace(old, new, 1)

old = "subtitle:'${memoraAiSourceLabel(a.modelSource)} • ${a.guideIds.length} base(s)'"
new = "subtitle:a.description.trim().isEmpty?'${memoraAiSourceLabel(a.modelSource)} • ${a.guideIds.length} base(s)':'${a.description} • ${memoraAiSourceLabel(a.modelSource)} • ${a.guideIds.length} base(s)'"
if old not in s:
    raise SystemExit('v162 agent card subtitle anchor missing')
s = s.replace(old, new, 1)

p.write_text(s)

p = Path('lib/agent_orchestrator_page.dart')
s = p.read_text()

anchor = "  Future<void> _edit()async{"
method = r"""  Future<String> _generateOrchestratorPrompt(String description) async {
    if (description.trim().isEmpty) return '';
    return AiService.askCascade(
      task: 'prompt',
      responseMode: 'fast',
      prompt: '''Crea un prompt de sistema conciso y listo para producción para un orquestador de Memora a partir de esta descripción del usuario:
$description

Define misión, coordinación de agentes autorizados, descomposición de trabajos, transferencia de contexto, integración final, manejo de contradicciones e incertidumbre. Nunca debe crear ni activar agentes automáticamente.
Devuelve solamente el prompt final.''',
    );
  }

"""
if '_generateOrchestratorPrompt(String description)' not in s:
    if anchor not in s:
        raise SystemExit('v162 orchestrator edit anchor missing')
    s = s.replace(anchor, method + anchor, 1)

old = """TextField(controller:desc,minLines:2,maxLines:4,decoration:const InputDecoration(labelText:'Descripción')),const SizedBox(height:12),TextField(controller:prompt,minLines:4,maxLines:8,decoration:const InputDecoration(labelText:'Instrucciones',alignLabelWithHint:true))"""
new = """TextField(controller:desc,minLines:2,maxLines:5,decoration:const InputDecoration(labelText:'Descripción',alignLabelWithHint:true)),const SizedBox(height:8),OutlinedButton.icon(onPressed:() async {if(desc.text.trim().isEmpty){ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('Escribe primero la descripción del orquestador.')));return;}try{final generated=await _generateOrchestratorPrompt(desc.text);if(generated.isNotEmpty){prompt.text=generated;setD((){});}}catch(e){if(context.mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('No pude generar el prompt: ${AiService.userFacingError(e)}')));}},icon:const Icon(Icons.auto_awesome),label:const Text('Generar prompt automáticamente')),const SizedBox(height:12),TextField(controller:prompt,minLines:4,maxLines:8,decoration:const InputDecoration(labelText:'Instrucciones',alignLabelWithHint:true))"""
if old not in s:
    raise SystemExit('v162 internal orchestrator fields anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)

p = Path('lib/tutor_page.dart')
s = p.read_text()
anchor = '  Future<TutorProfile?> _editTutorDialog({TutorProfile? existing}) async {\\n'
if '_generateTutorPrompt(String description)' not in s:
    method = r"""  Future<String> _generateTutorPrompt(String description) async {
    if (description.trim().isEmpty) return '';
    return AiService.askCascade(
      task: 'prompt',
      responseMode: 'fast',
      prompt: '''Crea un prompt de sistema conciso y listo para producción para un tutor de estudio de Memora a partir de esta descripción del usuario:
$description

Incluye rol, forma de enseñar, estilo de respuesta, uso de guías asignadas, manejo de incertidumbre y reglas útiles de aprendizaje.
Devuelve solamente el prompt final.''',
    );
  }

"""
    if anchor not in s:
        raise SystemExit('v162 tutor dialog anchor missing')
    s = s.replace(anchor, method + anchor, 1)

s = s.replace("label: const Text('Generate prompt from description')", "label: const Text('Generar prompt automáticamente')")
s = s.replace("label: const Text('Generate prompt with AI')", "label: const Text('Generar prompt automáticamente')")
p.write_text(s)

print('v162 applied: description-driven automatic prompts for Tutors, Agents and Orchestrators')
