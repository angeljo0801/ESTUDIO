from pathlib import Path
import re

p = Path('lib/daily_exam_page.dart')
s = p.read_text()

# -----------------------------------------------------------------------------
# Card-bank exams now honor the selected difficulty and rotate a real exam
# variant instead of merely reshuffling the same question formats.
# -----------------------------------------------------------------------------
old_signature = r'''  List<ExamQuestionData> _cardQuestions(
    List<StudyGuide> guides,
    int count, {
    List<String> avoidQuestions = const [],
  }) {
    final rng = Random(DateTime.now().microsecondsSinceEpoch);
'''
new_signature = r'''  List<ExamQuestionData> _cardQuestions(
    List<StudyGuide> guides,
    int count, {
    List<String> avoidQuestions = const [],
    String difficulty = 'Medium',
    int variant = 0,
  }) {
    final rng = Random(DateTime.now().microsecondsSinceEpoch);
    final difficultyKey = difficulty.toLowerCase().trim();
    final isHard = difficultyKey == 'hard' || difficultyKey == 'difícil' || difficultyKey == 'dificil';
    final isEasy = difficultyKey == 'basic' || difficultyKey == 'easy' || difficultyKey == 'básica' || difficultyKey == 'basica';
    final isAdaptive = difficultyKey == 'adaptive' || difficultyKey == 'adaptativa';
'''
if old_signature not in s:
    raise RuntimeError('v1.34 card-question signature anchor not found')
s = s.replace(old_signature, new_signature, 1)

old_lists = r'''    final conceptMcq = <ExamQuestionData>[];
    final trueFalse = <ExamQuestionData>[];
    final reverseMcq = <ExamQuestionData>[];
    final reverseOpen = <ExamQuestionData>[];
    final candidateQuestions = <String>[];
'''
new_lists = r'''    final conceptMcq = <ExamQuestionData>[];
    final trueFalse = <ExamQuestionData>[];
    final scenarios = <ExamQuestionData>[];
    final reverseMcq = <ExamQuestionData>[];
    final reverseOpen = <ExamQuestionData>[];
    final candidateQuestions = <String>[];
'''
if old_lists not in s:
    raise RuntimeError('v1.34 card group anchor not found')
s = s.replace(old_lists, new_lists, 1)

scenario_anchor = r'''    // 5) General reverse reasoning works for every card, including why/how
'''
scenario_block = r'''    // 5) Scenario/application prompts force the learner to use the idea rather
    // than merely recognize the original flashcard wording. The answer remains
    // strictly grounded in the saved AI card.
    for (final r in records) {
      final description = _examDescription(r.item.answer, r.concept);
      if (description.length < 18) continue;
      final topic = r.concept ?? _examOptionLabel(r.item.question, r.concept);
      final q = 'Scenario challenge: imagine you must use the idea below to justify a decision or explain what should be done. What principle or concept applies, and how should it guide the reasoning?\n\n“$description”';
      final a = '$topic — ${r.item.answer}';
      addTo(scenarios, q, a, '${r.guide.title} • Scenario');
    }

    // 6) General reverse reasoning works for every card, including why/how
'''
if scenario_anchor not in s:
    raise RuntimeError('v1.34 scenario insertion anchor not found')
s = s.replace(scenario_anchor, scenario_block, 1)
s = s.replace('    // 6) Always-available reverse recall fallback.', '    // 7) Always-available reverse recall fallback.', 1)

selection_pattern = re.compile(
    r'''    // Interleave categories so one exam does not become ten questions of the\n.*?    return selected\.take\(count\)\.toList\(\);\n''',
    re.S,
)
selection_replacement = r'''    // Difficulty now changes the cognitive load. Each exam variant also uses a
    // different weighted modality pattern, so creating another exam at the same
    // level yields a genuinely different composition instead of a reshuffle.
    final allGroups = <List<ExamQuestionData>>[
      formula,
      comparisons,
      scenarios,
      conceptMcq,
      trueFalse,
      reverseMcq,
      reverseOpen,
    ];
    for (final group in allGroups) {
      group.shuffle(rng);
    }

    final v = variant % 4;
    late final List<List<ExamQuestionData>> pattern;
    if (isHard || (isAdaptive && v.isOdd)) {
      final variants = <List<List<ExamQuestionData>>>[
        [formula, comparisons, scenarios, reverseOpen, scenarios, comparisons, reverseMcq, formula, trueFalse],
        [scenarios, comparisons, reverseMcq, formula, scenarios, reverseOpen, trueFalse, comparisons, conceptMcq],
        [reverseOpen, formula, scenarios, comparisons, reverseMcq, scenarios, formula, trueFalse, comparisons],
        [comparisons, scenarios, trueFalse, reverseOpen, formula, reverseMcq, scenarios, comparisons, conceptMcq],
      ];
      pattern = variants[v];
    } else if (isEasy) {
      final variants = <List<List<ExamQuestionData>>>[
        [conceptMcq, trueFalse, reverseMcq, conceptMcq, trueFalse, reverseOpen, comparisons],
        [trueFalse, conceptMcq, reverseMcq, reverseOpen, trueFalse, conceptMcq, scenarios],
        [reverseMcq, conceptMcq, trueFalse, conceptMcq, reverseOpen, trueFalse, comparisons],
        [conceptMcq, reverseOpen, trueFalse, reverseMcq, conceptMcq, trueFalse, scenarios],
      ];
      pattern = variants[v];
    } else {
      final variants = <List<List<ExamQuestionData>>>[
        [comparisons, conceptMcq, trueFalse, scenarios, reverseMcq, reverseOpen, formula],
        [trueFalse, scenarios, reverseOpen, comparisons, conceptMcq, reverseMcq, formula],
        [reverseMcq, formula, comparisons, conceptMcq, scenarios, trueFalse, reverseOpen],
        [scenarios, reverseOpen, trueFalse, formula, comparisons, reverseMcq, conceptMcq],
      ];
      pattern = variants[v];
    }

    ExamQuestionData? takeFrom(List<ExamQuestionData> group) {
      while (group.isNotEmpty) {
        final item = group.removeAt(0);
        if (selected.any((x) => _nearDuplicate(x.question, item.question))) continue;
        return item;
      }
      return null;
    }

    final selected = <ExamQuestionData>[];
    var cursor = 0;
    var misses = 0;
    while (selected.length < count && misses < pattern.length * 2) {
      final item = takeFrom(pattern[cursor % pattern.length]);
      cursor++;
      if (item == null) {
        misses++;
      } else {
        selected.add(item);
        misses = 0;
      }
    }

    // If a preferred modality runs out, fill only with remaining non-duplicate
    // grounded questions rather than repeating an earlier stem.
    for (final group in allGroups) {
      while (selected.length < count) {
        final item = takeFrom(group);
        if (item == null) break;
        selected.add(item);
      }
      if (selected.length >= count) break;
    }
    return selected.take(count).toList();
'''
s, n = selection_pattern.subn(lambda _m: selection_replacement, s, count=1)
if n != 1:
    raise RuntimeError('v1.34 modality selection block not found')

# -----------------------------------------------------------------------------
# Build a rotating variant number from previous exams at the same tutor + level.
# This is persistent because prior sessions are already stored by Memora.
# -----------------------------------------------------------------------------
recent_anchor = "    final recentQuestions = _recentQuestions(tutor.id);\n"
variant_block = """    final recentQuestions = _recentQuestions(tutor.id);
    final examVariant = sessions
            .where((e) =>
                e.tutorId == tutor.id &&
                e.difficulty.toLowerCase() == difficulty.toLowerCase())
            .length %
        4;
"""
if recent_anchor not in s:
    raise RuntimeError('v1.34 recent-question anchor not found')
s = s.replace(recent_anchor, variant_block, 1)

build_start = s.find('  Future<TutorExamSession> _buildExam({\n')
build_end = s.find('\n  Future<void> _openExam(', build_start)
if build_start < 0 or build_end < 0:
    raise RuntimeError('v1.34 build-exam block not found')
build = s[build_start:build_end]

# Add difficulty + variant to every card-bank generation call in the final build.
def add_card_args(match):
    block = match.group(0)
    if 'difficulty:' in block:
        return block
    close = block.rfind(')')
    before = block[:close].rstrip()
    if before.endswith(','):
        extra = "\n        difficulty: difficulty,\n        variant: examVariant,\n      "
    else:
        extra = ",\n        difficulty: difficulty,\n        variant: examVariant,\n      "
    return before + extra + block[close:]

build, card_calls = re.subn(
    r'''_cardQuestions\(\n\s*guides,\n\s*count,\n\s*avoidQuestions:.*?\n\s*\)''',
    add_card_args,
    build,
    flags=re.S,
)
if card_calls < 2:
    raise RuntimeError(f'v1.34 expected multiple card-bank calls, found {card_calls}')

# Pass the same variant to any fresh AI question batches used to fill missing
# material. This keeps the model-generated remainder aligned with the chosen mix.
def add_ai_variant(match):
    block = match.group(0)
    if 'variant:' in block:
        return block
    return block.replace(
        '        difficulty: difficulty,\n',
        '        difficulty: difficulty,\n        variant: examVariant,\n',
        1,
    )

build, ai_calls = re.subn(
    r'''_generateAiExamQuestions\(\n.*?\n\s*\)''',
    add_ai_variant,
    build,
    flags=re.S,
)
if ai_calls < 1:
    raise RuntimeError('v1.34 AI exam generation call not found')

s = s[:build_start] + build + s[build_end:]

# -----------------------------------------------------------------------------
# Fresh AI-generated questions also obey difficulty and variant-specific modality
# guidance, rather than treating "Hard" as a display-only label.
# -----------------------------------------------------------------------------
old_ai_sig = """    required int count,
    required String difficulty,
    required String provider,
"""
new_ai_sig = """    required int count,
    required String difficulty,
    required int variant,
    required String provider,
"""
if old_ai_sig not in s:
    raise RuntimeError('v1.34 AI generator signature anchor not found')
s = s.replace(old_ai_sig, new_ai_sig, 1)

attempt_anchor = "        var attempt = 0;\n"
difficulty_rules = r'''        final difficultyKey = difficulty.toLowerCase().trim();
        final difficultyRule =
            difficultyKey == 'hard' || difficultyKey == 'difícil' || difficultyKey == 'dificil'
                ? 'HARD: prioritize multi-step application, comparison, scenario reasoning, formulas/calculations, and justification. Minimize simple definition or recognition questions.'
                : difficultyKey == 'basic' || difficultyKey == 'easy' || difficultyKey == 'básica' || difficultyKey == 'basica'
                    ? 'BASIC: prioritize recognition, concept matching, straightforward true/false, and direct recall, with only light application.'
                    : difficultyKey == 'adaptive' || difficultyKey == 'adaptativa'
                        ? 'ADAPTIVE: mix recall, recognition, application and reasoning, with several challenging questions.'
                        : 'MEDIUM: balance recognition, comparison, application, true/false and reasoning.';
        final variantRule = <String>[
          'Variant A: emphasize application, comparison and scenario questions; use true/false sparingly.',
          'Variant B: emphasize scenario reasoning, true/false with justification, and reverse reasoning.',
          'Variant C: emphasize formulas/calculations when supported, comparison, and open reasoning.',
          'Variant D: emphasize concept matching, scenarios, cause/effect or decision reasoning, and comparison.',
        ][variant % 4];
'''
if attempt_anchor not in s:
    raise RuntimeError('v1.34 AI generator attempt anchor not found')
s = s.replace(attempt_anchor, attempt_anchor + difficulty_rules, 1)

old_prompt_head = """              prompt: '''Create exactly $askFor NEW high-quality exam questions using ONLY the MATERIAL below.
Difficulty: $difficulty.

RULES:
"""
new_prompt_head = """              prompt: '''Create exactly $askFor NEW high-quality exam questions using ONLY the MATERIAL below.
Difficulty: $difficulty.
$difficultyRule
$variantRule

RULES:
- Treat the selected difficulty as a real cognitive requirement, not just a label.
- Change the question modalities from previous exams; do not merely reorder or lightly rephrase them.
- Across the batch, vary among application, comparison, scenario/decision, true/false with justification, concept matching, reverse reasoning, and formulas/calculations when supported.
"""
if old_prompt_head not in s:
    raise RuntimeError('v1.34 AI prompt anchor not found')
s = s.replace(old_prompt_head, new_prompt_head, 1)

# Make the UI explanation match the new behavior.
s = s.replace(
    'Memora transforms your AI-generated study cards into varied exam questions: application, comparison, concept matching, true/false and reverse recall. It asks the selected AI only if more material is needed.',
    'Memora creates a new exam variant each time. The selected difficulty changes the reasoning level, and the modality mix rotates among application, comparison, scenarios, true/false, concept matching, reverse reasoning and formulas when supported. It asks the selected AI only if more material is needed.',
)

p.write_text(s)
print('Memora v1.34 difficulty-aware rotating exam variants patch applied successfully')
