from pathlib import Path

# v158: Orchestrator recommendations are advisory only.
# No agent is auto-created or auto-selected. Existing-agent recommendations are
# ranked locally to avoid extra AI calls; the user explicitly chooses what to use.

orch = r'''import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'agent_page.dart';
import 'ai_service.dart';
import 'guide_store.dart';
import 'knowledge_retriever.dart';
import 'llm_settings_page.dart';

class AgentOrchestratorPage extends StatefulWidget {
  const AgentOrchestratorPage({super.key, required this.store});
  final GuideStore store;

  @override
  State<AgentOrchestratorPage> createState() => _AgentOrchestratorPageState();
}

class _AgentRecommendation {
  const _AgentRecommendation(this.agent, this.score, this.matches);
  final AgentProfile agent;
  final int score;
  final List<String> matches;
}

class _AgentOrchestratorPageState extends State<AgentOrchestratorPage> {
  static const _profilesKey = 'memora_agent_profiles_v1';
  static const _enabledKey = 'memora_orchestrator_enabled_agent_ids_v1';

  final input = TextEditingController();
  List<AgentProfile> agents = [];
  Set<String> enabled = {};
  List<_AgentRecommendation> recommendations = [];
  List<String> suggestedRoles = [];
  String answer =
      'Describe un trabajo complejo. Puedes elegir los agentes manualmente o pedir recomendaciones opcionales.';
  bool busy = false;
  List<String> trace = [];

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
    final raw = prefs.getString(_profilesKey);
    if (raw != null) {
      try {
        agents = (jsonDecode(raw) as List)
            .whereType<Map>()
            .map((e) => AgentProfile.fromJson(Map<String, dynamic>.from(e)))
            .where((a) => a.id.isNotEmpty)
            .toList();
      } catch (_) {
        agents = [];
      }
    }
    final saved = prefs.getStringList(_enabledKey) ?? const <String>[];
    enabled = saved.where((id) => agents.any((a) => a.id == id)).toSet();
    if (mounted) setState(() {});
  }

  Future<void> _saveEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList(_enabledKey, enabled.toList());
  }

  Set<String> _words(String text) => RegExp(
        r'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+',
      )
          .allMatches(text.toLowerCase())
          .map((m) => m.group(0) ?? '')
          .where((w) => w.length >= 4)
          .toSet();

  List<_AgentRecommendation> _rankAgents(String task) {
    final taskWords = _words(task);
    if (taskWords.isEmpty) return const [];
    final ranked = <_AgentRecommendation>[];
    for (final agent in agents) {
      final agentWords = _words('${agent.name} ${agent.prompt}');
      final hits = taskWords.where(agentWords.contains).toList()..sort();
      var score = hits.length;
      if (task.toLowerCase().contains(agent.name.toLowerCase())) score += 5;
      if (score > 0) ranked.add(_AgentRecommendation(agent, score, hits));
    }
    ranked.sort((a, b) => b.score.compareTo(a.score));
    return ranked.take(4).toList();
  }

  bool _hasAgentFor(Iterable<String> terms) {
    final haystack = agents.map((a) => '${a.name} ${a.prompt}'.toLowerCase()).join(' ');
    return terms.any(haystack.contains);
  }

  List<String> _missingRoleSuggestions(String task) {
    final t = task.toLowerCase();
    final out = <String>[];

    void suggest(List<String> triggers, List<String> agentTerms, String role) {
      if (triggers.any(t.contains) && !_hasAgentFor(agentTerms)) out.add(role);
    }

    suggest(
      ['dato', 'data', 'estadíst', 'estadist', 'analiza', 'analysis', 'excel'],
      ['dato', 'data', 'estadíst', 'estadist', 'analista'],
      'Analista de datos',
    );
    suggest(
      ['finanza', 'presupuesto', 'gasto', 'costo', 'rentabilidad', 'cash flow'],
      ['finanza', 'presupuesto', 'contable', 'financial'],
      'Analista financiero',
    );
    suggest(
      ['informe', 'reporte', 'report', 'documento', 'resumen ejecutivo'],
      ['redactor', 'informe', 'report', 'writer'],
      'Redactor de informes',
    );
    suggest(
      ['código', 'codigo', 'program', 'flutter', 'android', 'app', 'apk', 'software'],
      ['program', 'desarroll', 'developer', 'flutter', 'software'],
      'Desarrollador de software',
    );
    suggest(
      ['investiga', 'research', 'fuente', 'mercado', 'comparar'],
      ['investiga', 'research', 'fuente', 'mercado'],
      'Investigador',
    );
    suggest(
      ['marketing', 'contenido', 'audiencia', 'publicidad', 'social'],
      ['marketing', 'contenido', 'audiencia', 'publicidad'],
      'Especialista de contenido y marketing',
    );

    return out.take(3).toList();
  }

  void _recommend() {
    final task = input.text.trim();
    if (task.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Escribe primero la tarea para recomendar agentes.')),
      );
      return;
    }
    setState(() {
      recommendations = _rankAgents(task);
      suggestedRoles = _missingRoleSuggestions(task);
    });
  }

  Future<void> _toggleAgent(String id, bool value) async {
    setState(() {
      if (value) {
        enabled.add(id);
      } else {
        enabled.remove(id);
      }
    });
    await _saveEnabled();
  }

  Future<void> _run() async {
    final task = input.text.trim();
    if (task.isEmpty || busy) return;
    final chosen = agents.where((a) => enabled.contains(a.id)).toList();
    if (chosen.isEmpty) {
      setState(() => answer =
          'Selecciona al menos un agente. Las recomendaciones son opcionales y nunca se aplican automáticamente.');
      return;
    }

    setState(() {
      busy = true;
      trace = [];
      answer = 'Planificando y delegando…';
    });

    try {
      var shared = '';
      for (final a in chosen) {
        if (mounted) setState(() => trace.add('${a.name}: trabajando…'));
        final guides = widget.store.guides.where((g) => a.guideIds.contains(g.id)).toList();
        final ctx = guides.isEmpty
            ? ''
            : KnowledgeRetriever.buildContext(
                guides: guides,
                query: task,
                maxChars: 5000,
                maxChunks: 5,
                allowUnmatchedFallback: false,
              );
        final r = await AiService.askConfigured(
          providerOverride: a.modelSource,
          responseMode: 'normal',
          prompt: '''Eres ${a.name}, un agente especializado dentro de un equipo coordinado por Memora.
TU FUNCIÓN:
${a.prompt}
TRABAJO GENERAL:
$task
RESULTADOS DE AGENTES ANTERIORES:
$shared
BASE ASIGNADA:
$ctx
Realiza la parte del trabajo que corresponde a tu especialidad. Devuelve resultados concretos que otro agente pueda continuar.''',
        );
        shared += '\n\n[${a.name}]\n$r';
        if (mounted) setState(() => trace[trace.length - 1] = '${a.name}: completado');
      }

      final finalResult = await AiService.askConfigured(
        providerOverride: 'global',
        responseMode: 'deep',
        prompt: '''Eres el Orquestador de Memora. Integra el trabajo de varios agentes en un único resultado final coherente. No inventes resultados que los agentes no proporcionaron.
SOLICITUD:
$task
TRABAJO DE LOS AGENTES:
$shared
Entrega el trabajo final, resolviendo duplicaciones y contradicciones cuando sea posible.''',
      );
      if (mounted) setState(() => answer = finalResult);
    } catch (e) {
      if (mounted) {
        setState(() => answer =
            'El Orquestador no pudo terminar: ${AiService.userFacingError(e)}');
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Orquestador'),
              Text('Agente de agentes', style: TextStyle(fontSize: 12, fontWeight: FontWeight.normal)),
            ],
          ),
          actions: [
            IconButton(
              tooltip: 'AI Settings',
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const LlmSettingsPage()),
              ),
              icon: const Icon(Icons.settings_outlined),
            ),
          ],
        ),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextField(
              controller: input,
              minLines: 3,
              maxLines: 7,
              onChanged: (_) {
                if (recommendations.isNotEmpty || suggestedRoles.isNotEmpty) {
                  setState(() {
                    recommendations = [];
                    suggestedRoles = [];
                  });
                }
              },
              decoration: const InputDecoration(
                labelText: 'Trabajo complejo',
                hintText: 'Ej. Analiza estos datos y prepara un informe final…',
              ),
            ),
            const SizedBox(height: 10),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Agentes recomendados (opcional)',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 17),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'La recomendación se calcula localmente para no sobrecargar el Orquestador. No selecciona ni crea agentes automáticamente.',
                    ),
                    const SizedBox(height: 10),
                    OutlinedButton.icon(
                      onPressed: busy ? null : _recommend,
                      icon: const Icon(Icons.recommend_outlined),
                      label: const Text('Recomendar para esta tarea'),
                    ),
                    if (recommendations.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      for (final r in recommendations)
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.smart_toy_outlined),
                          title: Text(r.agent.name),
                          subtitle: Text(
                            r.matches.isEmpty
                                ? 'Coincide con la tarea.'
                                : 'Coincide por: ${r.matches.take(4).join(', ')}',
                          ),
                          trailing: enabled.contains(r.agent.id)
                              ? const Text('Seleccionado')
                              : TextButton(
                                  onPressed: busy
                                      ? null
                                      : () => _toggleAgent(r.agent.id, true),
                                  child: const Text('Usar'),
                                ),
                        ),
                    ],
                    if (recommendations.isEmpty &&
                        suggestedRoles.isEmpty &&
                        input.text.trim().isNotEmpty) ...[
                      const SizedBox(height: 8),
                      const Text('Pulsa “Recomendar” si quieres ayuda para escoger agentes.'),
                    ],
                    if (suggestedRoles.isNotEmpty) ...[
                      const Divider(height: 24),
                      const Text(
                        'Especialidades que podrías crear',
                        style: TextStyle(fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'Son solo sugerencias. Si alguna te interesa, créala manualmente desde Agentes.',
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          for (final role in suggestedRoles)
                            Chip(
                              avatar: const Icon(Icons.lightbulb_outline, size: 18),
                              label: Text(role),
                            ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Agentes autorizados',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 17),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Solo se ejecutarán los que selecciones tú. La selección se recuerda para la próxima vez.',
                    ),
                    if (agents.isEmpty)
                      const Padding(
                        padding: EdgeInsets.only(top: 12),
                        child: Text('Todavía no has creado agentes.'),
                      ),
                    for (final a in agents)
                      CheckboxListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(a.name),
                        value: enabled.contains(a.id),
                        onChanged: busy
                            ? null
                            : (v) => _toggleAgent(a.id, v == true),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 10),
            FilledButton.icon(
              onPressed: busy ? null : _run,
              icon: const Icon(Icons.account_tree_outlined),
              label: Text(busy ? 'Coordinando agentes…' : 'Ejecutar con agentes'),
            ),
            if (trace.isNotEmpty) ...[
              const SizedBox(height: 14),
              const Text('Ejecución', style: TextStyle(fontWeight: FontWeight.bold)),
              for (final x in trace)
                ListTile(
                  dense: true,
                  leading: const Icon(Icons.subdirectory_arrow_right),
                  title: Text(x),
                ),
            ],
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: SelectableText(answer),
              ),
            ),
          ],
        ),
      );
}
'''

Path('lib/agent_orchestrator_page.dart').write_text(orch)
print('v158 applied: orchestrator recommendations are optional, local, and never auto-create/auto-select agents')
