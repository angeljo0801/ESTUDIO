from pathlib import Path

# v183: final-only card publication.
# Indexed cards stay hidden. AI reviews each source-grounded batch before any
# card from that batch can be exposed to the user.

# ---------------------------------------------------------------------------
# 1) Make incomplete AI batch responses resilient. Missing IDs are retried as
# a group and then individually. If any ID is still unresolved, the whole
# current batch remains hidden.
# ---------------------------------------------------------------------------
p = Path('lib/ai_card_review_service.dart')
s = p.read_text()

start = s.find("    var decisions = await _request(")
end = s.find("    final output = <StudyCard>[];", start)
if start < 0 or end < 0:
    raise SystemExit('v183 AI review decision anchors missing')

decision_block = r'''    var decisions = await _request(
      guide: guide,
      cards: cards,
      indexes: <int>[for (var i = 0; i < cards.length; i++) i],
    );

    for (var round = 0; round < 2; round++) {
      final missing = <int>[
        for (var i = 0; i < cards.length; i++)
          if (!decisions.containsKey(i)) i,
      ];
      if (missing.isEmpty) break;
      try {
        final retry = await _request(
          guide: guide,
          cards: cards,
          indexes: missing,
          focusedRetry: true,
        );
        decisions = <int, _Decision>{...decisions, ...retry};
      } catch (_) {
        // Individual retries below still get a chance to complete the batch.
      }
    }

    final unresolved = <int>[
      for (var i = 0; i < cards.length; i++)
        if (!decisions.containsKey(i)) i,
    ];

    for (final id in unresolved) {
      for (var attempt = 0;
          attempt < 2 && !decisions.containsKey(id);
          attempt++) {
        try {
          final retry = await _request(
            guide: guide,
            cards: cards,
            indexes: <int>[id],
            focusedRetry: true,
          );
          if (retry.containsKey(id)) {
            decisions = <int, _Decision>{...decisions, ...retry};
          }
        } catch (_) {
          // Never publish an unresolved draft card.
        }
      }
    }

    final stillMissing = <int>[
      for (var i = 0; i < cards.length; i++)
        if (!decisions.containsKey(i)) i,
    ];
    if (stillMissing.isNotEmpty) {
      throw Exception(
        'AI could not finish reviewing the current batch. '
        'That draft batch is still hidden and was not published.',
      );
    }

'''
s = s[:start] + decision_block + s[end:]

s = s.replace(
    "'La revision de IA es obligatoria. '",
    "'AI final review is required. '",
)
s = s.replace(
    "'La revisión de IA es obligatoria. '",
    "'AI final review is required. '",
)

p.write_text(s)

# ---------------------------------------------------------------------------
# 2) Make AiCardService obey the same architecture everywhere in Memora.
# Drafts are generated from the indexed/local system, remain local variables,
# are reviewed in batches of 2 against their page/section/source evidence, and
# only reviewed cards are returned or sent to onBatch.
# ---------------------------------------------------------------------------
p = Path('lib/ai_card_service.dart')
s = p.read_text()

if "import 'ai_card_review_service.dart';" not in s:
    anchor = "import 'ai_service.dart';\n"
    if anchor not in s:
        raise SystemExit('v183 AiCardService AI import anchor missing')
    s = s.replace(
        anchor,
        anchor + "import 'ai_card_review_service.dart';\n",
        1,
    )

if "import 'study_card_quality_service.dart';" not in s:
    anchor = "import 'models.dart';\n"
    if anchor not in s:
        raise SystemExit('v183 AiCardService quality import anchor missing')
    s = s.replace(
        anchor,
        anchor + "import 'study_card_quality_service.dart';\n",
        1,
    )

start = s.find("  static Future<List<StudyCard>> generateCards(")
end = s.find("  static List<String> _chunks(", start)
if start < 0 or end < 0:
    raise SystemExit('v183 AiCardService generateCards anchors missing')

generate = r'''  static Future<List<StudyCard>> generateCards(
    StudyGuide guide, {
    int target = defaultTarget,
    void Function(int generated, int target)? onProgress,
    Future<void> Function(List<StudyCard> cards, int target)? onBatch,
  }) async {
    final safeTarget = target.clamp(5, 120).toInt();

    // Phase 1: hidden indexed/local draft cards.
    final reserve = ((safeTarget * .65).ceil().clamp(18, 70)).toInt();
    final candidateTarget =
        (safeTarget + reserve).clamp(safeTarget, 190).toInt();

    final raw = StudyEngine.buildCards(
      guide.text,
      sourceBlocks: guide.sourceBlocks,
      requestedCount: candidateTarget,
    );

    final candidates = await StudyCardQualityService.finalizeCards(
      guide: guide,
      generated: raw,
      existing: guide.cards,
      append: false,
      targetCount: candidateTarget,
      filterMalformed: false,
    );

    if (candidates.isEmpty) {
      throw StateError(
        'The local index did not contain enough usable material to create cards.',
      );
    }

    // Phase 2: mandatory source-grounded AI review.
    final finalCards = <StudyCard>[];
    const batchSize = 2;

    for (var offset = 0;
        offset < candidates.length && finalCards.length < safeTarget;
        offset += batchSize) {
      final batchEnd =
          (offset + batchSize).clamp(0, candidates.length).toInt();
      final review = await AiCardReviewService.reviewBatch(
        guide: guide,
        cards: candidates.sublist(offset, batchEnd),
      );

      final before = finalCards.length;
      final merged = StudyCardQualityService.mergeUnique(
        existing: finalCards,
        generated: review.cards,
        maxNew: safeTarget - finalCards.length,
      );

      finalCards
        ..clear()
        ..addAll(merged);

      // This number never includes hidden drafts.
      onProgress?.call(finalCards.length, safeTarget);

      // A caller can publish only a completed AI-reviewed batch.
      if (onBatch != null && finalCards.length > before) {
        await onBatch(List<StudyCard>.of(finalCards), safeTarget);
      }
    }

    return List<StudyCard>.of(finalCards);
  }

'''
s = s[:start] + generate + s[end:]
p.write_text(s)

# ---------------------------------------------------------------------------
# 3) The Guide Detail pipeline from v179/v181 already keeps indexed candidates
# hidden and publishes each reviewed batch. Fix its status/error language so a
# failed current batch cannot imply that both "saved" and "not saved" happened.
# ---------------------------------------------------------------------------
p = Path('lib/guide_detail_page.dart')
s = p.read_text()

old = """            partialReady > 0
                ? 'AI review stopped after $partialReady reviewed cards. Those cards are already saved and can be studied now. $detail'
                : 'No new cards were saved because AI final review is required. $detail',
"""
new = """            partialReady > 0
                ? 'Card creation paused. $partialReady final cards are ready. The current draft batch is still hidden until AI review finishes. $detail'
                : 'Card creation paused. Draft cards are still hidden because the first AI-reviewed batch is not finished. $detail',
"""
if old not in s:
    raise SystemExit('v183 GuideDetail status-message anchor missing')
s = s.replace(old, new, 1)

# Make the notification explicitly count only published/final cards.
s = s.replace(
    "body: '0/$requestedCount cards created',",
    "body: '0/$requestedCount final cards ready',",
)
s = s.replace(
    "body: '$produced/$requestedCount cards created • '",
    "body: '$produced/$requestedCount final cards ready - '",
)

p.write_text(s)

print('v183 applied: hidden indexed drafts -> mandatory AI review -> final-only batches')
