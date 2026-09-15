import 'dart:io';
import 'package:fcllama/fllama.dart';
import 'package:shared_preferences/shared_preferences.dart';

class DeviceLlmService {
  static double? _contextId;
  static String? _loadedPath;

  static Future<String> ask(String prompt) async {
    final p = await SharedPreferences.getInstance();
    final path = p.getString('device_model_path') ?? '';
    if (path.isEmpty || !File(path).existsSync()) {
      throw Exception('Importa primero un modelo GGUF en Ajustes de IA.');
    }
    if (_contextId == null || _loadedPath != path) {
      await FCllama.instance()?.releaseAllContexts();
      final result = await FCllama.instance()?.initContext(
        path,
        nCtx: 4096,
        nBatch: 256,
        nThreads: 0,
        nGpuLayers: 0,
        useMlock: false,
        useMmap: true,
      );
      final rawId = result?['contextId'];
      _contextId = rawId is num ? rawId.toDouble() : double.tryParse('$rawId');
      if (_contextId == null) throw Exception('No se pudo cargar el modelo GGUF.');
      _loadedPath = path;
    }
    final wrapped = '<|system|>\nEres el tutor de Memora. Responde en español, de forma clara y únicamente con la información proporcionada.\n<|user|>\n$prompt\n<|assistant|>\n';
    final result = await FCllama.instance()?.completion(
      _contextId!,
      prompt: wrapped,
      temperature: 0.25,
      nPredict: 768,
      topK: 40,
      topP: 0.9,
      penaltyRepeat: 1.1,
      stop: ['<|user|>', '<|end|>', '<|eot_id|>'],
    );
    final text = result?['text']?.toString().trim() ?? '';
    if (text.isEmpty) throw Exception('El modelo local no generó una respuesta.');
    return text;
  }
}
