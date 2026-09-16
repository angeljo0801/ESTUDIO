from pathlib import Path

p = Path('lib/daily_exam_page.dart')
s = p.read_text()

# -----------------------------------------------------------------------------
# Memora v1.43: selective semantic quality review for AI-created exam questions.
# Fast deterministic filters remain first. Only higher-risk survivors are sent
# through one batched semantic review, avoiding one extra LLM call per question.
# -----------------------------------------------------------------------------
helper_anchor = "  List<String> _compactExamMaterial(\n"
helpers = r"""  bool _hardExamDifficulty(String difficulty) {
    final key = difficulty.toLowerCase().trim();
    return key == 'hard' || key == 'difícil' || key == 'dificil';
  }

  bool _directRecallExamQuestion(String question) {
    final clean = question.toLowerCase().trim();
    return RegExp(
      r'^(?:what\s+(?:is|are)|define|identify|name|list|state|describe|who\s+is|when\s+is|qué\s+es|que\s+es|define|identifica|nombra|menciona|enumera|indica|describe)\b',
      caseSensitive: false,
    ).hasMatch(clean);
  }

  int _semanticExamReviewRisk(
    ExamQuestionData item,
    List<StudyGuide> guides,
    String difficulty,
  ) {
    final question = item.question.toLowerCase().trim();
    final answer = item.answer.toLowerCase().trim();
    var risk = 0;

    if (RegExp(
      r'\b(compare|comparison|contrast|distinguish|difference|different|scenario|case|imagine|decision|justify|why|cómo se diferencia|como se diferencia|compara|comparación|comparacion|escenario|caso|decisión|decision|justifica)\b',
      caseSensitive: false,
    ).hasMatch(question)) {
      risk += 3;
    }

    if (_hardExamDifficulty(difficulty) && _directRecallExamQuestion(question)) {
      risk += 5;
    }

    // A question that already contains much of its own answer may be a disguised
    // flashcard or may be giving the learner the answer in the stem.
    if (_examLexicalOverlap(question, answer) >= 0.55) {
      risk += 4;
    }

    if (answer.length > 420) risk += 1;

    for (final guide in guides) {
      for (final card in guide.cards) {
        final sourceQuestion = card.question.trim();
        final sourceAnswer = card.answer.trim();
        if (sourceQuestion.isNotEmpty) {
          final overlap = _examLexicalOverlap(question, sourceQuestion);
          if (overlap >= 0.40 && overlap < 0.88) risk += 2;
        }
        if (sourceAnswer.length >= 24) {
          final overlap = _examLexicalOverlap(question, sourceAnswer);
          if (overlap >= 0.42 && overlap < 0.92) risk += 3;
        }
        if (risk >= 8) return risk;
      }
    }
    return risk;
  }

  String _semanticExamEvidenceFor(
    ExamQuestionData item,
    List<StudyGuide> guides,
  ) {
    final blocks = <String>[];
    for (final guide in guides) {
      for (final card in guide.cards) {
        final q = card.question.trim();
        final a = card.answer.trim();
        if (q.isEmpty || a.isEmpty) continue;
        final score = max(
          _examLexicalOverlap(item.question, q),
          _examLexicalOverlap(item.question, a),
        );
        if (score < 0.18) continue;
        blocks.add('CARD: $q\nANSWER: $a');
        if (blocks.length >= 3) return blocks.join('\n---\n');
      }
    }
    return blocks.join('\n---\n');
  }

  Future<Set<int>> _semanticExamRejectedIndexes({
    required List<ExamQuestionData> questions,
    required List<StudyGuide> guides,
    required String difficulty,
    required String provider,
    required bool directDevice,
    required bool ollamaLike,
  }) async {
    final risky = <({int index, int risk})>[];
    for (var i = 0; i < questions.length; i++) {
      final risk = _semanticExamReviewRisk(questions[i], guides, difficulty);
      if (risk > 0) risky.add((index: i, risk: risk));
    }
    if (risky.isEmpty) return <int>{};

    // One compact review call keeps quality high without reviewing every normal
    // question or doubling generation latency. Review the riskiest survivors.
    risky.sort((a, b) => b.risk.compareTo(a.risk));
    final review = risky.take(8).toList();

    if (mounted) {
      setState(() {
        examGenerationStage = 'Semantic quality check • ${review.length} question${review.length == 1 ? '' : 's'}';
      });
    }

    final candidates = review.map((entry) {
      final item = questions[entry.index];
      final evidence = _semanticExamEvidenceFor(item, guides);
      return '''ID: ${entry.index}
QUESTION: ${item.question}
ANSWER: ${item.answer}
NEARBY SOURCE CARDS:
${evidence.isEmpty ? '(no close source card; grounding already passed local validation)' : evidence}''';
    }).join('\n\n========\n\n');

    final prompt = '''You are Memora's exam-quality validator. Review ONLY the candidate questions below. They already passed deterministic grounding, duplicate, and pasted-card filters.

Selected difficulty: $difficulty

For each ID, set pass=false ONLY when there is a clear quality defect:
1. The displayed answer does not directly answer the displayed question, or contains unrelated appended material.
2. The question gives away most of its answer, merely disguises/repeats a source flashcard, or turns the source answer into the stem.
3. A comparison is incoherent because the two things are not meaningfully comparable in the study context. Do NOT reject a valid comparison merely because the concepts are different.
4. For HARD difficulty, a question that is only direct definition/recall with no meaningful application, inference, comparison, calculation, decision, cause/effect, or reasoning should fail.
5. The question or answer is internally contradictory, malformed, or impossible to grade from the stated answer.

Do NOT reject merely because necessary technical vocabulary overlaps with the source. Do NOT rewrite questions. Be conservative: when a question is valid, pass it.
Return ONLY a JSON array in this exact shape, with every supplied ID exactly once:
[{"id":0,"pass":true,"reason":"short reason"}]

CANDIDATES:
$candidates''';

    try {
      final raw = await AiService.askConfigured(
        providerOverride: provider,
        responseMode: 'fast',
        prompt: prompt,
      ).timeout(
        Duration(seconds: directDevice ? 35 : (ollamaLike ? 30 : 20)),
        onTimeout: () async {
          try {
            await AiService.cancelCurrent();
          } catch (_) {}
          return '';
        },
      );

      if (raw.trim().isEmpty) return <int>{};
      var clean = raw.trim();
      clean = clean.replaceFirst(RegExp(r'^```(?:json)?\s*', caseSensitive: false), '');
      clean = clean.replaceFirst(RegExp(r'\s*```$'), '');
      final first = clean.indexOf('[');
      final last = clean.lastIndexOf(']');
      if (first < 0 || last <= first) return <int>{};
      final decoded = jsonDecode(clean.substring(first, last + 1));
      if (decoded is! List) return <int>{};

      final reviewedIds = review.map((e) => e.index).toSet();
      final rejected = <int>{};
      for (final row in decoded) {
        if (row is! Map) continue;
        final rawId = row['id'];
        final id = rawId is int ? rawId : int.tryParse(rawId?.toString() ?? '');
        if (id == null || !reviewedIds.contains(id)) continue;
        final rawPass = row['pass'];
        final passed = rawPass is bool
            ? rawPass
            : rawPass?.toString().toLowerCase() == 'true';
        if (!passed) rejected.add(id);
      }
      return rejected;
    } catch (_) {
      // Semantic review is a quality enhancement, never a single point of
      // failure. If the reviewer is unavailable, retain the deterministic pass.
      return <int>{};
    }
  }

"""
if '_semanticExamRejectedIndexes(' not in s:
    if helper_anchor not in s:
        raise RuntimeError('v1.43 exam semantic helper anchor not found')
    s = s.replace(helper_anchor, helpers + helper_anchor, 1)

# Run one semantic review after all model batches. Rejected questions are simply
# removed; the existing transformed-card fallback in _buildExam fills the gap.
gen_start = s.find('  Future<List<ExamQuestionData>> _generateAiExamQuestions({\n')
gen_end = s.find('\n  Future<TutorExamSession> _buildExam({', gen_start)
if gen_start < 0 or gen_end < 0:
    raise RuntimeError('v1.43 AI generator block not found')
block = s[gen_start:gen_end]
old_end = """        return out;
      },
    );
  }
"""
new_end = """        final semanticRejected = await _semanticExamRejectedIndexes(
          questions: out,
          guides: guides,
          difficulty: difficulty,
          provider: provider,
          directDevice: directDevice,
          ollamaLike: ollamaLike,
        );
        if (semanticRejected.isNotEmpty) {
          final kept = <ExamQuestionData>[];
          for (var i = 0; i < out.length; i++) {
            if (!semanticRejected.contains(i)) kept.add(out[i]);
          }
          out
            ..clear()
            ..addAll(kept);
        }
        if (mounted) {
          setState(() {
            examGeneratedQuestions = out.length;
            examGenerationStage = semanticRejected.isEmpty
                ? 'Quality validated • ${out.length}/$count'
                : 'Rejected ${semanticRejected.length} weak question${semanticRejected.length == 1 ? '' : 's'} • ${out.length}/$count';
          });
        }
        return out;
      },
    );
  }
"""
if old_end not in block:
    raise RuntimeError('v1.43 AI generator return anchor not found')
block = block.replace(old_end, new_end, 1)
s = s[:gen_start] + block + s[gen_end:]

# Explain the quality pipeline in the exam creator UI where the existing v1.37
# copy is present.
s = s.replace(
    'When an AI is selected, Memora creates fresh reasoning questions and rejects questions that copy the study cards too closely. Each exam rotates application, comparison, scenarios, true/false, reverse reasoning and calculations when supported. Instant mode remains available for a faster transformed-card exam.',
    'When an AI is selected, Memora creates fresh reasoning questions, applies fast anti-copy and answer-cleanup filters, then semantically reviews higher-risk questions for answer alignment, hidden answer leakage, comparison coherence and real difficulty. Instant mode remains available for a faster transformed-card exam.',
)

p.write_text(s)
print('Memora v1.43 selective semantic exam-quality patch applied successfully')
