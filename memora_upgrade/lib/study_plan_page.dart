import 'package:flutter/material.dart';

import 'ai_service.dart';
import 'guide_store.dart';
import 'tutor_context_service.dart';

class StudyPlanPage extends StatefulWidget {
  const StudyPlanPage({super.key, required this.store});

  final GuideStore store;

  @override
  State<StudyPlanPage> createState() => _StudyPlanPageState();
}

class _StudyPlanPageState extends State<StudyPlanPage> {
  final goal = TextEditingController();
  final minutes = TextEditingController(text: '45');

  List<TutorContextProfile> tutors = const [];
  String intensity = 'Normal';
  String contentOwner = 'library';
  String creator = 'best';
  bool dated = false;
  bool loading = true;
  bool busy = false;
  String plan = '';
  String createdBy = '';
  String usedSource = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    goal.dispose();
    minutes.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final loaded = await TutorContextService.loadProfiles();
    if (!mounted) return;
    setState(() {
      tutors = loaded;
      loading = false;
    });
  }

  TutorContextProfile? _tutorById(String id) {
    for (final tutor in tutors) {
      if (tutor.id == id) return tutor;
    }
    return null;
  }

  Future<void> generate() async {
    if (busy || widget.store.guides.isEmpty) return;

    final ownerTutor = contentOwner == 'library' ? null : _tutorById(contentOwner);
    final guides = ownerTutor == null
        ? widget.store.guides
        : TutorContextService.guidesFor(widget.store, ownerTutor);

    if (guides.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            ownerTutor == null
                ? 'Añade al menos una guía a Biblioteca.'
                : '${ownerTutor.name} todavía no tiene guías asignadas.',
          ),
        ),
      );
      return;
    }

    final creatorTutor = creator == 'best' ? null : _tutorById(creator);
    final provider = creatorTutor == null
        ? await TutorContextService.bestAvailableProvider()
        : creatorTutor.modelSource;
    final sourceLabel = TutorContextService.sourceLabel(provider ?? 'global');
    final content = TutorContextService.contentForGuides(guides, maxChars: 18000);

    setState(() {
      busy = true;
      plan = '';
      createdBy = creatorTutor == null ? 'Mejor IA disponible' : '${creatorTutor.emoji} ${creatorTutor.name}';
      usedSource = sourceLabel;
    });

    try {
      final tutorStyle = creatorTutor == null
          ? 'Crea el mejor plan posible, práctico, claro y sostenible.'
          : '''Actúa como ${creatorTutor.name}.
ESTILO: ${creatorTutor.description}
INSTRUCCIONES: ${creatorTutor.instructions}''';
      final prompt = '''$tutorStyle

Crea en español un plan para aprender y dominar exclusivamente el contenido proporcionado.
Objetivo del estudiante: ${goal.text.trim().isEmpty ? 'Dominar progresivamente el contenido' : goal.text.trim()}.
Minutos diarios: ${minutes.text.trim()}.
Intensidad: $intensity.
Modalidad: ${dated ? 'preparación con fecha objetivo' : 'aprendizaje continuo para la vida'}.

Incluye:
- acciones diarias concretas;
- qué estudiar primero y por qué;
- práctica y recuperación activa;
- repetición espaciada;
- exámenes periódicos;
- revisión semanal;
- metas mensuales y, cuando tenga sentido, trimestrales;
- criterios claros para saber cuándo avanzar.

No mezcles temas que no estén en las fuentes. Si el material es demasiado amplio, prioriza y divide por etapas.

FUENTES DEL PLAN:
$content''';

      final result = await AiService.askConfigured(
        prompt: prompt,
        providerOverride: provider,
        responseMode: 'normal',
      );
      if (!mounted) return;
      setState(() => plan = result);
    } catch (e) {
      if (!mounted) return;
      setState(() => plan = 'No pude crear el plan: ${AiService.userFacingError(e)}');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Mi plan de aprendizaje')),
        body: loading
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 110),
                children: [
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Quién aporta el contenido',
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                          ),
                          const SizedBox(height: 10),
                          DropdownButtonFormField<String>(
                            initialValue: contentOwner,
                            decoration: const InputDecoration(
                              labelText: 'Contenido del plan',
                              prefixIcon: Icon(Icons.library_books_outlined),
                            ),
                            items: [
                              const DropdownMenuItem(
                                value: 'library',
                                child: Text('Toda mi Biblioteca'),
                              ),
                              for (final tutor in tutors)
                                DropdownMenuItem(
                                  value: tutor.id,
                                  child: Text('${tutor.emoji} ${tutor.name}'),
                                ),
                            ],
                            onChanged: busy ? null : (v) => setState(() => contentOwner = v ?? 'library'),
                          ),
                          const SizedBox(height: 14),
                          const Text(
                            'Quién crea el plan',
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                          ),
                          const SizedBox(height: 10),
                          DropdownButtonFormField<String>(
                            initialValue: creator,
                            decoration: const InputDecoration(
                              labelText: 'Generador del plan',
                              prefixIcon: Icon(Icons.auto_awesome),
                            ),
                            items: [
                              const DropdownMenuItem(
                                value: 'best',
                                child: Text('✨ Mejor IA disponible'),
                              ),
                              for (final tutor in tutors)
                                DropdownMenuItem(
                                  value: tutor.id,
                                  child: Text('${tutor.emoji} ${tutor.name}'),
                                ),
                            ],
                            onChanged: busy ? null : (v) => setState(() => creator = v ?? 'best'),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            creator == 'best'
                                ? 'Memora prioriza una IA online ya configurada cuando esté disponible; si no, usa tu configuración general.'
                                : 'Se usarán el estilo y la fuente de IA configurada para ese tutor.',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: goal,
                    decoration: const InputDecoration(labelText: '¿Qué quieres llegar a dominar?'),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: minutes,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Minutos disponibles por día'),
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    value: dated,
                    onChanged: busy ? null : (v) => setState(() => dated = v),
                    title: Text(dated ? 'Tengo una fecha objetivo' : 'Aprendizaje continuo'),
                  ),
                  DropdownButtonFormField<String>(
                    initialValue: intensity,
                    items: ['Tranquila', 'Normal', 'Intensiva']
                        .map((x) => DropdownMenuItem(value: x, child: Text(x)))
                        .toList(),
                    onChanged: busy ? null : (v) => setState(() => intensity = v ?? 'Normal'),
                    decoration: const InputDecoration(labelText: 'Intensidad'),
                  ),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    onPressed: busy ? null : generate,
                    icon: busy
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.auto_awesome),
                    label: Text(busy ? 'Creando plan…' : 'Crear mi plan'),
                  ),
                  if (createdBy.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Card(
                      child: ListTile(
                        leading: const Icon(Icons.verified_user_outlined),
                        title: Text('Creado por: $createdBy'),
                        subtitle: Text('Fuente de IA: $usedSource'),
                      ),
                    ),
                  ],
                  if (plan.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(18),
                        child: SelectableText(plan),
                      ),
                    ),
                  ],
                ],
              ),
      );
}
