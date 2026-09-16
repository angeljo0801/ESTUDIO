from pathlib import Path
import re

p = Path('lib/daily_exam_page.dart')
s = p.read_text()

# Ensure timeout support is available.
if "import 'dart:async';" not in s:
    if s.startswith("import 'dart:convert';"):
        s = s.replace("import 'dart:convert';", "import 'dart:async';\nimport 'dart:convert';", 1)
    else:
        s = "import 'dart:async';\n" + s

# Add a human-readable live stage next to the existing timer/progress counters.
state_anchor = "  int examTargetQuestions = 0;\n"
if "String examGenerationStage" not in s:
    if state_anchor not in s:
        raise RuntimeError('Exam target state anchor not found')
    s = s.replace(
        state_anchor,
        state_anchor + "  String examGenerationStage = 'Preparing';\n",
        1,
    )

# Show what Memora is actually doing instead of leaving 0/10 looking frozen.
s = s.replace(
    "'Creating exam… ${examElapsedSeconds}s${examTargetQuestions > 0 ? ' • $examGeneratedQuestions/$examTargetQuestions' : ''}'",
    "'Creating exam… ${examElapsedSeconds}s${examGenerationStage.isNotEmpty ? ' • $examGenerationStage' : ''}${examTargetQuestions > 0 ? ' • $examGeneratedQuestions/$examTargetQuestions' : ''}'",
)

# Replace the whole batched generator after the v1.23 wrapper has been applied.
start = s.find('  Future<List<ExamQuestionData>> _generateAiExamQuestions({\n')
end = s.find('\n  Future<TutorExamSession> _buildExam({', start)
if start < 0 or end < 0:
    raise RuntimeError('Final exam generator block not found')

new_method = r'''  List<String> _compactExamMaterial(
    List<StudyGuide> guides, {
    required int maxChars,
  }) {
    final chunks = <String>[];
    for (final guide in guides) {
      final cards = guide.cards.where((card) {
        final q = card.question.trim();
        final a = card.answer.trim();
        return q.length >= 8 && a.length >= 8;
      }).toList();
      if (cards.length < 6) continue;

      var buffer = StringBuffer('=== ${guide.title} • AI STUDY CARDS ===\n');
      for (final card in cards) {
        final line = 'Q: ${card.question.trim()}\nA: ${card.answer.trim()}\n';
        if (buffer.length + line.length > maxChars && buffer.length > 120) {
          chunks.add(buffer.toString().trim());
          buffer = StringBuffer('=== ${guide.title} • AI STUDY CARDS ===\n');
        }
        buffer.writeln(line);
      }
      final tail = buffer.toString().trim();
      if (tail.length > guide.title.length + 40) chunks.add(tail);
    }
    return chunks;
  }

  Future<List<ExamQuestionData>> _generateAiExamQuestions({
    required TutorContextProfile tutor,
    required List<StudyGuide> guides,
    required int count,
    required String difficulty,
    required String provider,
    required String resolvedProvider,
    required bool localish,
    required List<String> recentQuestions,
  }) async {
    return BackgroundTaskService.run<List<ExamQuestionData>>(
      title: 'Memora is creating an exam',
      body: 'Preparing the first question batch…',
      task: () async {
        final directDevice = resolvedProvider == 'private' ||
            resolvedProvider == 'shared' ||
            resolvedProvider == 'device';
        final ollamaLike = resolvedProvider == 'local' ||
            resolvedProvider == 'ollama';

        final materialLimit = directDevice ? 2800 : (ollamaLike ? 3800 : 7000);
        var chunks = _compactExamMaterial(guides, maxChars: materialLimit);
        // If cards have not been generated yet, fall back to real guide text.
        if (chunks.isEmpty) {
          chunks = _examContentChunks(guides, materialLimit);
        }
        if (chunks.isEmpty) return const [];

        final out = <ExamQuestionData>[];
        final batchSize = directDevice ? 3 : (ollamaLike ? 4 : 6);
        final expectedBatches = (count / batchSize).ceil();
        final maxAttempts = max(expectedBatches + 3, 5).clamp(5, 12).toInt();
        final timeout = Duration(seconds: directDevice ? 90 : (ollamaLike ? 75 : 50));
        var attempt = 0;

        if (mounted) {
          setState(() {
            examGeneratedQuestions = 0;
            examTargetQuestions = count;
            examGenerationStage = 'Batch 1/$expectedBatches • waiting for model';
          });
        }

        while (out.length < count && attempt < maxAttempts) {
          final batchNumber = min(attempt + 1, maxAttempts);
          final chunk = chunks[attempt % chunks.length];
          final needed = count - out.length;
          final askFor = min(batchSize, needed);
          final avoid = <String>[
            ...recentQuestions.take(18),
            ...out.map((q) => q.question),
          ];

          if (mounted) {
            setState(() {
              examGenerationStage =
                  'Batch $batchNumber/${max(expectedBatches, batchNumber)} • waiting for model';
            });
          }
          await BackgroundTaskService.update(
            title: 'Memora is creating an exam',
            body: 'Batch $batchNumber • ${out.length} of $count questions ready',
            progress: out.length,
            max: count,
          );

          String raw = '';
          var partialSeen = false;
          try {
            // IMPORTANT: use the normal configured route for exam batches. Direct
            // GGUF then stays loaded across batches instead of being disposed and
            // reloaded by the isolated one-shot task API every time.
            raw = await AiService.askConfigured(
              providerOverride: provider,
              responseMode: 'fast',
              onPartial: (partial) {
                if (partial.isEmpty || partialSeen) return;
                partialSeen = true;
                if (mounted) {
                  setState(() {
                    examGenerationStage =
                        'Batch $batchNumber/${max(expectedBatches, batchNumber)} • model responding';
                  });
                }
              },
              prompt: '''Create exactly $askFor NEW high-quality exam questions using ONLY the MATERIAL below.
Difficulty: $difficulty.

RULES:
- Test understanding, application, cause/effect, comparison, decision-making, formulas, or calculations when the material supports them.
- You may paraphrase and combine directly related ideas from the material.
- Do not use outside knowledge.
- Questions must stand alone and answers must be concise but complete enough to grade.
- Do not create isolated-word trivia, fragments, or vague questions.
- Avoid the previous questions below, including close rephrasings.
- Return ONLY a JSON array. No Markdown and no commentary.
- Item format: {"question":"...","answer":"...","source":"guide/topic"}.

QUESTIONS TO AVOID:
${avoid.isEmpty ? '(none)' : avoid.map((q) => '- $q').join('\n')}

MATERIAL:
$chunk''',
            ).timeout(
              timeout,
              onTimeout: () async {
                await AiService.cancelCurrent();
                return '';
              },
            );
          } catch (_) {
            // Keep previously accepted batches and move on. A single model or
            // formatting failure must not freeze the whole exam at 0/N.
            try {
              await AiService.cancelCurrent();
            } catch (_) {}
          }

          if (raw.trim().isNotEmpty) {
            final parsed = _parseAiQuestions(
              raw,
              guides: guides,
              avoidQuestions: avoid,
            );
            for (final item in parsed) {
              if (out.length >= count) break;
              if (out.any((old) => _nearDuplicate(old.question, item.question))) continue;
              out.add(item);
            }
          }

          if (mounted) {
            setState(() {
              examGeneratedQuestions = out.length;
              examGenerationStage = out.length >= count
                  ? 'Finalizing'
                  : 'Validated ${out.length}/$count';
            });
          }
          await BackgroundTaskService.update(
            title: 'Memora is creating an exam',
            body: '${out.length} of $count questions ready',
            progress: out.length,
            max: count,
          );
          attempt++;
        }
        return out;
      },
    );
  }

'''
s = s[:start] + new_method + s[end:]

# Pass the exact resolved provider so the batch strategy can distinguish direct
# GGUF, Ollama, and online providers.
old_call = """        provider: provider,
        localish: localish,
        recentQuestions: recentQuestions,
"""
new_call = """        provider: provider,
        resolvedProvider: resolvedProvider,
        localish: localish,
        recentQuestions: recentQuestions,
"""
if old_call not in s:
    raise RuntimeError('Exam generator call anchor not found')
s = s.replace(old_call, new_call, 1)

# Reset the stage with the existing progress reset lifecycle when present.
s = s.replace(
    "examGeneratedQuestions = 0;\n        examTargetQuestions = 0;",
    "examGeneratedQuestions = 0;\n        examTargetQuestions = 0;\n        examGenerationStage = 'Preparing';",
)

p.write_text(s)
print('Memora v1.27 fast resilient exam batches patch applied successfully')
