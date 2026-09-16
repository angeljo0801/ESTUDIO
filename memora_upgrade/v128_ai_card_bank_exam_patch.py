from pathlib import Path

p = Path('lib/daily_exam_page.dart')
s = p.read_text()

old = """      questions = await _generateAiExamQuestions(
        tutor: tutor,
        guides: guides,
        count: count,
        difficulty: difficulty,
        provider: provider,
        resolvedProvider: resolvedProvider,
        localish: localish,
        recentQuestions: recentQuestions,
      );

      if (questions.length < count) {
"""

new = """      // v1.28: reuse the AI-generated study-card bank first. These questions
      // were already created by the configured AI from the guide, so a normal
      // exam should not make a slow local model regenerate the same knowledge.
      questions = _cardQuestions(
        guides,
        count,
        avoidQuestions: recentQuestions,
      );

      // Prefer variety, but never make the user wait minutes just because the
      // recent-question filter left too few cards. Fill from the remaining AI
      // card bank before asking the model for anything new.
      if (questions.length < count) {
        final relaxed = _cardQuestions(
          guides,
          count,
          avoidQuestions: const <String>[],
        );
        for (final item in relaxed) {
          if (questions.length >= count) break;
          if (questions.any((old) => _nearDuplicate(old.question, item.question))) continue;
          questions.add(item);
        }
      }

      if (questions.length >= count) {
        questions = questions.take(count).toList();
        generatorLabel = 'AI card bank • $displayLabel';
        if (mounted) {
          setState(() {
            examGeneratedQuestions = count;
            examTargetQuestions = count;
            examGenerationStage = 'Ready from AI card bank';
          });
        }
      } else {
        final missing = count - questions.length;
        final fresh = await _generateAiExamQuestions(
          tutor: tutor,
          guides: guides,
          count: missing,
          difficulty: difficulty,
          provider: provider,
          resolvedProvider: resolvedProvider,
          localish: localish,
          recentQuestions: <String>[
            ...recentQuestions,
            ...questions.map((q) => q.question),
          ],
        );
        for (final item in fresh) {
          if (questions.length >= count) break;
          if (questions.any((old) => _nearDuplicate(old.question, item.question))) continue;
          questions.add(item);
        }
        generatorLabel = 'AI card bank + $displayLabel';
      }

      if (questions.length < count) {
"""

if old not in s:
    raise RuntimeError('v1.28 exam AI call anchor not found')
s = s.replace(old, new, 1)

# Update the UI explanation so System AI no longer implies every exam must wait
# for a brand-new model generation when an AI-generated card bank already exists.
s = s.replace(
    'When an AI generator is selected, Memora waits for that AI.\nThe stopwatch only shows how long generation is taking; it\ndoes not force a fallback to indexed questions.',
    'Memora first builds the exam from your AI-generated study cards.\nIf more questions are needed, it asks the selected AI only for\nthe missing ones.',
)
s = s.replace(
    'When an AI generator is selected, Memora waits for that AI. The stopwatch only shows how long generation is taking; it does not force a fallback to indexed questions.',
    'Memora first builds the exam from your AI-generated study cards. If more questions are needed, it asks the selected AI only for the missing ones.',
)

p.write_text(s)
print('Memora v1.28 AI card-bank exam patch applied successfully')
