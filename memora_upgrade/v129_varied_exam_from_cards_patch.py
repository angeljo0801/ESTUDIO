from pathlib import Path

p = Path('lib/daily_exam_page.dart')
s = p.read_text()

start = s.find('  List<ExamQuestionData> _cardQuestions(\n')
if start < 0:
    raise RuntimeError('v1.29 card question helper start not found')
end = s.find('  String _normalizeEvidence(', start)
if end < 0:
    end = s.find('  List<ExamQuestionData> _parseAiQuestions(', start)
if end < 0:
    raise RuntimeError('v1.29 card question helper end not found')

new_block = r'''  String? _examConceptFromQuestion(String question) {
    var q = question.trim().replaceAll(RegExp(r'[?¿]+$'), '').trim();
    final patterns = <RegExp>[
      RegExp(r'^(?:what is|what are|define|what is meant by)\s+(.+)$', caseSensitive: false),
      RegExp(r'^what does\s+(.+?)\s+mean$', caseSensitive: false),
      RegExp(r'^how is\s+(.+?)\s+calculated$', caseSensitive: false),
      RegExp(r'^what is the (?:formula|relationship) (?:for|of)\s+(.+)$', caseSensitive: false),
      RegExp(r'^what is the purpose of\s+(.+)$', caseSensitive: false),
      RegExp(r'^(?:qué es|qué son|define|qué significa)\s+(.+)$', caseSensitive: false),
      RegExp(r'^cómo se calcula\s+(.+)$', caseSensitive: false),
    ];
    for (final pattern in patterns) {
      final m = pattern.firstMatch(q);
      if (m == null) continue;
      final value = m.group(1)!.trim();
      if (value.length >= 2 && value.length <= 80 && _matchWords(value).length <= 10) {
        return value;
      }
    }
    return null;
  }

  String _examDescription(String answer, String? concept) {
    var text = answer.trim().replaceAll(RegExp(r'\s+'), ' ');
    if (concept != null && concept.trim().isNotEmpty) {
      final escaped = RegExp.escape(concept.trim());
      text = text.replaceFirst(
        RegExp('^$escaped\\s+(?:is|are|means|refers to)\\s+', caseSensitive: false),
        '',
      );
      text = text.replaceFirst(
        RegExp('^$escaped\\s*=\\s*', caseSensitive: false),
        '',
      );
    }
    if (text.length > 300) text = '${text.substring(0, 297).trim()}…';
    return text;
  }

  String _examOptionLabel(String question, String? concept) {
    if (concept != null && concept.trim().isNotEmpty) return concept.trim();
    var q = question.trim().replaceAll(RegExp(r'\s+'), ' ');
    if (q.length > 92) q = '${q.substring(0, 89).trim()}…';
    return q;
  }

  String _letterFor(int index) => String.fromCharCode(65 + index.clamp(0, 25));

  ({String lhs, String left, String op, String right})? _simpleFormula(String answer) {
    final normalized = answer.trim().replaceAll('×', '*').replaceAll('÷', '/');
    final m = RegExp(
      r'^([^=\n]{2,55})\s*=\s*([A-Za-z][A-Za-z0-9 $%()._-]{1,45}?)\s*([+\-*/])\s*([A-Za-z][A-Za-z0-9 $%()._-]{1,45})(?:[.;]|$)',
      caseSensitive: false,
    ).firstMatch(normalized);
    if (m == null) return null;
    final lhs = m.group(1)!.trim();
    final left = m.group(2)!.trim();
    final op = m.group(3)!.trim();
    final right = m.group(4)!.trim();
    if ([lhs, left, right].any((x) => x.length < 2 || x.length > 55)) return null;
    return (lhs: lhs, left: left, op: op, right: right);
  }

  List<ExamQuestionData> _cardQuestions(
    List<StudyGuide> guides,
    int count, {
    List<String> avoidQuestions = const [],
  }) {
    final rng = Random(DateTime.now().microsecondsSinceEpoch);
    final records = <({
      StudyGuide guide,
      StudyCard card,
      ExamQuestionData item,
      String? concept,
      double priority,
    })>[];

    for (final guide in guides) {
      for (final card in guide.cards) {
        final item = _cleanCard(guide, card);
        if (item == null) continue;
        final priority = card.wrong * 2.0 + (card.isDue ? 1.5 : 0) - card.correct * .15 + rng.nextDouble();
        records.add((
          guide: guide,
          card: card,
          item: item,
          concept: _examConceptFromQuestion(item.question),
          priority: priority,
        ));
      }
    }
    if (records.isEmpty) return const [];
    records.sort((a, b) => b.priority.compareTo(a.priority));

    final formula = <ExamQuestionData>[];
    final comparisons = <ExamQuestionData>[];
    final conceptMcq = <ExamQuestionData>[];
    final trueFalse = <ExamQuestionData>[];
    final reverseMcq = <ExamQuestionData>[];
    final reverseOpen = <ExamQuestionData>[];
    final candidateQuestions = <String>[];

    bool canAdd(String question) {
      final stem = question.split('\n').first.trim();
      if (stem.length < 8) return false;
      if (candidateQuestions.any((q) => _nearDuplicate(q, question))) return false;
      if (avoidQuestions.any((q) => _nearDuplicate(q, question))) return false;
      if (records.any((r) => _nearDuplicate(r.item.question, stem))) return false;
      candidateQuestions.add(question);
      return true;
    }

    void addTo(List<ExamQuestionData> group, String question, String answer, String source) {
      if (answer.trim().length < 2 || !canAdd(question)) return;
      group.add(ExamQuestionData(
        question: question.trim(),
        answer: answer.trim(),
        sourceTitle: source,
      ));
    }

    // 1) Formula cards become actual numeric application questions.
    for (final r in records) {
      final f = _simpleFormula(r.item.answer);
      if (f == null) continue;
      num leftValue;
      num rightValue;
      num result;
      switch (f.op) {
        case '+':
          leftValue = 38;
          rightValue = 17;
          result = leftValue + rightValue;
          break;
        case '-':
          leftValue = 80;
          rightValue = 35;
          result = leftValue - rightValue;
          break;
        case '*':
          leftValue = 12;
          rightValue = 6;
          result = leftValue * rightValue;
          break;
        case '/':
          leftValue = 84;
          rightValue = 7;
          result = leftValue / rightValue;
          break;
        default:
          continue;
      }
      final q = 'Application: using the relationship "${f.lhs} = ${f.left} ${f.op} ${f.right}", if ${f.left} = $leftValue and ${f.right} = $rightValue, what is ${f.lhs}?';
      final a = '$result. Apply ${f.lhs} = ${f.left} ${f.op} ${f.right}.';
      addTo(formula, q, a, '${r.guide.title} • Application');
    }

    final withConcept = records.where((r) => r.concept != null).toList();

    // 2) Compare two concepts instead of asking either definition directly.
    if (withConcept.length >= 2) {
      for (var i = 0; i < withConcept.length - 1; i++) {
        final a = withConcept[i];
        final b = withConcept[(i + 1) % withConcept.length];
        if (a.concept!.toLowerCase() == b.concept!.toLowerCase()) continue;
        final q = 'Comparison: a learner is confusing ${a.concept} with ${b.concept}. What is the key distinction between them?';
        final ans = '${a.concept}: ${a.item.answer}\n\n${b.concept}: ${b.item.answer}';
        addTo(comparisons, q, ans, '${a.guide.title} • Comparison');
      }
    }

    // 3) Reverse-definition multiple choice. The description comes from the AI
    // card, but the learner must identify the concept instead of reciting it.
    if (withConcept.length >= 4) {
      for (final r in withConcept) {
        final description = _examDescription(r.item.answer, r.concept);
        if (description.length < 12) continue;
        final distractors = withConcept
            .where((x) => x.concept!.toLowerCase() != r.concept!.toLowerCase())
            .map((x) => x.concept!.trim())
            .toSet()
            .toList()
          ..shuffle(rng);
        if (distractors.length < 3) continue;
        final options = <String>[r.concept!, ...distractors.take(3)]..shuffle(rng);
        final correct = options.indexWhere((x) => x.toLowerCase() == r.concept!.toLowerCase());
        final rendered = List.generate(options.length, (i) => '${_letterFor(i)}. ${options[i]}').join('\n');
        final q = 'Concept match: which concept best fits this description?\n\n“$description”\n\n$rendered';
        final ans = '${_letterFor(correct)}. ${r.concept}. ${r.item.answer}';
        addTo(conceptMcq, q, ans, '${r.guide.title} • Concept match');
      }
    }

    // 4) True/False uses a deliberately mismatched real concept as the false
    // association; no outside knowledge or invented definition is introduced.
    if (withConcept.length >= 2) {
      for (var i = 0; i < withConcept.length; i++) {
        final r = withConcept[i];
        final other = withConcept[(i + 1) % withConcept.length];
        if (r.concept!.toLowerCase() == other.concept!.toLowerCase()) continue;
        final description = _examDescription(r.item.answer, r.concept);
        if (description.length < 12) continue;
        final q = 'True or false: the description below refers to ${other.concept}.\n\n“$description”';
        final ans = 'False. It describes ${r.concept}. ${r.item.answer}';
        addTo(trueFalse, q, ans, '${r.guide.title} • True/False');
      }
    }

    // 5) General reverse reasoning works for every card, including why/how
    // cards: see the explanation first, then identify the matching topic/question.
    if (records.length >= 4) {
      for (final r in records) {
        final description = _examDescription(r.item.answer, r.concept);
        if (description.length < 10) continue;
        final others = records.where((x) => !identical(x, r)).toList()..shuffle(rng);
        final labels = <String>[_examOptionLabel(r.item.question, r.concept)];
        for (final x in others) {
          final label = _examOptionLabel(x.item.question, x.concept);
          if (labels.any((e) => e.toLowerCase() == label.toLowerCase())) continue;
          labels.add(label);
          if (labels.length == 4) break;
        }
        if (labels.length < 4) continue;
        final correctLabel = labels.first;
        labels.shuffle(rng);
        final correct = labels.indexWhere((x) => x == correctLabel);
        final rendered = List.generate(labels.length, (i) => '${_letterFor(i)}. ${labels[i]}').join('\n');
        final q = 'Reasoning match: which topic or study question is best matched to this explanation?\n\n“$description”\n\n$rendered';
        final ans = '${_letterFor(correct)}. $correctLabel\n${r.item.question} — ${r.item.answer}';
        addTo(reverseMcq, q, ans, '${r.guide.title} • Reasoning match');
      }
    }

    // 6) Always-available reverse recall fallback. It is intentionally the
    // opposite direction of the flashcard, so the exam never has to copy the
    // card question verbatim as its prompt.
    for (final r in records) {
      final description = _examDescription(r.item.answer, r.concept);
      if (description.length < 10) continue;
      final q = 'Reverse recall: identify the idea or study question that this explanation answers.\n\n“$description”';
      addTo(reverseOpen, q, r.item.question, '${r.guide.title} • Reverse recall');
    }

    // Interleave categories so one exam does not become ten questions of the
    // same shape. Formula/application and comparison get first chance, then
    // recognition/reverse-recall formats fill the rest.
    final groups = <List<ExamQuestionData>>[
      formula,
      comparisons,
      conceptMcq,
      trueFalse,
      reverseMcq,
      reverseOpen,
    ];
    for (final group in groups) {
      group.shuffle(rng);
    }
    final indexes = List<int>.filled(groups.length, 0);
    final selected = <ExamQuestionData>[];
    var madeProgress = true;
    while (selected.length < count && madeProgress) {
      madeProgress = false;
      for (var g = 0; g < groups.length && selected.length < count; g++) {
        final group = groups[g];
        while (indexes[g] < group.length) {
          final item = group[indexes[g]++];
          if (selected.any((x) => _nearDuplicate(x.question, item.question))) continue;
          selected.add(item);
          madeProgress = true;
          break;
        }
      }
    }
    return selected.take(count).toList();
  }

'''

s = s[:start] + new_block + s[end:]

s = s.replace("generatorLabel = 'AI card bank • $displayLabel';", "generatorLabel = 'Varied AI-card exam • $displayLabel';")
s = s.replace("generatorLabel = 'AI card bank + $displayLabel';", "generatorLabel = 'Varied AI-card exam + $displayLabel';")
s = s.replace("examGenerationStage = 'Ready from AI card bank';", "examGenerationStage = 'Ready • varied from AI cards';")
s = s.replace(
    'Memora first builds the exam from your AI-generated study cards. If more questions are needed, it asks the selected AI only for the missing ones.',
    'Memora transforms your AI-generated study cards into varied exam questions: application, comparison, concept matching, true/false and reverse recall. It asks the selected AI only if more material is needed.',
)
s = s.replace(
    'Memora first builds the exam from your AI-generated study cards.\\nIf more questions are needed, it asks the selected AI only for\\nthe missing ones.',
    'Memora transforms AI study cards into varied exam questions.\\nIt uses the selected AI only if more material is needed.',
)

p.write_text(s)
print('Memora v1.29 varied instant exam patch applied successfully')
