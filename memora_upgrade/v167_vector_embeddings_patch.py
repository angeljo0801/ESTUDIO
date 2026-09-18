from pathlib import Path

# v167: local vector knowledge base + downloadable embedding model.
# Imported guides are indexed when the model exists; otherwise indexing happens
# automatically on the first semantic query after the model is downloaded.

p = Path('pubspec.yaml')
s = p.read_text()
if 'flutter_onnxruntime:' not in s:
    s = s.replace("  http: ^1.5.0\n", "  http: ^1.5.0\n  flutter_onnxruntime: ^1.8.5\n  dart_sentencepiece_tokenizer: ^1.4.1\n", 1)
p.write_text(s)

embedding = r"""import 'dart:async';
import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:dart_sentencepiece_tokenizer/dart_sentencepiece_tokenizer.dart';
import 'package:flutter_onnxruntime/flutter_onnxruntime.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

class EmbeddingModelStatus {
  const EmbeddingModelStatus({
    required this.ready,
    required this.modelPath,
    required this.tokenizerPath,
    required this.modelBytes,
  });

  final bool ready;
  final String modelPath;
  final String tokenizerPath;
  final int modelBytes;
}

class EmbeddingService {
  static const String modelId =
      'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2-qint8-arm64';
  static const String modelLabel =
      'MiniLM multilingüe para embeddings (Android ARM64)';
  static const int dimensions = 384;
  static const int maxTokens = 128;

  static const String _modelUrl =
      'https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/resolve/main/onnx/model_qint8_arm64.onnx?download=true';
  static const String _tokenizerUrl =
      'https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/resolve/main/tokenizer.json?download=true';

  static OnnxRuntime? _runtime;
  static OrtSession? _session;
  static dynamic _tokenizer;
  static String? _loadedModelPath;

  static Future<Directory> _directory() async {
    final root = await getApplicationSupportDirectory();
    final dir = Directory('${root.path}/embedding_models/multilingual_minilm_l12');
    await dir.create(recursive: true);
    return dir;
  }

  static Future<File> _modelFile() async =>
      File('${(await _directory()).path}/model_qint8_arm64.onnx');

  static Future<File> _tokenizerFile() async =>
      File('${(await _directory()).path}/tokenizer.json');

  static Future<bool> isReady() async {
    final model = await _modelFile();
    final tokenizer = await _tokenizerFile();
    return await model.exists() &&
        await model.length() > 1000000 &&
        await tokenizer.exists() &&
        await tokenizer.length() > 10000;
  }

  static Future<EmbeddingModelStatus> status() async {
    final model = await _modelFile();
    final tokenizer = await _tokenizerFile();
    final ready = await isReady();
    return EmbeddingModelStatus(
      ready: ready,
      modelPath: model.path,
      tokenizerPath: tokenizer.path,
      modelBytes: await model.exists() ? await model.length() : 0,
    );
  }

  static Future<void> downloadDefaultModel({
    void Function(double progress, String stage)? onProgress,
  }) async {
    final model = await _modelFile();
    final tokenizer = await _tokenizerFile();

    onProgress?.call(0, 'Preparando descarga…');
    await _download(
      _modelUrl,
      model,
      onProgress: (p) => onProgress?.call(p * .88, 'Descargando modelo de embeddings…'),
    );
    await _download(
      _tokenizerUrl,
      tokenizer,
      onProgress: (p) => onProgress?.call(.88 + p * .12, 'Descargando tokenizer…'),
    );

    await _disposeLoaded();
    onProgress?.call(1, 'Modelo de embeddings listo.');
  }

  static Future<void> _download(
    String url,
    File target, {
    required void Function(double progress) onProgress,
  }) async {
    final part = File('${target.path}.part');
    if (await part.exists()) await part.delete();

    final client = http.Client();
    IOSink? sink;
    try {
      final request = http.Request('GET', Uri.parse(url));
      final response = await client.send(request).timeout(const Duration(minutes: 12));
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw Exception('La descarga respondió ${response.statusCode}.');
      }
      final total = response.contentLength ?? 0;
      var received = 0;
      sink = part.openWrite();
      await for (final chunk in response.stream) {
        sink.add(chunk);
        received += chunk.length;
        if (total > 0) onProgress((received / total).clamp(0.0, 1.0));
      }
      await sink.flush();
      await sink.close();
      sink = null;

      if (await part.length() < 10000) {
        throw Exception('El archivo descargado no es válido.');
      }
      if (await target.exists()) await target.delete();
      await part.rename(target.path);
      onProgress(1);
    } finally {
      try {
        await sink?.close();
      } catch (_) {}
      client.close();
      if (await part.exists()) {
        try {
          await part.delete();
        } catch (_) {}
      }
    }
  }

  static Future<void> deleteModel() async {
    await _disposeLoaded();
    final model = await _modelFile();
    final tokenizer = await _tokenizerFile();
    if (await model.exists()) await model.delete();
    if (await tokenizer.exists()) await tokenizer.delete();
  }

  static Future<void> _ensureLoaded() async {
    if (!await isReady()) {
      throw Exception(
        'El modelo de embeddings no está instalado. Ve a Ajustes de IA y toca "Descargar automáticamente".',
      );
    }

    final model = await _modelFile();
    final tokenizerFile = await _tokenizerFile();
    if (_session != null && _loadedModelPath == model.path && _tokenizer != null) return;

    await _disposeLoaded();
    _runtime = OnnxRuntime();
    _session = await _runtime!.createSession(model.path);
    _tokenizer = await TokenizerJsonLoader.fromJsonFile(tokenizerFile.path);
    _loadedModelPath = model.path;
  }

  static Future<void> _disposeLoaded() async {
    final session = _session;
    _session = null;
    _runtime = null;
    _tokenizer = null;
    _loadedModelPath = null;
    if (session != null) {
      try {
        await session.close();
      } catch (_) {}
    }
  }

  static Future<List<double>> embed(String text) async {
    await _ensureLoaded();
    final session = _session!;
    final encoding = _tokenizer.encode(text.trim());

    final rawIds = List<int>.from(encoding.ids);
    final rawMask = List<int>.from(encoding.attentionMask);
    final rawTypes = List<int>.from(encoding.typeIds);
    final take = math.min(maxTokens, rawIds.length);
    final idsList = rawIds.take(take).toList(growable: false);
    final maskList = rawMask.take(take).toList(growable: false);
    final typesList = rawTypes.take(take).toList(growable: false);
    final ids = Int64List.fromList(idsList);
    final mask = Int64List.fromList(maskList);
    final types = Int64List.fromList(typesList);
    final shape = <int>[1, ids.length];

    final inputs = <String, OrtValue>{};
    if (session.inputNames.contains('input_ids')) {
      inputs['input_ids'] = await OrtValue.fromList(ids, shape);
    }
    if (session.inputNames.contains('attention_mask')) {
      inputs['attention_mask'] = await OrtValue.fromList(mask, shape);
    }
    if (session.inputNames.contains('token_type_ids')) {
      inputs['token_type_ids'] = await OrtValue.fromList(types, shape);
    }

    if (inputs.isEmpty) {
      throw Exception('El modelo de embeddings no expone entradas compatibles.');
    }

    Map<String, OrtValue> outputs = const {};
    try {
      outputs = await session.run(inputs);
      final output = outputs['sentence_embedding'] ??
          outputs['sentence_embeddings'] ??
          outputs['last_hidden_state'] ??
          outputs.values.first;
      final flat = (await output.asFlattenedList())
          .map((e) => (e as num).toDouble())
          .toList(growable: false);

      List<double> vector;
      if (output.shape.length >= 3 && output.shape.last > 0) {
        final hidden = output.shape.last;
        final tokens = math.min(maskList.length, flat.length ~/ hidden);
        final pooled = List<double>.filled(hidden, 0);
        var weight = 0.0;
        for (var token = 0; token < tokens; token++) {
          final w = maskList[token] == 0 ? 0.0 : 1.0;
          if (w == 0) continue;
          weight += w;
          final offset = token * hidden;
          for (var d = 0; d < hidden; d++) {
            pooled[d] += flat[offset + d] * w;
          }
        }
        if (weight > 0) {
          for (var d = 0; d < hidden; d++) {
            pooled[d] /= weight;
          }
        }
        vector = pooled;
      } else if (flat.length >= dimensions) {
        vector = flat.take(dimensions).toList(growable: false);
      } else {
        vector = flat;
      }
      if (vector.isEmpty) throw Exception('El modelo devolvió un embedding vacío.');

      var norm2 = 0.0;
      for (final value in vector) {
        norm2 += value * value;
      }
      final norm = math.sqrt(norm2);
      if (norm <= 1e-12) return vector;
      return vector.map((e) => e / norm).toList(growable: false);
    } finally {
      for (final input in inputs.values) {
        try {
          await input.dispose();
        } catch (_) {}
      }
      for (final output in outputs.values) {
        try {
          await output.dispose();
        } catch (_) {}
      }
    }
  }
}
"""
Path('lib/embedding_service.dart').write_text(embedding)

vector_store = r"""import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:path_provider/path_provider.dart';

import 'embedding_service.dart';
import 'models.dart';

class VectorKnowledgeStore {
  static const int _chunkChars = 1100;
  static const int _overlapChars = 150;

  static Future<Directory> _directory() async {
    final root = await getApplicationDocumentsDirectory();
    final dir = Directory('${root.path}/vector_knowledge');
    await dir.create(recursive: true);
    return dir;
  }

  static Future<File> _fileFor(String guideId) async {
    final safe = guideId.replaceAll(RegExp(r'[^A-Za-z0-9_-]+'), '_');
    return File('${(await _directory()).path}/$safe.json');
  }

  static String _fingerprint(StudyGuide guide) {
    var hash = 0x811c9dc5;
    final text = '${guide.id}|${guide.title}|${guide.text}';
    for (final unit in text.codeUnits) {
      hash ^= unit;
      hash = (hash * 0x01000193) & 0xffffffff;
    }
    return '${text.length}:${hash.toRadixString(16)}';
  }

  static Future<void> deleteGuide(String guideId) async {
    final file = await _fileFor(guideId);
    if (await file.exists()) await file.delete();
  }

  static Future<int> ensureIndexed(
    StudyGuide guide, {
    void Function(int done, int total)? onProgress,
  }) async {
    if (!await EmbeddingService.isReady()) return 0;
    final file = await _fileFor(guide.id);
    final fingerprint = _fingerprint(guide);

    if (await file.exists()) {
      try {
        final data = jsonDecode(await file.readAsString()) as Map<String, dynamic>;
        if (data['fingerprint'] == fingerprint &&
            data['modelId'] == EmbeddingService.modelId &&
            data['chunks'] is List) {
          return (data['chunks'] as List).length;
        }
      } catch (_) {}
    }

    final chunks = _chunk(guide.text);
    final rows = <Map<String, dynamic>>[];
    for (var i = 0; i < chunks.length; i++) {
      final vector = await EmbeddingService.embed(chunks[i]);
      rows.add({
        'order': i,
        'text': chunks[i],
        'vector': _encodeVector(vector),
      });
      onProgress?.call(i + 1, chunks.length);
    }

    final payload = {
      'version': 1,
      'guideId': guide.id,
      'guideTitle': guide.title,
      'fingerprint': fingerprint,
      'modelId': EmbeddingService.modelId,
      'dimensions': EmbeddingService.dimensions,
      'createdAt': DateTime.now().toIso8601String(),
      'chunks': rows,
    };
    await file.writeAsString(jsonEncode(payload), flush: true);
    return rows.length;
  }

  static Future<String> buildContext({
    required List<StudyGuide> guides,
    required String query,
    int maxChars = 12000,
    int maxChunks = 10,
    bool allowUnmatchedFallback = true,
  }) async {
    if (guides.isEmpty) return '(No assigned knowledge bases)';
    if (!await EmbeddingService.isReady()) {
      return '(Embedding model unavailable)';
    }

    final queryVector = await EmbeddingService.embed(query);
    final matches = <_VectorMatch>[];

    for (final guide in guides) {
      await ensureIndexed(guide);
      final file = await _fileFor(guide.id);
      if (!await file.exists()) continue;
      try {
        final data = jsonDecode(await file.readAsString()) as Map<String, dynamic>;
        final chunks = (data['chunks'] as List<dynamic>? ?? const []);
        for (final raw in chunks) {
          final row = Map<String, dynamic>.from(raw as Map);
          final text = row['text']?.toString().trim() ?? '';
          final encoded = row['vector']?.toString() ?? '';
          if (text.isEmpty || encoded.isEmpty) continue;
          final vector = _decodeVector(encoded);
          if (vector.length != queryVector.length) continue;
          matches.add(
            _VectorMatch(
              guide: guide,
              text: text,
              score: _dot(queryVector, vector),
              order: (row['order'] as num?)?.toInt() ?? 0,
            ),
          );
        }
      } catch (_) {}
    }

    if (matches.isEmpty) return '(No matching evidence found in the assigned guides)';
    matches.sort((a, b) => b.score.compareTo(a.score));

    var selected = matches.where((m) => m.score >= .16).take(maxChunks).toList();
    if (selected.isEmpty && allowUnmatchedFallback) {
      selected = matches.take(maxChunks).toList();
    }
    if (selected.isEmpty) return '(No matching evidence found in the assigned guides)';

    final out = StringBuffer();
    var used = 0;
    for (final match in selected) {
      final header =
          '\n=== ${match.guide.title} [${match.guide.sourceType}] • vector ${match.score.toStringAsFixed(3)} ===\n';
      final remaining = maxChars - used - header.length;
      if (remaining <= 200) break;
      final body = match.text.length > remaining
          ? match.text.substring(0, remaining)
          : match.text;
      out.write(header);
      out.write(body);
      used += header.length + body.length;
      if (used >= maxChars) break;
    }
    return out.toString().trim();
  }

  static List<String> _chunk(String source) {
    final text = source.replaceAll('\r\n', '\n').trim();
    if (text.isEmpty) return const [];
    final result = <String>[];
    var start = 0;
    while (start < text.length) {
      var end = math.min(start + _chunkChars, text.length);
      if (end < text.length) {
        final boundary = text.lastIndexOf(RegExp(r'[\n.!?]\s'), end);
        if (boundary > start + (_chunkChars * .55).round()) {
          end = boundary + 1;
        }
      }
      final piece = text.substring(start, end).trim();
      if (piece.isNotEmpty) result.add(piece);
      if (end >= text.length) break;
      start = math.max(start + 1, end - _overlapChars);
    }
    return result;
  }

  static String _encodeVector(List<double> vector) {
    final floats = Float32List.fromList(vector);
    return base64Encode(floats.buffer.asUint8List());
  }

  static List<double> _decodeVector(String encoded) {
    final bytes = base64Decode(encoded);
    final safe = Uint8List.fromList(bytes);
    final floats = Float32List.view(safe.buffer);
    return floats.map((e) => e.toDouble()).toList(growable: false);
  }

  static double _dot(List<double> a, List<double> b) {
    final n = math.min(a.length, b.length);
    var sum = 0.0;
    for (var i = 0; i < n; i++) {
      sum += a[i] * b[i];
    }
    return sum;
  }
}

class _VectorMatch {
  const _VectorMatch({
    required this.guide,
    required this.text,
    required this.score,
    required this.order,
  });

  final StudyGuide guide;
  final String text;
  final double score;
  final int order;
}
"""
Path('lib/vector_knowledge_store.dart').write_text(vector_store)

p = Path('lib/knowledge_retriever.dart')
s = p.read_text()
if "import 'embedding_service.dart';" not in s:
    s = s.replace(
        "import 'models.dart';\n",
        "import 'embedding_service.dart';\nimport 'models.dart';\nimport 'vector_knowledge_store.dart';\n",
        1,
    )

anchor = "class KnowledgeRetriever {\n"
method = r"""class KnowledgeRetriever {
  static Future<String> buildSmartContext({
    required List<StudyGuide> guides,
    required String query,
    int maxChars = 12000,
    int maxChunks = 10,
    bool allowUnmatchedFallback = true,
  }) async {
    if (guides.isEmpty) return '(No assigned knowledge bases)';
    try {
      if (await EmbeddingService.isReady()) {
        final vector = await VectorKnowledgeStore.buildContext(
          guides: guides,
          query: query,
          maxChars: maxChars,
          maxChunks: maxChunks,
          allowUnmatchedFallback: allowUnmatchedFallback,
        );
        if (!vector.startsWith('(Embedding model unavailable)')) {
          return vector;
        }
      }
    } catch (_) {}
    return buildContext(
      guides: guides,
      query: query,
      maxChars: maxChars,
      maxChunks: maxChunks,
      allowUnmatchedFallback: allowUnmatchedFallback,
    );
  }

"""
if 'buildSmartContext({' not in s:
    if anchor not in s:
        raise SystemExit('v167 KnowledgeRetriever anchor missing')
    s = s.replace(anchor, method, 1)
p.write_text(s)

p = Path('lib/guide_store.dart')
s = p.read_text()
if "import 'vector_knowledge_store.dart';" not in s:
    s = s.replace("import 'study_engine.dart';\n", "import 'study_engine.dart';\nimport 'vector_knowledge_store.dart';\n", 1)

old = """  Future<void> add(StudyGuide guide) async {
    guides.insert(0, guide);
    await _persist();
    notifyListeners();
  }
"""
new = """  Future<void> add(StudyGuide guide) async {
    guides.insert(0, guide);
    await _persist();
    notifyListeners();
    try {
      await VectorKnowledgeStore.ensureIndexed(guide);
    } catch (_) {}
  }
"""
if old not in s:
    raise SystemExit('v167 GuideStore add anchor missing')
s = s.replace(old, new, 1)

old = """    guides.removeWhere((guide) => guide.id == id);
    await _persist();
    notifyListeners();
"""
new = """    guides.removeWhere((guide) => guide.id == id);
    await _persist();
    notifyListeners();
    try {
      await VectorKnowledgeStore.deleteGuide(id);
    } catch (_) {}
"""
if old not in s:
    raise SystemExit('v167 GuideStore remove anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)

p = Path('lib/llm_settings_page.dart')
s = p.read_text()
if "import 'embedding_service.dart';" not in s:
    s = s.replace(
        "import 'package:shared_preferences/shared_preferences.dart';\n",
        "import 'package:shared_preferences/shared_preferences.dart';\n\nimport 'embedding_service.dart';\n",
        1,
    )

old = """  bool selectingShared = false;

  String deviceModelPath = '';
"""
new = """  bool selectingShared = false;
  bool embeddingReady = false;
  bool embeddingDownloading = false;
  double embeddingProgress = 0;
  String embeddingStage = '';

  String deviceModelPath = '';
"""
if old not in s:
    raise SystemExit('v167 settings state anchor missing')
s = s.replace(old, new, 1)

old = """    sharedModelName = p.getString('shared_model_name') ?? '';
    if (mounted) setState(() => loading = false);
  }
"""
new = """    sharedModelName = p.getString('shared_model_name') ?? '';
    embeddingReady = await EmbeddingService.isReady();
    if (mounted) setState(() => loading = false);
  }

  Future<void> _downloadEmbeddingModel() async {
    if (embeddingDownloading) return;
    setState(() {
      embeddingDownloading = true;
      embeddingProgress = 0;
      embeddingStage = 'Preparando descarga…';
    });
    try {
      await EmbeddingService.downloadDefaultModel(
        onProgress: (progress, stage) {
          if (!mounted) return;
          setState(() {
            embeddingProgress = progress;
            embeddingStage = stage;
          });
        },
      );
      if (!mounted) return;
      setState(() {
        embeddingReady = true;
        embeddingProgress = 1;
        embeddingStage = 'Modelo de embeddings listo.';
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Modelo de embeddings instalado. Las guías se indexarán automáticamente al importarse o al consultarlas.',
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No pude descargar el modelo de embeddings: $e')),
      );
    } finally {
      if (mounted) setState(() => embeddingDownloading = false);
    }
  }

  Future<void> _deleteEmbeddingModel() async {
    if (embeddingDownloading) return;
    await EmbeddingService.deleteModel();
    if (!mounted) return;
    setState(() {
      embeddingReady = false;
      embeddingProgress = 0;
      embeddingStage = '';
    });
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Modelo de embeddings eliminado.')),
    );
  }
"""
if old not in s:
    raise SystemExit('v167 settings load anchor missing')
s = s.replace(old, new, 1)

block = """                  const SizedBox(height: 22),
                  const Divider(),
                  const SizedBox(height: 14),
                  const Text(
                    'Modelo de embeddings',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Convierte PDF, DOCX, TXT, Excel y otras guías en una base vectorial local. Memora recupera por significado solo los fragmentos relevantes para cada pregunta.',
                  ),
                  const SizedBox(height: 10),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(
                                embeddingReady
                                    ? Icons.check_circle_outline
                                    : Icons.hub_outlined,
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  embeddingReady
                                      ? 'Embeddings listos'
                                      : 'Modelo multilingüe no instalado',
                                  style: const TextStyle(fontWeight: FontWeight.w700),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'Modelo recomendado para español e inglés. Se guarda dentro de Memora y funciona localmente después de descargarlo.',
                          ),
                          if (embeddingDownloading) ...[
                            const SizedBox(height: 12),
                            LinearProgressIndicator(
                              value: embeddingProgress > 0 ? embeddingProgress : null,
                            ),
                            const SizedBox(height: 6),
                            Text(
                              embeddingStage.isEmpty
                                  ? 'Descargando…'
                                  : embeddingStage,
                            ),
                          ],
                          const SizedBox(height: 12),
                          if (!embeddingReady)
                            FilledButton.icon(
                              onPressed: embeddingDownloading
                                  ? null
                                  : _downloadEmbeddingModel,
                              icon: const Icon(Icons.download_rounded),
                              label: const Text(
                                'Descargar automáticamente modelo de embeddings',
                              ),
                            ),
                          if (embeddingReady)
                            OutlinedButton.icon(
                              onPressed: embeddingDownloading
                                  ? null
                                  : _deleteEmbeddingModel,
                              icon: const Icon(Icons.delete_outline),
                              label: const Text('Eliminar modelo de embeddings'),
                            ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
"""
ui_anchor = "                  const Text('AI by task', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),\n"
if ui_anchor not in s:
    raise SystemExit('v167 settings AI-by-task anchor missing')
s = s.replace(ui_anchor, block + ui_anchor, 1)
p.write_text(s)

for filename in [
    'lib/tutor_page.dart',
    'lib/agent_page.dart',
    'lib/general_ai_chat_page.dart',
    'lib/agent_orchestrator_page.dart',
]:
    p = Path(filename)
    s = p.read_text()
    if 'KnowledgeRetriever.buildContext(' in s:
        s = s.replace(
            'KnowledgeRetriever.buildContext(',
            'await KnowledgeRetriever.buildSmartContext(',
        )
    p.write_text(s)

print('v167 applied: downloadable local embedding model + automatic vector knowledge indexing/retrieval')
