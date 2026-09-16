from pathlib import Path

p = Path('lib/daily_exam_page.dart')
s = p.read_text()

# -----------------------------------------------------------------------------
# 1) Let users really delete saved exam sessions from app storage.
# -----------------------------------------------------------------------------
upsert_start = s.find('  Future<void> _upsertExam(TutorExamSession exam) async {\n')
upsert_end = s.find('\n  List<ExamQuestionData> _cardQuestions(', upsert_start)
if upsert_start < 0 or upsert_end < 0:
    raise RuntimeError('v1.37 upsert exam anchor not found')

if 'Future<void> _deleteExam(TutorExamSession exam)' not in s:
    delete_method = r'''
  Future<void> _deleteExam(TutorExamSession exam) async {
    final confirmed = await showDialog<bool>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            title: const Text('Delete exam?'),
            content: Text(
              'This will permanently remove the saved exam for ${exam.tutorName} and its ${exam.questions.length} questions from Memora.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: const Text('Cancel'),
              ),
              FilledButton.tonalIcon(
                onPressed: () => Navigator.pop(dialogContext, true),
                icon: const Icon(Icons.delete_outline_rounded),
                label: const Text('Delete'),
              ),
            ],
          ),
        ) ??
        false;
    if (!confirmed) return;

    final copy = List<TutorExamSession>.from(sessions)
      ..removeWhere((item) => item.id == exam.id);
    if (mounted) setState(() => sessions = copy);
    await _saveSessions();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Exam deleted from Memora.')),
    );
  }

'''
    s = s[:upsert_end] + delete_method + s[upsert_end:]

# Add delete beside the existing PDF export button, keeping row tap to open.
old_trailing = """                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      tooltip: 'Export exam to PDF',
                      onPressed: () => _exportExamPdf(exam),
                      icon: const Icon(Icons.picture_as_pdf_outlined),
                    ),
                    const Icon(Icons.chevron_right_rounded),
                  ],
                ),
                onTap: () => _openExam(exam),
"""
# Some older translation stage may leave the Spanish tooltip.
old_trailing_es = old_trailing.replace('Export exam to PDF', 'Exportar examen a PDF')
new_trailing = """                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      tooltip: 'Delete exam',
                      onPressed: () => _deleteExam(exam),
                      icon: const Icon(Icons.delete_outline_rounded),
                    ),
                    IconButton(
                      tooltip: 'Export exam to PDF',
                      onPressed: () => _exportExamPdf(exam),
                      icon: const Icon(Icons.picture_as_pdf_outlined),
                    ),
                    const Icon(Icons.chevron_right_rounded),
                  ],
                ),
                onTap: () => _openExam(exam),
"""
if old_trailing in s:
    s = s.replace(old_trailing, new_trailing, 1)
elif old_trailing_es in s:
    s = s.replace(old_trailing_es, new_trailing, 1)
else:
    raise RuntimeError('v1.37 created exam trailing anchor not found')

# -----------------------------------------------------------------------------
# 2) Reject AI questions that are too lexically close to the study cards.
# -----------------------------------------------------------------------------
compact_anchor = '  List<String> _compactExamMaterial(\n'
if compact_anchor not in s:
    raise RuntimeError('v1.37 compact exam material anchor not found')

anti_copy_helpers = r'''  Set<String> _examLexemes(String value) {
    const stop = <String>{
      'the','and','for','with','that','this','from','into','what','which','when','where','does','are','is','to','of','a','an',
      'que','como','para','con','del','los','las','una','uno','por','qué','cual','cuál','es','son','se','de','el','la','y','en',
    };
    return value
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-z0-9áéíóúüñ%$]+'), ' ')
        .split(RegExp(r'\s+'))
        .map((e) => e.trim())
        .where((e) => e.length >= 3 && !stop.contains(e))
        .toSet();
  }

  double _examLexicalOverlap(String a, String b) {
    final left = _examLexemes(a);
    final right = _examLexemes(b);
    if (left.isEmpty || right.isEmpty) return 0;
    final shared = left.intersection(right).length;
    final base = min(left.length, right.length);
    return base == 0 ? 0 : shared / base;
  }

  bool _tooCloseToStudyCards(ExamQuestionData item, List<StudyGuide> guides) {
    final question = item.question.trim();
    if (question.length < 8) return true;
    for (final guide in guides) {
      for (final card in guide.cards) {
        final originalQuestion = card.question.trim();
        final originalAnswer = card.answer.trim();
        if (originalQuestion.isNotEmpty) {
          if (_nearDuplicate(question, originalQuestion)) return true;
          if (_examLexicalOverlap(question, originalQuestion) >= 0.70) return true;
        }
        if (originalAnswer.length >= 28 &&
            _examLexicalOverlap(question, originalAnswer) >= 0.82) {
          return true;
        }
      }
    }
    return false;
  }

'''
s = s.replace(compact_anchor, anti_copy_helpers + compact_anchor, 1)

parsed_loop = """            for (final item in parsed) {
              if (out.length >= count) break;
              if (out.any((old) => _nearDuplicate(old.question, item.question))) continue;
              out.add(item);
            }
"""
parsed_loop_new = """            for (final item in parsed) {
              if (out.length >= count) break;
              if (out.any((old) => _nearDuplicate(old.question, item.question))) continue;
              // Do not accept an AI question that merely copies or lightly
              // rewords one of the source flashcards. Keep generating until the
              // learner has to understand and transfer the idea.
              if (_tooCloseToStudyCards(item, guides)) continue;
              out.add(item);
            }
"""
if parsed_loop not in s:
    raise RuntimeError('v1.37 parsed-question validation anchor not found')
s = s.replace(parsed_loop, parsed_loop_new, 1)

# Stronger generation rules: facts stay grounded, wording and cognitive task do not.
prompt_rules = """- Across the batch, vary among application, comparison, scenario/decision, true/false with justification, concept matching, reverse reasoning, and formulas/calculations when supported.
"""
prompt_rules_new = """- Across the batch, vary among application, comparison, scenario/decision, true/false with justification, concept matching, reverse reasoning, and formulas/calculations when supported.
- NEVER copy a study-card question verbatim or with only minor word substitutions.
- NEVER paste a long study-card answer into the question stem as a quotation.
- Preserve the underlying facts, but express the task in genuinely different language and structure.
- Prefer transfer: give a new situation, consequence, comparison, decision, cause/effect relation, or calculation that requires the learner to reason from the material.
- For HARD difficulty, most questions must require at least two reasoning steps or applying the idea in a new context; avoid direct definition prompts unless absolutely necessary.
- If a proposed question resembles a source card too closely, discard it internally and create another variant before returning JSON.
"""
if prompt_rules not in s:
    raise RuntimeError('v1.37 AI anti-copy prompt anchor not found')
s = s.replace(prompt_rules, prompt_rules_new, 1)

# -----------------------------------------------------------------------------
# 3) When the user explicitly chooses an AI generator, let that AI create the
# fresh reasoning exam first. The fast transformed-card bank remains a fallback,
# and Instant mode remains available when speed matters most.
# -----------------------------------------------------------------------------
start_marker = '      // v1.28: reuse the AI-generated study-card bank first.'
end_marker = "        generatorLabel = 'Varied AI-card exam + $displayLabel';\n      }\n"
start = s.find(start_marker)
end = s.find(end_marker, start)
if start < 0 or end < 0:
    raise RuntimeError('v1.37 AI-first exam block anchor not found')
end += len(end_marker)

ai_first = r'''      // v1.37: an explicit AI generator now writes a genuinely fresh exam.
      // The saved AI-card bank is still a fast grounded fallback if the model
      // cannot provide enough validated, non-copying questions.
      questions = await _generateAiExamQuestions(
        tutor: tutor,
        guides: guides,
        count: count,
        difficulty: difficulty,
        variant: examVariant,
        provider: provider,
        resolvedProvider: resolvedProvider,
        localish: localish,
        recentQuestions: recentQuestions,
      );
      generatorLabel = 'Reasoning AI exam • $displayLabel';

      if (questions.length < count) {
        final transformed = _cardQuestions(
          guides,
          count,
          avoidQuestions: <String>[
            ...recentQuestions,
            ...questions.map((q) => q.question),
          ],
          difficulty: difficulty,
          variant: examVariant,
        );
        for (final item in transformed) {
          if (questions.length >= count) break;
          if (questions.any((old) => _nearDuplicate(old.question, item.question))) continue;
          questions.add(item);
        }
        generatorLabel = 'Reasoning AI exam + transformed fallback • $displayLabel';
      }
'''
s = s[:start] + ai_first + s[end:]

# UI copy should explain the difference between AI and Instant modes.
s = s.replace(
    'Memora creates a new exam variant each time. The selected difficulty changes the reasoning level, and the modality mix rotates among application, comparison, scenarios, true/false, concept matching, reverse reasoning and formulas when supported. It asks the selected AI only if more material is needed.',
    'When an AI is selected, Memora creates fresh reasoning questions and rejects questions that copy the study cards too closely. Each exam rotates application, comparison, scenarios, true/false, reverse reasoning and calculations when supported. Instant mode remains available for a faster transformed-card exam.',
)

p.write_text(s)
print('Memora v1.37 exam deletion + reasoning anti-copy patch applied successfully')
