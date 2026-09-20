import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'device_llm_service.dart';

class AiService {
  static const MethodChannel _managerChannel =
      MethodChannel('com.angelapps.local_ai_manager/client');
  static http.Client? _activeHttpClient;
  static int _onlineSerial = 0;
  static int? _activeOnlineId;
  static final Set<int> _cancelledOnline = <int>{};

  static String get localAccelerationLabel => DeviceLlmService.accelerationLabel;

  static Future<void> releaseDeviceModel() async {
    await DeviceLlmService.releaseModel(stopGeneration: true);
  }

  static Future<void> cancelCurrent() async {
    final id = _activeOnlineId;
    if (id != null) _cancelledOnline.add(id);
    final client = _activeHttpClient;
    _activeHttpClient = null;
    try {
      client?.close();
    } catch (_) {}
    await DeviceLlmService.stopCurrent();
  }

  static Future<T> _runOnline<T>(Future<T> Function(http.Client client, int requestId) action) async {
    final id = ++_onlineSerial;
    final client = http.Client();
    _activeOnlineId = id;
    _activeHttpClient = client;
    try {
      final value = await action(client, id);
      if (_cancelledOnline.contains(id)) {
        throw Exception('Generación cancelada.');
      }
      return value;
    } catch (e) {
      if (_cancelledOnline.contains(id)) {
        throw Exception('Generación cancelada.');
      }
      rethrow;
    } finally {
      try {
        client.close();
      } catch (_) {}
      _cancelledOnline.remove(id);
      if (_activeOnlineId == id) _activeOnlineId = null;
      if (identical(_activeHttpClient, client)) _activeHttpClient = null;
    }
  }

  static Future<String> askConfigured({
    required String prompt,
    String? deviceModeOverride,
    String? providerOverride,
    String responseMode = 'normal',
    void Function(String text)? onPartial,
    List<String> imagePaths = const [],
  }) async {
    final prefs = await SharedPreferences.getInstance();

    final explicit = providerOverride?.trim();
    if (explicit == 'private' || explicit == 'shared') {
      return DeviceLlmService.askWithMode(
        prompt,
        mode: explicit!,
        responseMode: responseMode,
        onPartial: onPartial,
      );
    }
    if (deviceModeOverride == 'private' || deviceModeOverride == 'shared') {
      return DeviceLlmService.askWithMode(
        prompt,
        mode: deviceModeOverride!,
        responseMode: responseMode,
        onPartial: onPartial,
      );
    }

    final provider = (explicit == null || explicit.isEmpty || explicit == 'global')
        ? (prefs.getString('llm_provider') ?? 'gemini')
        : explicit;

    if (provider == 'device') {
      return DeviceLlmService.ask(
        prompt,
        responseMode: responseMode,
        onPartial: onPartial,
      );
    }
    if (provider == 'gemini') {
      final key = prefs.getString('gemini_key')?.trim() ?? '';
      if (key.isEmpty) {
        throw Exception('Configura la clave de Gemini en Ajustes de IA.');
      }
      final result = await _runOnline((client, _) => askGemini(
            client: client,
            apiKey: key,
            prompt: prompt,
            imagePaths: imagePaths,
          ));
      onPartial?.call(result);
      return result;
    }
    if (provider == 'openai') {
      final key = prefs.getString('openai_key')?.trim() ?? '';
      final model = prefs.getString('openai_model')?.trim() ?? '';
      final baseUrl = prefs.getString('openai_base_url')?.trim() ??
          'https://api.openai.com/v1';
      if (key.isEmpty || model.isEmpty) {
        throw Exception('Configura la clave y el modelo online en Ajustes de IA.');
      }
      final result = await _runOnline((client, _) => askOpenAiCompatible(
            client: client,
            baseUrl: baseUrl,
            apiKey: key,
            model: model,
            prompt: prompt,
            imagePaths: imagePaths,
          ));
      onPartial?.call(result);
      return result;
    }

    if (provider == 'manager') {
      try {
        final managerPrompt = prompt.length <= 5200
            ? prompt
            : '${prompt.substring(0, 1400)}\n\n'
                '[Contexto intermedio recortado para mantener estable el modelo local]\n\n'
                '${prompt.substring(prompt.length - 3600)}';
        final managerMaxTokens = responseMode == 'fast'
            ? 160
            : responseMode == 'deep'
                ? 384
                : 280;
        final answer = await _managerChannel
            .invokeMethod<String>('ask', {
              'prompt': managerPrompt,
              'system':
                  'Eres la inteligencia de Memora. Sigue cuidadosamente las instrucciones específicas incluidas en la solicitud.',
              'maxTokens': managerMaxTokens,
              'temperature': 0.25,
            })
            .timeout(const Duration(minutes: 6));
        final text = (answer ?? '').trim();
        if (text.isEmpty) {
          throw Exception('Local AI Manager no devolvió una respuesta.');
        }
        onPartial?.call(text);
        return text;
      } on PlatformException catch (e) {
        throw Exception(
          e.message?.trim().isNotEmpty == true
              ? e.message!.trim()
              : 'No pude comunicarme con Local AI Manager.',
        );
      }
    }

    if (provider == 'local' || provider == 'ollama') {
      final baseUrl = prefs.getString('local_base_url')?.trim() ??
          'http://127.0.0.1:11434/v1';
      final model = prefs.getString('local_model')?.trim() ?? '';
      final key = prefs.getString('local_key')?.trim() ?? '';
      if (model.isEmpty) {
        throw Exception('Indica el nombre del modelo local/Ollama en Ajustes de IA.');
      }
      final result = await _runOnline((client, _) => askOpenAiCompatible(
            client: client,
            baseUrl: baseUrl,
            apiKey: key,
            model: model,
            prompt: prompt,
          ));
      onPartial?.call(result);
      return result;
    }

    throw Exception('Fuente de IA no reconocida: $provider');
  }

  static Future<String> askGemini({
    required http.Client client,
    required String apiKey,
    required String prompt,
    List<String> imagePaths = const [],
  }) async {
    final parts = <Map<String, dynamic>>[
      {'text': prompt},
    ];
    for (final path in imagePaths.take(4)) {
      final file = File(path);
      if (!await file.exists()) continue;
      final bytes = await file.readAsBytes();
      if (bytes.isEmpty) continue;
      parts.add({
        'inline_data': {
          'mime_type': _imageMime(path),
          'data': base64Encode(bytes),
        },
      });
    }

    final uri = Uri.parse(
      'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=$apiKey',
    );
    final response = await client
        .post(
          uri,
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'contents': [
              {'parts': parts},
            ],
            'generationConfig': {'temperature': 0.25},
          }),
        )
        .timeout(const Duration(minutes: 3));
    if (response.statusCode != 200) {
      throw Exception(
        'Gemini respondió ${response.statusCode}: ${_message(response.body)}',
      );
    }
    final data = jsonDecode(response.body);
    return data['candidates']?[0]?['content']?['parts']?[0]?['text'] ??
        'No pude generar una respuesta.';
  }

  static Future<String> askOpenAiCompatible({
    required http.Client client,
    required String baseUrl,
    required String apiKey,
    required String model,
    required String prompt,
    List<String> imagePaths = const [],
  }) async {
    final cleanBase = baseUrl.replaceAll(RegExp(r'/+$'), '');
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (apiKey.isNotEmpty) headers['Authorization'] = 'Bearer $apiKey';

    dynamic userContent = prompt;
    if (imagePaths.isNotEmpty) {
      final content = <Map<String, dynamic>>[
        {'type': 'text', 'text': prompt},
      ];
      for (final path in imagePaths.take(4)) {
        final file = File(path);
        if (!await file.exists()) continue;
        final bytes = await file.readAsBytes();
        if (bytes.isEmpty) continue;
        content.add({
          'type': 'image_url',
          'image_url': {
            'url': 'data:${_imageMime(path)};base64,${base64Encode(bytes)}',
          },
        });
      }
      userContent = content;
    }

    final response = await client
        .post(
          Uri.parse('$cleanBase/chat/completions'),
          headers: headers,
          body: jsonEncode({
            'model': model,
            'messages': [
              {
                'role': 'system',
                'content':
                    'Eres la inteligencia de Memora. Sigue cuidadosamente las instrucciones específicas incluidas en la solicitud.',
              },
              {'role': 'user', 'content': userContent},
            ],
            'temperature': 0.25,
          }),
        )
        .timeout(const Duration(minutes: 5));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        'El modelo respondió ${response.statusCode}: ${_message(response.body)}',
      );
    }
    final data = jsonDecode(response.body);
    return data['choices']?[0]?['message']?['content'] ??
        'No pude generar una respuesta.';
  }

  static String userFacingError(Object error) {
    var text = error.toString().trim();
    final lower = text.toLowerCase();
    if (lower.contains('generación cancelada') || lower.contains('generation cancelled')) {
      return 'Generación cancelada.';
    }
    if (lower.contains('already generating') ||
        lower.contains('context is busy') ||
        lower.contains('context busy')) {
      return 'El modelo local está ocupado con otra tarea. Espera unos segundos y vuelve a intentarlo.';
    }
    if (text.startsWith('Exception: ')) {
      text = text.substring('Exception: '.length).trim();
    }
    if (text.startsWith('PlatformException(')) {
      final firstLine = text.split('\n').first;
      final parts = firstLine.split(',');
      if (parts.length >= 2) {
        final message = parts[1].trim();
        if (message.isNotEmpty) return message;
      }
      return 'La IA encontró un error interno. Inténtalo nuevamente.';
    }
    if (text.length > 320) {
      return '${text.substring(0, 320).trim()}…';
    }
    return text.isEmpty ? 'La IA no pudo completar la solicitud.' : text;
  }

  static String _imageMime(String path) {
    final lower = path.toLowerCase();
    if (lower.endsWith('.png')) return 'image/png';
    if (lower.endsWith('.webp')) return 'image/webp';
    if (lower.endsWith('.gif')) return 'image/gif';
    if (lower.endsWith('.heic') || lower.endsWith('.heif')) return 'image/heic';
    return 'image/jpeg';
  }

  static String _message(String body) {
    try {
      final data = jsonDecode(body);
      return data['error']?['message']?.toString() ?? body;
    } catch (_) {
      return body.length > 250 ? body.substring(0, 250) : body;
    }
  }
}
