import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:excel/excel.dart';
import 'package:file_picker/file_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:pdfrx/pdfrx.dart';
import 'package:xml/xml.dart';

import 'models.dart';
import 'study_engine.dart';

class GuideImporter {
  static const supportedExtensions = ['pdf', 'docx', 'txt', 'md', 'xlsx', 'xls'];

  static Future<StudyGuide?> pickAndBuild() async {
    final file = await FilePicker.pickFile(
      type: FileType.custom,
      allowedExtensions: supportedExtensions,
      dialogTitle: 'Escoge una guía o base de conocimiento',
    );
    if (file == null) return null;
    final bytes = await file.readAsBytes();
    if (bytes.isEmpty) {
      throw const FormatException('El archivo está vacío.');
    }
    final extension = (file.extension ?? _extensionOf(file.name)).toLowerCase();
    final text = await extractText(bytes, extension, file.name);
    if (text.trim().length < 20) {
      throw const FormatException(
        'No pude extraer suficiente contenido. Si es un PDF escaneado como imagen, necesitará OCR.',
      );
    }
    final storedPath = await _storeSource(bytes, file.name);
    final title = _titleFromFilename(file.name);
    return StudyEngine.buildGuide(
      title: title,
      sourceType: extension,
      sourceName: file.name,
      text: text,
      filePath: storedPath,
    );
  }

  static Future<String> extractText(
    Uint8List bytes,
    String extension,
    String sourceName,
  ) async {
    switch (extension.toLowerCase()) {
      case 'txt':
      case 'md':
        return utf8.decode(bytes, allowMalformed: true);
      case 'docx':
        return _extractDocx(bytes);
      case 'pdf':
        return _extractPdf(bytes, sourceName);
      case 'xlsx':
      case 'xls':
        return _extractExcel(bytes);
      default:
        throw FormatException('Formato .$extension no compatible todavía.');
    }
  }

  static String _extractExcel(Uint8List bytes) {
    final workbook = Excel.decodeBytes(bytes);
    final buffer = StringBuffer();
    for (final sheetName in workbook.tables.keys) {
      final sheet = workbook.tables[sheetName];
      if (sheet == null) continue;
      buffer.writeln('HOJA: $sheetName');
      for (final row in sheet.rows) {
        final values = row
            .map((cell) => cell?.value?.toString().trim() ?? '')
            .toList();
        if (values.every((value) => value.isEmpty)) continue;
        buffer.writeln(values.join(' | '));
      }
      buffer.writeln();
    }
    return buffer.toString().trim();
  }

  static String _extractDocx(Uint8List bytes) {
    final archive = ZipDecoder().decodeBytes(bytes);
    final entry = archive.findFile('word/document.xml');
    final content = entry?.readBytes();
    if (content == null) {
      throw const FormatException('El DOCX no contiene un documento de Word válido.');
    }
    final document = XmlDocument.parse(utf8.decode(content, allowMalformed: true));
    final paragraphs = document.descendants
        .whereType<XmlElement>()
        .where((node) => node.name.local == 'p')
        .map((paragraph) {
          return paragraph.descendants
              .whereType<XmlElement>()
              .where((node) => node.name.local == 't')
              .map((node) => node.innerText)
              .join();
        })
        .map((text) => text.trim())
        .where((text) => text.isNotEmpty)
        .toList();
    return paragraphs.join('\n');
  }

  static Future<String> _extractPdf(Uint8List bytes, String sourceName) async {
    final document = await PdfDocument.openData(bytes, sourceName: sourceName);
    final buffer = StringBuffer();
    try {
      for (final page in document.pages) {
        final rawText = await page.loadText();
        final pageText = rawText?.fullText.trim() ?? '';
        if (pageText.isNotEmpty) {
          buffer.writeln(pageText);
          buffer.writeln();
        }
      }
    } finally {
      await document.dispose();
    }
    return buffer.toString();
  }

  static Future<String> _storeSource(Uint8List bytes, String originalName) async {
    final root = await getApplicationDocumentsDirectory();
    final directory = Directory('${root.path}/guide_files');
    await directory.create(recursive: true);
    final safe = originalName
        .replaceAll(RegExp(r'[^A-Za-z0-9._-]+'), '_')
        .replaceAll(RegExp(r'_+'), '_');
    final filename = '${DateTime.now().microsecondsSinceEpoch}_$safe';
    final stored = File('${directory.path}/$filename');
    await stored.writeAsBytes(bytes, flush: true);
    return stored.path;
  }

  static String _extensionOf(String filename) {
    final dot = filename.lastIndexOf('.');
    return dot < 0 ? '' : filename.substring(dot + 1);
  }

  static String _titleFromFilename(String filename) {
    final dot = filename.lastIndexOf('.');
    final raw = dot > 0 ? filename.substring(0, dot) : filename;
    return raw.replaceAll(RegExp(r'[_-]+'), ' ').trim();
  }
}
