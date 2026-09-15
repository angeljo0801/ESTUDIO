import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'ai_service.dart';
import 'guide_store.dart';
import 'knowledge_retriever.dart';
import 'models.dart';

const Set<String> _agentSources = {
  'global',
  'private',
  'shared',
  'gemini',
  'openai',
  'local',
};

class AgentProfile {
  const AgentProfile({
    required this.id,
    required this.name,
    required this.prompt,
    this.modelSource = 'global',
    this.guideIds = const [],
  });

  final String id;
  final String name;
  final String prompt;
  final String modelSource;
  final List<String> guideIds;

  AgentProfile copyWith({
    String? name,
    String? prompt,
    String? modelSource,
    List<String>? guideIds,
  }) =>
      AgentProfile(
        id: id,
        name: name ?? this.name,
        prompt: prompt ?? this.prompt,
        modelSource: modelSource ?? this.modelSource,
        guideIds: guideIds ?? this.guideIds,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'prompt': prompt,
        'modelSource': modelSource,
        'guideIds': guideIds,
      };

  factory AgentProfile.fromJson(Map<String, dynamic> json) {
    final source = json['modelSource']?.toString() ?? 'global';
    final rawGuides = json['guideIds'];
    return AgentProfile(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? 'Agente',
      prompt: json['prompt']?.toString() ?? '',
      modelSource: _agentSources.contains(source) ? source : 'global',
      guideIds: rawGuides is List
          ? rawGuides.map((e) => e.toString()).where((e) => e.isNotEmpty).toList()
          : const [],
    );
  }
}

class AgentPage extends StatefulWidget {
  const AgentPage({super.key, required this.store});
  final GuideStore store;

  @override
  State<AgentPage> createState() => _AgentPageState();
}

class _AgentPageState extends State<AgentPage> {
  static const _profilesKey = 'memora_agent_profiles_v1';
  static const _activeKey = 'memora_active_agent_id';
  static const _responseModeKey = 'memora_response_mode';

  final input = TextEditingController();
  List<AgentProfile> agents = [];
  String? activeId;
  String answer =
      'Crea un agente, asígnale un prompt, una IA y sus bases de conocimiento.';
  String responseMode = 'fast';
  String accelerationLabel = 'Se detectará al usar un GGUF';
  bool loading = true;
  bool busy = false;

  AgentProfile? get activeAgent {
    if (agents.isEmpty) return null;
    return agents.firstWhere((a) => a.id == activeId, orElse: () => agents.first);
  }

  List<StudyGuide> get activeGuides {
    final agent = activeAgent;
    if (agent == null) return const [];
    return widget.store.guides.where((g) => agent.guideIds.contains(g.id)).toList();
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    input.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    responseMode = prefs.getString(_responseModeKey) ?? 'fast';
    accelerationLabel =
        prefs.getString('device_acceleration_status') ?? 'Se detectará al usar un GGUF';
    final raw = prefs.getString(_profilesKey);
    if (raw != null && raw.isNotEmpty) {
      try {
        final decoded = jsonDecode(raw) as List<dynamic>;
        agents = decoded
            .whereType<Map>()
            .map((e) => AgentProfile.fromJson(Map<String, dynamic>.from(e)))
            .where((a) => a.id.isNotEmpty)
            .map(
              (a) => a.copyWith(
                guideIds: a.guideIds
                    .where((id) => widget.store.guides.any((g) => g.id == id))
                    .toList(),
              ),
            )
            .toList();
      } catch (_) {
        agents = [];
      }
    }
    final saved = prefs.getString(_activeKey);
    if (saved != null && agents.any((a) => a.id == saved)) {
      activeId = saved;
    } else if (agents.isNotEmpty) {
      activeId = agents.first.id;
    }
    if (mounted) setState(() => loading = false);
  }

  Future<void> _save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _profilesKey,
      jsonEncode(agents.map((a) => a.toJson()).toList()),
    );
    if (activeId != null) await prefs.setString(_activeKey, activeId!);
  }

  Future<void> _setResponseMode(String mode) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_responseModeKey, mode);
    if (mounted) setState(() => responseMode = mode);
  }

  (int, int) _retrievalLimits() {
    switch (responseMode) {
      case 'fast':
        return (4500, 4);
      case 'deep':
        return (12000, 10);
      default:
        return (8000, 6);
    }
  }

  String _sourceLabel(String value) {
    switch (value) {
      case 'private':
        return 'GGUF privado';
      case 'shared':
        return 'GGUF compartido';
      case 'gemini':
        return 'Gemini';
      case 'openai':
        return 'OpenAI / compatible';
      case 'local':
        return 'Ollama / servidor local';
      default:
        return 'Configuración general';
    }
  }

  Future<AgentProfile?> _agentDialog({AgentProfile? existing}) async {
    final name = TextEditingController(text: existing?.name ?? '');
    final prompt = TextEditingController(text: existing?.prompt ?? '');
    var source = existing?.modelSource ?? 'global';

    final result = await showDialog<AgentProfile>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text(existing == null ? 'Crear agente' : 'Editar agente'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: name,
                  decoration: const InputDecoration(
                    labelText: 'Nombre del agente',
                    hintText: 'Ej. Analista de gastos',
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: prompt,
                  minLines: 5,
                  maxLines: 10,
                  decoration: const InputDecoration(
                    labelText: 'Prompt del agente',
                    alignLabelWithHint: true,
                    hintText: 'Define qué debe hacer, cómo responder y qué reglas seguir…',
                  ),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: source,
                  decoration: const InputDecoration(labelText: 'IA / modelo del agente'),
                  items: const [
                    DropdownMenuItem(value: 'global', child: Text('Configuración general')),
                    DropdownMenuItem(
                      value: 'private',
                      child: Text('GGUF privado de Memora'),
                    ),
                    DropdownMenuItem(value: 'shared', child: Text('GGUF compartido')),
                    DropdownMenuItem(value: 'gemini', child: Text('Gemini configurado')),
                    DropdownMenuItem(
                      value: 'openai',
                      child: Text('OpenAI / compatible configurado'),
                    ),
                    DropdownMenuItem(
                      value: 'local',
                      child: Text('Ollama / servidor local configurado'),
                    ),
                  ],
                  onChanged: (value) =>
                      setDialogState(() => source = value ?? 'global'),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              onPressed: () {
                if (name.text.trim().isEmpty || prompt.text.trim().isEmpty) return;
                Navigator.pop(
                  dialogContext,
                  AgentProfile(
                    id: existing?.id ??
                        'agent_${DateTime.now().microsecondsSinceEpoch}',
                    name: name.text.trim(),
                    prompt: prompt.text.trim(),
                    modelSource: source,
                    guideIds: existing?.guideIds ?? const [],
                  ),
                );
              },
              child: const Text('Guardar'),
            ),
          ],
        ),
      ),
    );

    name.dispose();
    prompt.dispose();
    return result;
  }

  Future<void> _createAgent() async {
    final created = await _agentDialog();
    if (created == null) return;
    setState(() {
      agents = [...agents, created];
      activeId = created.id;
      answer = 'Agente ${created.name} creado. Asígnale sus bases de conocimiento.';
    });
    await _save();
  }

  Future<void> _editAgent() async {
    final current = activeAgent;
    if (current == null) return;
    final edited = await _agentDialog(existing: current);
    if (edited == null) return;
    final index = agents.indexWhere((a) => a.id == current.id);
    final updated = List<AgentProfile>.from(agents);
    updated[index] = edited;
    setState(() => agents = updated);
    await _save();
  }

  Future<void> _assignGuides() async {
    final current = activeAgent;
    if (current == null) return;
    final working = current.guideIds.toSet();
    final result = await showModalBottomSheet<Set<String>>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => StatefulBuilder(
        builder: (context, setSheetState) => SafeArea(
          child: SizedBox(
            height: MediaQuery.of(context).size.height * .8,
            child: Column(
              children: [
                const Padding(
                  padding: EdgeInsets.all(16),
                  child: Text(
                    'Bases de conocimiento del agente',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                ),
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 16),
                  child: Text(
                    'Puedes asignar PDF, Excel u otras guías. Memora buscará primero los fragmentos más relacionados con cada solicitud.',
                  ),
                ),
                Expanded(
                  child: ListView(
                    children: [
                      for (final guide in widget.store.guides)
                        CheckboxListTile(
                          value: working.contains(guide.id),
                          title: Text(guide.title),
                          subtitle: Text(
                            '${guide.sourceType.toUpperCase()} • ${guide.sourceName}',
                          ),
                          onChanged: (value) => setSheetState(() {
                            if (value == true) {
                              working.add(guide.id);
                            } else {
                              working.remove(guide.id);
                            }
                          }),
                        ),
                    ],
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: FilledButton(
                    onPressed: () => Navigator.pop(sheetContext, working),
                    child: Text('Guardar ${working.length} base(s)'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
    if (result == null) return;
    final index = agents.indexWhere((a) => a.id == current.id);
    final updated = List<AgentProfile>.from(agents);
    updated[index] = current.copyWith(guideIds: result.toList());
    setState(() => agents = updated);
    await _save();
  }

  Future<void> _deleteAgent() async {
    final current = activeAgent;
    if (current == null) return;
    final yes = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Eliminar agente'),
        content: Text('¿Eliminar a ${current.name}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Eliminar'),
          ),
        ],
      ),
    );
    if (yes != true) return;
    setState(() {
      agents = agents.where((a) => a.id != current.id).toList();
      activeId = agents.isEmpty ? null : agents.first.id;
      answer = agents.isEmpty
          ? 'Crea un agente para empezar.'
          : 'Agente activo: ${activeAgent!.name}';
    });
    await _save();
  }

  Future<void> _cancel() async {
    await AiService.cancelCurrent();
  }

  Future<void> _runAgent() async {
    final agent = activeAgent;
    final request = input.text.trim();
    if (agent == null || request.isEmpty || busy) return;

    setState(() {
      busy = true;
      answer = 'Preparando respuesta…';
    });

    try {
      final limits = _retrievalLimits();
      final context = KnowledgeRetriever.buildContext(
        guides: activeGuides,
        query: '${agent.prompt}\n$request',
        maxChars: limits.$1,
        maxChunks: limits.$2,
      );
      final result = await AiService.askConfigured(
        providerOverride: agent.modelSource,
        responseMode: responseMode,
        onPartial: (partial) {
          if (mounted && partial.isNotEmpty) setState(() => answer = partial);
        },
        prompt: '''Eres un agente personalizado de Memora llamado ${agent.name}.
PROMPT DEL AGENTE:
${agent.prompt}

FRAGMENTOS RELEVANTES DE SUS BASES:
$context

SOLICITUD DEL USUARIO:
$request

Sigue el prompt del agente. Usa los fragmentos asignados cuando sean relevantes. Si un dato solicitado debería estar en las bases pero no aparece, indícalo en vez de inventarlo. En modo rápido prioriza una respuesta breve; en modo profundo puedes desarrollar más el análisis.''',
      );
      if (mounted) {
        setState(() {
          answer = result;
          accelerationLabel = AiService.localAccelerationLabel;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => answer =
            'El agente no pudo responder: ${AiService.userFacingError(e)}');
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('Agentes'),
          actions: [
            IconButton(
              onPressed: _createAgent,
              tooltip: 'Crear agente',
              icon: const Icon(Icons.add_circle_outline),
            ),
          ],
        ),
        body: loading
            ? const Center(child: CircularProgressIndicator())
            : agents.isEmpty
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(28),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.smart_toy_outlined, size: 72),
                          const SizedBox(height: 16),
                          const Text(
                            'Crea tu primer agente',
                            style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 8),
                          const Text(
                            'Dale un nombre, un prompt, una IA y sus PDF/Excel como bases de conocimiento.',
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 18),
                          FilledButton.icon(
                            onPressed: _createAgent,
                            icon: const Icon(Icons.add),
                            label: const Text('Crear agente'),
                          ),
                        ],
                      ),
                    ),
                  )
                : ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      DropdownButtonFormField<String>(
                        initialValue: activeAgent!.id,
                        decoration: const InputDecoration(
                          labelText: 'Agente activo',
                          prefixIcon: Icon(Icons.smart_toy_outlined),
                        ),
                        items: [
                          for (final agent in agents)
                            DropdownMenuItem(
                              value: agent.id,
                              child: Text(agent.name),
                            ),
                        ],
                        onChanged: (value) async {
                          if (value == null) return;
                          setState(() => activeId = value);
                          await _save();
                        },
                      ),
                      const SizedBox(height: 10),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                activeAgent!.name,
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 18,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                activeAgent!.prompt,
                                maxLines: 4,
                                overflow: TextOverflow.ellipsis,
                              ),
                              const SizedBox(height: 6),
                              Text(
                                '${_sourceLabel(activeAgent!.modelSource)} • ${activeGuides.length} base(s)',
                              ),
                              const SizedBox(height: 10),
                              Wrap(
                                spacing: 8,
                                runSpacing: 8,
                                children: [
                                  OutlinedButton.icon(
                                    onPressed: _editAgent,
                                    icon: const Icon(Icons.edit),
                                    label: const Text('Editar'),
                                  ),
                                  OutlinedButton.icon(
                                    onPressed: _assignGuides,
                                    icon: const Icon(Icons.library_add_check),
                                    label: const Text('Bases'),
                                  ),
                                  OutlinedButton.icon(
                                    onPressed: _deleteAgent,
                                    icon: const Icon(Icons.delete_outline),
                                    label: const Text('Eliminar'),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 10),
                      SegmentedButton<String>(
                        segments: const [
                          ButtonSegment(
                            value: 'fast',
                            icon: Icon(Icons.bolt),
                            label: Text('Rápido'),
                          ),
                          ButtonSegment(
                            value: 'normal',
                            icon: Icon(Icons.balance),
                            label: Text('Normal'),
                          ),
                          ButtonSegment(
                            value: 'deep',
                            icon: Icon(Icons.psychology),
                            label: Text('Profundo'),
                          ),
                        ],
                        selected: {responseMode},
                        onSelectionChanged: busy
                            ? null
                            : (values) => _setResponseMode(values.first),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Motor GGUF: $accelerationLabel',
                        style: Theme.of(context).textTheme.bodySmall,
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 10),
                      if (activeGuides.isNotEmpty)
                        Card(
                          child: ExpansionTile(
                            title: const Text('Bases de conocimiento'),
                            subtitle: Text('${activeGuides.length} asignada(s)'),
                            children: [
                              for (final guide in activeGuides)
                                ListTile(
                                  dense: true,
                                  leading: Icon(
                                    guide.sourceType == 'xlsx' ||
                                            guide.sourceType == 'xls'
                                        ? Icons.table_chart
                                        : Icons.description_outlined,
                                  ),
                                  title: Text(guide.title),
                                  subtitle: Text(guide.sourceType.toUpperCase()),
                                ),
                            ],
                          ),
                        ),
                      const SizedBox(height: 10),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(18),
                          child: SelectableText(answer),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: input,
                        minLines: 2,
                        maxLines: 6,
                        decoration: InputDecoration(
                          hintText: 'Pide algo a ${activeAgent!.name}…',
                          suffixIcon: IconButton(
                            tooltip: busy ? 'Detener generación' : 'Enviar',
                            onPressed: busy ? _cancel : _runAgent,
                            icon: busy
                                ? const Icon(Icons.stop_circle_outlined)
                                : const Icon(Icons.send),
                          ),
                        ),
                        onSubmitted: (_) {
                          if (!busy) _runAgent();
                        },
                      ),
                    ],
                  ),
      );
}
