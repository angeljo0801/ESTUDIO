from pathlib import Path

# v179: mandatory AI final review for every card + progressive reviewed batches.
# The deterministic parser remains the generator. No card is added to the new
# set until Library AI has explicitly KEEP/FIXed it using its source evidence.

p = Path('lib/study_card_quality_service.dart')
s = p.read_text()
old = """    bool append = false,
    int? targetCount,
  }) async {
    var fresh = generated.where((card) => !isObviouslyMalformed(card)).toList();
"""
new = """    bool append = false,
    int? targetCount,
    bool filterMalformed = true,
  }) async {
    var fresh = filterMalformed
        ? generated.where((card) => !isObviouslyMalformed(card)).toList()
        : List<StudyCard>.of(generated);
"""
if old not in s:
    raise SystemExit('v179 quality candidate filter anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)

Path('lib/ai_card_review_service.dart').write_text(r"""import 'dart:convert';

import 'ai_service.dart';
import 'models.dart';
import 'study_card_quality_service.dart';

class AiCardReviewResult {
  const AiCardReviewResult({
    required this.cards,
    required this.reviewed,
    required this.fixed,
    required this.rejected,
  });

  final List<StudyCard> cards;
  final int reviewed;
  final int fixed;
  final int rejected;
}

class AiCardReviewService {
  static Future<AiCardReviewResult> reviewBatch({
    required StudyGuide guide,
    required List<StudyCard> cards,
  }) async {
    if (cards.isEmpty) {
      return const AiCardReviewResult(
        cards: <StudyCard>[],
        reviewed: 0,
        fixed: 0,
        rejected: 0,
      );
    }

    var decisions = await _request(
      guide: guide,
      cards: cards,
      indexes: <int>[for (var i = 0; i < cards.length; i++) i],
    );

    final missing = <int>[
      for (var i = 0; i < cards.length; i++)
        if (!decisions.containsKey(i)) i,
    ];

    if (missing.isNotEmpty) {
      final retry = await _request(
        guide: guide,
        cards: cards,
        indexes: missing,
        focusedRetry: true,
      );
      decisions = <int, _Decision>{...decisions, ...retry};
    }

    final stillMissing = <int>[
      for (var i = 0; i < cards.length; i++)
        if (!decisions.containsKey(i)) i,
    ];
    if (stillMissing.isNotEmpty) {
      throw Exception(
        'La IA no completó la revisión obligatoria de este lote. '
        'Las tarjetas de este lote no se guardaron.',
      );
    }

    final output = <StudyCard>[];
    var fixed = 0;
    var rejected = 0;

    for (var i = 0; i < cards.length; i++) {
      final original = cards[i];
      final decision = decisions[i]!;

      if (decision.action == 'REJECT') {
        rejected++;
        continue;
      }

      if (decision.action == 'KEEP') {
        if (StudyCardQualityService.isObviouslyMalformed(original)) {
          rejected++;
          continue;
        }
        output.add(original);
        continue;
      }

      final question = _clean(decision.question);
      final answer = _clean(decision.answer);
      final evidence = _evidenceFor(guide, original);

      if (question.length < 10 ||
          answer.length < 6 ||
          !_numbersSupported(question + ' ' + answer, evidence)) {
        rejected++;
        continue;
      }

      final repaired = StudyCard(
        id: original.id,
        question: question.endsWith('?') ? question : '$question?',
        answer: answer,
        source: original.source,
        dueAt: original.dueAt,
        intervalDays: original.intervalDays,
        ease: original.ease,
        correct: original.correct,
        wrong: original.wrong,
        streak: original.streak,
        page: original.page,
        section: original.section,
        sourceExcerpt: original.sourceExcerpt,
      );

      if (StudyCardQualityService.isObviouslyMalformed(repaired)) {
        rejected++;
        continue;
      }

      output.add(repaired);
      fixed++;
    }

    return AiCardReviewResult(
      cards: output,
      reviewed: cards.length,
      fixed: fixed,
      rejected: rejected,
    );
  }

  static Future<Map<int, _Decision>> _request({
    required StudyGuide guide,
    required List<StudyCard> cards,
    required List<int> indexes,
    bool focusedRetry = false,
  }) async {
    if (indexes.isEmpty) return const <int, _Decision>{};

    final candidates = indexes.map((index) {
      final card = cards[index];
      final evidence = _evidenceFor(guide, card);
      return '''ID: $index
PAGE: ${card.page ?? 'unknown'}
SECTION: ${card.section.trim().isEmpty ? '(none)' : card.section.trim()}
QUESTION: ${card.question}
ANSWER: ${card.answer}
SOURCE EVIDENCE:
${evidence.isEmpty ? '(no exact source evidence available)' : evidence}''';
    }).join('\n\n========\n\n');

    final retryNote = focusedRetry
        ? '\nIMPORTANT: Return one JSON decision for EVERY ID below. '
            'Do not omit any card.\n'
        : '';

    final prompt = '''You are Memora's MANDATORY FINAL FLASHCARD EDITOR.

The local parser already created these study cards. You are the final quality
step before any card can be saved.$retryNote

For EVERY ID choose exactly one:
- KEEP: already clear, useful, grammatical and supported by SOURCE EVIDENCE.
- FIX: improve the question/answer so it makes more sense, using ONLY the
  supplied SOURCE EVIDENCE.
- REJECT: mixed fragments, insufficient source evidence, ambiguous, ungradable,
  or impossible to repair without guessing.

STRICT RULES:
1. Review EVERY ID.
2. Use only SOURCE EVIDENCE. Never add outside knowledge.
3. Never invent a formula, number, definition, example or relationship.
4. If wording is awkward but the source is clear, FIX it.
5. The corrected card must stay on the same concept.
6. Prefer one specific question with one clear answer.
7. Preserve meaningful numbers and formulas exactly.
8. If the PDF extraction mixed headings, glossary entries or unrelated lines,
   reconstruct only when the intended meaning is explicit in the evidence;
   otherwise REJECT.
9. Return ONLY a JSON array. No Markdown.

JSON FORMAT:
[
  {"id":0,"action":"KEEP","question":"","answer":"","reason":"short reason"},
  {"id":1,"action":"FIX","question":"better question","answer":"better answer","reason":"short reason"},
  {"id":2,"action":"REJECT","question":"","answer":"","reason":"short reason"}
]

CARDS:
$candidates''';

    try {
      final raw = await AiService.askTaskConfigured(
        prompt: prompt,
        providerOverride: 'global',
        settingsScope: 'library',
        responseMode: 'fast',
      ).timeout(
        const Duration(seconds: 90),
        onTimeout: () async {
          try {
            await AiService.cancelCurrent();
          } catch (_) {}
          throw Exception('La revisión obligatoria de IA tardó demasiado.');
        },
      );

      final parsed = _parse(raw);
      final allowed = indexes.toSet();
      parsed.removeWhere((id, _) => !allowed.contains(id));
      return parsed;
    } catch (e) {
      throw Exception(
        'La revisión de IA es obligatoria. '
        'Revisa AI Settings · Library. ${AiService.userFacingError(e)}',
      );
    }
  }

  static String _evidenceFor(StudyGuide guide, StudyCard card) {
    final blocks = guide.sourceBlocks;
    final exact = card.sourceExcerpt.trim();
    final chunks = <String>[];

    if (blocks.isNotEmpty) {
      var center = -1;

      if (exact.isNotEmpty) {
        center = blocks.indexWhere((block) {
          final text = block.text.trim();
          return text == exact ||
              text.contains(exact) ||
              (text.isNotEmpty && exact.contains(text));
        });
      }

      if (center < 0 && card.page != null) {
        center = blocks.indexWhere(
          (block) =>
              block.page == card.page &&
              (card.section.trim().isEmpty ||
                  block.section.trim() == card.section.trim()),
        );
      }

      if (center < 0 && card.section.trim().isNotEmpty) {
        center = blocks.indexWhere(
          (block) => block.section.trim() == card.section.trim(),
        );
      }

      if (center >= 0) {
        final first = (center - 2).clamp(0, blocks.length - 1).toInt();
        final last = (center + 2).clamp(0, blocks.length - 1).toInt();
        for (var i = first; i <= last; i++) {
          final text = blocks[i].text.trim();
          if (text.isNotEmpty && !chunks.contains(text)) chunks.add(text);
        }
      }

      if (chunks.isEmpty) {
        for (final block in blocks) {
          if (chunks.length >= 5) break;
          final samePage = card.page != null && block.page == card.page;
          final sameSection = card.section.trim().isNotEmpty &&
              block.section.trim() == card.section.trim();
          if (!samePage && !sameSection) continue;
          final text = block.text.trim();
          if (text.isNotEmpty && !chunks.contains(text)) chunks.add(text);
        }
      }
    }

    if (exact.isNotEmpty && !chunks.contains(exact)) {
      chunks.insert(0, exact);
    }

    if (chunks.isEmpty) {
      final probe = exact.isNotEmpty ? exact : card.answer.trim();
      final index = probe.isEmpty ? -1 : guide.text.indexOf(probe);
      if (index >= 0) {
        final first = (index - 700).clamp(0, guide.text.length).toInt();
        final last =
            (index + probe.length + 1100).clamp(0, guide.text.length).toInt();
        chunks.add(guide.text.substring(first, last).trim());
      }
    }

    var evidence = chunks.join('\n');
    if (evidence.length > 2400) evidence = evidence.substring(0, 2400);
    return evidence;
  }

  static Map<int, _Decision> _parse(String raw) {
    final out = <int, _Decision>{};
    final start = raw.indexOf('[');
    final end = raw.lastIndexOf(']');
    if (start < 0 || end <= start) return out;

    try {
      final decoded = jsonDecode(raw.substring(start, end + 1));
      if (decoded is! List) return out;

      for (final item in decoded) {
        if (item is! Map) continue;
        final id = (item['id'] as num?)?.toInt();
        if (id == null) continue;

        final action =
            item['action']?.toString().toUpperCase().trim() ?? '';
        if (action != 'KEEP' && action != 'FIX' && action != 'REJECT') continue;

        out[id] = _Decision(
          action: action,
          question: item['question']?.toString() ?? '',
          answer: item['answer']?.toString() ?? '',
        );
      }
    } catch (_) {}

    return out;
  }

  static bool _numbersSupported(String proposed, String evidence) {
    if (evidence.trim().isEmpty) return false;
    final sourceNumbers = RegExp(r'\d+(?:[.,]\d+)*')
        .allMatches(evidence)
        .map((match) => match.group(0)!)
        .toSet();
    final proposedNumbers = RegExp(r'\d+(?:[.,]\d+)*')
        .allMatches(proposed)
        .map((match) => match.group(0)!)
        .toSet();
    return proposedNumbers.every(sourceNumbers.contains);
  }

  static String _clean(String value) => value
      .replaceAll(RegExp(r'\s+'), ' ')
      .replaceAll(RegExp(r'^[\-•*\s]+|[\s]+$'), '')
      .trim();
}

class _Decision {
  const _Decision({
    required this.action,
    required this.question,
    required this.answer,
  });

  final String action;
  final String question;
  final String answer;
}
""")

p = Path('lib/guide_detail_page.dart')
s = p.read_text()

start = s.find("  Future<void> _regenerate(")
end = s.find("  Future<void> _reprocessPdf()", start)
if start < 0 or end < 0:
    raise SystemExit('v179 GuideDetail regenerate anchors missing')

method = r'''  Future<void> _regenerate({bool automatic = false}) async {
    if (_generatingCards) return;

    final prefs = await SharedPreferences.getInstance();
    var requestedCount =
        (prefs.getInt('memora_card_target_count') ?? 50).clamp(5, 120).toInt();
    var mode = 'replace';
    final countController =
        TextEditingController(text: requestedCount.toString());

    if (!automatic) {
      final accepted = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => StatefulBuilder(
          builder: (dialogContext, setDialogState) => AlertDialog(
            title: const Text('Generate study cards'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    controller: countController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Number of cards',
                      helperText: 'Memora targets this many reviewed cards (5–120).',
                      border: OutlineInputBorder(),
                    ),
                    onChanged: (value) {
                      final parsed = int.tryParse(value);
                      if (parsed != null) {
                        requestedCount = parsed.clamp(5, 120).toInt();
                      }
                    },
                  ),
                  if (widget.guide.cards.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    SegmentedButton<String>(
                      segments: const [
                        ButtonSegment(
                          value: 'replace',
                          label: Text('Replace'),
                          icon: Icon(Icons.refresh_rounded),
                        ),
                        ButtonSegment(
                          value: 'add',
                          label: Text('Add new'),
                          icon: Icon(Icons.add_rounded),
                        ),
                      ],
                      selected: {mode},
                      onSelectionChanged: (value) {
                        setDialogState(() => mode = value.first);
                      },
                    ),
                  ],
                  const SizedBox(height: 14),
                  Card(
                    child: ListTile(
                      leading: const Icon(Icons.auto_fix_high_rounded),
                      title: const Text('AI Final Review · Required'),
                      subtitle: const Text(
                        'Every card must pass through the Library AI before it is saved. The AI receives its page, section and nearby source text, so it knows where to verify and repair the card.',
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: () => Navigator.of(dialogContext).push(
                      MaterialPageRoute(
                        builder: (_) => const LlmSettingsPage(
                          scope: 'library',
                          scopeLabel: 'Biblioteca / Tarjetas',
                        ),
                      ),
                    ),
                    icon: const Icon(Icons.settings_outlined),
                    label: const Text('AI Settings · Library'),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Memora reviews in batches. Each finished batch is saved immediately, so you can start Review while the AI keeps cleaning the remaining cards.',
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () {
                  final parsed = int.tryParse(countController.text.trim());
                  requestedCount =
                      (parsed ?? requestedCount).clamp(5, 120).toInt();
                  Navigator.pop(dialogContext, true);
                },
                child: const Text('Generate'),
              ),
            ],
          ),
        ),
      );
      if (accepted != true) {
        countController.dispose();
        return;
      }
    }

    countController.dispose();
    await prefs.setInt('memora_card_target_count', requestedCount);

    final oldCards = List<StudyCard>.of(widget.guide.cards);
    var progressiveCards =
        mode == 'add' ? List<StudyCard>.of(oldCards) : <StudyCard>[];
    var reviewedCount = 0;
    var fixedCount = 0;
    var rejectedCount = 0;
    var produced = 0;

    setState(() {
      _generatingCards = true;
      _cardProgress = 0;
    });

    try {
      final reserve = ((requestedCount * .65).ceil().clamp(18, 70)).toInt();
      final candidateTarget =
          (requestedCount + reserve).clamp(requestedCount, 190).toInt();

      final raw = StudyEngine.buildCards(
        widget.guide.text,
        sourceBlocks: widget.guide.sourceBlocks,
        requestedCount: candidateTarget,
      );

      final candidates = await StudyCardQualityService.finalizeCards(
        guide: widget.guide,
        generated: raw,
        existing: mode == 'replace' ? oldCards : const [],
        append: false,
        targetCount: candidateTarget,
        filterMalformed: false,
      );

      const batchSize = 6;
      for (var offset = 0;
          offset < candidates.length && produced < requestedCount;
          offset += batchSize) {
        final end =
            (offset + batchSize).clamp(0, candidates.length).toInt();
        final batch = candidates.sublist(offset, end);

        final review = await AiCardReviewService.reviewBatch(
          guide: widget.guide,
          cards: batch,
        );

        reviewedCount += review.reviewed;
        fixedCount += review.fixed;
        rejectedCount += review.rejected;

        final remaining = requestedCount - produced;
        progressiveCards = StudyCardQualityService.mergeUnique(
          existing: progressiveCards,
          generated: review.cards,
          maxNew: remaining,
        );

        produced = mode == 'add'
            ? progressiveCards.length - oldCards.length
            : progressiveCards.length;

        widget.guide.cards = List<StudyCard>.of(progressiveCards);
        await _save();

        if (mounted) {
          setState(() => _cardProgress = produced);
        }

        await Future<void>.delayed(const Duration(milliseconds: 80));
      }

      if (!mounted) return;

      final exact = produced == requestedCount;
      final topics = widget.guide.cards
          .map((card) => card.section.trim().isNotEmpty
              ? card.section.trim()
              : card.source.trim())
          .where((topic) => topic.isNotEmpty)
          .toSet()
          .length;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            exact
                ? '$produced/$requestedCount cards ready • AI reviewed $reviewedCount, fixed $fixedCount, rejected $rejectedCount'
                    '${topics > 0 ? ' • $topics topics' : ''}.'
                : '$produced/$requestedCount reviewed cards were supported by the source • AI reviewed $reviewedCount, fixed $fixedCount, rejected $rejectedCount. Memora did not add unreviewed filler.',
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;

      final partialReady = mode == 'add'
          ? widget.guide.cards.length - oldCards.length
          : widget.guide.cards.length;
      final detail = AiService.userFacingError(e);

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            partialReady > 0
                ? 'AI review stopped after $partialReady reviewed cards. Those cards are already saved and can be studied now. $detail'
                : 'No new cards were saved because AI final review is required. $detail',
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _generatingCards = false);
    }
  }

'''
s = s[:start] + method + s[end:]
p.write_text(s)

print('v179 applied: mandatory AI review for all cards + progressive reviewed batches')
