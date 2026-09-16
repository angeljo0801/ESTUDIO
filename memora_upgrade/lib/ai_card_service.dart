import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:shared_preferences/shared_preferences.dart';

import 'ai_service.dart';
import 'models.dart';

class SystemAiDescriptor {
  const SystemAiDescriptor({
    required this.provider,
    required this.label,
    required this.ready,
  });

  final String provider;
  final String label;
  final bool ready;

  bool get isDirectGguf =>
      provider == 'device' || provider == 'private' || provider == 'shared';

  bool get isLocalServer => provider == 'local' || provider == 'ollama';
}

class AiCardService {
  static const int defaultTarget = 50;

  static Future<SystemAiDescriptor> systemAi() async {
    final prefs = await SharedPreferences.getInstance();
    final provider = (prefs.getString('llm_provider') ?? 'gemini').trim();

    switch (provider) {
      case 'local':
      case 'ollama':
        final model = (prefs.getString('local_model') ?? '').trim();
        return SystemAiDescriptor(
          provider: 'local',
          label: model.isEmpty ? 'Ollama' : 'Ollama • $model',
          ready: model.isNotEmpty,
        );
      case 'openai':
        final model = (prefs.getString('openai_model') ?? '').trim();
        final key = (prefs.getString('openai_key') ?? '').trim();
        return SystemAiDescriptor(
          provider: 'openai',
          label: model.isEmpty ? 'OpenAI / compatible' : 'OpenAI • $model',
          ready: model.isNotEmpty && key.isNotEmpty,
        );
      case 'device':
        final mode = (prefs.getString('device_model_mode') ?? 'private').trim();
        if (mode == 'shared') {
          final uri = (prefs.getString('shared_model_uri') ?? '').trim();
          final name = (prefs.getString('shared_model_name') ?? '').trim();
          return SystemAiDescriptor(
            provider: 'device',
            label: 'Local GGUF • ${name.isEmpty ? 'shared model' : name}',
            ready: uri.isNotEmpty,
          );
        }
        final path = (prefs.getString('device_model_path') ?? '').trim();
        final name = path.isEmpty ? '' : path.split(Platform.pathSeparator).last;
        return SystemAiDescriptor(
          provider: 'device',
          label: 'Local GGUF • ${name.isEmpty ? 'private model' : name}',
          ready: path.isNotEmpty && await File(path).exists(),
        );
      case 'private':
        final path = (prefs.getString('device_model_path') ?? '').trim();
        final name = path.isEmpty ? '' : path.split(Platform.pathSeparator).last;
        return SystemAiDescriptor(
          provider: 'private',
          label: 'Local GGUF • ${name.isEmpty ? 'private model' : name}',
          ready: path.isNotEmpty && await File(path).exists(),
        );
      case 'shared':
        final uri = (prefs.getString('shared_model_uri') ?? '').trim();
        final name = (prefs.getString('shared_model_name') ?? '').trim();
        return SystemAiDescriptor(
          provider: 'shared',
          label: 'Local GGUF • ${name.isEmpty ? 'shared model' : name}',
          ready: uri.isNotEmpty,
        );
      case 'gemini':
      default:
        final key = (prefs.getString('gemini_key') ?? '').trim();
        return SystemAiDescriptor(
          provider: 'gemini',
          label: 'Gemini • 2.5 Flash',
          ready: key.isNotEmpty,
        );
    }
  }

  static Future<List<StudyCard>> generateCards(
    StudyGuide guide, {
    int target = defaultTarget,
    void Function(int generated, int target)? onProgress,
  }) async {
    final material = guide.text.replaceAll('\r', '').trim();
    if (material.length < 40) {
      throw StateError('This guide does not contain enough extracted text to create cards.');
    }

    final ai = await systemAi();
    if (!ai.ready) {
      throw StateError(
        'The system AI is not ready. Configure Gemini, OpenAI, Ollama, or a local GGUF first.',
      );
    }

    final safeTarget = target.clamp(10, 120).toInt();
    final chunkChars = ai.isDirectGguf
        ? 2600
        : ai.isLocalServer
            ? 4200
            : 7200;
    final batchSize = ai.isDirectGguf
        ? 4
        : ai.isLocalServer
            ? 6
            : 10;
    final chunks = _chunks(material, chunkChars);
    final cards = <StudyCard>[];
    final seenQuestions = <String>{};
    final oldByPair = <String, StudyCard>{
      for (final card in guide.cards)
        '${_key(card.question)}|${_key(card.answer)}': card,
    };
    final now = DateTime.now();
    var serial = 0;
    var attempt = 0;
    final minimumCalls = (safeTarget / batchSize).ceil();
    final maxAttempts = max(minimumCalls + 8, chunks.length * 3).clamp(10, 32).toInt();

    while (cards.length < safeTarget && attempt < maxAttempts) {
      final chunk = chunks[attempt % chunks.length];
      final needed = safeTarget - cards.length;
      final requestCount = min(batchSize + 2, needed + 2);
      final recent = cards.reversed.take(18).map((c) => c.question).toList().reversed;
      final prompt = '''Create $requestCount high-quality study flashcards from ONLY the MATERIAL SEGMENT below.

The cards are for serious learning, not word matching.
RULES:
- You MAY paraphrase, combine ideas, and derive a direct implication from the material. The wording does not have to be copied literally.
- Do NOT add outside facts that are not supported by the material.
- Prefer useful concepts, why/how, cause and effect, comparisons, applications, decisions, formulas, calculations, and relationships.
- Avoid vague fragments, isolated-word trivia, and questions such as "What does the content say about X?".
- Each question must be understandable by itself.
- Each answer must be concise but complete, normally 1-4 sentences.
- Make every new card meaningfully different from the cards to avoid below.
- Return ONLY a JSON array. No Markdown and no commentary.
- Exact item format: {"question":"...","answer":"...","source":"short topic label"}.

CARDS TO AVOID REPEATING:
${recent.isEmpty ? '(none yet)' : recent.map((q) => '- $q').join('\n')}

GUIDE: ${guide.title}
MATERIAL SEGMENT:
$chunk''';

      final raw = await AiService.askTaskConfigured(
        prompt: prompt,
        providerOverride: 'global',
        responseMode: ai.isDirectGguf ? 'normal' : (ai.isLocalServer ? 'normal' : 'deep'),
      );

      final parsed = _parseCards(raw);
      for (final item in parsed) {
        if (cards.length >= safeTarget) break;
        final question = _clean(item.$1);
        final answer = _clean(item.$2);
        final source = _clean(item.$3);
        if (!_usable(question, answer)) continue;
        final qKey = _key(question);
        if (!seenQuestions.add(qKey)) continue;
        final pairKey = '$qKey|${_key(answer)}';
        final old = oldByPair[pairKey];
        final card = StudyCard(
          id: old?.id ?? '${now.microsecondsSinceEpoch}-${serial++}',
          question: question.endsWith('?') ? question : '$question?',
          answer: answer,
          source: source.isEmpty ? guide.title : source,
          dueAt: old?.dueAt ?? now,
          intervalDays: old?.intervalDays ?? 0,
          ease: old?.ease ?? 2.5,
          correct: old?.correct ?? 0,
          wrong: old?.wrong ?? 0,
          streak: old?.streak ?? 0,
        );
        cards.add(card);
        onProgress?.call(cards.length, safeTarget);
      }
      attempt++;
    }

    if (cards.isEmpty) {
      throw StateError(
        'The selected system AI did not return any usable study cards for this guide.',
      );
    }
    return cards.take(safeTarget).toList();
  }

  static List<String> _chunks(String text, int maxChars) {
    final paragraphs = text
        .split(RegExp(r'\n{2,}'))
        .map((e) => e.replaceAll(RegExp(r'[\t ]+'), ' ').trim())
        .where((e) => e.isNotEmpty)
        .toList();
    final result = <String>[];
    var buffer = StringBuffer();

    void flush() {
      final value = buffer.toString().trim();
      if (value.isNotEmpty) result.add(value);
      buffer = StringBuffer();
    }

    for (final paragraph in paragraphs) {
      if (paragraph.length > maxChars) {
        flush();
        var start = 0;
        while (start < paragraph.length) {
          var end = min(start + maxChars, paragraph.length);
          if (end < paragraph.length) {
            final breakAt = paragraph.lastIndexOf(' ', end);
            if (breakAt > start + maxChars ~/ 2) end = breakAt;
          }
          result.add(paragraph.substring(start, end).trim());
          start = end;
          while (start < paragraph.length && paragraph[start] == ' ') start++;
        }
        continue;
      }
      if (buffer.isNotEmpty && buffer.length + paragraph.length + 2 > maxChars) {
        flush();
      }
      if (buffer.isNotEmpty) buffer.writeln('\n');
      buffer.write(paragraph);
    }
    flush();
    return result.isEmpty ? [text.substring(0, min(text.length, maxChars))] : result;
  }

  static List<(String, String, String)> _parseCards(String raw) {
    final out = <(String, String, String)>[];
    void addMap(Map<dynamic, dynamic> map) {
      final q = (map['question'] ?? map['q'] ?? map['pregunta'])?.toString() ?? '';
      final a = (map['answer'] ?? map['a'] ?? map['respuesta'])?.toString() ?? '';
      final s = (map['source'] ?? map['topic'] ?? map['tema'])?.toString() ?? '';
      if (q.trim().isNotEmpty && a.trim().isNotEmpty) out.add((q, a, s));
    }

    final start = raw.indexOf('[');
    final end = raw.lastIndexOf(']');
    if (start >= 0 && end > start) {
      try {
        final decoded = jsonDecode(raw.substring(start, end + 1));
        if (decoded is List) {
          for (final item in decoded.whereType<Map>()) addMap(item);
          if (out.isNotEmpty) return out;
        }
      } catch (_) {}
    }

    final objects = RegExp(r'\{[^{}]*\}', dotAll: true).allMatches(raw);
    for (final match in objects) {
      try {
        final decoded = jsonDecode(match.group(0)!);
        if (decoded is Map) addMap(decoded);
      } catch (_) {}
    }
    return out;
  }

  static bool _usable(String question, String answer) {
    if (question.length < 12 || question.length > 260) return false;
    if (answer.length < 12 || answer.length > 900) return false;
    if (_key(question) == _key(answer)) return false;
    if (answer.endsWith('?')) return false;
    if (RegExp(
      r'^(?:what does the content|what does work|what is or what does)\b',
      caseSensitive: false,
    ).hasMatch(question)) return false;
    final qWords = RegExp(r"[A-Za-z0-9À-ÿ']+").allMatches(question).length;
    final aWords = RegExp(r"[A-Za-z0-9À-ÿ']+").allMatches(answer).length;
    return qWords >= 4 && aWords >= 3;
  }

  static String _clean(String value) => value
      .replaceAll(RegExp(r'\s+'), ' ')
      .replaceAll(RegExp(r'^[\-•*\s]+|[\s]+$'), '')
      .trim();

  static String _key(String value) => value
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9áéíóúüñ]+'), ' ')
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim();
}
