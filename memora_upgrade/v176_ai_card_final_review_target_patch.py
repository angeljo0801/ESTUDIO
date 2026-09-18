from pathlib import Path

# v176: exact requested card count + AI final debugger for suspicious cards only.

# --- StudyEngine candidate target ------------------------------------------------
p = Path('lib/study_engine.dart')
s = p.read_text()
old = """  static List<StudyCard> buildCards(
    String text, {
    List<GuideSourceBlock> sourceBlocks = const [],
  }) {
"""
new = """  static List<StudyCard> buildCards(
    String text, {
    List<GuideSourceBlock> sourceBlocks = const [],
    int? requestedCount,
  }) {
"""
if old not in s:
    raise SystemExit('v176 StudyEngine signature anchor missing')
s = s.replace(old, new, 1)

old = """    final target = recommendedCardCount(clean);
    final maxCards = (target + 28).clamp(20, 120).toInt();
"""
new = """    final target = requestedCount == null
        ? recommendedCardCount(clean)
        : requestedCount.clamp(1, 200).toInt();
    final reserve = requestedCount == null
        ? 28
        : ((target * .5).ceil().clamp(12, 60)).toInt();
    final maxCards = (target + reserve).clamp(20, 240).toInt();
"""
if old not in s:
    raise SystemExit('v176 StudyEngine target anchor missing')
s = s.replace(old, new, 1)

old = """      if (RegExp(r'[?!:;]').hasMatch(subject)) return true;
      return false;
"""
new = """      if (RegExp(r'[?!:;]').hasMatch(subject)) return true;
      if (RegExp(r'^[+\\-×÷/*=]').hasMatch(subject)) return true;
      if (RegExp(r'\\s[=×÷]\\s').hasMatch(subject)) return true;
      if (RegExp(r'\\b\\d+\\.\\d+\\b').hasMatch(subject) &&
          RegExp(r'[+\\-×÷/*=]').hasMatch(subject)) {
        return true;
      }
      return false;
"""
if old not in s:
    raise SystemExit('v176 StudyEngine weakSubject anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)

# --- Local card quality: target-aware coverage + malformed rejection -------------
p = Path('lib/study_card_quality_service.dart')
s = p.read_text()
old = """    List<StudyCard> existing = const [],
    bool append = false,
  }) async {
    var fresh = _exactDedupe(generated);
"""
new = """    List<StudyCard> existing = const [],
    bool append = false,
    int? targetCount,
  }) async {
    var fresh = generated.where((card) => !isObviouslyMalformed(card)).toList();
    fresh = _exactDedupe(fresh);
"""
if old not in s:
    raise SystemExit('v176 quality signature anchor missing')
s = s.replace(old, new, 1)
s = s.replace(
    "    fresh = _balanceCoverage(guide, fresh);\n",
    "    fresh = _balanceCoverage(guide, fresh, targetCount: targetCount);\n",
    1,
)

old = """  static List<StudyCard> _balanceCoverage(
    StudyGuide guide,
    List<StudyCard> cards,
  ) {
"""
new = """  static List<StudyCard> _balanceCoverage(
    StudyGuide guide,
    List<StudyCard> cards, {
    int? targetCount,
  }) {
"""
if old not in s:
    raise SystemExit('v176 balance signature anchor missing')
s = s.replace(old, new, 1)

old = """    final recommended = StudyEngine.recommendedCardCount(guide.text);
    final desired = math.min(
      cards.length,
      math.max(groups.length * 2, (recommended * 1.25).ceil()),
    );
"""
new = """    final recommended = targetCount ??
        (StudyEngine.recommendedCardCount(guide.text) * 1.25).ceil();
    final desired = math.min(
      cards.length,
      math.max(groups.length * 2, recommended),
    );
"""
if old not in s:
    raise SystemExit('v176 desired-count anchor missing')
s = s.replace(old, new, 1)

anchor = "  static List<StudyCard> _exactDedupe(List<StudyCard> cards) {\n"
helpers = r'''  static bool isObviouslyMalformed(StudyCard card) {
    final q = card.question.replaceAll(RegExp(r'\s+'), ' ').trim();
    final a = card.answer.replaceAll(RegExp(r'\s+'), ' ').trim();
    if (q.isEmpty || a.isEmpty) return true;
    if (_delimiterBalance(q) != 0 || _delimiterBalance(a) != 0) return true;
    if (RegExp(r'^[+×÷/*=]|[+×÷/*=]\s*\?$').hasMatch(q)) return true;

    final modal = RegExp(
      r'^what\s+(?:should|must|can|may)\s+(.+?)\s+do\?$',
      caseSensitive: false,
    ).firstMatch(q);
    if (modal != null) {
      final subject = modal.group(1)!.trim();
      if (RegExp(r'^[+\-×÷/*=]').hasMatch(subject) ||
          RegExp(r'\s[=×÷]\s').hasMatch(subject) ||
          (RegExp(r'\b\d+\.\d+\b').hasMatch(subject) &&
              RegExp(r'[+\-×÷/*=]').hasMatch(subject))) {
        return true;
      }
    }

    if (RegExp(r'[×÷=]').hasMatch(q) &&
        RegExp(r'\b\d+\.\d+\b').hasMatch(q) &&
        RegExp(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+').hasMatch(q)) {
      return true;
    }
    final words = _tokens(a);
    if (words.length < 3 && a.length < 24) return true;
    return false;
  }

  static int _delimiterBalance(String value) {
    var balance = 0;
    for (final rune in value.runes) {
      final c = String.fromCharCode(rune);
      if (c == '(' || c == '[' || c == '{') balance++;
      if (c == ')' || c == ']' || c == '}') balance--;
    }
    return balance;
  }

  static List<StudyCard> mergeUnique({
    required List<StudyCard> existing,
    required List<StudyCard> generated,
    required int maxNew,
  }) {
    if (maxNew <= 0) return List<StudyCard>.of(existing);
    final result = List<StudyCard>.of(existing);
    final keys = existing.map(_pairKey).toSet();
    final tokenSets = existing
        .map((card) => _tokens(card.question + ' ' + card.answer))
        .toList();
    var added = 0;
    for (final card in generated) {
      if (added >= maxNew) break;
      if (isObviouslyMalformed(card)) continue;
      if (!keys.add(_pairKey(card))) continue;
      final tokens = _tokens(card.question + ' ' + card.answer);
      if (tokenSets.any((prior) => _jaccard(tokens, prior) >= .84)) continue;
      result.add(card);
      tokenSets.add(tokens);
      added++;
    }
    return result;
  }

'''
if anchor not in s:
    raise SystemExit('v176 quality helper anchor missing')
s = s.replace(anchor, helpers + anchor, 1)
p.write_text(s)

# --- AI final debugger -----------------------------------------------------------
Path('lib/ai_card_review_service.dart').write_text(r'''import 'dart:convert';

import 'ai_service.dart';
import 'models.dart';
import 'study_card_quality_service.dart';

class AiCardReviewResult {
  const AiCardReviewResult({
    required this.cards,
    this.reviewed = 0,
    this.fixed = 0,
    this.rejected = 0,
    this.aiUsed = false,
    this.error,
  });

  final List<StudyCard> cards;
  final int reviewed;
  final int fixed;
  final int rejected;
  final bool aiUsed;
  final String? error;
}

class AiCardReviewService {
  static Future<AiCardReviewResult> reviewSuspicious({
    required StudyGuide guide,
    required List<StudyCard> cards,
    required bool enabled,
  }) async {
    if (!enabled || cards.isEmpty) {
      return AiCardReviewResult(cards: List<StudyCard>.of(cards));
    }

    final suspicious = <int>[
      for (var i = 0; i < cards.length; i++)
        if (_isSuspicious(cards[i])) i,
    ];
    if (suspicious.isEmpty) {
      return AiCardReviewResult(cards: List<StudyCard>.of(cards));
    }

    final decisions = <int, _Decision>{};
    var aiUsed = false;
    String? lastError;

    for (var offset = 0; offset < suspicious.length; offset += 6) {
      final end = (offset + 6).clamp(0, suspicious.length).toInt();
      final batch = suspicious.sublist(offset, end);
      final candidates = batch.map((index) {
        final card = cards[index];
        final evidence = _evidenceFor(guide, card);
        return '''ID: $index
PAGE: ${card.page ?? 'unknown'}
SECTION: ${card.section.trim().isEmpty ? '(none)' : card.section.trim()}
QUESTION: ${card.question}
ANSWER: ${card.answer}
SOURCE EVIDENCE:
${evidence.isEmpty ? '(no exact source excerpt available)' : evidence}''';
      }).join('\n\n========\n\n');

      final prompt = '''You are Memora's FINAL FLASHCARD DEBUGGER.

Review ONLY the suspicious cards below.

For each ID return exactly one action:
KEEP = clear, coherent, and fully supported by SOURCE EVIDENCE.
FIX = malformed, but repairable using ONLY SOURCE EVIDENCE.
REJECT = mixed PDF fragments, incomplete, ungradable, or not safely repairable.

STRICT RULES:
- Never add outside knowledge.
- Never invent formulas, numbers, definitions, or relationships.
- If evidence is insufficient, REJECT.
- Broken equations, section numbers, headings, and unrelated fragments should be FIXED only when the intended card is unambiguous.
- A FIX must remain about the same source concept.
- Preserve meaningful formulas and numbers exactly.
- Return ONLY JSON.

FORMAT:
[{"id":0,"action":"KEEP","question":"","answer":"","reason":"short reason"}]

CANDIDATES:
$candidates''';

      try {
        final raw = await AiService.askTaskConfigured(
          prompt: prompt,
          providerOverride: 'global',
          settingsScope: 'global',
          responseMode: 'fast',
        ).timeout(
          const Duration(seconds: 75),
          onTimeout: () async {
            try {
              await AiService.cancelCurrent();
            } catch (_) {}
            return '';
          },
        );
        if (raw.trim().isEmpty) continue;
        final parsed = _parse(raw);
        if (parsed.isNotEmpty) {
          aiUsed = true;
          decisions.addAll(parsed);
        }
      } catch (e) {
        lastError = AiService.userFacingError(e);
      }
    }

    final output = <StudyCard>[];
    var reviewed = 0;
    var fixed = 0;
    var rejected = 0;

    for (var i = 0; i < cards.length; i++) {
      final original = cards[i];
      final isSuspect = suspicious.contains(i);
      final decision = decisions[i];

      if (!isSuspect) {
        output.add(original);
        continue;
      }

      if (decision == null) {
        if (StudyCardQualityService.isObviouslyMalformed(original)) {
          rejected++;
        } else {
          output.add(original);
        }
        continue;
      }

      reviewed++;
      if (decision.action == 'REJECT') {
        rejected++;
        continue;
      }
      if (decision.action == 'KEEP') {
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
      reviewed: reviewed,
      fixed: fixed,
      rejected: rejected,
      aiUsed: aiUsed,
      error: lastError,
    );
  }

  static bool _isSuspicious(StudyCard card) {
    if (StudyCardQualityService.isObviouslyMalformed(card)) return true;
    final q = card.question.replaceAll(RegExp(r'\s+'), ' ').trim();
    final a = card.answer.replaceAll(RegExp(r'\s+'), ' ').trim();
    if (q.length > 175 || a.length < 20) return true;
    if (_delimiterBalance(q) != 0 || _delimiterBalance(a) != 0) return true;
    if (RegExp(r'[×÷=]').hasMatch(q) && RegExp(r'\b\d+\.\d+\b').hasMatch(q)) {
      return true;
    }
    if (RegExp(r'\b(?:chapter|section)\s+\d+(?:\.\d+)+\b',
            caseSensitive: false)
        .hasMatch(q)) {
      return true;
    }
    if (RegExp(r'\b\d+\.\d+\s+[A-Z][A-Za-z]+').hasMatch(q) &&
        q.split(' ').length > 12) {
      return true;
    }
    return false;
  }

  static String _evidenceFor(StudyGuide guide, StudyCard card) {
    final chunks = <String>[];
    final exact = card.sourceExcerpt.trim();
    if (exact.isNotEmpty) chunks.add(exact);

    for (final block in guide.sourceBlocks) {
      if (chunks.length >= 4) break;
      final samePage = card.page != null && block.page == card.page;
      final sameSection = card.section.trim().isNotEmpty &&
          block.section.trim() == card.section.trim();
      if (!samePage && !sameSection) continue;
      final text = block.text.trim();
      if (text.isEmpty || chunks.contains(text)) continue;
      chunks.add(text);
    }

    var evidence = chunks.join('\n');
    if (evidence.length > 1800) evidence = evidence.substring(0, 1800);
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
        final action = item['action']?.toString().toUpperCase().trim() ?? '';
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
        .map((m) => m.group(0)!)
        .toSet();
    final proposedNumbers = RegExp(r'\d+(?:[.,]\d+)*')
        .allMatches(proposed)
        .map((m) => m.group(0)!)
        .toSet();
    return proposedNumbers.every(sourceNumbers.contains);
  }

  static int _delimiterBalance(String value) {
    var balance = 0;
    for (final rune in value.runes) {
      final c = String.fromCharCode(rune);
      if (c == '(' || c == '[' || c == '{') balance++;
      if (c == ')' || c == ']' || c == '}') balance--;
    }
    return balance;
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
''')

# --- Guide Detail generation dialog ---------------------------------------------
p = Path('lib/guide_detail_page.dart')
s = p.read_text()
if "package:shared_preferences/shared_preferences.dart" not in s:
    s = s.replace(
        "import 'package:flutter/material.dart';\n",
        "import 'package:flutter/material.dart';\n"
        "import 'package:shared_preferences/shared_preferences.dart';\n",
        1,
    )
if "import 'ai_card_review_service.dart';" not in s:
    s = s.replace(
        "import 'study_card_quality_service.dart';\n",
        "import 'study_card_quality_service.dart';\n"
        "import 'ai_card_review_service.dart';\n",
        1,
    )

start = s.find("  Future<void> _regenerate(")
end = s.find("  Future<void> _reprocessPdf()", start)
if start < 0 or end < 0:
    raise SystemExit('v176 GuideDetail method anchors missing')

method = r'''  Future<void> _regenerate({bool automatic = false}) async {
    if (_generatingCards) return;

    final prefs = await SharedPreferences.getInstance();
    var requestedCount =
        (prefs.getInt('memora_card_target_count') ?? 50).clamp(5, 120).toInt();
    var useAiReview =
        prefs.getBool('memora_ai_final_card_review') ?? true;
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
                      helperText: 'Memora targets exactly this number (5–120).',
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
                    const SizedBox(height: 6),
                    Text(
                      mode == 'replace'
                          ? 'The final card bank will target the number above.'
                          : 'Memora will try to add that many NEW cards without duplicating the current bank.',
                      style: Theme.of(dialogContext).textTheme.bodySmall,
                    ),
                  ],
                  const SizedBox(height: 14),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    value: useAiReview,
                    onChanged: (value) =>
                        setDialogState(() => useAiReview = value),
                    title: const Text('AI Final Card Review'),
                    subtitle: const Text(
                      'The configured Memora AI reviews only suspicious cards. It can keep, repair from the exact source, or reject them. If AI is unavailable, local generation still works.',
                    ),
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
    await prefs.setBool('memora_ai_final_card_review', useAiReview);

    setState(() {
      _generatingCards = true;
      _cardProgress = 0;
    });

    try {
      final extra = ((requestedCount * .35).ceil().clamp(12, 42)).toInt();
      final candidateTarget =
          (requestedCount + extra).clamp(requestedCount, 160).toInt();

      final raw = StudyEngine.buildCards(
        widget.guide.text,
        sourceBlocks: widget.guide.sourceBlocks,
        requestedCount: candidateTarget,
      );
      if (mounted) setState(() => _cardProgress = raw.length);

      final local = await StudyCardQualityService.finalizeCards(
        guide: widget.guide,
        generated: raw,
        existing: mode == 'replace' ? widget.guide.cards : const [],
        append: false,
        targetCount: candidateTarget,
      );

      final aiReview = await AiCardReviewService.reviewSuspicious(
        guide: widget.guide,
        cards: local,
        enabled: useAiReview,
      );

      final reviewed = aiReview.cards;
      List<StudyCard> finalCards;
      int produced;

      if (mode == 'add') {
        final before = widget.guide.cards.length;
        finalCards = StudyCardQualityService.mergeUnique(
          existing: widget.guide.cards,
          generated: reviewed,
          maxNew: requestedCount,
        );
        produced = finalCards.length - before;
      } else {
        finalCards = reviewed.take(requestedCount).toList();
        produced = finalCards.length;
      }

      if (!mounted) return;
      setState(() {
        widget.guide.cards = finalCards;
        _cardProgress = produced;
      });
      await _save();

      if (!mounted || automatic) return;
      final topics = finalCards
          .map((card) => card.section.trim().isNotEmpty
              ? card.section.trim()
              : card.source.trim())
          .where((topic) => topic.isNotEmpty)
          .toSet()
          .length;

      final exact = produced == requestedCount;
      final reviewText = useAiReview
          ? (aiReview.aiUsed
              ? ' • AI reviewed ${aiReview.reviewed}, fixed ${aiReview.fixed}, rejected ${aiReview.rejected}'
              : aiReview.error != null
                  ? ' • AI review unavailable; local filters used'
                  : ' • no suspicious cards needed AI review')
          : '';

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            exact
                ? '$produced/$requestedCount cards ready'
                    '${topics > 0 ? ' across $topics topics' : ''}$reviewText.'
                : '$produced/$requestedCount high-quality cards found'
                    '${topics > 0 ? ' across $topics topics' : ''}$reviewText '
                    'Memora did not pad the set with weak or unsupported cards.',
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Card generation failed: $e')),
      );
    } finally {
      if (mounted) setState(() => _generatingCards = false);
    }
  }

'''
s = s[:start] + method + s[end:]
p.write_text(s)

print('v176 applied: AI final debugger + exact requested card count')
