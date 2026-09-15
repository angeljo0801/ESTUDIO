import 'dart:convert';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'ai_service.dart';
import 'guide_store.dart';
import 'models.dart';
import 'tutor_context_service.dart';

class ExamQuestionData {
  const ExamQuestionData({
    required this.question,
    required this.answer,
    required this.sourceTitle,
  });

  final String question;
  final String answer;
  final String sourceTitle;

  Map<String, dynamic> toJson() => {
        'question': question,
        'answer': answer,
        'sourceTitle': sourceTitle,
      };

  factory ExamQuestionData.fromJson(Map<String, dynamic> json) => ExamQuestionData(
        question: json['question']?.toString() ?? '',
        answer: json['answer']?.toString() ?? '',
        sourceTitle: json['sourceTitle']?.toString() ?? '',
      );
}

class TutorExamSession {
  const TutorExamSession({
    required this.id,
    required this.tutorId,
    required this.tutorName,
    required this.tutorEmoji,
    required this.createdAt,
    required this.dateKey,
    required this.isDaily,
    required this.difficulty,
    required this.generatorLabel,
    required this.questions,
    this.currentIndex = 0,
    this.correct = 0,
    this.completed = false,
  });

  final String id;
  final String tutorId;
  final String tutorName;
  final String tutorEmoji;
  final DateTime createdAt;
  final String dateKey;
  final bool isDaily;
  final String difficulty;
  final String generatorLabel;
  final List<ExamQuestionData> questions;
  final int currentIndex;
  final int correct;
  final bool completed;

  TutorExamSession copyWith({
    int? currentIndex,
    int? correct,
    bool? completed,
  }) =>
      TutorExamSession(
        id: id,
        tutorId: tutorId,
        tutorName: tutorName,
        tutorEmoji: tutorEmoji,
        createdAt: createdAt,
        dateKey: dateKey,
        isDaily: isDaily,
        difficulty: difficulty,
        generatorLabel: generatorLabel,
        questions: questions,
        currentIndex: currentIndex ?? this.currentIndex,
        correct: correct ?? this.correct,
        completed: completed ?? this.completed,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'tutorId': tutorId,
        'tutorName': tutorName,
        'tutorEmoji': tutorEmoji,
        'createdAt': createdAt.toIso8601String(),
        'dateKey': dateKey,
        'isDaily': isDaily,
        'difficulty': difficulty,
        'generatorLabel': generatorLabel,
        'questions': questions.map((e) => e.toJson()).toList(),
        'currentIndex': currentIndex,
        'correct': correct,
        'completed': completed,
      };

  factory TutorExamSession.fromJson(Map<String, dynamic> json) => TutorExamSession(
        id: json['id']?.toString() ?? '',
        tutorId: json['tutorId']?.toString() ?? '',
        tutorName: json['tutorName']?.toString() ?? 'Tutor',
        tutorEmoji: json['tutorEmoji']?.toString() ?? '🧠',
        createdAt: DateTime.tryParse(json['createdAt']?.toString() ?? '') ?? DateTime.now(),
        dateKey: json['dateKey']?.toString() ?? '',
        isDaily: json['isDaily'] == true,
        difficulty: json['difficulty']?.toString() ?? 'Media',
        generatorLabel: json['generatorLabel']?.toString() ?? '',
        questions: (json['questions'] is List)
            ? (json['questions'] as List)
                .whereType<Map>()
                .map((e) => ExamQuestionData.fromJson(Map<String, dynamic>.from(e)))
                .where((e) => e.question.trim().isNotEmpty && e.answer.trim().isNotEmpty)
                .toList()
            : const [],
        currentIndex: (json['currentIndex'] as num?)?.toInt() ?? 0,
        correct: (json['correct'] as num?)?.toInt() ?? 0,
        completed: json['completed'] == true,
      );
}

class DailyExamPage extends StatefulWidget {
  const DailyExamPage({super.key, required this.store});

  final GuideStore store;

  @override
  State<DailyExamPage> createState() => _DailyExamPageState();
}

class _DailyExamPageState extends State<DailyExamPage> {
  static const _storageKey = 'memora_tutor_exams_v1';

  List<TutorContextProfile> tutors = const [];
  List<TutorExamSession> sessions = const [];
  bool loading = true;
  String dailyGenerator = 'best';
  String customGenerator = 'best';
  String difficulty = 'Media';
  int customCount = 10;
  String? customTutorId;
  String? busyTutorId;

  String get today {
    final d = DateTime.now();
    return '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final loadedTutors = await TutorContextService.loadProfiles();
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_storageKey);
    final loadedSessions = <TutorExamSession>[];
    if (raw != null && raw.isNotEmpty) {
      try {
        final decoded = jsonDecode(raw);
        if (decoded is List) {
          loadedSessions.addAll(
            decoded
                .whereType<Map>()
                .map((e) => TutorExamSession.fromJson(Map<String, dynamic>.from(e)))
                .where((e) => e.id.isNotEmpty && e.tutorId.isNotEmpty && e.questions.isNotEmpty),
          );
        }
      } catch (_) {}
    }
    if (!mounted) return;
    setState(() {
      tutors = loadedTutors;
      sessions = loadedSessions;
      customTutorId = loadedTutors.isEmpty ? null : loadedTutors.first.id;
      loading = false;
    });
  }

  Future<void> _saveSessions() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_storageKey, jsonEncode(sessions.map((e) => e.toJson()).toList()));
  }

  TutorExamSession? _dailyFor(String tutorId) {
    for (final exam in sessions) {
      if (exam.isDaily && exam.tutorId == tutorId && exam.dateKey == today) return exam;
    }
    return null;
  }

  TutorContextProfile? _tutorById(String? id) {
    if (id == null) return null;
    for (final tutor in tutors) {
      if (tutor.id == id) return tutor;
    }
    return null;
  }

  Future<void> _upsertExam(TutorExamSession exam) async {
    final copy = List<TutorExamSession>.from(sessions);
    final index = copy.indexWhere((e) => e.id == exam.id);
    if (index >= 0) {
      copy[index] = exam;
    } else {
      copy.insert(0, exam);
    }
    if (mounted) setState(() => sessions = copy);
    await _saveSessions();
  }

  List<ExamQuestionData> _cardQuestions(List<StudyGuide> guides, int count) {
    final pool = <({StudyGuide guide, StudyCard card})>[];
    for (final guide in guides) {
      for (final card in guide.cards) {
        if (card.question.trim().isNotEmpty && card.answer.trim().isNotEmpty) {
          pool.add((guide: guide, card: card));
        }
      }
    }
    pool.sort((a, b) {
      final aw = a.card.wrong * 4 + (a.card.isDue ? 3 : 0) - a.card.correct;
      final bw = b.card.wrong * 4 + (b.card.isDue ? 3 : 0) - b.card.correct;
      return bw.compareTo(aw);
    });
    if (pool.length > 5) {
      final priority = pool.take(min(6, pool.length)).toList();
      final rest = pool.skip(priority.length).toList()..shuffle(Random());
      pool
        ..clear()
        ..addAll(priority)
        ..addAll(rest);
    }
    return pool
        .take(count)
        .map(
          (e) => ExamQuestionData(
            question: e.card.question.trim(),
            answer: e.card.answer.trim(),
            sourceTitle: e.guide.title,
          ),
        )
        .toList();
  }

  List<ExamQuestionData> _parseAiQuestions(String raw) {
    try {
      final start = raw.indexOf('[');
      final end = raw.lastIndexOf(']');
      if (start < 0 || end <= start) return const [];
      final decoded = jsonDecode(raw.substring(start, end + 1));
      if (decoded is! List) return const [];
      final out = <ExamQuestionData>[];
      for (final item in decoded.whereType<Map>()) {
        final map = Map<String, dynamic>.from(item);
        final q = (map['question'] ?? map['pregunta'])?.toString().trim() ?? '';
        final a = (map['answer'] ?? map['respuesta'])?.toString().trim() ?? '';
        final source = (map['source'] ?? map['fuente'])?.toString().trim() ?? 'Contenido del tutor';
        if (q.isNotEmpty && a.isNotEmpty) {
          out.add(ExamQuestionData(question: q, answer: a, sourceTitle: source));
        }
      }
      return out;
    } catch (_) {
      return const [];
    }
  }

  Future<TutorExamSession> _buildExam({
    required TutorContextProfile tutor,
    required int count,
    required String difficulty,
    required String generatorMode,
    required bool daily,
  }) async {
    final guides = TutorContextService.guidesFor(widget.store, tutor);
    if (guides.isEmpty) {
      throw Exception('${tutor.name} todavía no tiene material asignado para examinarte.');
    }

    final fallback = _cardQuestions(guides, count);
    var questions = <ExamQuestionData>[];
    var generatorLabel = 'Instantáneo • contenido indexado';

    if (generatorMode != 'instant') {
      String? provider;
      if (generatorMode == 'best') {
        provider = await TutorContextService.bestAvailableProvider();
        generatorLabel = 'Mejor IA disponible • ${TutorContextService.sourceLabel(provider ?? 'global')}';
      } else {
        provider = tutor.modelSource;
        generatorLabel = '${tutor.name} • ${TutorContextService.sourceLabel(provider)}';
      }

      final localish = provider == 'private' ||
          provider == 'shared' ||
          provider == 'device' ||
          provider == 'local' ||
          provider == 'ollama';
      final aiCount = min(count, localish ? 10 : 20);
      final content = TutorContextService.contentForGuides(
        guides,
        maxChars: localish ? 12000 : 24000,
      );

      try {
        final raw = await AiService.askConfigured(
          providerOverride: provider,
          responseMode: localish ? 'normal' : 'deep',
          prompt: '''Crea un examen de $aiCount preguntas basado EXCLUSIVAMENTE en el contenido del tutor ${tutor.name}.
Dificultad: $difficulty.

REGLAS:
- Evalúa comprensión real, no solo memorización literal.
- No uses información de otros tutores ni conocimiento externo.
- Distribuye las preguntas entre los temas disponibles.
- La respuesta debe ser breve pero suficiente para corregir.
- Devuelve SOLO un arreglo JSON válido, sin Markdown y sin explicaciones adicionales.
- Formato exacto de cada elemento: {"question":"...","answer":"...","source":"nombre o tema de la fuente"}.

CONTENIDO DEL TUTOR:
$content''',
        );
        questions = _parseAiQuestions(raw);
      } catch (_) {
        questions = <ExamQuestionData>[];
      }
    }

    final seen = questions.map((e) => e.question.toLowerCase()).toSet();
    for (final item in fallback) {
      if (questions.length >= count) break;
      if (seen.add(item.question.toLowerCase())) questions.add(item);
    }
    if (questions.length > count) questions = questions.take(count).toList();
    if (questions.isEmpty) {
      throw Exception('No pude crear preguntas con el contenido asignado a ${tutor.name}.');
    }

    final now = DateTime.now();
    return TutorExamSession(
      id: 'exam_${now.microsecondsSinceEpoch}',
      tutorId: tutor.id,
      tutorName: tutor.name,
      tutorEmoji: tutor.emoji,
      createdAt: now,
      dateKey: daily ? today : '',
      isDaily: daily,
      difficulty: difficulty,
      generatorLabel: generatorLabel,
      questions: questions,
    );
  }

  Future<void> _openExam(TutorExamSession exam) async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => _ExamRunnerPage(
          exam: exam,
          onSave: _upsertExam,
        ),
      ),
    );
    if (mounted) setState(() {});
  }

  Future<void> _prepareDaily(TutorContextProfile tutor, {bool regenerate = false}) async {
    if (busyTutorId != null) return;
    final existing = _dailyFor(tutor.id);
    if (existing != null && !regenerate) {
      await _openExam(existing);
      return;
    }
    final guides = TutorContextService.guidesFor(widget.store, tutor);
    if (guides.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${tutor.name} todavía no tiene material para examinarte.')),
      );
      return;
    }

    setState(() => busyTutorId = tutor.id);
    try {
      final exam = await _buildExam(
        tutor: tutor,
        count: 10,
        difficulty: 'Adaptativa',
        generatorMode: dailyGenerator,
        daily: true,
      );
      final copy = List<TutorExamSession>.from(sessions)
        ..removeWhere((e) => e.isDaily && e.tutorId == tutor.id && e.dateKey == today)
        ..insert(0, exam);
      setState(() => sessions = copy);
      await _saveSessions();
      if (!mounted) return;
      await _openExam(exam);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AiService.userFacingError(e))),
      );
    } finally {
      if (mounted) setState(() => busyTutorId = null);
    }
  }

  Future<void> _createCustomExam() async {
    final tutor = _tutorById(customTutorId);
    if (tutor == null || busyTutorId != null) return;
    if (TutorContextService.guidesFor(widget.store, tutor).isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${tutor.name} todavía no tiene material para examinarte.')),
      );
      return;
    }

    setState(() => busyTutorId = tutor.id);
    try {
      final exam = await _buildExam(
        tutor: tutor,
        count: customCount,
        difficulty: difficulty,
        generatorMode: customGenerator,
        daily: false,
      );
      await _upsertExam(exam);
      if (!mounted) return;
      await _openExam(exam);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AiService.userFacingError(e))),
      );
    } finally {
      if (mounted) setState(() => busyTutorId = null);
    }
  }

  Widget _generatorDropdown({
    required String value,
    required ValueChanged<String?> onChanged,
    String label = 'Cómo redactar las preguntas',
  }) =>
      DropdownButtonFormField<String>(
        initialValue: value,
        decoration: InputDecoration(labelText: label, prefixIcon: const Icon(Icons.auto_awesome)),
        items: const [
          DropdownMenuItem(value: 'best', child: Text('✨ Mejor IA disponible')),
          DropdownMenuItem(value: 'tutor', child: Text('🧑‍🏫 IA del tutor')),
          DropdownMenuItem(value: 'instant', child: Text('⚡ Instantáneo (sin IA)')),
        ],
        onChanged: busyTutorId == null ? onChanged : null,
      );

  Widget _dailyTab() {
    if (tutors.isEmpty) {
      return const Center(child: Text('No hay tutores disponibles.'));
    }
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 110),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Exámenes diarios por tutor',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Cada tutor te examina únicamente de sus propias guías. El examen de hoy se guarda y no se vuelve a generar al abrir esta pantalla.',
                ),
                const SizedBox(height: 14),
                _generatorDropdown(
                  value: dailyGenerator,
                  onChanged: (v) => setState(() => dailyGenerator = v ?? 'best'),
                  label: 'Generador de exámenes diarios',
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 10),
        for (final tutor in tutors) _dailyTutorCard(tutor),
      ],
    );
  }

  Widget _dailyTutorCard(TutorContextProfile tutor) {
    final guides = TutorContextService.guidesFor(widget.store, tutor);
    final exam = _dailyFor(tutor.id);
    final working = busyTutorId == tutor.id;
    final status = exam == null
        ? 'Pendiente'
        : exam.completed
            ? 'Completado • ${exam.correct}/${exam.questions.length}'
            : 'En progreso • ${exam.currentIndex}/${exam.questions.length}';

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(tutor.emoji, style: const TextStyle(fontSize: 28)),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(tutor.name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 17)),
                      Text('${guides.length} guía(s) • $status'),
                    ],
                  ),
                ),
                if (exam?.completed == true) const Icon(Icons.verified_rounded),
              ],
            ),
            if (exam != null) ...[
              const SizedBox(height: 8),
              Text(exam.generatorLabel, style: Theme.of(context).textTheme.bodySmall),
            ],
            if (guides.isEmpty) ...[
              const SizedBox(height: 10),
              const Text('Este tutor todavía no tiene material para examinarte.'),
            ] else ...[
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: working || busyTutorId != null ? null : () => _prepareDaily(tutor),
                      icon: working
                          ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                          : Icon(exam == null ? Icons.play_arrow_rounded : Icons.fact_check_outlined),
                      label: Text(
                        working
                            ? 'Preparando…'
                            : exam == null
                                ? 'Crear examen de hoy'
                                : 'Abrir examen',
                      ),
                    ),
                  ),
                  if (exam != null) ...[
                    const SizedBox(width: 8),
                    IconButton.filledTonal(
                      tooltip: 'Regenerar examen de hoy',
                      onPressed: busyTutorId == null ? () => _prepareDaily(tutor, regenerate: true) : null,
                      icon: const Icon(Icons.refresh_rounded),
                    ),
                  ],
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _createTab() {
    final tutor = _tutorById(customTutorId);
    final guides = tutor == null ? const <StudyGuide>[] : TutorContextService.guidesFor(widget.store, tutor);
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 110),
      children: [
        const Text(
          'Crear examen',
          style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 6),
        const Text('Elige un tutor. Memora usará exclusivamente el contenido asignado a ese tutor.'),
        const SizedBox(height: 16),
        DropdownButtonFormField<String>(
          initialValue: customTutorId,
          decoration: const InputDecoration(
            labelText: 'Tutor / contenido del examen',
            prefixIcon: Icon(Icons.school_outlined),
          ),
          items: [
            for (final item in tutors)
              DropdownMenuItem(value: item.id, child: Text('${item.emoji} ${item.name}')),
          ],
          onChanged: busyTutorId == null ? (v) => setState(() => customTutorId = v) : null,
        ),
        const SizedBox(height: 8),
        Text(
          tutor == null
              ? 'Selecciona un tutor.'
              : guides.isEmpty
                  ? '${tutor.name} no tiene guías asignadas.'
                  : '${guides.length} guía(s) disponibles para este examen.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        const SizedBox(height: 14),
        DropdownButtonFormField<int>(
          initialValue: customCount,
          decoration: const InputDecoration(labelText: 'Número de preguntas'),
          items: const [5, 10, 20, 30, 50]
              .map((n) => DropdownMenuItem(value: n, child: Text('$n preguntas')))
              .toList(),
          onChanged: busyTutorId == null ? (v) => setState(() => customCount = v ?? 10) : null,
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: difficulty,
          decoration: const InputDecoration(labelText: 'Dificultad'),
          items: const ['Básica', 'Media', 'Difícil', 'Adaptativa']
              .map((x) => DropdownMenuItem(value: x, child: Text(x)))
              .toList(),
          onChanged: busyTutorId == null ? (v) => setState(() => difficulty = v ?? 'Media') : null,
        ),
        const SizedBox(height: 12),
        _generatorDropdown(
          value: customGenerator,
          onChanged: (v) => setState(() => customGenerator = v ?? 'best'),
        ),
        const SizedBox(height: 8),
        Text(
          customGenerator == 'instant'
              ? 'Más rápido: usa las preguntas ya creadas a partir de las guías del tutor.'
              : 'La IA redacta nuevas preguntas, pero solo recibe el material de este tutor. Para exámenes grandes, Memora completa con preguntas indexadas si hace falta.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        const SizedBox(height: 18),
        FilledButton.icon(
          onPressed: tutor == null || guides.isEmpty || busyTutorId != null ? null : _createCustomExam,
          icon: busyTutorId != null
              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.add_task_rounded),
          label: Text(busyTutorId != null ? 'Creando examen…' : 'Crear examen'),
        ),
        if (sessions.where((e) => !e.isDaily).isNotEmpty) ...[
          const SizedBox(height: 24),
          const Text('Exámenes creados', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
          const SizedBox(height: 8),
          for (final exam in sessions.where((e) => !e.isDaily).take(10))
            Card(
              child: ListTile(
                leading: Text(exam.tutorEmoji, style: const TextStyle(fontSize: 24)),
                title: Text('${exam.tutorName} • ${exam.questions.length} preguntas'),
                subtitle: Text(
                  exam.completed
                      ? '${exam.difficulty} • Resultado ${exam.correct}/${exam.questions.length}'
                      : '${exam.difficulty} • En progreso',
                ),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () => _openExam(exam),
              ),
            ),
        ],
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    if (loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Exámenes'),
          bottom: const TabBar(
            tabs: [
              Tab(icon: Icon(Icons.today_rounded), text: 'Examen diario'),
              Tab(icon: Icon(Icons.add_task_rounded), text: 'Crear examen'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _dailyTab(),
            _createTab(),
          ],
        ),
      ),
    );
  }
}

class _ExamRunnerPage extends StatefulWidget {
  const _ExamRunnerPage({required this.exam, required this.onSave});

  final TutorExamSession exam;
  final Future<void> Function(TutorExamSession exam) onSave;

  @override
  State<_ExamRunnerPage> createState() => _ExamRunnerPageState();
}

class _ExamRunnerPageState extends State<_ExamRunnerPage> {
  late TutorExamSession exam;
  bool reveal = false;

  @override
  void initState() {
    super.initState();
    exam = widget.exam;
  }

  Future<void> _answer(bool knew) async {
    if (exam.completed || exam.currentIndex >= exam.questions.length) return;
    final next = exam.currentIndex + 1;
    exam = exam.copyWith(
      currentIndex: next,
      correct: exam.correct + (knew ? 1 : 0),
      completed: next >= exam.questions.length,
    );
    await widget.onSave(exam);
    if (!mounted) return;
    setState(() => reveal = false);
  }

  @override
  Widget build(BuildContext context) {
    if (exam.completed || exam.currentIndex >= exam.questions.length) {
      final pct = exam.questions.isEmpty ? 0 : ((exam.correct / exam.questions.length) * 100).round();
      return Scaffold(
        appBar: AppBar(title: Text('${exam.tutorEmoji} ${exam.tutorName}')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(28),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.verified_rounded, size: 68),
                    const SizedBox(height: 12),
                    Text(
                      exam.isDaily ? 'Examen diario completado' : 'Examen completado',
                      style: const TextStyle(fontSize: 21, fontWeight: FontWeight.bold),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 12),
                    Text('${exam.correct}/${exam.questions.length}', style: const TextStyle(fontSize: 38, fontWeight: FontWeight.bold)),
                    Text('$pct%'),
                    const SizedBox(height: 8),
                    Text(exam.generatorLabel, textAlign: TextAlign.center),
                    const SizedBox(height: 18),
                    FilledButton(onPressed: () => Navigator.pop(context), child: const Text('Volver a Exámenes')),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    }

    final question = exam.questions[exam.currentIndex];
    return Scaffold(
      appBar: AppBar(
        title: Text('${exam.tutorEmoji} ${exam.tutorName}'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(3),
          child: LinearProgressIndicator(value: exam.currentIndex / exam.questions.length),
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.fromLTRB(18, 18, 18, 28),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Pregunta ${exam.currentIndex + 1} de ${exam.questions.length} • Puntos: ${exam.correct}',
              style: Theme.of(context).textTheme.labelLarge,
            ),
            const SizedBox(height: 14),
            Expanded(
              child: SingleChildScrollView(
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(22),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(question.sourceTitle, style: Theme.of(context).textTheme.labelMedium),
                        const SizedBox(height: 16),
                        Text(question.question, style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w600)),
                        if (reveal) ...[
                          const Divider(height: 32),
                          const Text('Respuesta', style: TextStyle(fontWeight: FontWeight.bold)),
                          const SizedBox(height: 8),
                          SelectableText(question.answer, style: const TextStyle(fontSize: 17)),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            if (!reveal)
              FilledButton(
                onPressed: () => setState(() => reveal = true),
                child: const Text('Mostrar respuesta'),
              )
            else
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => _answer(false),
                      icon: const Icon(Icons.close_rounded),
                      label: const Text('No la sabía'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: () => _answer(true),
                      icon: const Icon(Icons.check_rounded),
                      label: const Text('La sabía'),
                    ),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}
