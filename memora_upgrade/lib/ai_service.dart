import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'device_llm_service.dart';

class AiService {
  static Future<String> askConfigured({
    required String prompt,
    String? deviceModeOverride,
    String? providerOverride,
  }) async {
    final prefs = await SharedPreferences.getInstance();

    final explicit = providerOverride?.trim();
    if (explicit == 'private' || explicit == 'shared') {
      return DeviceLlmService.askWithMode(prompt, mode: explicit!);
    }
    if (deviceModeOverride == 'private' || deviceModeOverride == 'shared') {
      return DeviceLlmService.askWithMode(prompt, mode: deviceModeOverride!);
    }

    final provider = (explicit == null || explicit.isEmpty || explicit == 'global')
        ? (prefs.getString('llm_provider') ?? 'gemini')
        : explicit;

    if (provider == 'device') return DeviceLlmService.ask(prompt);
    if (provider == 'gemini') {
      final key = prefs.getString('gemini_key')?.trim() ?? '';
      if (key.isEmpty) {
        throw Exception('Configura la clave de Gemini en Ajustes de IA.');
      }
      return askGemini(apiKey: key, prompt: prompt);
    }
    if (provider == 'openai') {
      final key = prefs.getString('openai_key')?.trim() ?? '';
      final model = prefs.getString('openai_model')?.trim() ?? '';
      final baseUrl = prefs.getString('openai_base_url')?.trim() ??
          'https://api.openai.com/v1';
      if (key.isEmpty || model.isEmpty) {
        throw Exception('Configura la clave y el modelo online en Ajustes de IA.');
      }
      return askOpenAiCompatible(
        baseUrl: baseUrl,
        apiKey: key,
        model: model,
        prompt: prompt,
      );
    }

    if (provider == 'local' || provider == 'ollama') {
      final baseUrl = prefs.getString('local_base_url')?.trim() ??
          'http://127.0.0.1:11434/v1';
      final model = prefs.getString('local_model')?.trim() ?? '';
      final key = prefs.getString('local_key')?.trim() ?? '';
      if (model.isEmpty) {
        throw Exception('Indica el nombre del modelo local/Ollama en Ajustes de IA.');
      }
      return askOpenAiCompatible(
        baseUrl: baseUrl,
        apiKey: key,
        model: model,
        prompt: prompt,
      );
    }

    throw Exception('Fuente de IA no reconocida: $provider');
  }

  static Future<String> askGemini({
    required String apiKey,
    required String prompt,
  }) async {
    final uri = Uri.parse(
      'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=$apiKey',
    );
    final response = await http
        .post(
          uri,
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'contents': [
              {
                'parts': [
                  {'text': prompt},
                ],
              },
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
    required String baseUrl,
    required String apiKey,
    required String model,
    required String prompt,
  }) async {
    final cleanBase = baseUrl.replaceAll(RegExp(r'/+$'), '');
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (apiKey.isNotEmpty) headers['Authorization'] = 'Bearer $apiKey';
    final response = await http
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
              {'role': 'user', 'content': prompt},
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
    if (lower.contains('context is busy') || lower.contains('context busy')) {
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

  static String _message(String body) {
    try {
      final data = jsonDecode(body);
      return data['error']?['message']?.toString() ?? body;
    } catch (_) {
      return body.length > 250 ? body.substring(0, 250) : body;
    }
  }
}
