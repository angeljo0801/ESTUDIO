from pathlib import Path

# v173: Smart PDF Extractor.
# Rebuild visual reading order from PDF coordinates, clean repeated page
# furniture, join wrapped formulas/prose, and use OCR only for damaged/scanned pages.

p = Path('pubspec.yaml')
s = p.read_text()
if "  image: ^4.5.4\n" not in s:
    anchor = "  image_picker: ^1.2.3\n"
    if anchor not in s:
        raise SystemExit('v173 pubspec image_picker anchor missing')
    s = s.replace(anchor, anchor + "  image: ^4.5.4\n", 1)
p.write_text(s)

p = Path('lib/guide_importer.dart')
s = p.read_text()

if "package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart" not in s:
    s = s.replace(
        "import 'package:file_picker/file_picker.dart';\n",
        "import 'package:file_picker/file_picker.dart';\n"
        "import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';\n"
        "import 'package:image/image.dart' as img;\n",
        1,
    )

start = s.find("  static Future<String> _extractPdf(Uint8List bytes, String sourceName) async {")
end = s.find("  static Future<String> _storeSource(", start)
if start < 0 or end < 0:
    raise SystemExit('v173 PDF extractor anchor missing')

replacement = r'''  static Future<String> _extractPdf(Uint8List bytes, String sourceName) async {
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
          } catch (_) {
            // OCR failure does not block import.
          }
        }
        pages.add(best);
      }
    } finally {
      if (recognizer != null) await recognizer.close();
      await document.dispose();
    }

    final cleaned = _removePdfFurniture(pages);
    final out = StringBuffer();
    for (final page in cleaned) {
      final lines = _mergePdfLines(page);
      for (final line in lines) {
        out.writeln(line);
      }
      if (lines.isNotEmpty) out.writeln();
    }
    return out.toString().trim();
  }

  static List<String> _structuredPdfLines(PdfPageText text, double pageWidth) {
    final pieces = <_PdfPiece>[];
    for (final fragment in text.fragments) {
      final value = _cleanPdfLine(fragment.text);
      final b = fragment.bounds;
      if (value.isEmpty || b.width <= 0 || b.height <= 0) continue;
      pieces.add(_PdfPiece(value, b.left, b.right, b.top, b.bottom));
    }
    if (pieces.isEmpty) return _rawPdfLines(text.fullText);

    pieces.sort((a, b) {
      final y = b.cy.compareTo(a.cy);
      return y != 0 ? y : a.left.compareTo(b.left);
    });

    final rows = <_PdfRow>[];
    for (final piece in pieces) {
      _PdfRow? match;
      var distance = double.infinity;
      for (final row in rows) {
        final tolerance =
            (piece.height > row.avgHeight ? piece.height : row.avgHeight) * 0.58;
        final d = (piece.cy - row.cy).abs();
        if (d <= tolerance.clamp(2.0, 8.0) && d < distance) {
          match = row;
          distance = d;
        }
      }
      if (match == null) {
        rows.add(_PdfRow(piece));
      } else {
        match.add(piece);
      }
    }

    final visual = <_PdfVisualLine>[];
    for (final row in rows) {
      visual.addAll(row.segments(pageWidth));
    }
    return _orderPdfColumns(visual, pageWidth)
        .map((line) => _cleanPdfLine(line.text))
        .where((line) => line.isNotEmpty)
        .toList();
  }

  static List<_PdfVisualLine> _orderPdfColumns(
    List<_PdfVisualLine> source,
    double pageWidth,
  ) {
    final visual = List<_PdfVisualLine>.of(source)
      ..sort((a, b) {
        final y = b.cy.compareTo(a.cy);
        return y != 0 ? y : a.left.compareTo(b.left);
      });
    if (pageWidth <= 0 || visual.length < 8) return visual;

    final mid = pageWidth / 2;
    final margin = pageWidth * 0.07;
    final left = <_PdfVisualLine>[];
    final right = <_PdfVisualLine>[];
    final spanning = <_PdfVisualLine>[];

    for (final line in visual) {
      if (line.right <= mid + margin && line.cx < mid - pageWidth * 0.04) {
        left.add(line);
      } else if (line.left >= mid - margin &&
          line.cx > mid + pageWidth * 0.04) {
        right.add(line);
      } else {
        spanning.add(line);
      }
    }

    final evidence = left.length + right.length;
    final isTwoColumn = left.length >= 3 &&
        right.length >= 3 &&
        evidence >= (visual.length * 0.52).ceil();
    if (!isTwoColumn) return visual;

    spanning.sort((a, b) => b.cy.compareTo(a.cy));
    final result = <_PdfVisualLine>[];
    var upper = double.infinity;

    void band(double lower) {
      final l = left.where((x) => x.cy < upper && x.cy > lower).toList()
        ..sort((a, b) => b.cy.compareTo(a.cy));
      final r = right.where((x) => x.cy < upper && x.cy > lower).toList()
        ..sort((a, b) => b.cy.compareTo(a.cy));
      result
        ..addAll(l)
        ..addAll(r);
    }

    for (final anchor in spanning) {
      band(anchor.cy);
      result.add(anchor);
      upper = anchor.cy;
    }
    band(-double.infinity);
    return result.length == visual.length ? result : visual;
  }

  static List<String> _rawPdfLines(String raw) {
    if (raw.trim().isEmpty) return const [];
    return raw
        .replaceAll('\r', '\n')
        .split('\n')
        .map(_cleanPdfLine)
        .where((line) => line.isNotEmpty)
        .toList();
  }

  static String _cleanPdfLine(String value) => value
      .replaceAll('\u00ad', '')
      .replaceAll('\ufb00', 'ff')
      .replaceAll('\ufb01', 'fi')
      .replaceAll('\ufb02', 'fl')
      .replaceAll('\ufb03', 'ffi')
      .replaceAll('\ufb04', 'ffl')
      .replaceAll(RegExp(r'[\t ]+'), ' ')
      .replaceAll(RegExp(r'\s*\n\s*'), ' ')
      .trim();

  static List<List<String>> _removePdfFurniture(List<List<String>> pages) {
    if (pages.length < 3) {
      return pages.map((p) => p.where((x) => !_isPageNumber(x)).toList()).toList();
    }

    final counts = <String, int>{};
    for (final page in pages) {
      final edge = <String>[...page.take(2), ...page.reversed.take(2)];
      final seen = <String>{};
      for (final line in edge) {
        final key = _pdfFurnitureKey(line);
        if (key.length < 3 || key.length > 100 || !seen.add(key)) continue;
        counts[key] = (counts[key] ?? 0) + 1;
      }
    }

    final threshold = (pages.length * 0.45).ceil().clamp(2, pages.length);
    final repeated = counts.entries
        .where((e) => e.value >= threshold)
        .map((e) => e.key)
        .toSet();

    return pages.map((page) {
      final result = <String>[];
      for (var i = 0; i < page.length; i++) {
        final line = page[i];
        final edge = i < 2 || i >= page.length - 2;
        if (_isPageNumber(line)) continue;
        if (edge && repeated.contains(_pdfFurnitureKey(line))) continue;
        result.add(line);
      }
      return result;
    }).toList();
  }

  static bool _isPageNumber(String line) => RegExp(
        r'^(?:page\s+)?\d{1,4}(?:\s*(?:/|of)\s*\d{1,4})?$',
        caseSensitive: false,
      ).hasMatch(line.trim());

  static String _pdfFurnitureKey(String line) => line
      .toLowerCase()
      .replaceAll(RegExp(r'\d+'), '#')
      .replaceAll(RegExp(r'[^a-záéíóúüñ# ]+'), ' ')
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim();

  static List<String> _mergePdfLines(List<String> lines) {
    final result = <String>[];
    for (final raw in lines) {
      final current = _cleanPdfLine(raw);
      if (current.isEmpty) continue;
      if (result.isEmpty) {
        result.add(current);
        continue;
      }

      final previous = result.last;
      if (_joinPdfLine(previous, current)) {
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

  static bool _joinPdfLine(String previous, String current) {
    final a = previous.trim();
    final b = current.trim();
    if (a.isEmpty || b.isEmpty) return false;
    if (_unclosedPdfDelimiters(a) > 0) return true;
    if (RegExp(r'[=+\-×÷/*,(\\[]$').hasMatch(a)) return true;
    if (RegExp(r'^[=+×÷/*,\])]').hasMatch(b)) return true;

    final formulaA = _formulaLike(a);
    final formulaB = _formulaLike(b);
    if ((formulaA || formulaB) &&
        !RegExp(r'[.!?;:]$').hasMatch(a) &&
        (a.contains('=') || b.contains('=') || formulaA && formulaB)) {
      return true;
    }

    if (a.endsWith('-') && RegExp(r'^[a-záéíóúüñ]').hasMatch(b)) return true;

    if (!RegExp(r'[.!?;:]$').hasMatch(a)) {
      if (RegExp(r'^[a-záéíóúüñ]').hasMatch(b)) return true;
      if (a.endsWith(',') || a.endsWith('—') || a.endsWith('–')) return true;
      if (_pdfWordCount(a) >= 7 &&
          _pdfWordCount(b) >= 4 &&
          !_pdfHeadingLike(a) &&
          !_pdfHeadingLike(b)) {
        return true;
      }
    }
    return false;
  }

  static int _unclosedPdfDelimiters(String text) {
    var balance = 0;
    for (final rune in text.runes) {
      final c = String.fromCharCode(rune);
      if (c == '(' || c == '[' || c == '{') balance++;
      if (c == ')' || c == ']' || c == '}') balance--;
    }
    return balance;
  }

  static bool _formulaLike(String line) {
    if (line.contains('=')) return true;
    final operators = RegExp(r'[+\-×÷/*=]').allMatches(line).length;
    final digits = RegExp(r'\d').allMatches(line).length;
    return operators >= 2 && (digits >= 1 || _pdfWordCount(line) <= 8);
  }

  static bool _pdfHeadingLike(String line) {
    final value = line.trim();
    if (value.length > 100 || RegExp(r'[.!?;]$').hasMatch(value)) return false;
    if (value.contains('=') || _formulaLike(value)) return false;
    final words = RegExp(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9'-]+")
        .allMatches(value)
        .map((m) => m.group(0)!)
        .toList();
    if (words.isEmpty || words.length > 12) return false;
    final title = words
        .where((w) => RegExp(r'^[A-ZÁÉÍÓÚÜÑ0-9]').hasMatch(w))
        .length;
    return title / words.length >= 0.55;
  }

  static int _pdfWordCount(String text) =>
      RegExp(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9'-]+").allMatches(text).length;

  static double _pdfQuality(String text) {
    final value = text.trim();
    if (value.isEmpty) return 0;
    final compact = value.replaceAll(RegExp(r'\s'), '');
    if (compact.isEmpty) return 0;
    final words = _pdfWordCount(value);
    final alnum = RegExp(r'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]')
        .allMatches(compact)
        .length;
    final replacement = RegExp(r'[�\u0000]').allMatches(value).length;
    final lines = value
        .split('\n')
        .map((x) => x.trim())
        .where((x) => x.isNotEmpty)
        .toList();
    final tiny = lines.where((x) => x.length <= 2).length;

    var score = alnum / compact.length;
    if (words < 8) score -= 0.28;
    if (replacement > 0) score -= (replacement * 0.03).clamp(0, 0.25);
    if (lines.isNotEmpty && tiny / lines.length > 0.25) score -= 0.12;
    return score.clamp(0.0, 1.0);
  }

  static Future<List<String>> _ocrPdfPage(
    PdfPage page,
    TextRecognizer recognizer,
    int pageIndex,
  ) async {
    const dpi = 170.0;
    const maxSide = 2400.0;
    var width = page.width * dpi / 72.0;
    var height = page.height * dpi / 72.0;
    final longest = width > height ? width : height;
    if (longest > maxSide) {
      final factor = maxSide / longest;
      width *= factor;
      height *= factor;
    }

    final rendered = await page.render(
      fullWidth: width,
      fullHeight: height,
      backgroundColor: 0xffffffff,
    );
    if (rendered == null) return const [];

    File? temp;
    try {
      final bitmap = img.Image.fromBytes(
        width: rendered.width,
        height: rendered.height,
        bytes: rendered.pixels.buffer,
        bytesOffset: rendered.pixels.offsetInBytes,
        order: img.ChannelOrder.bgra,
      );
      final dir = await getTemporaryDirectory();
      temp = File(
        dir.path +
            '/memora_pdf_ocr_' +
            DateTime.now().microsecondsSinceEpoch.toString() +
            '_' +
            pageIndex.toString() +
            '.jpg',
      );
      await temp.writeAsBytes(img.encodeJpg(bitmap, quality: 90), flush: true);

      final recognized =
          await recognizer.processImage(InputImage.fromFilePath(temp.path));
      final lines = <String>[];
      for (final block in recognized.blocks) {
        for (final line in block.lines) {
          final clean = _cleanPdfLine(line.text);
          if (clean.isNotEmpty) lines.add(clean);
        }
      }
      return lines.isEmpty ? _rawPdfLines(recognized.text) : lines;
    } finally {
      rendered.dispose();
      if (temp != null) {
        try {
          if (await temp.exists()) await temp.delete();
        } catch (_) {}
      }
    }
  }

'''

s = s[:start] + replacement + s[end:]

if "class _PdfPiece {" not in s:
    s += r'''

class _PdfPiece {
  const _PdfPiece(this.text, this.left, this.right, this.top, this.bottom);

  final String text;
  final double left;
  final double right;
  final double top;
  final double bottom;

  double get cy => (top + bottom) / 2;
  double get height => (top - bottom).abs();
}

class _PdfRow {
  _PdfRow(_PdfPiece first) {
    add(first);
  }

  final List<_PdfPiece> pieces = [];

  void add(_PdfPiece piece) => pieces.add(piece);

  double get cy => pieces.isEmpty
      ? 0
      : pieces.map((x) => x.cy).reduce((a, b) => a + b) / pieces.length;

  double get avgHeight => pieces.isEmpty
      ? 1
      : pieces.map((x) => x.height).reduce((a, b) => a + b) / pieces.length;

  List<_PdfVisualLine> segments(double pageWidth) {
    final ordered = List<_PdfPiece>.of(pieces)
      ..sort((a, b) => a.left.compareTo(b.left));
    if (ordered.isEmpty) return const [];

    final gapLimit = (pageWidth * 0.055).clamp(28.0, 52.0);
    final groups = <List<_PdfPiece>>[];
    var group = <_PdfPiece>[];

    for (final piece in ordered) {
      if (group.isNotEmpty && piece.left - group.last.right > gapLimit) {
        groups.add(group);
        group = <_PdfPiece>[];
      }
      group.add(piece);
    }
    if (group.isNotEmpty) groups.add(group);
    return groups.map(_PdfVisualLine.fromPieces).toList();
  }
}

class _PdfVisualLine {
  const _PdfVisualLine(
    this.text,
    this.left,
    this.right,
    this.top,
    this.bottom,
  );

  factory _PdfVisualLine.fromPieces(List<_PdfPiece> pieces) {
    final ordered = List<_PdfPiece>.of(pieces)
      ..sort((a, b) => a.left.compareTo(b.left));
    final buffer = StringBuffer();

    for (final piece in ordered) {
      final value = piece.text.trim();
      if (value.isEmpty) continue;
      if (buffer.isNotEmpty) {
        final previous = buffer.toString();
        final noSpaceBefore = RegExp(r'^[,.;:!?%)\]}]').hasMatch(value);
        final noSpaceAfter = RegExp(r'[(\[{/$]$').hasMatch(previous);
        if (!noSpaceBefore && !noSpaceAfter) buffer.write(' ');
      }
      buffer.write(value);
    }

    double minOf(Iterable<double> values) =>
        values.reduce((a, b) => a < b ? a : b);
    double maxOf(Iterable<double> values) =>
        values.reduce((a, b) => a > b ? a : b);

    return _PdfVisualLine(
      buffer.toString().replaceAll(RegExp(r'\s+'), ' ').trim(),
      minOf(ordered.map((x) => x.left)),
      maxOf(ordered.map((x) => x.right)),
      maxOf(ordered.map((x) => x.top)),
      minOf(ordered.map((x) => x.bottom)),
    );
  }

  final String text;
  final double left;
  final double right;
  final double top;
  final double bottom;

  double get cx => (left + right) / 2;
  double get cy => (top + bottom) / 2;
}
'''

p.write_text(s)
print('v173 applied: Smart PDF layout extraction + cleanup + OCR fallback')
