from pathlib import Path

# Final English cleanup after every previous patch, plus a safe migration for
# old generated card labels that preserves review statistics.

# Fix the old-card label migration inserted by v1.18. Dart String.replaceFirst
# does not use regex capture substitutions in the replacement text, so use
# replaceFirstMapped instead. Also migrate the semantic question form introduced
# in v1.16 so old guides do not keep Spanish wrappers around English content.
p = Path('lib/guide_store.dart')
s = p.read_text()
s = s.replace(
    "q = q.replaceFirst(RegExp(r'^¿Cuál es la fórmula o relación de (.+)\\?$'), 'What is the formula or relationship for \\$1?');",
    "q = q.replaceFirstMapped(RegExp(r'^¿Cuál es la fórmula o relación de (.+)\\?$'), (m) => 'What is the formula or relationship for ${m.group(1)}?');",
)
s = s.replace(
    "q = q.replaceFirst(RegExp(r'^¿Qué significa o cómo se explica [“\"](.+)[”\"]\\?$'), 'What does “\\$1” mean?');",
    "q = q.replaceFirstMapped(RegExp(r'^¿Qué significa o cómo se explica [“\"](.+)[”\"]\\?$'), (m) => 'What does “${m.group(1)}” mean?');",
)
s = s.replace(
    "q = q.replaceFirst(RegExp(r'^¿Qué es o qué significa (.+)\\?$'), 'What is or what does \\$1 mean?');",
    "q = q.replaceFirstMapped(RegExp(r'^¿Qué es o qué significa (.+)\\?$'), (m) => 'What is or what does ${m.group(1)} mean?');",
)
# Add the v1.16 semantic wrapper migration directly before returning q.
old_return = """        q = q.replaceFirst('Explica esta idea:', 'Explain this idea:');
        return q;
"""
new_return = """        q = q.replaceFirst('Explica esta idea:', 'Explain this idea:');
        q = q.replaceFirstMapped(
          RegExp(r'^¿Qué explica el contenido sobre [“\"](.+)[”\"]\\?$'),
          (m) => 'What does the content explain about “${m.group(1)}”?',
        );
        return q;
"""
if old_return not in s:
    raise RuntimeError('GuideStore semantic English migration anchor not found')
s = s.replace(old_return, new_return, 1)
p.write_text(s)

# Strings added by the timer/notification/PDF patches after their base files.
translations = {
    'lib/study_engine.dart': [
        ("'¿Qué explica el contenido sobre “$keyword”?'", "'What does the content explain about “$keyword”?'"),
        ("q.startsWith('¿Qué explica el contenido sobre')", "q.startsWith('What does the content explain about')"),
    ],
    'lib/daily_exam_page.dart': [
        ("'La IA superó el límite de 20 segundos.'", "'The AI exceeded the 20-second limit.'"),
        ("' • límite 20 s; completado con contenido verificado'", "' • 20 s limit; completed with verified content'"),
        ("'Preparando… ${examElapsedSeconds}s'", "'Preparing… ${examElapsedSeconds}s'"),
        ("'Creando examen… ${examElapsedSeconds}s'", "'Creating exam… ${examElapsedSeconds}s'"),
        ("'La IA redacta una parte y Memora completa el resto con contenido verificado del tutor. La IA tiene un máximo de 20 segundos; después el examen termina automáticamente sin seguir esperando.'", "'The AI writes part of the exam and Memora completes the rest with verified tutor content. The AI has a 20-second limit; after that the exam finishes automatically without waiting longer.'"),
        ("'Examen diario listo'", "'Daily exam ready'"),
        ("'${tutor.name}: ${exam.questions.length} preguntas preparadas.'", "'${tutor.name}: ${exam.questions.length} questions ready.'"),
        ("'Examen listo'", "'Exam ready'"),
        ("'Examen diario - ${exam.tutorName}'", "'Daily Exam - ${exam.tutorName}'"),
        ("'Examen - ${exam.tutorName}'", "'Exam - ${exam.tutorName}'"),
        ("'Tutor: ${exam.tutorName}'", "'Tutor: ${exam.tutorName}'"),
        ("'Dificultad: ${exam.difficulty}'", "'Difficulty: ${exam.difficulty}'"),
        ("'Fecha: $date'", "'Date: $date'"),
        ("'Preguntas: ${exam.questions.length}'", "'Questions: ${exam.questions.length}'"),
        ("'Generador: ${exam.generatorLabel}'", "'Generator: ${exam.generatorLabel}'"),
        ("'PREGUNTAS'", "'QUESTIONS'"),
        ("'Fuente: ${exam.questions[i].sourceTitle}'", "'Source: ${exam.questions[i].sourceTitle}'"),
        ("'RESPUESTAS'", "'ANSWERS'"),
        ("'Memora_Examen_${safeTutor.isEmpty ? 'Tutor' : safeTutor}_$date.pdf'", "'Memora_Exam_${safeTutor.isEmpty ? 'Tutor' : safeTutor}_$date.pdf'"),
        ("'Examen exportado como PDF.'", "'Exam exported as PDF.'"),
        ("'No pude exportar el PDF: $e'", "'I could not export the PDF: $e'"),
        ("'Exportar examen a PDF'", "'Export exam to PDF'"),
    ],
    'lib/study_plan_page.dart': [
        ("'Plan de aprendizaje listo'", "'Learning plan ready'"),
        ("'Memora terminó de crear tu plan con ${TutorContextService.sourceLabel(completedProvider)}.'", "'Memora finished creating your plan with ${TutorContextService.sourceLabel(completedProvider)}.'"),
        ("'PDF del plan listo'", "'Plan PDF ready'"),
        ("'El plan de aprendizaje fue exportado correctamente.'", "'The learning plan was exported successfully.'"),
    ],
    'lib/guide_creator_page.dart': [
        ("format == 'pdf' ? 'PDF listo' : 'Excel listo'", "format == 'pdf' ? 'PDF ready' : 'Excel ready'"),
        ("'$title fue creado y añadido a tu Biblioteca.'", "'$title was created and added to your Library.'"),
    ],
    'lib/ai_study_guide_page.dart': [
        ("'Guía de estudio lista'", "'Study guide ready'"),
        ("'Memora terminó la guía de ${g.title}.'", "'Memora finished the study guide for ${g.title}.'"),
    ],
    'lib/ai_service.dart': [
        ("'Tarea del tutor/agente terminada'", "'Tutor/agent task complete'"),
        ("'Memora terminó el trabajo que le pediste.'", "'Memora finished the task you requested.'"),
        ("'El contenido supera el contexto de este modelo local. Memora reducirá el contexto en las tareas compatibles; si vuelve a ocurrir, usa un modelo con una ventana de contexto mayor.'", "'The content exceeds this local model context window. Memora reduces context for compatible tasks; if it happens again, use a model with a larger context window.'"),
    ],
    'lib/tutor_page.dart': [
        ("'Selector rápido de IA'", "'Quick AI selector'"),
        ("'Cambia la IA general de todos los tutores.'", "'Change the general AI used by all tutors.'"),
        ("'IA general: ${_sourceLabel(provider)}'", "'General AI: ${_sourceLabel(provider)}'"),
        ("'Gemini online'", "'Gemini online'"),
        ("'OpenAI / compatible'", "'OpenAI / compatible'"),
        ("'Ollama / servidor local'", "'Ollama / local server'"),
        ("'GGUF del teléfono'", "'On-phone GGUF'"),
        ("'Ajustes completos de IA'", "'Full AI settings'"),
        ("'Este tutor usa la IA general de Memora. Puedes cambiarla al instante desde el selector rápido.'", "'This tutor uses Memora general AI. You can change it instantly from the quick selector.'"),
        ("'IA general de Memora • ${tutor.guideIds.length} guía(s)'", "'Memora general AI • ${tutor.guideIds.length} guide(s)'"),
        ("'IA general de los tutores'", "'General tutor AI'"),
    ],
}

for filename, pairs in translations.items():
    p = Path(filename)
    s = p.read_text()
    for old, new in pairs:
        s = s.replace(old, new)
    p.write_text(s)

# A few common user-facing words can be safely translated only when they are
# complete Dart string literals. This catches small UI labels from older patches.
common = [
    ("'Cancelar'", "'Cancel'"),
    ("'Guardar'", "'Save'"),
    ("'Eliminar'", "'Delete'"),
    ("'Cerrar'", "'Close'"),
    ("'Siguiente'", "'Next'"),
    ("'Respuesta'", "'Answer'"),
    ("'Pregunta'", "'Question'"),
]
for p in Path('lib').glob('*.dart'):
    s = p.read_text()
    for old, new in common:
        s = s.replace(old, new)
    p.write_text(s)

print('Memora v1.18.1 English cleanup patch applied successfully')
