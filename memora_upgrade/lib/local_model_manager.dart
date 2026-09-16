import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

class PrivateGgufModel {
  const PrivateGgufModel({
    required this.name,
    required this.path,
    required this.bytes,
  });

  final String name;
  final String path;
  final int bytes;
}

class OllamaModelInfo {
  const OllamaModelInfo({
    required this.name,
    this.size = 0,
  });

  final String name;
  final int size;
}

class LocalModelManager {
  static Future<Directory> privateModelDirectory() async {
    final root = await getApplicationSupportDirectory();
    final directory = Directory('${root.path}/models');
    await directory.create(recursive: true);
    return directory;
  }

  static Future<List<PrivateGgufModel>> privateModels() async {
    final directory = await privateModelDirectory();
    final result = <PrivateGgufModel>[];
    await for (final entity in directory.list(followLinks: false)) {
      if (entity is! File || !entity.path.toLowerCase().endsWith('.gguf')) continue;
      try {
        result.add(
          PrivateGgufModel(
            name: entity.uri.pathSegments.isEmpty
                ? entity.path.split('/').last
                : entity.uri.pathSegments.last,
            path: entity.path,
            bytes: await entity.length(),
          ),
        );
      } catch (_) {}
    }
    result.sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
    return result;
  }

  static Future<void> deletePrivateModel(String path) async {
    final directory = await privateModelDirectory();
    final canonicalDir = directory.absolute.path;
    final file = File(path);
    final canonicalFile = file.absolute.path;
    if (!canonicalFile.startsWith('$canonicalDir${Platform.pathSeparator}')) {
      throw StateError('Memora can only delete its own private GGUF copies.');
    }
    if (await file.exists()) await file.delete();

    final prefs = await SharedPreferences.getInstance();
    if ((prefs.getString('device_model_path') ?? '') == path) {
      await prefs.remove('device_model_path');
    }
  }

  static Future<Uri> _ollamaRoot() async {
    final prefs = await SharedPreferences.getInstance();
    var raw = (prefs.getString('local_base_url') ?? 'http://127.0.0.1:11434/v1').trim();
    if (raw.isEmpty) raw = 'http://127.0.0.1:11434/v1';
    raw = raw.replaceAll(RegExp(r'/+$'), '');
    if (raw.endsWith('/v1')) raw = raw.substring(0, raw.length - 3);
    return Uri.parse(raw);
  }

  static Future<List<OllamaModelInfo>> ollamaModels() async {
    final root = await _ollamaRoot();
    final response = await http
        .get(root.resolve('/api/tags'))
        .timeout(const Duration(seconds: 10));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw HttpException('Ollama returned HTTP ${response.statusCode}.');
    }
    final decoded = jsonDecode(response.body);
    final raw = decoded is Map ? decoded['models'] : null;
    if (raw is! List) return const [];
    final models = <OllamaModelInfo>[];
    for (final item in raw.whereType<Map>()) {
      final name = (item['name'] ?? item['model'])?.toString().trim() ?? '';
      if (name.isEmpty) continue;
      models.add(
        OllamaModelInfo(
          name: name,
          size: (item['size'] as num?)?.toInt() ?? 0,
        ),
      );
    }
    models.sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
    return models;
  }

  static Future<void> pullOllamaModel(
    String model, {
    void Function(String status, int completed, int total)? onProgress,
  }) async {
    final clean = model.trim();
    if (clean.isEmpty) throw ArgumentError('Model name is empty.');
    final root = await _ollamaRoot();
    final client = http.Client();
    try {
      final request = http.Request('POST', root.resolve('/api/pull'))
        ..headers['Content-Type'] = 'application/json'
        ..body = jsonEncode({'name': clean, 'stream': true});
      final response = await client.send(request).timeout(const Duration(seconds: 20));
      if (response.statusCode < 200 || response.statusCode >= 300) {
        final body = await response.stream.bytesToString();
        throw HttpException('Ollama returned HTTP ${response.statusCode}: $body');
      }
      await for (final line in response.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter())) {
        final text = line.trim();
        if (text.isEmpty) continue;
        try {
          final data = jsonDecode(text);
          if (data is! Map) continue;
          final error = data['error']?.toString().trim() ?? '';
          if (error.isNotEmpty) throw StateError(error);
          final status = data['status']?.toString() ?? 'Downloading…';
          final completed = (data['completed'] as num?)?.toInt() ?? 0;
          final total = (data['total'] as num?)?.toInt() ?? 0;
          onProgress?.call(status, completed, total);
        } catch (e) {
          if (e is StateError) rethrow;
        }
      }
    } finally {
      client.close();
    }
  }

  static Future<void> deleteOllamaModel(String model) async {
    final clean = model.trim();
    if (clean.isEmpty) return;
    final root = await _ollamaRoot();
    final response = await http
        .delete(
          root.resolve('/api/delete'),
          headers: const {'Content-Type': 'application/json'},
          body: jsonEncode({'name': clean}),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw HttpException('Ollama returned HTTP ${response.statusCode}: ${response.body}');
    }

    final prefs = await SharedPreferences.getInstance();
    if ((prefs.getString('local_model') ?? '') == clean) {
      await prefs.setString('local_model', '');
    }
  }

  static Future<void> useOllamaModel(String model) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('local_model', model.trim());
    await prefs.setString('llm_provider', 'local');
  }
}
