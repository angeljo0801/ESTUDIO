from pathlib import Path

p = Path('lib/daily_exam_page.dart')
s = p.read_text()

# v1.39: AI exam validation must ground against the same material that the
# generator actually receives. When compact AI-card material is used, validating
# only against guide.text can reject every otherwise-good question.
old_combined = "    final combined = guides.map((g) => g.text.toLowerCase()).join('\\n');\n"
new_combined = """    final combined = guides.map((g) {
      final cardText = g.cards
          .map((card) => '${card.question}\\n${card.answer}')
          .join('\\n');
      return '${g.text}\\n$cardText'.toLowerCase();
    }).join('\\n');
"""
if old_combined not in s:
    raise RuntimeError('v1.39 exam grounding corpus anchor not found')
s = s.replace(old_combined, new_combined, 1)

# Keep the anti-copy guard, but do not punish legitimate domain vocabulary.
# Near-duplicate detection still rejects truly copied card stems; lexical overlap
# is now reserved for extremely close wording.
old_overlap_q = "          if (_examLexicalOverlap(question, originalQuestion) >= 0.70) return true;\n"
new_overlap_q = "          if (_examLexicalOverlap(question, originalQuestion) >= 0.88) return true;\n"
if old_overlap_q not in s:
    raise RuntimeError('v1.39 question overlap threshold anchor not found')
s = s.replace(old_overlap_q, new_overlap_q, 1)

old_overlap_a = "            _examLexicalOverlap(question, originalAnswer) >= 0.82) {\n"
new_overlap_a = "            _examLexicalOverlap(question, originalAnswer) >= 0.92) {\n"
if old_overlap_a not in s:
    raise RuntimeError('v1.39 answer overlap threshold anchor not found')
s = s.replace(old_overlap_a, new_overlap_a, 1)

# On-device GGUF is intentionally capped to a couple of reasoning batches.
# After that, the existing transformed-card reasoning fallback fills the rest.
# This preserves variety without making a 10-question exam wait through many
# slow local-model passes.
old_batch = """        final batchSize = directDevice ? 3 : (ollamaLike ? 4 : 6);
        final expectedBatches = (count / batchSize).ceil();
        final maxAttempts = max(expectedBatches + 3, 5).clamp(5, 12).toInt();
        final timeout = Duration(seconds: directDevice ? 90 : (ollamaLike ? 75 : 50));
"""
new_batch = """        final batchSize = directDevice ? 3 : (ollamaLike ? 4 : 6);
        final expectedBatches = (count / batchSize).ceil();
        final maxAttempts = directDevice
            ? min(expectedBatches, 2)
            : ollamaLike
                ? min(max(expectedBatches, 2), 3)
                : min(max(expectedBatches, 2), 4);
        final timeout = Duration(seconds: directDevice ? 60 : (ollamaLike ? 60 : 45));
"""
if old_batch not in s:
    raise RuntimeError('v1.39 exam batch timing anchor not found')
s = s.replace(old_batch, new_batch, 1)

# Make the transition explicit in the live progress text instead of leaving the
# user staring at 0/N while the fallback is being assembled.
old_fallback = """      if (questions.length < count) {
        final transformed = _cardQuestions(
"""
new_fallback = """      if (questions.length < count) {
        if (mounted) {
          setState(() {
            examGenerationStage = 'Finishing with reasoning variants • ${questions.length}/$count';
          });
        }
        final transformed = _cardQuestions(
"""
if old_fallback not in s:
    raise RuntimeError('v1.39 transformed fallback stage anchor not found')
s = s.replace(old_fallback, new_fallback, 1)

p.write_text(s)
print('Memora v1.39 exam validation + speed patch applied successfully')

import os
_v140 = Path(os.environ['GITHUB_WORKSPACE']) / 'memora_upgrade' / 'v140_conversational_open_ended_followup_patch.py'
exec(compile(_v140.read_text(), str(_v140), 'exec'))
