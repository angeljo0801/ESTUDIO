import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'ai_service.dart';
import 'guide_store.dart';
import 'llm_settings_page.dart';

class TutorProfile {
  const TutorProfile({
    required this.id,
    required this.name,
    required this.emoji,
    required this.description,
    required this.instructions,
    this.isBuiltIn = false,
  });

  final String id;
  final String name;
  final String emoji;
  final String description;
  final String instructions;
  final bool isBuiltIn;

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'emoji': emoji,
        'description': description,
        'instructions': instructions,
        'isBuiltIn': isBuiltIn,
      };

  factory TutorProfile.fromJson(Map<String, dynamic> json) => TutorProfile(
        id: json['id']?.toString() ?? '',
        name: json['name']?.toString() ?? 'Tutor',
        emoji: json['emoji']?.toString() ?? '🧠',
        description: json['description']?.toString() ?? '',
        instructions: json['instructions']?.toString() ?? '',
        isBuiltIn: json['isBuiltIn'] == true,
      );
}

const List<TutorProfile> _defaultTutors = [
  TutorProfile(
    id: 'memora_general',
    name: 'Memora',
    emoji: '🧠',
    description: 'Tutor equilibrado para aprender y entender cualquier tema.',
    instructions:
        'Explica con claridad, adapta la profundidad a la pregunta, divide los temas difíciles en pasos y comprueba que el estudiante entienda.',
    isBuiltIn: true,
  ),
  TutorProfile(
    id: 'paso_a_paso',
    name: 'Profesor Paso a Paso',
    emoji: '🪜',
    description: 'Descompone lo difícil en partes pequeñas y ordenadas.',
    instructions:
        'Enseña paso a paso. No saltes operaciones ni conceptos intermedios. Usa ejemplos sencillos antes de aumentar la dificultad y resume la idea clave al final.',
    isBuiltIn: true,
  ),
  TutorProfile(
    id: 'socratico',
    name: 'Tutor Socrático',
    emoji: '❓',
    description: 'Te guía con preguntas para que descubras la respuesta.',
    instructions:
        'Usa el método socrático. Antes de entregar una solución completa, haz preguntas útiles que ayuden al estudiante a razonar. Si está bloqueado, da pistas graduales y luego explica.',
    isBuiltIn: true,
  ),
  TutorProfile(
    id: 'examinador',
    name: 'Examinador Estricto',
    emoji: '🎯',
    description: 'Busca errores, exige precisión y comprueba dominio real.',
    instructions:
        'Actúa como examinador exigente pero respetuoso. Señala imprecisiones, pide definiciones exactas, formula preguntas de comprobación y explica por qué una respuesta está bien o mal.',
    isBuiltIn: true,
  ),
  TutorProfile(
    id: 'repaso_express',
    name: 'Repaso Express',
    emoji: '⚡',
    description: 'Respuestas breves, ideas clave y repasos rápidos.',
    instructions:
        'Prioriza velocidad y retención. Da respuestas concisas, usa palabras clave, mini-resúmenes y reglas fáciles de recordar. Evita detalles secundarios salvo que se pidan.',
    isBuiltIn: true,
  ),
  TutorProfile(
    id: 'ejemplos',
    name: 'Tutor de Ejemplos',
    emoji: '💡',
    description: 'Enseña principalmente mediante ejemplos y analogías.',
    instructions:
        'Explica cada concepto con ejemplos concretos y analogías cotidianas. Luego conecta el ejemplo con la definición formal y crea otro ejemplo cuando sea útil.',
    isBuiltIn: true,
  ),
];

class TutorPage extends StatefulWidget {
  const TutorPage({super.key, required this.store});
  final GuideStore store;

  @override
  State<TutorPage> createState() => _TutorPageState();
}

class _TutorPageState extends State<TutorPage> {
  static const _profilesKey = 'memora_tutor_profiles_v1';
  static const _activeTutorKey = 'memora_active_tutor_id';

  final q = TextEditingController();
  List<TutorProfile> tutors = List<TutorProfile>.from(_defaultTutors);
  String activeTutorId = _defaultTutors.first.id;
  String answer = 'Selecciona una guía y pregúntame cualquier cosa que aparezca en ella.';
  int selectedGuide = 0;
  bool busy = false;
  bool loadingTutors = true;

  TutorProfile get activeTutor => tutors.firstWhere(
        (t) => t.id == activeTutorId,
        orElse: () => tutors.first,
      );

  @override
  void initState() {
    super.initState();
    _loadTutors();
  }

  @override
  void dispose() {
    q.dispose();
    super.dispose();
  }

  Future<void> _loadTutors() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_profilesKey);
    if (raw != null && raw.isNotEmpty) {
      try {
        final decoded = jsonDecode(raw) as List<dynamic>;
        final loaded = decoded
            .whereType<Map>()
            .map((e) => TutorProfile.fromJson(Map<String, dynamic>.from(e)))
            .where((t) => t.id.isNotEmpty)
            .toList();
        if (loaded.isNotEmpty) tutors = loaded;
      } catch (_) {
        tutors = List<TutorProfile>.from(_defaultTutors);
      }
    }

    final savedActive = prefs.getString(_activeTutorKey);
    if (savedActive != null && tutors.any((t) => t.id == savedActive)) {
      activeTutorId = savedActive;
    } else {
      activeTutorId = tutors.first.id;
    }

    if (mounted) {
      setState(() {
        loadingTutors = false;
        answer = '${activeTutor.emoji} Soy ${activeTutor.name}. ${activeTutor.description}';
      });
    }
  }

  Future<void> _saveTutors() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _profilesKey,
      jsonEncode(tutors.map((t) => t.toJson()).toList()),
    );
    await prefs.setString(_activeTutorKey, activeTutorId);
  }

  Future<void> _selectTutor(String? id) async {
    if (id == null || !tutors.any((t) => t.id == id)) return;
    setState(() {
      activeTutorId = id;
      answer = '${activeTutor.emoji} Soy ${activeTutor.name}. ${activeTutor.description}';
    });
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_activeTutorKey, id);
  }

  Future<void> _settings() async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const LlmSettingsPage()),
    );
  }

  Future<void> _ask() async {
    if (widget.store.guides.isEmpty || q.text.trim().isEmpty || busy) return;
    final safeIndex = selectedGuide.clamp(0, widget.store.guides.length - 1);
    final guide = widget.store.guides[safeIndex];
    final tutor = activeTutor;
    final question = q.text.trim();
    setState(() => busy = true);

    try {
      final text = guide.text.length > 24000
          ? guide.text.substring(0, 24000)
          : guide.text;
      final prompt = '''
Eres ${tutor.name}, uno de los tutores de Memora.
TU ESTILO: ${tutor.description}
INSTRUCCIONES DEL TUTOR: ${tutor.instructions}

REGLAS GENERALES:
- Responde en español.
- Basa la respuesta SOLO en la información del documento proporcionado.
- Si la respuesta no aparece en el documento, dilo claramente y no inventes datos.
- Cuando corresponda, menciona el título del documento usado.
- Mantén siempre la personalidad y método de enseñanza del tutor activo.

DOCUMENTO: ${guide.title}
$text

PREGUNTA DEL ESTUDIANTE: $question
''';
      final result = await AiService.askConfigured(prompt: prompt);
      if (mounted) setState(() => answer = result);
    } catch (e) {
      if (mounted) setState(() => answer = 'No pude consultar la IA: $e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<TutorProfile?> _editTutorDialog({TutorProfile? existing}) async {
    final name = TextEditingController(text: existing?.name ?? '');
    final emoji = TextEditingController(text: existing?.emoji ?? '🧑‍🏫');
    final description = TextEditingController(text: existing?.description ?? '');
    final instructions = TextEditingController(text: existing?.instructions ?? '');

    return showDialog<TutorProfile>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(existing == null ? 'Crear tutor' : 'Editar tutor'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: name,
                decoration: const InputDecoration(
                  labelText: 'Nombre del tutor',
                  hintText: 'Ej. Profesor de Finanzas',
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: emoji,
                decoration: const InputDecoration(
                  labelText: 'Icono o emoji',
                  hintText: '🧑‍🏫',
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: description,
                minLines: 2,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: 'Descripción / estilo',
                  hintText: 'Cómo quieres que enseñe',
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: instructions,
                minLines: 3,
                maxLines: 6,
                decoration: const InputDecoration(
                  labelText: 'Instrucciones personalizadas',
                  hintText: 'Ej. usa ejemplos, hazme preguntas, corrige mis errores…',
                ),
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
              if (name.text.trim().isEmpty) return;
              Navigator.pop(
                dialogContext,
                TutorProfile(
                  id: existing?.id ?? 'custom_${DateTime.now().microsecondsSinceEpoch}',
                  name: name.text.trim(),
                  emoji: emoji.text.trim().isEmpty ? '🧑‍🏫' : emoji.text.trim(),
                  description: description.text.trim().isEmpty
                      ? 'Tutor personalizado de Memora.'
                      : description.text.trim(),
                  instructions: instructions.text.trim().isEmpty
                      ? 'Explica con claridad y adapta la enseñanza al estudiante.'
                      : instructions.text.trim(),
                  isBuiltIn: existing?.isBuiltIn ?? false,
                ),
              );
            },
            child: const Text('Guardar'),
          ),
        ],
      ),
    );
  }

  Future<void> _addTutor() async {
    final created = await _editTutorDialog();
    if (created == null) return;
    setState(() {
      tutors = [...tutors, created];
      activeTutorId = created.id;
      answer = '${created.emoji} Soy ${created.name}. ${created.description}';
    });
    await _saveTutors();
  }

  Future<void> _editActiveTutor() async {
    final current = activeTutor;
    final edited = await _editTutorDialog(existing: current);
    if (edited == null) return;
    final index = tutors.indexWhere((t) => t.id == current.id);
    if (index < 0) return;
    final updated = List<TutorProfile>.from(tutors);
    updated[index] = edited;
    setState(() {
      tutors = updated;
      answer = '${edited.emoji} Soy ${edited.name}. ${edited.description}';
    });
    await _saveTutors();
  }

  Future<void> _deleteActiveTutor() async {
    if (tutors.length <= 1) return;
    final current = activeTutor;
    final confirmed = await showDialog<bool>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            title: const Text('Eliminar tutor'),
            content: Text('¿Eliminar a ${current.name}?'),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: const Text('Cancelar'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(dialogContext, true),
                child: const Text('Eliminar'),
              ),
            ],
          ),
        ) ??
        false;
    if (!confirmed) return;

    setState(() {
      tutors = tutors.where((t) => t.id != current.id).toList();
      activeTutorId = tutors.first.id;
      answer = '${activeTutor.emoji} Soy ${activeTutor.name}. ${activeTutor.description}';
    });
    await _saveTutors();
  }

  Future<void> _restoreDefaults() async {
    final custom = tutors.where((t) => !t.isBuiltIn).toList();
    setState(() {
      tutors = [..._defaultTutors, ...custom];
      activeTutorId = _defaultTutors.first.id;
      answer = '${activeTutor.emoji} Soy ${activeTutor.name}. ${activeTutor.description}';
    });
    await _saveTutors();
  }

  Future<void> _openTutorManager() async {
    final action = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => SafeArea(
        child: SizedBox(
          height: MediaQuery.of(sheetContext).size.height * 0.78,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 8, 8),
                child: Row(
                  children: [
                    const Expanded(
                      child: Text(
                        'Mis tutores',
                        style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.pop(sheetContext, 'add'),
                      tooltip: 'Crear tutor',
                      icon: const Icon(Icons.person_add_alt_1),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  children: [
                    for (final tutor in tutors)
                      Card(
                        child: ListTile(
                          leading: Text(tutor.emoji, style: const TextStyle(fontSize: 28)),
                          title: Text(tutor.name),
                          subtitle: Text(
                            tutor.description,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          trailing: tutor.id == activeTutorId
                              ? const Icon(Icons.check_circle)
                              : null,
                          onTap: () {
                            _selectTutor(tutor.id);
                            Navigator.pop(sheetContext);
                          },
                        ),
                      ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: () => Navigator.pop(sheetContext, 'edit'),
                            icon: const Icon(Icons.edit_outlined),
                            label: const Text('Editar activo'),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: tutors.length <= 1
                                ? null
                                : () => Navigator.pop(sheetContext, 'delete'),
                            icon: const Icon(Icons.delete_outline),
                            label: const Text('Eliminar'),
                          ),
                        ),
                      ],
                    ),
                    TextButton.icon(
                      onPressed: () => Navigator.pop(sheetContext, 'restore'),
                      icon: const Icon(Icons.restore),
                      label: const Text('Restaurar tutores predeterminados'),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );

    if (!mounted) return;
    if (action == 'add') await _addTutor();
    if (action == 'edit') await _editActiveTutor();
    if (action == 'delete') await _deleteActiveTutor();
    if (action == 'restore') await _restoreDefaults();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('Tutores con IA'),
          actions: [
            IconButton(
              onPressed: _openTutorManager,
              tooltip: 'Administrar tutores',
              icon: const Icon(Icons.groups_2_outlined),
            ),
            IconButton(
              onPressed: _settings,
              tooltip: 'Elegir IA online o local',
              icon: const Icon(Icons.tune),
            ),
          ],
        ),
        body: loadingTutors
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  DropdownButtonFormField<String>(
                    initialValue: activeTutorId,
                    decoration: const InputDecoration(
                      labelText: 'Tutor activo',
                      prefixIcon: Icon(Icons.school_outlined),
                    ),
                    items: [
                      for (final tutor in tutors)
                        DropdownMenuItem(
                          value: tutor.id,
                          child: Text(
                            '${tutor.emoji} ${tutor.name}',
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                    ],
                    onChanged: _selectTutor,
                  ),
                  const SizedBox(height: 8),
                  Text(activeTutor.description, style: Theme.of(context).textTheme.bodySmall),
                  const SizedBox(height: 16),
                  if (widget.store.guides.isEmpty)
                    const Text('Añade primero una guía a tu biblioteca.')
                  else
                    DropdownButtonFormField<int>(
                      initialValue: selectedGuide,
                      decoration: const InputDecoration(
                        labelText: 'Guía de estudio',
                        prefixIcon: Icon(Icons.menu_book_outlined),
                      ),
                      items: [
                        for (int i = 0; i < widget.store.guides.length; i++)
                          DropdownMenuItem(
                            value: i,
                            child: Text(
                              widget.store.guides[i].title,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                      ],
                      onChanged: (v) => setState(() => selectedGuide = v ?? 0),
                    ),
                  const SizedBox(height: 16),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(activeTutor.emoji, style: const TextStyle(fontSize: 26)),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  activeTutor.name,
                                  style: const TextStyle(fontWeight: FontWeight.bold),
                                ),
                              ),
                            ],
                          ),
                          const Divider(),
                          SelectableText(answer),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: q,
                    minLines: 2,
                    maxLines: 5,
                    decoration: InputDecoration(
                      hintText: 'Pregunta a ${activeTutor.name}…',
                      suffixIcon: IconButton(
                        onPressed: busy ? null : _ask,
                        icon: busy
                            ? const Padding(
                                padding: EdgeInsets.all(12),
                                child: CircularProgressIndicator(),
                              )
                            : const Icon(Icons.send),
                      ),
                    ),
                    onSubmitted: (_) => _ask(),
                  ),
                ],
              ),
      );
}
