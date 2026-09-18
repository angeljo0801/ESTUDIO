from pathlib import Path
import re

# v171: study-card generation returns to Memora's indexed/local path.
# No LLM/provider is required. The button builds cards deterministically from
# the vector/index coverage and falls back to the extracted guide text.

p = Path('lib/ai_card_service.dart')
s = p.read_text()

if "import 'study_engine.dart';" not in s:
    s = s.replace(
        "import 'models.dart';\n",
        "import 'models.dart';\nimport 'study_engine.dart';\n",
        1,
    )
if "import 'vector_knowledge_store.dart';" not in s:
    s = s.replace(
        "import 'study_engine.dart';\n",
        "import 'study_engine.dart';\nimport 'vector_knowledge_store.dart';\n",
        1,
    )

start = s.find("  static Future<List<StudyCard>> generateCards(")
end = s.find("  static List<String> _chunks(", start)
if start < 0 or end < 0:
    raise SystemExit('v171 AiCardService generateCards block not found')

method = r'''  static Future<List<StudyCard>> generateCards(
    StudyGuide guide, {
    int target = defaultTarget,
    void Function(int generated, int target)? onProgress,
    Future<void> Function(List<StudyCard> cards, int target)? onBatch,
  }) async {
    final safeTarget = target.clamp(10, 120).toInt();

    var material = (await VectorKnowledgeStore.buildCoverageContext(
      [guide],
      maxChars: guide.text.length.clamp(12000, 100000).toInt(),
      maxChunks: 96,
    )).trim();

    if (material.length < 40) {
      material = guide.text.replaceAll('\r', '').trim();
    }
    if (material.length < 40) {
      throw StateError(
        'This guide does not contain enough indexed text to create study cards.',
      );
    }

    final candidates = <StudyCard>[];
    final seen = <String>{};

    void addAllUnique(Iterable<StudyCard> source) {
      for (final card in source) {
        if (!StudyEngine.isCardUsable(card)) continue;
        final key =
            '${_key(card.question)}|${_key(card.answer)}';
        if (!seen.add(key)) continue;
        candidates.add(card);
      }
    }

    addAllUnique(StudyEngine.buildCards(material));

    if (candidates.length < safeTarget &&
        guide.text.trim().isNotEmpty &&
        guide.text.trim() != material) {
      addAllUnique(StudyEngine.buildCards(guide.text));
    }

    if (candidates.isEmpty) {
      throw StateError(
        'The local index did not contain enough usable material to create cards.',
      );
    }

    final oldByPair = <String, StudyCard>{
      for (final card in guide.cards)
        '${_key(card.question)}|${_key(card.answer)}': card,
    };
    final now = DateTime.now();
    final output = <StudyCard>[];

    for (var i = 0; i < candidates.length && output.length < safeTarget; i++) {
      final candidate = candidates[i];
      final pairKey =
          '${_key(candidate.question)}|${_key(candidate.answer)}';
      final old = oldByPair[pairKey];

      output.add(
        StudyCard(
          id: old?.id ?? '${now.microsecondsSinceEpoch}-$i',
          question: candidate.question,
          answer: candidate.answer,
          source: candidate.source.isEmpty ? guide.title : candidate.source,
          dueAt: old?.dueAt ?? now,
          intervalDays: old?.intervalDays ?? 0,
          ease: old?.ease ?? 2.5,
          correct: old?.correct ?? 0,
          wrong: old?.wrong ?? 0,
          streak: old?.streak ?? 0,
        ),
      );

      onProgress?.call(output.length, safeTarget);

      if (onBatch != null &&
          (output.length % 10 == 0 ||
              output.length == safeTarget ||
              i == candidates.length - 1)) {
        await onBatch(List<StudyCard>.of(output), safeTarget);
      }
    }

    return output;
  }

'''
s = s[:start] + method + s[end:]
p.write_text(s)

p = Path('lib/guide_detail_page.dart')
s = p.read_text()

s = re.sub(
    r"""    final ai = await AiCardService\.systemAi\(\);
    if \(!ai\.ready\) \{
      if \(!mounted\) return;
      ScaffoldMessenger\.of\(context\)\.showSnackBar\(
        const SnackBar\(
          content: Text\('Configure a system AI/model before generating study cards\.'\),
        \),
      \);
      return;
    \}
""",
    "",
    s,
    count=1,
)

s = re.sub(
    r"body: '\$\{widget\.guide\.title\}: \$\{cards\.length\} cards generated with \$\{ai\.label\}\.',",
    "body: '${widget.guide.title}: ${cards.length} cards generated from the local index.',",
    s,
    count=1,
)
s = s.replace(
    "SnackBar(content: Text('${cards.length} AI study cards generated.'))",
    "SnackBar(content: Text('${cards.length} study cards generated from the local index.'))",
)

replacements = {
    "'Generating study cards… $_cardProgress/${AiCardService.defaultTarget}'":
        "'Generating cards from the index… $_cardProgress/${AiCardService.defaultTarget}'",
    "'No AI-generated study cards yet.'":
        "'No indexed study cards yet.'",
    "const Text('Generate 50 AI cards')":
        "const Text('Generate 50 cards from index')",
    "Text('Regenerate 50 AI cards')":
        "Text('Regenerate cards from index')",
}
for old, new in replacements.items():
    s = s.replace(old, new)

p.write_text(s)

print('v171 applied: study cards now use Memora local/vector index only; no AI model is required')
