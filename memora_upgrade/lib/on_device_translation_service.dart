import 'package:google_mlkit_translation/google_mlkit_translation.dart';

class OnDeviceTranslationService {
  static final OnDeviceTranslatorModelManager _models =
      OnDeviceTranslatorModelManager();
  static OnDeviceTranslator? _translator;
  static Future<void>? _prepareFuture;

  static Future<void> warmUpSpanish() async {
    try {
      await _prepare();
    } catch (_) {
      // Translation can still be requested later; do not block chat startup.
    }
  }

  static Future<void> _prepare() {
    return _prepareFuture ??= _prepareInternal();
  }

  static Future<void> _prepareInternal() async {
    final english = TranslateLanguage.english.bcpCode;
    final spanish = TranslateLanguage.spanish.bcpCode;
    if (!await _models.isModelDownloaded(english)) {
      await _models.downloadModel(english, isWifiRequired: false);
    }
    if (!await _models.isModelDownloaded(spanish)) {
      await _models.downloadModel(spanish, isWifiRequired: false);
    }
    _translator ??= OnDeviceTranslator(
      sourceLanguage: TranslateLanguage.english,
      targetLanguage: TranslateLanguage.spanish,
    );
  }

  static Future<String> toSpanish(String text) async {
    final clean = text.trim();
    if (clean.isEmpty) return clean;
    try {
      await _prepare();
    } catch (_) {
      // Allow a later tap to retry after connectivity is restored.
      _prepareFuture = null;
      rethrow;
    }
    final translated = (await _translator!.translateText(clean)).trim();
    if (translated.isEmpty) {
      throw Exception('The on-device translator returned an empty result.');
    }
    return translated;
  }
}
