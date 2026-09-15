from pathlib import Path
import re

# -----------------------------------------------------------------------------
# Daily exams: visible stopwatch + hard 20 s AI budget + completion notification.
# -----------------------------------------------------------------------------
p = Path('lib/daily_exam_page.dart')
s = p.read_text()

if "import 'dart:async';\n" not in s:
    s = s.replace("import 'dart:convert';\n", "import 'dart:async';\nimport 'dart:convert';\n", 1)

local_anchor = "import 'ai_service.dart';\n"
if local_anchor not in s:
    raise RuntimeError('Daily exam ai_service import anchor not found')
if "completion_notification_service.dart" not in s:
    s = s.replace(local_anchor, local_anchor + "import 'completion_notification_service.dart';\n", 1)

state_anchor = "  String? busyTutorId;\n"
if state_anchor not in s:
    raise RuntimeError('Daily exam busyTutorId anchor not found')
s = s.replace(
    state_anchor,
    state_anchor + "  int examElapsedSeconds = 0;\n  Timer? _examTimer;\n",
    1,
)

get_today = "  String get today {\n"
helpers = r'''  void _beginExamWork(String tutorId) {
    _examTimer?.cancel();
    if (mounted) {
      setState(() {
        busyTutorId = tutorId;
        examElapsedSeconds = 0;
      });
    }
    _examTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted || busyTutorId == null) return;
      setState(() => examElapsedSeconds++);
    });
  }

  void _endExamWork() {
    _examTimer?.cancel();
    _examTimer = null;
    if (mounted) {
      setState(() {
        busyTutorId = null;
        examElapsedSeconds = 0;
      });
    }
  }

  @override
  void dispose() {
    _examTimer?.cancel();
    super.dispose();
  }

'''
if get_today not in s:
    raise RuntimeError('Daily exam today getter anchor not found')
s = s.replace(get_today, helpers + get_today, 1)

# Wrap only the exam AI call with a 20-second budget. AiService.cancelCurrent()
# actually closes HTTP transports and asks the local GGUF engine to stop.
pattern = re.compile(
    r"(        final raw = await AiService\.askTaskConfigured\(.*?\n        )\);",
    re.S,
)
match = pattern.search(s)
if not match:
    raise RuntimeError('Daily exam askTaskConfigured call not found')
replacement = match.group(1) + r''').timeout(
          const Duration(seconds: 20),
          onTimeout: () async {
            await AiService.cancelCurrent();
            throw TimeoutException('La IA superó el límite de 20 segundos.');
          },
        );'''
s = s[:match.start()] + replacement + s[match.end():]

old_catch = """      } catch (_) {
        questions = <ExamQuestionData>[];
      }
"""
new_catch = """      } on TimeoutException {
        generatorLabel = '$generatorLabel • límite 20 s; completado con contenido verificado';
        questions = <ExamQuestionData>[];
      } catch (_) {
        questions = <ExamQuestionData>[];
      }
"""
if old_catch not in s:
    raise RuntimeError('Daily exam generation catch anchor not found')
s = s.replace(old_catch, new_catch, 1)

count = s.count("    setState(() => busyTutorId = tutor.id);\n")
if count != 2:
    raise RuntimeError(f'Expected 2 daily exam busy starts, found {count}')
s = s.replace("    setState(() => busyTutorId = tutor.id);\n", "    _beginExamWork(tutor.id);\n")

count = s.count("      if (mounted) setState(() => busyTutorId = null);\n")
if count != 2:
    raise RuntimeError(f'Expected 2 daily exam busy endings, found {count}')
s = s.replace("      if (mounted) setState(() => busyTutorId = null);\n", "      _endExamWork();\n")

s = s.replace("? 'Preparando…'", "? 'Preparando… ${examElapsedSeconds}s'", 1)
s = s.replace(
    "Text(busyTutorId != null ? 'Creando examen…' : 'Crear examen')",
    "Text(busyTutorId != null ? 'Creando examen… ${examElapsedSeconds}s' : 'Crear examen')",
    1,
)

speed_help = """              : 'La IA redacta nuevas preguntas, pero solo recibe el material de este tutor. Para exámenes grandes, Memora completa con preguntas indexadas si hace falta.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
"""
speed_help_new = """              : 'La IA redacta una parte y Memora completa el resto con contenido verificado del tutor. La IA tiene un máximo de 20 segundos; después el examen termina automáticamente sin seguir esperando.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
"""
if speed_help not in s:
    raise RuntimeError('Daily exam speed help anchor not found')
s = s.replace(speed_help, speed_help_new, 1)

# Notify only after the exam has actually been stored and is ready to open.
old_daily_saved = """      await _saveSessions();
      if (!mounted) return;
      await _openExam(exam);
"""
new_daily_saved = """      await _saveSessions();
      await CompletionNotificationService.show(
        title: 'Examen diario listo',
        body: '${tutor.name}: ${exam.questions.length} preguntas preparadas.',
      );
      if (!mounted) return;
      await _openExam(exam);
"""
if old_daily_saved not in s:
    raise RuntimeError('Daily exam saved notification anchor not found')
s = s.replace(old_daily_saved, new_daily_saved, 1)

old_custom_saved = """      await _upsertExam(exam);
      if (!mounted) return;
      await _openExam(exam);
"""
new_custom_saved = """      await _upsertExam(exam);
      await CompletionNotificationService.show(
        title: 'Examen listo',
        body: '${tutor.name}: ${exam.questions.length} preguntas preparadas.',
      );
      if (!mounted) return;
      await _openExam(exam);
"""
if old_custom_saved not in s:
    raise RuntimeError('Custom exam saved notification anchor not found')
s = s.replace(old_custom_saved, new_custom_saved, 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# Study plans: notify after generation and after PDF export.
# -----------------------------------------------------------------------------
p = Path('lib/study_plan_page.dart')
s = p.read_text()
anchor = "import 'ai_service.dart';\n"
if anchor not in s:
    raise RuntimeError('Study plan ai import anchor not found')
if "completion_notification_service.dart" not in s:
    s = s.replace(anchor, anchor + "import 'completion_notification_service.dart';\n", 1)

old_plan_done = """      setState(() {
        plan = completedPlan;
        usedSource = TutorContextService.sourceLabel(completedProvider);
      });
"""
new_plan_done = """      setState(() {
        plan = completedPlan;
        usedSource = TutorContextService.sourceLabel(completedProvider);
      });
      await CompletionNotificationService.show(
        title: 'Plan de aprendizaje listo',
        body: 'Memora terminó de crear tu plan con ${TutorContextService.sourceLabel(completedProvider)}.',
      );
"""
if old_plan_done not in s:
    raise RuntimeError('Study plan completion anchor not found')
s = s.replace(old_plan_done, new_plan_done, 1)

old_export_done = """      if (!mounted || result == null) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Plan exportado como PDF.')),
      );
"""
new_export_done = """      if (result == null) return;
      await CompletionNotificationService.show(
        title: 'PDF del plan listo',
        body: 'El plan de aprendizaje fue exportado correctamente.',
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Plan exportado como PDF.')),
      );
"""
if old_export_done not in s:
    raise RuntimeError('Study plan PDF export notification anchor not found')
s = s.replace(old_export_done, new_export_done, 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# AI-created PDF/Excel guides: notify only after file + library entry are ready.
# -----------------------------------------------------------------------------
p = Path('lib/guide_creator_page.dart')
s = p.read_text()
anchor = "import 'ai_service.dart';\n"
if anchor not in s:
    raise RuntimeError('Guide creator ai import anchor not found')
if "completion_notification_service.dart" not in s:
    s = s.replace(anchor, anchor + "import 'completion_notification_service.dart';\n", 1)

old = """      await widget.store.add(guide);
      if (!mounted) return;
"""
new = """      await widget.store.add(guide);
      await CompletionNotificationService.show(
        title: format == 'pdf' ? 'PDF listo' : 'Excel listo',
        body: '$title fue creado y añadido a tu Biblioteca.',
      );
      if (!mounted) return;
"""
if old not in s:
    raise RuntimeError('Guide creator completion anchor not found')
s = s.replace(old, new, 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# AI study guide: notify once the generated guide has been persisted.
# -----------------------------------------------------------------------------
p = Path('lib/ai_study_guide_page.dart')
s = p.read_text()
anchor = "import 'ai_service.dart';\n"
if anchor not in s:
    raise RuntimeError('AI study guide import anchor not found')
if "completion_notification_service.dart" not in s:
    s = s.replace(anchor, anchor + "import 'completion_notification_service.dart';\n", 1)

old = "await p.setString('ai_guide_${g.id}', result);"
new = """await p.setString('ai_guide_${g.id}', result); await CompletionNotificationService.show(title: 'Guía de estudio lista', body: 'Memora terminó la guía de ${g.title}.');"""
if old not in s:
    raise RuntimeError('AI study guide completion anchor not found')
s = s.replace(old, new, 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# Tutor/Agent chat creation tasks: generic completion notification. Ordinary
# conversation does not notify, only messages detected as explicit tasks.
# -----------------------------------------------------------------------------
p = Path('lib/ai_service.dart')
s = p.read_text()
import_anchor = "import 'device_llm_service.dart';\n"
if import_anchor not in s:
    raise RuntimeError('AiService device import anchor not found')
if "completion_notification_service.dart" not in s:
    s = s.replace(import_anchor, import_anchor + "import 'completion_notification_service.dart';\n", 1)

old = """    if (taskHint != null && looksLikeTask(taskHint)) {
      return askTaskConfigured(
        prompt: prompt,
        deviceModeOverride: deviceModeOverride,
        providerOverride: providerOverride,
        responseMode: responseMode,
        onPartial: onPartial,
        imagePaths: imagePaths,
      );
    }
"""
new = """    if (taskHint != null && looksLikeTask(taskHint)) {
      final taskResult = await askTaskConfigured(
        prompt: prompt,
        deviceModeOverride: deviceModeOverride,
        providerOverride: providerOverride,
        responseMode: responseMode,
        onPartial: onPartial,
        imagePaths: imagePaths,
      );
      await CompletionNotificationService.show(
        title: 'Tarea del tutor/agente terminada',
        body: 'Memora terminó el trabajo que le pediste.',
      );
      return taskResult;
    }
"""
if old not in s:
    raise RuntimeError('AiService taskHint notification anchor not found')
s = s.replace(old, new, 1)
p.write_text(s)

print('Memora v1.13 exam timer, 20-second cutoff and completion notifications applied successfully')
