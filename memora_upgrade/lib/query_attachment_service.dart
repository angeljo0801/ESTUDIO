import 'dart:io';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';

import 'guide_importer.dart';
import 'models.dart';
import 'study_engine.dart';

class QueryAttachment {
  const QueryAttachment({
    required this.name,
    required this.path,
    required this.kind,
    required this.mimeType,
    required this.extractedText,
  });

  final String name;
  final String path;
  final String kind; // pdf | image
  final String mimeType;
  final String extractedText;

  bool get isImage => kind == 'image';
}

class QueryAttachmentService {
  static final ImagePicker _picker = ImagePicker();

  static Future<QueryAttachment?> pickPdf() async {
    final picked = await FilePicker.pickFile(
      type: FileType.custom,
      allowedExtensions: const ['pdf'],
      dialogTitle: 'Adjuntar PDF',
    );
    if (picked == null) return null;
    final bytes = await picked.readAsBytes();
    if (bytes.isEmpty) throw const FormatException('El PDF está vacío.');
    final path = picked.path ?? await _writeTemp(bytes, picked.name);
    final text = await GuideImporter.extractText(bytes, 'pdf', picked.name);
    return QueryAttachment(
      name: picked.name,
      path: path,
      kind: 'pdf',
      mimeType: 'application/pdf',
      extractedText: text.trim().isEmpty
          ? '[PDF ${picked.name}: no se pudo extraer texto; podría ser un PDF escaneado.]'
          : text.trim(),
    );
  }

  static Future<QueryAttachment?> pickImageFromGallery() async {
    final file = await _picker.pickImage(
      source: ImageSource.gallery,
      imageQuality: 95,
    );
    if (file == null) return null;
    return _imageAttachment(file);
  }

  static Future<QueryAttachment?> takePhoto() async {
    final file = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 92,
    );
    if (file == null) return null;
    return _imageAttachment(file);
  }

  static Future<QueryAttachment> _imageAttachment(XFile file) async {
    final recognizer = TextRecognizer(script: TextRecognitionScript.latin);
    String text = '';
    try {
      final result = await recognizer.processImage(InputImage.fromFilePath(file.path));
      text = result.text.trim();
    } finally {
      await recognizer.close();
    }
    final name = file.name.trim().isEmpty
        ? 'imagen_${DateTime.now().millisecondsSinceEpoch}.jpg'
        : file.name;
    return QueryAttachment(
      name: name,
      path: file.path,
      kind: 'image',
      mimeType: mimeForPath(file.path),
      extractedText: text.isEmpty
          ? '[Imagen $name: OCR no detectó texto. Usa análisis visual si el modelo lo admite.]'
          : text,
    );
  }

  static String buildTextContext(List<QueryAttachment> attachments, {int maxChars = 9000}) {
    if (attachments.isEmpty) return '';
    final out = StringBuffer();
    var used = 0;
    for (final item in attachments) {
      final header = '\n=== ADJUNTO: ${item.name} (${item.kind.toUpperCase()}) ===\n';
      final remaining = maxChars - used - header.length;
      if (remaining <= 100) break;
      final body = item.extractedText.length > remaining
          ? item.extractedText.substring(0, remaining)
          : item.extractedText;
      out.write(header);
      out.write(body);
      used += header.length + body.length;
      if (used >= maxChars) break;
    }
    return out.toString().trim();
  }

  static List<String> imagePaths(List<QueryAttachment> attachments) =>
      attachments.where((a) => a.isImage && a.path.isNotEmpty).map((a) => a.path).toList();

  static Future<StudyGuide> saveImageToLibrary(QueryAttachment attachment) async {
    if (!attachment.isImage) {
      throw ArgumentError('El adjunto no es una imagen.');
    }
    final source = File(attachment.path);
    if (!await source.exists()) throw const FileSystemException('La imagen ya no existe.');
    final root = await getApplicationDocumentsDirectory();
    final dir = Directory('${root.path}/guide_files');
    await dir.create(recursive: true);
    final ext = _extensionOf(attachment.name).isEmpty ? 'jpg' : _extensionOf(attachment.name);
    final safeBase = attachment.name
        .replaceAll(RegExp(r'[^A-Za-z0-9._-]+'), '_')
        .replaceAll(RegExp(r'_+'), '_');
    final stored = File('${dir.path}/${DateTime.now().microsecondsSinceEpoch}_$safeBase');
    await source.copy(stored.path);
    final title = _titleFromFilename(attachment.name);
    final text = attachment.extractedText.trim().isEmpty
        ? 'Imagen guardada en Memora. No se detectó texto mediante OCR.'
        : attachment.extractedText.trim();
    return StudyEngine.buildGuide(
      title: title.isEmpty ? 'Imagen' : title,
      sourceType: 'image',
      sourceName: attachment.name,
      text: text,
      filePath: stored.path,
    );
  }

  static String mimeForPath(String path) {
    final lower = path.toLowerCase();
    if (lower.endsWith('.png')) return 'image/png';
    if (lower.endsWith('.webp')) return 'image/webp';
    if (lower.endsWith('.gif')) return 'image/gif';
    if (lower.endsWith('.heic') || lower.endsWith('.heif')) return 'image/heic';
    return 'image/jpeg';
  }

  static String _extensionOf(String filename) {
    final dot = filename.lastIndexOf('.');
    return dot < 0 ? '' : filename.substring(dot + 1).toLowerCase();
  }

  static String _titleFromFilename(String filename) {
    final dot = filename.lastIndexOf('.');
    final raw = dot > 0 ? filename.substring(0, dot) : filename;
    return raw.replaceAll(RegExp(r'[_-]+'), ' ').trim();
  }

  static Future<String> _writeTemp(Uint8List bytes, String name) async {
    final root = await getTemporaryDirectory();
    final safe = name.replaceAll(RegExp(r'[^A-Za-z0-9._-]+'), '_');
    final file = File('${root.path}/${DateTime.now().microsecondsSinceEpoch}_$safe');
    await file.writeAsBytes(bytes, flush: true);
    return file.path;
  }
}
