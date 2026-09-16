from pathlib import Path

p = Path('lib/daily_exam_page.dart')
s = p.read_text()

# Memora v1.43: keep the comparison modality exactly as a normal exam mode.
# v1.42 was too aggressive and removed deterministic comparisons entirely.
# Restore them, but format the answer as ONE clean comparative response instead
# of stacking two source flashcards underneath each other.
old = """    // 2) Comparisons are intentionally not synthesized by blindly pairing
    // unrelated cards. Semantic AI generation handles true comparisons; the
    // deterministic fallback leaves this group empty when no relationship is known.

    // 3) Reverse-definition multiple choice.
"""

new = """    // 2) Comparison questions remain available. Keep the familiar behavior,
    // but render the answer as one comparative response instead of two pasted
    // flashcards separated by blank lines.
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

    // 3) Reverse-definition multiple choice.
"""

if old not in s:
    raise RuntimeError('v1.43 comparison restore anchor not found')
s = s.replace(old, new, 1)

p.write_text(s)
print('Memora v1.43 restored comparisons with clean answers successfully')
