from pathlib import Path
import re

# v175: card provenance, semantic de-duplication, coverage balancing,
# replace/add regeneration, extraction preview and PDF reprocess UI.

# ---------------------------------------------------------------------------
# Pure PDF cleanup heuristics used by importer + regression tests.
# ---------------------------------------------------------------------------
Path('lib/pdf_text_heuristics.dart').write_text(r'''class PdfTextHeuristics {
  static List<String> mergeLines(List<String> lines) {
    final result = <String>[];
    for (final raw in lines) {
      final current = cleanLine(raw);
      if (current.isEmpty) continue;
      if (result.isEmpty) {
        result.add(current);
        continue;
      }
      final previous = result.last;
      if (shouldJoin(previous, current)) {
        if (previous.endsWith('-') &&
            RegExp(r'^[a-záéíóúüñ]').hasMatch(current)) {
          result[result.length - 1] =
              previous.substring(0, previous.length - 1) + current;
        } else {
          result[result.length - 1] =
              (previous + ' ' + current).replaceAll(RegExp(r'\s+'), ' ').trim();
        }
      } else {
        result.add(current);
      }
    }
    return result;
  }

  static List<List<String>> removeFurniture(List<List<String>> pages) {
    if (pages.length < 3) {
      return pages
          .map((page) => page.where((line) => !isPageNumber(line)).toList())
          .toList();
    }
    final counts = <String, int>{};
    for (final page in pages) {
      final edges = <String>[...page.take(2), ...page.reversed.take(2)];
      final seen = <String>{};
      for (final line in edges) {
        final key = furnitureKey(line);
        if (key.length < 3 || key.length > 100 || !seen.add(key)) continue;
        counts[key] = (counts[key] ?? 0) + 1;
      }
    }
    final threshold = (pages.length * .45).ceil().clamp(2, pages.length);
    final repeated = counts.entries
        .where((entry) => entry.value >= threshold)
        .map((entry) => entry.key)
        .toSet();
    return pages.map((page) {
      final out = <String>[];
      for (var i = 0; i < page.length; i++) {
        final line = page[i];
        final edge = i < 2 || i >= page.length - 2;
        if (isPageNumber(line)) continue;
        if (edge && repeated.contains(furnitureKey(line))) continue;
        out.add(line);
      }
      return out;
    }).toList();
  }

  static double quality(String text) {
    final value = text.trim();
    if (value.isEmpty) return 0;
    final compact = value.replaceAll(RegExp(r'\s'), '');
    if (compact.isEmpty) return 0;
    final words = wordCount(value);
    final alnum = RegExp(r'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]')
        .allMatches(compact)
        .length;
    final replacement = RegExp(r'[�\u0000]').allMatches(value).length;
    final lines = value
        .split('\n')
        .map((line) => line.trim())
        .where((line) => line.isNotEmpty)
        .toList();
    final tiny = lines.where((line) => line.length <= 2).length;
    var score = alnum / compact.length;
    if (words < 8) score -= .28;
    if (replacement > 0) score -= (replacement * .03).clamp(0, .25);
    if (lines.isNotEmpty && tiny / lines.length > .25) score -= .12;
    return score.clamp(0.0, 1.0);
  }

  static String cleanLine(String value) => value
      .replaceAll('\u00ad', '')
      .replaceAll('\ufb00', 'ff')
      .replaceAll('\ufb01', 'fi')
      .replaceAll('\ufb02', 'fl')
      .replaceAll('\ufb03', 'ffi')
      .replaceAll('\ufb04', 'ffl')
      .replaceAll(RegExp(r'[\t ]+'), ' ')
      .replaceAll(RegExp(r'\s*\n\s*'), ' ')
      .trim();

  static bool shouldJoin(String previous, String current) {
    final a = previous.trim();
    final b = current.trim();
    if (a.isEmpty || b.isEmpty) return false;
    if (unclosedDelimiters(a) > 0) return true;
    if (RegExp(r'[=+\-×÷/*,(\\[]$').hasMatch(a)) return true;
    if (RegExp(r'^[=+×÷/*,\])]').hasMatch(b)) return true;
    final formulaA = formulaLike(a);
    final formulaB = formulaLike(b);
    if ((formulaA || formulaB) &&
        !RegExp(r'[.!?;:]$').hasMatch(a) &&
        (a.contains('=') || b.contains('=') || formulaA && formulaB)) {
      return true;
    }
    if (a.endsWith('-') && RegExp(r'^[a-záéíóúüñ]').hasMatch(b)) return true;
    if (!RegExp(r'[.!?;:]$').hasMatch(a)) {
      if (RegExp(r'^[a-záéíóúüñ]').hasMatch(b)) return true;
      if (a.endsWith(',') || a.endsWith('—') || a.endsWith('–')) return true;
      if (wordCount(a) >= 7 &&
          wordCount(b) >= 4 &&
          !headingLike(a) &&
          !headingLike(b)) {
        return true;
      }
    }
    return false;
  }

  static int unclosedDelimiters(String text) {
    var balance = 0;
    for (final rune in text.runes) {
      final c = String.fromCharCode(rune);
      if (c == '(' || c == '[' || c == '{') balance++;
      if (c == ')' || c == ']' || c == '}') balance--;
    }
    return balance;
  }

  static bool formulaLike(String line) {
    if (line.contains('=')) return true;
    final operators = RegExp(r'[+\-×÷/*=]').allMatches(line).length;
    final digits = RegExp(r'\d').allMatches(line).length;
    return operators >= 2 && (digits >= 1 || wordCount(line) <= 8);
  }

  static bool headingLike(String line) {
    final value = line.trim();
    if (value.length > 100 || RegExp(r'[.!?;]$').hasMatch(value)) return false;
    if (value.contains('=') || formulaLike(value)) return false;
    final words = RegExp(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9'-]+")
        .allMatches(value)
        .map((m) => m.group(0)!)
        .toList();
    if (words.isEmpty || words.length > 12) return false;
    final title = words
        .where((word) => RegExp(r'^[A-ZÁÉÍÓÚÜÑ0-9]').hasMatch(word))
        .length;
    return title / words.length >= .55;
  }

  static int wordCount(String text) =>
      RegExp(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9'-]+").allMatches(text).length;

  static bool isPageNumber(String line) => RegExp(
        r'^(?:page\s+)?\d{1,4}(?:\s*(?:/|of)\s*\d{1,4})?$',
        caseSensitive: false,
      ).hasMatch(line.trim());

  static String furnitureKey(String line) => line
      .toLowerCase()
      .replaceAll(RegExp(r'\d+'), '#')
      .replaceAll(RegExp(r'[^a-záéíóúüñ# ]+'), ' ')
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim();
}
''')

# Route the existing importer helpers through the pure tested implementation.
p = Path('lib/guide_importer.dart')
s = p.read_text()
if "import 'pdf_text_heuristics.dart';" not in s:
    s = s.replace(
        "import 'models.dart';\n",
        "import 'models.dart';\nimport 'pdf_text_heuristics.dart';\n",
        1,
    )

def replace_method(source, signature, next_signature, body):
    start = source.find(signature)
    end = source.find(next_signature, start)
    if start < 0 or end < 0:
        raise SystemExit('v175 importer method anchor missing: ' + signature)
    return source[:start] + body + source[end:]

s = replace_method(
    s,
    "  static List<List<String>> _removePdfFurniture(",
    "  static bool _isPageNumber(",
    r'''  static List<List<String>> _removePdfFurniture(
    List<List<String>> pages,
  ) =>
      PdfTextHeuristics.removeFurniture(pages);

''',
)
s = replace_method(
    s,
    "  static bool _isPageNumber(",
    "  static String _pdfFurnitureKey(",
    r'''  static bool _isPageNumber(String line) =>
      PdfTextHeuristics.isPageNumber(line);

''',
)
s = replace_method(
    s,
    "  static String _pdfFurnitureKey(",
    "  static List<String> _mergePdfLines(",
    r'''  static String _pdfFurnitureKey(String line) =>
      PdfTextHeuristics.furnitureKey(line);

''',
)
s = replace_method(
    s,
    "  static List<String> _mergePdfLines(",
    "  static bool _joinPdfLine(",
    r'''  static List<String> _mergePdfLines(List<String> lines) =>
      PdfTextHeuristics.mergeLines(lines);

''',
)
s = replace_method(
    s,
    "  static bool _joinPdfLine(",
    "  static int _unclosedPdfDelimiters(",
    r'''  static bool _joinPdfLine(String previous, String current) =>
      PdfTextHeuristics.shouldJoin(previous, current);

''',
)
s = replace_method(
    s,
    "  static int _unclosedPdfDelimiters(",
    "  static bool _formulaLike(",
    r'''  static int _unclosedPdfDelimiters(String text) =>
      PdfTextHeuristics.unclosedDelimiters(text);

''',
)
s = replace_method(
    s,
    "  static bool _formulaLike(",
    "  static bool _pdfHeadingLike(",
    r'''  static bool _formulaLike(String line) =>
      PdfTextHeuristics.formulaLike(line);

''',
)
s = replace_method(
    s,
    "  static bool _pdfHeadingLike(",
    "  static int _pdfWordCount(",
    r'''  static bool _pdfHeadingLike(String line) =>
      PdfTextHeuristics.headingLike(line);

''',
)
s = replace_method(
    s,
    "  static int _pdfWordCount(",
    "  static double _pdfQuality(",
    r'''  static int _pdfWordCount(String text) =>
      PdfTextHeuristics.wordCount(text);

''',
)
s = replace_method(
    s,
    "  static double _pdfQuality(",
    "  static Future<List<String>> _ocrPdfPage(",
    r'''  static double _pdfQuality(String text) =>
      PdfTextHeuristics.quality(text);

''',
)
p.write_text(s)

# ---------------------------------------------------------------------------
# StudyEngine: attach page/section/excerpt to cards from structured PDF blocks.
# ---------------------------------------------------------------------------
p = Path('lib/study_engine.dart')
s = p.read_text()

s = s.replace(
    "  static List<StudyCard> buildCards(String text) {\n",
    "  static List<StudyCard> buildCards(\n"
    "    String text, {\n"
    "    List<GuideSourceBlock> sourceBlocks = const [],\n"
    "  }) {\n",
    1,
)

candidate_old = """      final candidate = StudyCard(
        id: '${now.microsecondsSinceEpoch}-${counter++}',
        question: q.endsWith('?') ? q : '$q?',
        answer: a,
        source: source,
        dueAt: now,
      );
"""
candidate_new = """      final origin = _findSourceBlock(a, sourceBlocks);
      final originSection = (origin?.section.trim().isNotEmpty ?? false)
          ? origin!.section.trim()
          : source;
      final candidate = StudyCard(
        id: '${now.microsecondsSinceEpoch}-${counter++}',
        question: q.endsWith('?') ? q : '$q?',
        answer: a,
        source: originSection,
        dueAt: now,
        page: origin?.page,
        section: originSection,
        sourceExcerpt: origin?.text ?? '',
      );
"""
if candidate_old not in s:
    # Older parser variant fallback.
    candidate_old = """      final candidate = StudyCard(
        id: '${now.microsecondsSinceEpoch}-${counter}',
        question: q,
        answer: a,
        source: source,
        dueAt: now,
      );
"""
    candidate_new = """      final origin = _findSourceBlock(a, sourceBlocks);
      final originSection = (origin?.section.trim().isNotEmpty ?? false)
          ? origin!.section.trim()
          : source;
      final candidate = StudyCard(
        id: '${now.microsecondsSinceEpoch}-${counter}',
        question: q,
        answer: a,
        source: originSection,
        dueAt: now,
        page: origin?.page,
        section: originSection,
        sourceExcerpt: origin?.text ?? '',
      );
"""
if candidate_old not in s:
    raise SystemExit('v175 StudyEngine card constructor anchor missing')
s = s.replace(candidate_old, candidate_new, 1)

helper_anchor = "  /// Final safety check"
source_helper = r'''  static GuideSourceBlock? _findSourceBlock(
    String answer,
    List<GuideSourceBlock> blocks,
  ) {
    if (blocks.isEmpty || answer.trim().isEmpty) return null;
    final answerKey = _normalizedKey(answer);
    if (answerKey.isEmpty) return null;

    GuideSourceBlock? best;
    var bestScore = 0.0;
    final answerWords = _words(answer).where((word) => word.length >= 3).toSet();

    for (final block in blocks) {
      final text = block.text.trim();
      if (text.isEmpty) continue;
      final blockKey = _normalizedKey(text);
      if (blockKey.contains(answerKey) || answerKey.contains(blockKey)) {
        return block;
      }
      if (answerWords.isEmpty) continue;
      final blockWords = _words(text).where((word) => word.length >= 3).toSet();
      final intersection = answerWords.intersection(blockWords).length;
      final union = answerWords.union(blockWords).length;
      final score = union == 0 ? 0.0 : intersection / union;
      if (score > bestScore) {
        bestScore = score;
        best = block;
      }
    }
    return bestScore >= .18 ? best : null;
  }

'''
if helper_anchor not in s:
    raise SystemExit('v175 StudyEngine source helper anchor missing')
s = s.replace(helper_anchor, source_helper + helper_anchor, 1)
p.write_text(s)

# ---------------------------------------------------------------------------
# Card quality service: preserve coverage and remove semantic duplicates.
# Embeddings are optional; lexical de-duplication always works.
# ---------------------------------------------------------------------------
Path('lib/study_card_quality_service.dart').write_text(r'''import 'dart:math' as math;

import 'embedding_service.dart';
import 'models.dart';
import 'study_engine.dart';

class StudyCardQualityService {
  static Future<List<StudyCard>> finalizeCards({
    required StudyGuide guide,
    required List<StudyCard> generated,
    List<StudyCard> existing = const [],
    bool append = false,
  }) async {
    var fresh = _exactDedupe(generated);
    fresh = _lexicalDedupe(fresh);
    fresh = _balanceCoverage(guide, fresh);
    fresh = await _semanticDedupe(fresh);

    if (!append) {
      _restoreProgress(existing, fresh);
      return fresh;
    }

    final combined = <StudyCard>[...existing];
    final existingKeys = existing.map(_pairKey).toSet();
    for (final card in fresh) {
      if (existingKeys.add(_pairKey(card))) combined.add(card);
    }
    return _lexicalDedupe(combined, preserveFirst: true);
  }

  static List<StudyCard> _exactDedupe(List<StudyCard> cards) {
    final seen = <String>{};
    return [
      for (final card in cards)
        if (seen.add(_pairKey(card))) card,
    ];
  }

  static List<StudyCard> _lexicalDedupe(
    List<StudyCard> cards, {
    bool preserveFirst = false,
  }) {
    final kept = <StudyCard>[];
    for (final card in cards) {
      final tokens = _tokens(card.question + ' ' + card.answer);
      var duplicate = false;
      for (final prior in kept) {
        final other = _tokens(prior.question + ' ' + prior.answer);
        if (_jaccard(tokens, other) >= .84) {
          duplicate = true;
          break;
        }
      }
      if (!duplicate) kept.add(card);
    }
    return kept;
  }

  static Future<List<StudyCard>> _semanticDedupe(
    List<StudyCard> cards,
  ) async {
    if (cards.length < 2) return cards;
    try {
      if (!await EmbeddingService.isReady()) return cards;
      final kept = <StudyCard>[];
      final vectors = <List<double>>[];
      for (final card in cards) {
        final vector = await EmbeddingService.embed(
          '${card.question}\n${card.answer}',
        );
        var duplicate = false;
        for (final prior in vectors) {
          if (_dot(vector, prior) >= .925) {
            duplicate = true;
            break;
          }
        }
        if (!duplicate) {
          kept.add(card);
          vectors.add(vector);
        }
      }
      return kept;
    } catch (_) {
      return cards;
    }
  }

  static List<StudyCard> _balanceCoverage(
    StudyGuide guide,
    List<StudyCard> cards,
  ) {
    if (cards.length < 8) return cards;
    final groups = <String, List<StudyCard>>{};
    for (final card in cards) {
      final key = card.section.trim().isNotEmpty
          ? card.section.trim()
          : card.source.trim().isNotEmpty
              ? card.source.trim()
              : 'General';
      groups.putIfAbsent(key, () => <StudyCard>[]).add(card);
    }
    if (groups.length <= 1) return cards;

    final recommended = StudyEngine.recommendedCardCount(guide.text);
    final desired = math.min(
      cards.length,
      math.max(groups.length * 2, (recommended * 1.25).ceil()),
    );

    final queues = groups.values.map((items) => List<StudyCard>.of(items)).toList();
    final balanced = <StudyCard>[];
    var cursor = 0;
    while (balanced.length < desired && queues.any((queue) => queue.isNotEmpty)) {
      final queue = queues[cursor % queues.length];
      if (queue.isNotEmpty) balanced.add(queue.removeAt(0));
      cursor++;
    }
    return balanced;
  }

  static void _restoreProgress(
    List<StudyCard> oldCards,
    List<StudyCard> newCards,
  ) {
    final oldByPair = {for (final card in oldCards) _pairKey(card): card};
    for (final card in newCards) {
      final old = oldByPair[_pairKey(card)];
      if (old == null) continue;
      card.dueAt = old.dueAt;
      card.intervalDays = old.intervalDays;
      card.ease = old.ease;
      card.correct = old.correct;
      card.wrong = old.wrong;
      card.streak = old.streak;
    }
  }

  static String _pairKey(StudyCard card) =>
      '${_normalize(card.question)}|${_normalize(card.answer)}';

  static Set<String> _tokens(String value) => RegExp(
        r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9'-]+",
      )
          .allMatches(value.toLowerCase())
          .map((match) => match.group(0)!)
          .where((token) => token.length >= 3)
          .toSet();

  static double _jaccard(Set<String> a, Set<String> b) {
    if (a.isEmpty || b.isEmpty) return 0;
    return a.intersection(b).length / a.union(b).length;
  }

  static String _normalize(String value) => value
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-záéíóúüñ0-9]+'), ' ')
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim();

  static double _dot(List<double> a, List<double> b) {
    final n = math.min(a.length, b.length);
    var total = 0.0;
    for (var i = 0; i < n; i++) {
      total += a[i] * b[i];
    }
    return total;
  }
}
''')

# ---------------------------------------------------------------------------
# Guide Detail: replace/add options + Smart PDF reprocess.
# ---------------------------------------------------------------------------
p = Path('lib/guide_detail_page.dart')
s = p.read_text()
if "import 'guide_importer.dart';" not in s:
    s = s.replace(
        "import 'guide_file_service.dart';\n",
        "import 'guide_file_service.dart';\nimport 'guide_importer.dart';\n",
        1,
    )
if "import 'study_card_quality_service.dart';" not in s:
    s = s.replace(
        "import 'study_engine.dart';\n",
        "import 'study_engine.dart';\nimport 'study_card_quality_service.dart';\n",
        1,
    )

if "bool _reprocessingPdf = false;" not in s:
    state_anchor = "  int _cardProgress = 0;\n"
    if state_anchor not in s:
        raise SystemExit('v175 GuideDetail state anchor missing')
    s = s.replace(state_anchor, state_anchor + "  bool _reprocessingPdf = false;\n", 1)

start = s.find("  Future<void> _regenerate(")
end = s.find("  Future<void> _export()", start)
if start < 0 or end < 0:
    raise SystemExit('v175 GuideDetail regenerate anchor missing')

regenerate = r'''  Future<void> _regenerate({bool automatic = false}) async {
    if (_generatingCards) return;

    var mode = 'replace';
    if (widget.guide.cards.isNotEmpty && !automatic) {
      final selected = await showDialog<String>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('Generate study cards'),
          content: const Text(
            'Do you want to replace the current cards or add new cards while keeping the existing ones and their progress?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Cancel'),
            ),
            OutlinedButton(
              onPressed: () => Navigator.pop(dialogContext, 'add'),
              child: const Text('Add new'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, 'replace'),
              child: const Text('Replace'),
            ),
          ],
        ),
      );
      if (selected == null) return;
      mode = selected;
    }

    setState(() {
      _generatingCards = true;
      _cardProgress = 0;
    });

    try {
      final raw = StudyEngine.buildCards(
        widget.guide.text,
        sourceBlocks: widget.guide.sourceBlocks,
      );
      if (mounted) setState(() => _cardProgress = raw.length);

      final finalized = await StudyCardQualityService.finalizeCards(
        guide: widget.guide,
        generated: raw,
        existing: widget.guide.cards,
        append: mode == 'add',
      );

      if (!mounted) return;
      setState(() {
        widget.guide.cards = finalized;
        _cardProgress = finalized.length;
      });
      await _save();

      if (!mounted || automatic) return;
      final topics = finalized
          .map((card) => card.section.trim().isNotEmpty
              ? card.section.trim()
              : card.source.trim())
          .where((topic) => topic.isNotEmpty)
          .toSet()
          .length;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '${finalized.length} study cards ready'
            '${topics > 0 ? ' across $topics topics' : ''}.',
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

  Future<void> _reprocessPdf() async {
    if (_reprocessingPdf) return;
    final guide = widget.guide;
    if (guide.sourceType.toLowerCase() != 'pdf' || !guide.hasFile) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Re-extract PDF'),
        content: const Text(
          'Memora will run the Smart PDF Extractor again, replace the extracted text, and rebuild the vector index. Existing card progress stays untouched until you regenerate the cards.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Re-extract'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    setState(() => _reprocessingPdf = true);
    try {
      await GuideImporter.reprocessPdfGuide(guide);
      await widget.store.update(guide);
      await widget.store.reindexGuide(guide);
      if (!mounted) return;
      setState(() {});
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('Updated extraction'),
          content: SizedBox(
            width: 680,
            height: MediaQuery.of(dialogContext).size.height * .58,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Review the cleaned text below. Regenerate the study cards when you want them to use this version.',
                ),
                const SizedBox(height: 10),
                const Divider(),
                Expanded(
                  child: SingleChildScrollView(
                    child: SelectableText(
                      guide.text,
                      style: const TextStyle(height: 1.45),
                    ),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Done'),
            ),
          ],
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not re-extract this PDF: $e')),
      );
    } finally {
      if (mounted) setState(() => _reprocessingPdf = false);
    }
  }

'''
s = s[:start] + regenerate + s[end:]

s = s.replace(
    "              if (value == 'export') _export();\n",
    "              if (value == 'export') _export();\n"
    "              if (value == 'reextract') _reprocessPdf();\n",
    1,
)

menu_marker = "              const PopupMenuItem(value: 'delete'"
menu_index = s.find(menu_marker)
if menu_index >= 0 and "value: 'reextract'" not in s[:menu_index]:
    menu = """              PopupMenuItem(
                value: 'reextract',
                enabled: guide.sourceType.toLowerCase() == 'pdf' && guide.hasFile,
                child: const Text('Re-extract PDF with Smart Extractor'),
              ),
"""
    s = s[:menu_index] + menu + s[menu_index:]

# Add a visible re-extract button after the source/export area.
if "'Re-extract PDF with Smart Extractor'" not in s[s.find("body: ListView"):]:
    source_card_end = s.find("          const SizedBox(height: 12),", s.find("body: ListView"))
    if source_card_end >= 0:
        ui = """          if (guide.sourceType.toLowerCase() == 'pdf' && guide.hasFile) ...[
            OutlinedButton.icon(
              onPressed: _reprocessingPdf ? null : _reprocessPdf,
              icon: _reprocessingPdf
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.document_scanner_outlined),
              label: Text(
                _reprocessingPdf
                    ? 'Re-extracting PDF…'
                    : 'Re-extract PDF with Smart Extractor',
              ),
            ),
            const SizedBox(height: 12),
          ],
"""
        s = s[:source_card_end] + ui + s[source_card_end:]

p.write_text(s)

# ---------------------------------------------------------------------------
# Library import preview before committing the guide.
# ---------------------------------------------------------------------------
p = Path('lib/home_page.dart')
s = p.read_text()
start = s.find("  Future<void> _importFile() async {")
end = s.find("  Future<void> _importImage(", start)
if end < 0:
    end = s.find("  Future<void> _pasteText()", start)
if start < 0 or end < 0:
    raise SystemExit('v175 Home import anchor missing')

home_import = r'''  Future<void> _importFile() async {
    setState(() => _busy = true);
    StudyGuide? guide;
    try {
      guide = await GuideImporter.pickAndBuild();
      if (guide == null || !mounted) return;

      setState(() => _busy = false);
      final confirmed = await _previewImportedGuide(guide);
      if (confirmed != true) {
        await GuideImporter.deleteStoredSource(guide);
        return;
      }

      setState(() => _busy = true);
      await widget.store.add(guide);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Imported ${guide.title}. Open it and tap Generate study cards when ready.',
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not import the guide: $e')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<bool?> _previewImportedGuide(StudyGuide guide) {
    final pageCount = guide.sourceBlocks.fold<int>(
      0,
      (maxPage, block) => block.page > maxPage ? block.page : maxPage,
    );
    return showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Review extracted content'),
        content: SizedBox(
          width: 680,
          height: MediaQuery.of(dialogContext).size.height * .65,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                pageCount > 0
                    ? '$pageCount pages • ${guide.text.length} characters'
                    : '${guide.text.length} characters extracted',
              ),
              const SizedBox(height: 8),
              const Text(
                'Check titles, paragraphs, formulas and tables before adding this guide.',
              ),
              const Divider(),
              Expanded(
                child: SingleChildScrollView(
                  child: SelectableText(
                    guide.text,
                    style: const TextStyle(height: 1.45),
                  ),
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
          FilledButton.icon(
            onPressed: () => Navigator.pop(dialogContext, true),
            icon: const Icon(Icons.library_add_rounded),
            label: const Text('Add to Library'),
          ),
        ],
      ),
    );
  }

'''
s = s[:start] + home_import + s[end:]
p.write_text(s)

# ---------------------------------------------------------------------------
# Review UI: source provenance button.
# ---------------------------------------------------------------------------
p = Path('lib/review_page.dart')
s = p.read_text()

method_anchor = "  Future<void> _rate(int quality) async {\n"
source_method = r'''  void _showCardSource() {
    final card = _card;
    final excerpt = card.sourceExcerpt.trim();
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Card source'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              if (card.page != null)
                Text(
                  'Page ${card.page}',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
              if (card.section.trim().isNotEmpty) ...[
                const SizedBox(height: 6),
                Text(card.section),
              ],
              if (excerpt.isNotEmpty) ...[
                const SizedBox(height: 14),
                const Divider(),
                SelectableText(excerpt),
              ],
            ],
          ),
        ),
        actions: [
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

'''
if method_anchor not in s:
    raise SystemExit('v175 Review source method anchor missing')
s = s.replace(method_anchor, source_method + method_anchor, 1)

# Prefer clean section/page label over a fragment-like source chip.
s = s.replace(
    "              if (_card.source.isNotEmpty)\n",
    "              if (_card.section.isNotEmpty || _card.source.isNotEmpty || _card.page != null)\n",
    1,
)
s = s.replace(
    "child: Chip(label: Text(_card.source, maxLines: 1, overflow: TextOverflow.ellipsis)),",
    "child: Chip(\n"
    "                    label: Text(\n"
    "                      [\n"
    "                        if (_card.page != null) 'Page ${_card.page}',\n"
    "                        if (_card.section.trim().isNotEmpty) _card.section.trim()\n"
    "                        else if (_card.source.trim().isNotEmpty) _card.source.trim(),\n"
    "                      ].join(' • '),\n"
    "                      maxLines: 1,\n"
    "                      overflow: TextOverflow.ellipsis,\n"
    "                    ),\n"
    "                  ),",
    1,
)

answer_anchor = """                                Text(
                                  _card.answer,
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(fontSize: 19, height: 1.4),
                                ),
"""
answer_extra = answer_anchor + """                                if (_card.page != null ||
                                    _card.sourceExcerpt.trim().isNotEmpty) ...[
                                  const SizedBox(height: 14),
                                  TextButton.icon(
                                    onPressed: _showCardSource,
                                    icon: const Icon(Icons.find_in_page_outlined),
                                    label: const Text('View source'),
                                  ),
                                ],
"""
if answer_anchor not in s:
    raise SystemExit('v175 Review answer anchor missing')
s = s.replace(answer_anchor, answer_extra, 1)
p.write_text(s)

print('v175 applied: provenance cards, coverage, semantic dedupe, preview/reprocess UI')
