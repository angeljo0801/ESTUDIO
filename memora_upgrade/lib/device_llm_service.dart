import 'dart:async';
import 'dart:io';

import 'package:fcllama/fllama.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

class DeviceLlmService {
  static const MethodChannel _sharedModelChannel =
      MethodChannel('com.memora/shared_model');

  static double? _contextId;
  static String? _loadedKey;
  static bool _loadedFromShared = false;

  static Future<void> _operationQueue = Future<void>.value();

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

  static bool _isContextBusy(Object error) {
    final text = error.toString().toLowerCase();
    return text.contains('context is busy') ||
        text.contains('context busy') ||
        text.contains('already running');
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
    if (uri == null) throw Exception('La ubicación del modelo compartido no es válida.');
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

  static Future<String> ask(String prompt) async {
    final p = await SharedPreferences.getInstance();
    final mode = p.getString('device_model_mode') ?? 'private';
    return askWithMode(prompt, mode: mode);
  }

  static Future<String> askWithMode(String prompt, {required String mode}) {
    return _enqueue(() => _askWithModeInternal(prompt, mode: mode));
  }

  static Future<String> _askWithModeInternal(
    String prompt, {
    required String mode,
  }) async {
    final p = await SharedPreferences.getInstance();
    final normalizedMode = mode == 'shared' ? 'shared' : 'private';
    final isShared = normalizedMode == 'shared';
    final sharedUri = p.getString('shared_model_uri') ?? '';
    final privatePath = p.getString('device_model_path') ?? '';
    final modelKey = isShared ? 'shared:$sharedUri' : 'private:$privatePath';

    if (_contextId == null || _loadedKey != modelKey) {
      if (_contextId != null) {
        await FCllama.instance()?.releaseAllContexts();
        _contextId = null;
      }
      if (_loadedFromShared) {
        await _closeSharedModelHandle();
        _loadedFromShared = false;
      }

      final path = isShared ? await _openSharedModel(p) : await _resolvePrivateModel(p);
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
      if (_contextId == null) {
        if (isShared) await _closeSharedModelHandle();
        throw Exception('No se pudo cargar el modelo GGUF.');
      }
      _loadedKey = modelKey;
      _loadedFromShared = isShared;
    }

    final wrapped =
        '<|system|>\nEres un tutor de Memora. Sigue cuidadosamente las instrucciones incluidas en la solicitud, responde con claridad y no inventes información.\n<|user|>\n$prompt\n<|assistant|>\n';

    dynamic result;
    Object? lastBusyError;
    for (var attempt = 0; attempt < 3; attempt++) {
      try {
        result = await FCllama.instance()?.completion(
          _contextId!,
          prompt: wrapped,
          temperature: 0.25,
          nPredict: 448,
          topK: 40,
          topP: 0.9,
          penaltyRepeat: 1.1,
          stop: ['<|user|>', '<|end|>', '<|eot_id|>'],
        );
        lastBusyError = null;
        break;
      } catch (error) {
        if (!_isContextBusy(error)) rethrow;
        lastBusyError = error;
        if (attempt < 2) {
          await Future<void>.delayed(Duration(milliseconds: 400 * (attempt + 1)));
        }
      }
    }

    if (lastBusyError != null) {
      throw Exception(
        'El modelo local está terminando otra tarea. Espera unos segundos y vuelve a intentarlo.',
      );
    }

    final text = result?['text']?.toString().trim() ?? '';
    if (text.isEmpty) throw Exception('El modelo local no generó una respuesta.');
    return text;
  }
}
