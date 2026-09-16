from pathlib import Path
import re

p = Path('lib/daily_exam_page.dart')
s = p.read_text()

# -----------------------------------------------------------------------------
# Memora v1.42: exam answers must be clean answers, never pasted source cards.
# -----------------------------------------------------------------------------

# Build a usable application/scenario stem from the original card question
# without pasting the card answer into the prompt.
card_anchor = "  List<ExamQuestionData> _cardQuestions(\n"
scenario_helper = r'''  String _scenarioStemFromCardQuestion(String question) {
    final clean = question
        .trim()
        .replaceAll(RegExp(r'\\s+'), ' ')
        .replaceAll(RegExp(r'[?¿]+$'), '')
        .trim();
    if (clean.isEmpty) {
      return 'A practical situation requires applying the relevant idea from the study material. What should be done, and why?';
    }

    final how = RegExp(
      r'^how\\s+(?:does\\s+one|do\\s+you|can\\s+(?:one|someone|a|an))\\s+(.+)$',
      caseSensitive: false,
    ).firstMatch(clean);
    if (how != null) {
      final action = how.group(1)!.trim();
      return 'A person faces a practical situation where they need to $action. What should they do, and what reasoning from the material supports that choice?';
    }

    final purpose = RegExp(
      r'^what\\s+is\\s+the\\s+purpose\\s+of\\s+(.+)$',
      caseSensitive: false,
    ).firstMatch(clean);
    if (purpose != null) {
      final subject = purpose.group(1)!.trim();
      return 'A professional must decide whether and how to use $subject in a real situation. What purpose should guide the decision, and why?';
    }

    return 'A practical case depends on the idea tested by this study question: “$clean”. How should the situation be handled, and why?';
  }

'''
if '_scenarioStemFromCardQuestion(' not in s:
    if card_anchor not in s:
        raise RuntimeError('v1.42 card-question helper anchor not found')
    s = s.replace(card_anchor, scenario_helper + card_anchor, 1)

# Keep comparison questions. The problem was not the comparison modality itself,
# but answers that visually stacked two source flashcards. Preserve the familiar
# comparison question while rendering one clean comparative answer.
comparison_pattern = re.compile(
    r'''    // 2\) Compare two concepts instead of asking either definition directly\.\n.*?\n    // 3\) Reverse-definition multiple choice\.''',
    re.S,
)
comparison_replacement = r'''    // 2) Compare two concepts instead of asking either definition directly.
    if (withConcept.length >= 2) {
      for (var i = 0; i < withConcept.length - 1; i++) {
        final a = withConcept[i];
        final b = withConcept[(i + 1) % withConcept.length];
        if (a.concept!.toLowerCase() == b.concept!.toLowerCase()) continue;
        final q = 'Comparison: a learner is confusing ${a.concept} with ${b.concept}. What is the key distinction between them?';
        final left = _examDescription(a.item.answer, a.concept).trim();
        final right = _examDescription(b.item.answer, b.concept).trim();
        if (left.length < 8 || right.length < 8) continue;
        final ans = '${a.concept}: $left. By contrast, ${b.concept}: $right.';
        addTo(comparisons, q, ans, '${a.guide.title} • Comparison');
      }
    }

    // 3) Reverse-definition multiple choice.'''
s, n = comparison_pattern.subn(lambda _m: comparison_replacement, s, count=1)
if n != 1:
    raise RuntimeError('v1.42 comparison cleanup block not found')

# Multiple-choice and true/false answers should contain only the actual answer,
# not a copy of the source card beneath it.
s = s.replace(
    "        final ans = '${_letterFor(correct)}. ${r.concept}. ${r.item.answer}';\n",
    "        final ans = '${_letterFor(correct)}. ${r.concept}';\n",
    1,
)
s = s.replace(
    "        final ans = 'False. It describes ${r.concept}. ${r.item.answer}';\n",
    "        final ans = 'False. It describes ${r.concept}.';\n",
    1,
)
s = s.replace(
    "        final ans = '${_letterFor(correct)}. $correctLabel\\n${r.item.question} — ${r.item.answer}';\n",
    "        final ans = '${_letterFor(correct)}. $correctLabel';\n",
    1,
)

# Scenario questions previously pasted the card answer into the question and
# prefixed the answer with the original card question/topic. Replace that with a
# real application stem and a clean answer only.
scenario_pattern = re.compile(
    r'''    // 5\) Scenario/application prompts force the learner to use the idea rather\n.*?\n    // 6\) General reverse reasoning''',
    re.S,
)
scenario_replacement = r'''    // 5) Scenario/application prompts use the original card question only as
    // a semantic seed. Never paste the source answer into the prompt, and never
    // prepend the source card question to the displayed answer.
    for (final r in records) {
      final answer = r.item.answer.trim();
      if (answer.length < 12) continue;
      final q = _scenarioStemFromCardQuestion(r.item.question);
      addTo(scenarios, q, answer, '${r.guide.title} • Scenario');
    }

    // 6) General reverse reasoning'''
s, n = scenario_pattern.subn(lambda _m: scenario_replacement, s, count=1)
if n != 1:
    raise RuntimeError('v1.42 scenario fallback block not found')

# Reverse-recall fallback must not use an entire source flashcard question as the
# displayed answer. Only create it when a concise concept was extracted.
reverse_pattern = re.compile(
    r'''    // 7\) Always-available reverse recall fallback\..*?\n    for \(final r in records\) \{\n      final description = _examDescription\(r\.item\.answer, r\.concept\);\n      if \(description\.length < 10\) continue;\n      final q = 'Reverse recall: identify the idea or study question that this explanation answers\.\\n\\n“\$description”';\n      addTo\(reverseOpen, q, r\.item\.question, '\$\{r\.guide\.title\} • Reverse recall'\);\n    \}''',
    re.S,
)
reverse_replacement = r'''    // 7) Reverse recall is used only when Memora can identify a concise concept.
    // This prevents an entire flashcard question from being pasted as the answer.
    for (final r in records) {
      final concept = r.concept?.trim();
      if (concept == null || concept.isEmpty) continue;
      final description = _examDescription(r.item.answer, r.concept);
      if (description.length < 10) continue;
      final q = 'Reverse recall: which concept is best represented by this explanation?\n\n“$description”';
      addTo(reverseOpen, q, concept, '${r.guide.title} • Reverse recall');
    }'''
s, n = reverse_pattern.subn(lambda _m: reverse_replacement, s, count=1)
if n != 1:
    raise RuntimeError('v1.42 reverse-recall fallback block not found')

# Reject AI output whose ANSWER field contains pasted source-card questions or
# multiple complete card answers. One grounded card answer may legitimately be
# the concise answer; two or more indicate concatenated cards.
validator_anchor = "  List<String> _compactExamMaterial(\n"
answer_guard = r'''  bool _answerLooksLikePastedCards(ExamQuestionData item, List<StudyGuide> guides) {
    final answer = item.answer
        .toLowerCase()
        .replaceAll(RegExp(r'\\s+'), ' ')
        .trim();
    if (answer.isEmpty) return true;

    var fullAnswerHits = 0;
    for (final guide in guides) {
      for (final card in guide.cards) {
        final sourceQuestion = card.question
            .toLowerCase()
            .replaceAll(RegExp(r'\\s+'), ' ')
            .trim();
        if (sourceQuestion.length >= 18 && answer.contains(sourceQuestion)) {
          return true;
        }

        final sourceAnswer = card.answer
            .toLowerCase()
            .replaceAll(RegExp(r'\\s+'), ' ')
            .trim();
        if (sourceAnswer.length >= 28 && answer.contains(sourceAnswer)) {
          fullAnswerHits++;
          if (fullAnswerHits >= 2) return true;
        }
      }
    }
    return false;
  }

'''
if '_answerLooksLikePastedCards(' not in s:
    if validator_anchor not in s:
        raise RuntimeError('v1.42 answer guard anchor not found')
    s = s.replace(validator_anchor, answer_guard + validator_anchor, 1)

parsed_guard = """              if (_tooCloseToStudyCards(item, guides)) continue;
              out.add(item);
"""
parsed_guard_new = """              if (_tooCloseToStudyCards(item, guides)) continue;
              if (_answerLooksLikePastedCards(item, guides)) continue;
              out.add(item);
"""
if parsed_guard not in s:
    raise RuntimeError('v1.42 parsed AI answer validation anchor not found')
s = s.replace(parsed_guard, parsed_guard_new, 1)

# Tell every selected model explicitly that the answer field is a clean answer,
# never a source dump or another card appended below it.
prompt_anchor = "- NEVER paste a long study-card answer into the question stem as a quotation.\n"
prompt_extra = """- NEVER paste a long study-card answer into the question stem as a quotation.
- The JSON answer field must contain only the answer to the generated exam question. Never append the source flashcard question, a second flashcard, card metadata, Topic/Question/Answer labels, or unrelated study text beneath the answer.
- Comparison questions remain valid. When generating one, return one clean comparative answer rather than stacking two source cards or source excerpts.
"""
if prompt_anchor not in s:
    raise RuntimeError('v1.42 AI clean-answer prompt anchor not found')
s = s.replace(prompt_anchor, prompt_extra, 1)

p.write_text(s)
print('Memora v1.42 clean exam answer patch applied successfully')
