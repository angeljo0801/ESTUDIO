import 'package:flutter/services.dart';

class OnDeviceTranslationService {
  static const MethodChannel _channel = MethodChannel('com.memora/translation');

  static Future<void> warmUpSpanish() async {
    try {
      await _channel.invokeMethod<void>('prepareSpanish');
    } catch (_) {
      // Translation can still be requested later; do not block chat startup.
    }
  }

  static Future<String> toSpanish(String text) async {
    final clean = text.trim();
    if (clean.isEmpty) return clean;
    final translated = await _channel.invokeMethod<String>(
      'translateToSpanish',
      {'text': clean},
    );
    final result = translated?.trim() ?? '';
    if (result.isEmpty) {
      throw Exception('The on-device translator returned an empty result.');
    }
    return result;
  }
}
