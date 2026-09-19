from pathlib import Path

# v184: second-chance AI repair + target-filling candidate reserve.
#
# A first-pass REJECT is no longer final. Memora gives the same card a second,
# source-grounded review with a wider context around its page/section. Only if
# that second review still says REJECT is the draft discarded.
#
# Rejected drafts do not reduce the requested target. Memora keeps consuming
# fresh indexed candidates until it reaches the requested number of FINAL cards
# or genuinely exhausts distinct source-backed material.

# ---------------------------------------------------------------------------
# AI reviewer: second review for first-pass rejects, with wider evidence.
# ---------------------------------------------------------------------------
p = Path('lib/ai_card_review_service.dart')
s = p.read_text()

# Add a second-review flag to the request helper.
old = """    required List<int> indexes,
    bool focusedRetry = false,
  }) async {
"""
new = """    required List<int> indexes,
    bool focusedRetry = false,
    bool secondReview = false,
  }) async {
"""
if old not in s:
    raise SystemExit('v184 request signature anchor missing')
s = s.replace(old, new, 1)

# Use a broader source window only during the second review.
old = """    final candidates = indexes.map((index) {
      final card = cards[index];
      final evidence = _evidenceFor(guide, card);
"""
new = """    final candidates = indexes.map((index) {
      final card = cards[index];
      final evidence = _evidenceFor(
        guide,
        card,
        expanded: secondReview,
      );
"""
if old not in s:
    raise SystemExit('v184 request evidence anchor missing')
s = s.replace(old, new, 1)

# Tell the model explicitly that this is a rescue pass.
old = """    final retryNote = focusedRetry
        ? '\\nIMPORTANT: Return one JSON decision for EVERY ID below. '
            'Do not omit any card.\\n'
        : '';

    final prompt = '''You are Memora's MANDATORY FINAL FLASHCARD EDITOR.
"""
new = """    final retryNote = focusedRetry
        ? '\\nIMPORTANT: Return one JSON decision for EVERY ID below. '
            'Do not omit any card.\\n'
        : '';
    final secondReviewNote = secondReview
        ? '''
SECOND REVIEW:
These drafts were rejected once. Re-check them using the WIDER source context.
Try to rescue the underlying concept when the source makes it explicit.
Prefer FIX over REJECT when a clear, source-supported card can be reconstructed.
Do not invent missing facts. REJECT only when the wider source still cannot
support a clear, gradable card.
'''
        : '';

    final prompt = '''You are Memora's MANDATORY FINAL FLASHCARD EDITOR.
"""
if old not in s:
    raise SystemExit('v184 retry prompt anchor missing')
s = s.replace(old, new, 1)

old = """The local parser already created these study cards. You are the final quality
step before any card can be saved.$retryNote
"""
new = """The local parser already created these study cards. You are the final quality
step before any card can be saved.$retryNote$secondReviewNote
"""
if old not in s:
    # v183 wording uses indexed/local wording.
    old = """The indexed/local system already created the hidden draft cards below. You are
the final quality step before a batch can become visible.$retryNote
"""
    new = """The indexed/local system already created the hidden draft cards below. You are
the final quality step before a batch can become visible.$retryNote$secondReviewNote
"""
if old not in s:
    raise SystemExit('v184 prompt intro anchor missing')
s = s.replace(old, new, 1)

# Expand the evidence helper.
old = """  static String _evidenceFor(StudyGuide guide, StudyCard card) {
"""
new = """  static String _evidenceFor(
    StudyGuide guide,
    StudyCard card, {
    bool expanded = false,
  }) {
"""
if old not in s:
    raise SystemExit('v184 evidence signature anchor missing')
s = s.replace(old, new, 1)

old = """      if (center >= 0) {
        final first = (center - 2).clamp(0, blocks.length - 1).toInt();
        final last = (center + 2).clamp(0, blocks.length - 1).toInt();
"""
new = """      if (center >= 0) {
        final radius = expanded ? 5 : 2;
        final first = (center - radius).clamp(0, blocks.length - 1).toInt();
        final last = (center + radius).clamp(0, blocks.length - 1).toInt();
"""
if old not in s:
    raise SystemExit('v184 evidence radius anchor missing')
s = s.replace(old, new, 1)

old = """    var evidence = chunks.join('\\n');
    if (evidence.length > 1400) evidence = evidence.substring(0, 1400);
    return evidence;
"""
new = """    var evidence = chunks.join('\\n');
    final limit = expanded ? 3200 : 1400;
    if (evidence.length > limit) evidence = evidence.substring(0, limit);
    return evidence;
"""
if old not in s:
    raise SystemExit('v184 evidence length anchor missing')
s = s.replace(old, new, 1)

# Insert the rescue pass after every ID has a first-pass decision, but before
# final KEEP/FIX/REJECT handling.
anchor = """    final output = <StudyCard>[];
"""
second_review = r'''    // Second chance: a first-pass REJECT is not final.
    final firstPassRejected = <int>[
      for (var i = 0; i < cards.length; i++)
        if (decisions[i]?.action == 'REJECT') i,
    ];

    for (var offset = 0; offset < firstPassRejected.length; offset += 2) {
      final end =
          (offset + 2).clamp(0, firstPassRejected.length).toInt();
      final ids = firstPassRejected.sublist(offset, end);
      try {
        final reconsidered = await _request(
          guide: guide,
          cards: cards,
          indexes: ids,
          focusedRetry: true,
          secondReview: true,
        );
        for (final id in ids) {
          final reconsideredDecision = reconsidered[id];
          if (reconsideredDecision != null) {
            decisions[id] = reconsideredDecision;
          }
        }
      } catch (_) {
        // If the rescue call itself fails, keep the original REJECT decision.
      }
    }

'''
if anchor not in s:
    raise SystemExit('v184 final-output anchor missing')
s = s.replace(anchor, second_review + anchor, 1)

p.write_text(s)

# ---------------------------------------------------------------------------
# Guide detail: build a much larger hidden reserve. The AI still stops as soon
# as the requested FINAL count is reached, so extra candidates are cheap local
# drafts, not extra visible cards or mandatory extra model work.
# ---------------------------------------------------------------------------
p = Path('lib/guide_detail_page.dart')
s = p.read_text()

old = """      final reserve = ((requestedCount * .65).ceil().clamp(18, 70)).toInt();
      final candidateTarget =
          (requestedCount + reserve).clamp(requestedCount, 190).toInt();
"""
new = """      // Rejections never subtract from the user's target. Build a generous
      // hidden reserve and keep reviewing replacement candidates until the
      // FINAL count reaches requestedCount or source-backed material is exhausted.
      final candidateTarget =
          (requestedCount * 4).clamp(requestedCount, 200).toInt();
"""
if old not in s:
    raise SystemExit('v184 candidate reserve anchor missing')
s = s.replace(old, new, 1)

old = """                : '$produced/$requestedCount reviewed cards were supported by the source • AI reviewed $reviewedCount, fixed $fixedCount, rejected $rejectedCount. Memora did not add unreviewed filler.',
"""
new = """                : '$produced/$requestedCount final cards ready • AI reviewed $reviewedCount, fixed $fixedCount, rejected $rejectedCount. Memora exhausted the distinct source-backed candidates without adding weak or unreviewed filler.',
"""
if old in s:
    s = s.replace(old, new, 1)

p.write_text(s)

print('v184 applied: second review rescues rejected drafts; replacements continue toward final target')
