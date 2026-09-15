import 'dart:io';

import 'package:excel/excel.dart';
import 'package:flutter_file_dialog/flutter_file_dialog.dart';
import 'package:path_provider/path_provider.dart';
import 'package:pdf/widgets.dart' as pw;

import 'models.dart';

class GuideFileService {
  static Future<Directory> _outputDirectory() async {
    final root = await getApplicationDocumentsDirectory();
    final directory = Directory('${root.path}/generated_guides');
    await directory.create(recursive: true);
    return directory;
  }

  static String _safeName(String title) {
    final cleaned = title
        .trim()
        .replaceAll(RegExp(r'[^A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ._ -]+'), '')
        .replaceAll(RegExp(r'[\s_-]+'), '_');
    return cleaned.isEmpty ? 'guia_memora' : cleaned;
  }

  static String _pdfSafe(String text) {
    return text
        .replaceAll('—', '-')
        .replaceAll('–', '-')
        .replaceAll('“', '"')
        .replaceAll('”', '"')
        .replaceAll('’', "'")
        .replaceAll(RegExp(r'[^\x09\x0A\x0D\x20-\xFF]'), '');
  }

  static Future<String> createPdf({
    required String title,
    required String content,
  }) async {
    final directory = await _outputDirectory();
    final name = '${DateTime.now().millisecondsSinceEpoch}_${_safeName(title)}.pdf';
    final path = '${directory.path}/$name';
    final document = pw.Document();
    final safeTitle = _pdfSafe(title);
    final safeContent = _pdfSafe(content);

    document.addPage(
      pw.MultiPage(
        margin: const pw.EdgeInsets.all(36),
        build: (context) => [
          pw.Text(
            safeTitle,
            style: pw.TextStyle(fontSize: 22, fontWeight: pw.FontWeight.bold),
          ),
          pw.SizedBox(height: 16),
          ...safeContent.split(RegExp(r'\n{2,}')).map(
                (paragraph) => pw.Padding(
                  padding: const pw.EdgeInsets.only(bottom: 10),
                  child: pw.Text(paragraph.trim(), style: const pw.TextStyle(fontSize: 11)),
                ),
              ),
        ],
      ),
    );
    await File(path).writeAsBytes(await document.save(), flush: true);
    return path;
  }

  static List<List<String>> parseTable(String content) {
    final rows = <List<String>>[];
    for (final raw in content.replaceAll('\r', '').split('\n')) {
      var line = raw.trim();
      if (line.isEmpty || line.startsWith('```')) continue;
      if (line.startsWith('|') && line.endsWith('|')) {
        line = line.substring(1, line.length - 1);
      }
      List<String> cells;
      if (line.contains('\t')) {
        cells = line.split('\t');
      } else if (line.contains('|')) {
        cells = line.split('|');
      } else {
        cells = [line];
      }
      cells = cells.map((e) => e.trim()).toList();
      final separator = cells.every((e) => RegExp(r'^:?-{2,}:?$').hasMatch(e));
      if (!separator && cells.any((e) => e.isNotEmpty)) rows.add(cells);
    }
    if (rows.isEmpty) {
      rows.add(['Contenido']);
      rows.add([content.trim()]);
    }
    return rows;
  }

  static Future<String> createExcel({
    required String title,
    required String tableContent,
  }) async {
    final directory = await _outputDirectory();
    final name = '${DateTime.now().millisecondsSinceEpoch}_${_safeName(title)}.xlsx';
    final path = '${directory.path}/$name';
    final workbook = Excel.createExcel();
    const sheetName = 'Guia';
    final sheet = workbook[sheetName];
    final rows = parseTable(tableContent);
    for (final row in rows) {
      sheet.appendRow(row.map((value) => TextCellValue(value)).toList());
    }
    if (workbook.tables.containsKey('Sheet1') && workbook.tables.length > 1) {
      workbook.delete('Sheet1');
    }
    workbook.setDefaultSheet(sheetName);
    for (var i = 0; i < 6; i++) {
      sheet.setColumnWidth(i, 28);
    }
    final bytes = workbook.save();
    if (bytes == null) throw Exception('No se pudo crear el archivo Excel.');
    await File(path).writeAsBytes(bytes, flush: true);
    return path;
  }

  static Future<String?> exportGuideFile(StudyGuide guide) async {
    final path = guide.filePath;
    if (path == null || path.isEmpty || !File(path).existsSync()) {
      throw Exception('Esta guía no tiene un archivo guardado para exportar.');
    }
    return FlutterFileDialog.saveFile(
      params: SaveFileDialogParams(
        sourceFilePath: path,
        fileName: guide.sourceName.isEmpty
            ? '${_safeName(guide.title)}.${guide.sourceType}'
            : guide.sourceName,
        mimeTypesFilter: const ['application/octet-stream'],
        localOnly: true,
      ),
    );
  }
}
