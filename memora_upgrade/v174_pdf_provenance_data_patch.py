from pathlib import Path
import re

# v174: structured PDF provenance + reprocessing support.

p = Path('lib/models.dart')
s = p.read_text()

if 'class GuideSourceBlock {' not in s:
    s = r'''class GuideSourceBlock {
  const GuideSourceBlock({
    required this.page,
    required this.text,
    this.section = '',
  });

  final int page;
  final String text;
  final String section;

  Map<String, dynamic> toJson() => {
        'page': page,
        'text': text,
        'section': section,
      };

  factory GuideSourceBlock.fromJson(Map<String, dynamic> json) =>
      GuideSourceBlock(
        page: (json['page'] as num?)?.toInt() ?? 0,
        text: json['text']?.toString() ?? '',
        section: json['section']?.toString() ?? '',
      );
}

''' + s

s = s.replace(
    "    this.streak = 0,\n  });",
    "    this.streak = 0,\n"
    "    this.page,\n"
    "    this.section = '',\n"
    "    this.sourceExcerpt = '',\n"
    "  });",
    1,
)
s = s.replace(
    "  int streak;\n\n  bool get isDue",
    "  int streak;\n"
    "  final int? page;\n"
    "  final String section;\n"
    "  final String sourceExcerpt;\n\n"
    "  bool get isDue",
    1,
)
s = s.replace(
    "        'streak': streak,\n      };",
    "        'streak': streak,\n"
    "        'page': page,\n"
    "        'section': section,\n"
    "        'sourceExcerpt': sourceExcerpt,\n"
    "      };",
    1,
)
s = s.replace(
    "        streak: (json['streak'] as num?)?.toInt() ?? 0,\n      );",
    "        streak: (json['streak'] as num?)?.toInt() ?? 0,\n"
    "        page: (json['page'] as num?)?.toInt(),\n"
    "        section: json['section']?.toString() ?? '',\n"
    "        sourceExcerpt: json['sourceExcerpt']?.toString() ?? '',\n"
    "      );",
    1,
)

s = s.replace(
    "    this.lastStudiedAt,\n  });",
    "    this.lastStudiedAt,\n"
    "    this.sourceBlocks = const [],\n"
    "    this.extractionVersion = 1,\n"
    "  });",
    1,
)
s = s.replace("  final String text;\n", "  String text;\n", 1)
s = s.replace(
    "  DateTime? lastStudiedAt;\n\n  bool get hasFile",
    "  DateTime? lastStudiedAt;\n"
    "  List<GuideSourceBlock> sourceBlocks;\n"
    "  int extractionVersion;\n\n"
    "  bool get hasFile",
    1,
)
s = s.replace(
    "        'lastStudiedAt': lastStudiedAt?.toIso8601String(),\n      };",
    "        'lastStudiedAt': lastStudiedAt?.toIso8601String(),\n"
    "        'sourceBlocks': sourceBlocks.map((block) => block.toJson()).toList(),\n"
    "        'extractionVersion': extractionVersion,\n"
    "      };",
    1,
)
s = s.replace(
    "        lastStudiedAt: json['lastStudiedAt'] == null\n"
    "            ? null\n"
    "            : DateTime.tryParse(json['lastStudiedAt'] as String),\n"
    "      );",
    "        lastStudiedAt: json['lastStudiedAt'] == null\n"
    "            ? null\n"
    "            : DateTime.tryParse(json['lastStudiedAt'] as String),\n"
    "        sourceBlocks: ((json['sourceBlocks'] as List<dynamic>?) ?? const [])\n"
    "            .map((item) => GuideSourceBlock.fromJson(\n"
    "                  Map<String, dynamic>.from(item as Map),\n"
    "                ))\n"
    "            .toList(),\n"
    "        extractionVersion: (json['extractionVersion'] as num?)?.toInt() ?? 1,\n"
    "      );",
    1,
)
p.write_text(s)

p = Path('lib/guide_importer.dart')
s = p.read_text()

if 'class SmartPdfExtraction {' not in s:
    s = s.replace(
        'class GuideImporter {\n',
        r'''class SmartPdfExtraction {
  const SmartPdfExtraction({
    required this.text,
    required this.blocks,
    required this.pageCount,
  });

  final String text;
  final List<GuideSourceBlock> blocks;
  final int pageCount;
}

class GuideImporter {
''',
        1,
    )

old = """    final extension = (file.extension ?? _extensionOf(file.name)).toLowerCase();
    final text = await extractText(bytes, extension, file.name);
    if (text.trim().length < 20) {
"""
new = """    final extension = (file.extension ?? _extensionOf(file.name)).toLowerCase();
    SmartPdfExtraction? pdfExtraction;
    final text = extension == 'pdf'
        ? (pdfExtraction = await extractPdfDetailed(bytes, file.name)).text
        : await extractText(bytes, extension, file.name);
    if (text.trim().length < 20) {
"""
if old not in s:
    raise SystemExit('v174 pickAndBuild extraction anchor missing')
s = s.replace(old, new, 1)

old = """    return StudyEngine.buildGuide(
      title: title,
      sourceType: extension,
      sourceName: file.name,
      text: text,
      filePath: storedPath,
    );
"""
new = """    final guide = StudyEngine.buildGuide(
      title: title,
      sourceType: extension,
      sourceName: file.name,
      text: text,
      filePath: storedPath,
    );
    if (pdfExtraction != null) {
      guide.sourceBlocks = pdfExtraction.blocks;
      guide.extractionVersion = 2;
    }
    return guide;
"""
if old not in s:
    raise SystemExit('v174 buildGuide anchor missing')
s = s.replace(old, new, 1)

start = s.find("  static Future<String> _extractPdf(Uint8List bytes, String sourceName) async {")
end = s.find("  static List<String> _structuredPdfLines(", start)
if start < 0 or end < 0:
    raise SystemExit('v174 smart PDF detail anchor missing')

detailed = r'''  static Future<String> _extractPdf(
    Uint8List bytes,
    String sourceName,
  ) async {
    return (await extractPdfDetailed(bytes, sourceName)).text;
  }

  static Future<SmartPdfExtraction> extractPdfDetailed(
    Uint8List bytes,
    String sourceName,
  ) async {
    final document = await PdfDocument.openData(bytes, sourceName: sourceName);
    final pages = <List<String>>[];
    TextRecognizer? recognizer;

    try {
      for (var pageIndex = 0; pageIndex < document.pages.length; pageIndex++) {
        final page = document.pages[pageIndex];
        List<String> best = const [];
        var bestScore = 0.0;

        try {
          final structured = await page.loadStructuredText();
          final lines = _structuredPdfLines(structured, page.width);
          final score = _pdfQuality(lines.join('\n'));
          if (lines.isNotEmpty) {
            best = lines;
            bestScore = score;
          }
        } catch (_) {}

        try {
          final raw = await page.loadText();
          final lines = _rawPdfLines(raw?.fullText ?? '');
          final score = _pdfQuality(lines.join('\n'));
          if (lines.isNotEmpty && (best.isEmpty || score > bestScore + 0.12)) {
            best = lines;
            bestScore = score;
          }
        } catch (_) {}

        final currentWords = _pdfWordCount(best.join(' '));
        if (best.isEmpty || currentWords < 8 || bestScore < 0.43) {
          try {
            recognizer ??= TextRecognizer(script: TextRecognitionScript.latin);
            final lines = await _ocrPdfPage(page, recognizer, pageIndex);
            final score = _pdfQuality(lines.join('\n'));
            if (lines.isNotEmpty &&
                (best.isEmpty || currentWords < 8 || score > bestScore + 0.04)) {
              best = lines;
              bestScore = score;
            }
          } catch (_) {}
        }
        pages.add(best);
      }
    } finally {
      if (recognizer != null) await recognizer.close();
      await document.dispose();
    }

    final cleaned = _removePdfFurniture(pages);
    final blocks = <GuideSourceBlock>[];
    final out = StringBuffer();
    var currentSection = '';

    for (var pageIndex = 0; pageIndex < cleaned.length; pageIndex++) {
      final logical = _mergePdfLines(cleaned[pageIndex]);
      for (final rawLine in logical) {
        final line = _normalizePdfTableRow(rawLine);
        if (line.isEmpty) continue;
        if (_pdfHeadingLike(line) && !_formulaLike(line)) {
          currentSection = line.replaceAll(RegExp(r'[:\s]+$'), '').trim();
        }
        out.writeln(line);
        blocks.add(
          GuideSourceBlock(
            page: pageIndex + 1,
            text: line,
            section: currentSection,
          ),
        );
      }
      if (logical.isNotEmpty) out.writeln();
    }

    return SmartPdfExtraction(
      text: out.toString().trim(),
      blocks: blocks,
      pageCount: cleaned.length,
    );
  }

  static String _normalizePdfTableRow(String line) {
    final clean = _cleanPdfLine(line);
    if (!clean.contains(' | ')) return clean;
    return clean
        .split('|')
        .map((cell) => cell.trim())
        .where((cell) => cell.isNotEmpty)
        .join(' | ');
  }

  static Future<void> reprocessPdfGuide(StudyGuide guide) async {
    if (guide.sourceType.toLowerCase() != 'pdf' ||
        guide.filePath == null ||
        guide.filePath!.trim().isEmpty) {
      throw const FormatException('This guide has no original PDF to reprocess.');
    }
    final file = File(guide.filePath!);
    if (!await file.exists()) {
      throw const FileSystemException('The original PDF is no longer available.');
    }
    final extraction = await extractPdfDetailed(
      await file.readAsBytes(),
      guide.sourceName,
    );
    if (extraction.text.trim().length < 20) {
      throw const FormatException('Not enough text could be recovered from the PDF.');
    }
    guide.text = extraction.text;
    guide.sourceBlocks = extraction.blocks;
    guide.extractionVersion = 2;
    guide.summary = StudyEngine.buildSummary(extraction.text);
  }

  static Future<void> deleteStoredSource(StudyGuide guide) async {
    final path = guide.filePath;
    if (path == null || path.trim().isEmpty) return;
    try {
      final file = File(path);
      if (await file.exists()) await file.delete();
    } catch (_) {}
  }

'''
s = s[:start] + detailed + s[end:]

needle = "    if (group.isNotEmpty) groups.add(group);\n    return groups.map(_PdfVisualLine.fromPieces).toList();\n"
replacement = """    if (group.isNotEmpty) groups.add(group);
    if (groups.length >= 3) {
      return [_PdfVisualLine.fromTableGroups(groups)];
    }
    return groups.map(_PdfVisualLine.fromPieces).toList();
"""
if needle not in s:
    raise SystemExit('v174 PDF table groups anchor missing')
s = s.replace(needle, replacement, 1)

factory_anchor = "  factory _PdfVisualLine.fromPieces(List<_PdfPiece> pieces) {\n"
table_factory = r'''  factory _PdfVisualLine.fromTableGroups(
    List<List<_PdfPiece>> groups,
  ) {
    final lines = groups.map(_PdfVisualLine.fromPieces).toList();
    double minOf(Iterable<double> values) =>
        values.reduce((a, b) => a < b ? a : b);
    double maxOf(Iterable<double> values) =>
        values.reduce((a, b) => a > b ? a : b);
    return _PdfVisualLine(
      lines.map((line) => line.text).where((text) => text.isNotEmpty).join(' | '),
      minOf(lines.map((line) => line.left)),
      maxOf(lines.map((line) => line.right)),
      maxOf(lines.map((line) => line.top)),
      minOf(lines.map((line) => line.bottom)),
    );
  }

'''
if factory_anchor not in s:
    raise SystemExit('v174 PDF table factory anchor missing')
s = s.replace(factory_anchor, table_factory + factory_anchor, 1)

store_anchor = "\n  static Future<String> _storeSource("
test_helpers = r'''
  static List<String> debugMergePdfLines(List<String> lines) =>
      _mergePdfLines(lines);

  static List<List<String>> debugRemovePdfFurniture(
    List<List<String>> pages,
  ) =>
      _removePdfFurniture(pages);

  static double debugPdfQuality(String text) => _pdfQuality(text);

'''
if store_anchor not in s:
    raise SystemExit('v174 importer helper anchor missing')
s = s.replace(store_anchor, test_helpers + store_anchor, 1)
p.write_text(s)

p = Path('lib/guide_store.dart')
s = p.read_text()
anchor = "  Future<void> remove(String id) async {\n"
method = r'''  Future<void> reindexGuide(StudyGuide guide) async {
    try {
      await VectorKnowledgeStore.deleteGuide(guide.id);
      await VectorKnowledgeStore.ensureIndexed(guide);
    } catch (_) {
      // The guide remains usable without embeddings. It will index later.
    }
  }

'''
if 'Future<void> reindexGuide(' not in s:
    if anchor not in s:
        raise SystemExit('v174 GuideStore reindex anchor missing')
    s = s.replace(anchor, method + anchor, 1)
p.write_text(s)

print('v174 applied: PDF source blocks, tables, reprocessing and reindex support')
