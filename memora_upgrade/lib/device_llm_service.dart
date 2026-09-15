import 'dart:async';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:llama_flutter_android/llama_flutter_android.dart';
import 'package:shared_preferences/shared_preferences.dart';

class DeviceLlmService {
  static const MethodChannel _sharedModelChannel =
      MethodChannel('com.memora/shared_model');

  static LlamaController? _controller;
  static String? _loadedKey;
  static bool _loadedFromShared = false;
  static Future<void> _operationQueue = Future<void>.value();
  static bool _cancelRequested = false;
  static String _accelerationLabel = 'Sin cargar';

  static String get accelerationLabel => _accelerationLabel;

  static Future<T> _enqueue<T>(Future<T> Function() operation) {
    final completer = Completer<T>();
    _operationQueue = _operationQueue.then((_) async {
      try {
        final value = await operation();
        if (!completer.isCompleted) completer.complete(value);
      } catch (error, stackTrace) {
        if (!completer.isCompleted) completer.completeError(error, stackTrace);
      }
    }).catchError((_) {});
    return completer.future;
  }

  static Future<String> _resolvePrivateModel(SharedPreferences p) async {
    final path = p.getString('device_model_path') ?? '';
    if (path.isEmpty || !File(path).existsSync()) {
      throw Exception(
        'Memora no tiene un modelo privado. Ve a Ajustes de IA y dale un archivo GGUF.',
      );
    }
    return path;
  }

  static Future<String> _openSharedModel(SharedPreferences p) async {
    final uriText = p.getString('shared_model_uri') ?? '';
    if (uriText.isEmpty) {
      throw Exception(
        'No hay un modelo compartido seleccionado. Ve a Ajustes de IA y elige un GGUF compartido.',
      );
    }
    final uri = Uri.tryParse(uriText);
    if (uri == null) {
      throw Exception('La ubicación del modelo compartido no es válida.');
    }
    if (uri.scheme == 'file') {
      final path = uri.toFilePath();
      if (!File(path).existsSync()) {
        throw Exception('El modelo compartido ya no existe en esa ubicación.');
      }
      return path;
    }
    final fdPath = await _sharedModelChannel.invokeMethod<String>(
      'openSharedModel',
      {'uri': uriText},
    );
    if (fdPath == null || fdPath.isEmpty) {
      throw Exception('Android no pudo abrir el modelo compartido.');
    }
    return fdPath;
  }

  static Future<void> _closeSharedModelHandle() async {
    try {
      await _sharedModelChannel.invokeMethod<void>('closeSharedModel');
    } catch (_) {}
  }

  static int _maxTokens(String mode) {
    switch (mode) {
      case 'fast':
        return 180;
      case 'deep':
        return 640;
      default:
        return 320;
    }
  }

  static Future<void> _disposeController() async {
    final current = _controller;
    _controller = null;
    _loadedKey = null;
    if (current != null) {
      try {
        await current.dispose();
      } catch (_) {}
    }
    if (_loadedFromShared) {
      await _closeSharedModelHandle();
      _loadedFromShared = false;
    }
  }

  static Future<void> _ensureLoaded({
    required SharedPreferences prefs,
    required String mode,
  }) async {
    final normalizedMode = mode == 'shared' ? 'shared' : 'private';
    final isShared = normalizedMode == 'shared';
    final sharedUri = prefs.getString('shared_model_uri') ?? '';
    final privatePath = prefs.getString('device_model_path') ?? '';
    final modelKey = isShared ? 'shared:$sharedUri' : 'private:$privatePath';
    if (_controller != null && _loadedKey == modelKey) return;

    await _disposeController();
    final path = isShared
        ? await _openSharedModel(prefs)
        : await _resolvePrivateModel(prefs);

    final threads = (Platform.numberOfProcessors - 2).clamp(2, 8).toInt();
    var controller = LlamaController();
    var gpuLayers = 0;
    String gpuName = '';

    try {
      final gpu = await controller.detectGpu();
      gpuName = gpu.gpuName;
      if (gpu.vulkanSupported) {
        gpuLayers = gpu.recommendedGpuLayers;
      }
    } catch (_) {
      gpuLayers = 0;
    }

    try {
      await controller.loadModel(
        modelPath: path,
        threads: threads,
        contextSize: 4096,
        gpuLayers: gpuLayers,
      );
      _accelerationLabel = gpuLayers > 0
          ? 'GPU Vulkan${gpuName.isEmpty ? '' : ' • $gpuName'}'
          : 'CPU • $threads hilos';
    } catch (gpuError) {
      if (gpuLayers <= 0) {
        if (isShared) await _closeSharedModelHandle();
        rethrow;
      }
      try {
        await controller.dispose();
      } catch (_) {}
      controller = LlamaController();
      await controller.loadModel(
        modelPath: path,
        threads: threads,
        contextSize: 4096,
        gpuLayers: 0,
      );
      _accelerationLabel = 'CPU • $threads hilos (GPU no compatible con este modelo)';
    }

    _controller = controller;
    _loadedKey = modelKey;
    _loadedFromShared = isShared;
    await prefs.setString('device_acceleration_status', _accelerationLabel);
  }

  static Future<String> ask(
    String prompt, {
    String responseMode = 'normal',
    void Function(String text)? onPartial,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final mode = prefs.getString('device_model_mode') ?? 'private';
    return askWithMode(
      prompt,
      mode: mode,
      responseMode: responseMode,
      onPartial: onPartial,
    );
  }

  static Future<String> askWithMode(
    String prompt, {
    required String mode,
    String responseMode = 'normal',
    void Function(String text)? onPartial,
  }) {
    return _enqueue(() => _askInternal(
          prompt,
          mode: mode,
          responseMode: responseMode,
          onPartial: onPartial,
        ));
  }

  static Future<String> _askInternal(
    String prompt, {
    required String mode,
    required String responseMode,
    void Function(String text)? onPartial,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await _ensureLoaded(prefs: prefs, mode: mode);
    final controller = _controller;
    if (controller == null) throw Exception('No se pudo iniciar el modelo GGUF.');

    _cancelRequested = false;
    final buffer = StringBuffer();
    var lastUiUpdate = DateTime.fromMillisecondsSinceEpoch(0);

    final stream = controller.generateChat(
      messages: [
        ChatMessage(
          role: 'system',
          content:
              'Eres la inteligencia local de Memora. Sigue cuidadosamente las instrucciones del tutor o agente, responde con claridad y no inventes información.',
        ),
        ChatMessage(role: 'user', content: prompt),
      ],
      temperature: 0.25,
      maxTokens: _maxTokens(responseMode),
    );

    await for (final token in stream) {
      if (_cancelRequested) break;
      buffer.write(token);
      final now = DateTime.now();
      if (onPartial != null &&
          now.difference(lastUiUpdate) >= const Duration(milliseconds: 55)) {
        onPartial(buffer.toString());
        lastUiUpdate = now;
      }
    }

    final text = buffer.toString().trim();
    if (text.isNotEmpty) {
      onPartial?.call(text);
      return text;
    }
    if (_cancelRequested) return 'Generación cancelada.';
    throw Exception('El modelo local no generó una respuesta.');
  }

  static Future<void> stopCurrent() async {
    _cancelRequested = true;
    final controller = _controller;
    if (controller != null) {
      try {
        await controller.stop();
      } catch (_) {}
    }
  }
}
