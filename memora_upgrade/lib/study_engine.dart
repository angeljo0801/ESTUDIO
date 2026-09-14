import 'dart:math';

import 'models.dart';

class StudyEngine {
  static final Set<String> _stopWords = {
    'porque', 'cuando', 'donde', 'desde', 'hasta', 'sobre', 'entre', 'para', 'como',
    'esta', 'este', 'estos', 'estas', 'tiene', 'tienen', 'puede', 'pueden', 'tambien',
    'that', 'this', 'these', 'those', 'with', 'from', 'into', 'about', 'which', 'their',
    'there', 'where', 'when', 'while', 'have', 'has', 'been', 'being', 'would', 'could',
    'should', 'through', 'between', 'using', 'used', 'than', 'then', 'more', 'most',
  };

  static StudyGuide buildGuide({
    required String title,
    required String sourceType,
    required String sourceName,
    required String text,
  }) {
    final clean = _normalize(text);
    final now = DateTime.now();
    return StudyGuide(
      id: now.microsecondsSinceEpoch.toString(),
      title: title.trim().isEmpty ? 'Guía sin título' : title.trim(),
      sourceType: sourceType,
      sourceName: sourceName,
      text: clean,
      summary: buildSummary(clean),
      cards: buildCards(clean),
      createdAt: now,
    );
  }

  static String buildSummary(String text) {
    final sentences = _sentences(text)
        .where((s) => s.length >= 35 && s.length <= 320)
        .toList();
    if (sentences.isEmpty) {
      return text.length <= 700 ? text : '${text.substring(0, 700)}…';
    }

    final frequencies = <String, int>{};
    for (final sentence in sentences) {
      for (final word in _words(sentence)) {
        if (word.length < 6 || _stopWords.contains(word)) continue;
        frequencies[word] = (frequencies[word] ?? 0) + 1;
      }
    }

    final scored = <({String text, double score, int index})>[];
    for (var i = 0; i < sentences.length; i++) {
      final sentence = sentences[i];
      var score = 0.0;
      for (final word in _words(sentence)) {
        score += (frequencies[word] ?? 0).toDouble();
      }
      score /= max(1, _words(sentence).length);
      if (i < 4) score += 1.4;
      scored.add((text: sentence, score: score, index: i));
    }
    scored.sort((a, b) => b.score.compareTo(a.score));
    final selected = scored.take(min(6, scored.length)).toList()
      ..sort((a, b) => a.index.compareTo(b.index));
    return selected.map((e) => '• ${e.text.trim()}').join('\n\n');
  }

  static List<StudyCard> buildCards(String text) {
    final cards = <StudyCard>[];
    final seen = <String>{};
    var currentTopic = '';
    var counter = 0;
    final now = DateTime.now();

    void addCard(String question, String answer, String source) {
      final q = question.trim();
      final a = answer.trim();
      if (q.length < 5 || a.length < 2) return;
      final key = '${q.toLowerCase()}|${a.toLowerCase()}';
      if (!seen.add(key)) return;
      cards.add(StudyCard(
        id: '${now.microsecondsSinceEpoch}-${counter++}',
        question: q,
        answer: a,
        source: source,
        dueAt: now,
      ));
    }

    final lines = text
        .replaceAll('\r', '')
        .split('\n')
        .map((line) => line.replaceAll(RegExp(r'[\t ]+'), ' ').trim())
        .where((line) => line.isNotEmpty)
        .toList();

    final definitionRegex = RegExp(
      r'^(.{2,90}?)\s+(es|son|significa|se define como|se refiere a|is|are|means|refers to)\s+(.{8,300})$',
      caseSensitive: false,
    );

    for (final raw in lines) {
      final line = raw.replaceFirst(RegExp(r'^[\-•*\d\s\.\)\(]+'), '').trim();
      if (line.isEmpty) continue;

      final looksLikeHeading = line.length <= 80 &&
          !RegExp(r'[\.!?;:]$').hasMatch(line) &&
          _words(line).length <= 10;
      if (looksLikeHeading) currentTopic = line;

      final colonIndex = line.indexOf(':');
      if (colonIndex >= 2 && colonIndex <= 90 && line.length - colonIndex > 8) {
        final term = line.substring(0, colonIndex).trim();
        final definition = line.substring(colonIndex + 1).trim();
        if (_words(term).length <= 12 && definition.length >= 10) {
          addCard('Explica: $term', definition, currentTopic);
        }
      }

      final match = definitionRegex.firstMatch(line);
      if (match != null) {
        final term = match.group(1)!.trim();
        final definition = match.group(3)!.trim();
        addCard('¿Qué es o qué significa $term?', definition, currentTopic);
      }

      if (cards.length >= 220) break;
    }

    for (final sentence in _sentences(text)) {
      if (cards.length >= 220) break;
      if (sentence.length < 35 || sentence.length > 300) continue;
      final keyword = _bestKeyword(sentence);
      if (keyword == null) continue;
      final blanked = sentence.replaceFirst(
        RegExp(RegExp.escape(keyword), caseSensitive: false),
        '______',
      );
      if (blanked == sentence) continue;
      addCard('Completa la idea:\n$blanked', keyword, currentTopic);
    }

    if (cards.length < 12) {
      for (final raw in lines) {
        if (cards.length >= 40) break;
        final line = raw.replaceFirst(RegExp(r'^[\-•*\d\s\.\)\(]+'), '').trim();
        if (line.length < 25 || line.length > 260) continue;
        final words = _words(line);
        if (words.length < 5) continue;
        final cue = words.take(min(6, words.length)).join(' ');
        addCard('Explica esta idea: $cue…', line, currentTopic);
      }
    }

    return cards;
  }

  static String _normalize(String text) {
    var result = text.replaceAll('\r\n', '\n').replaceAll('\r', '\n');
    result = result.replaceAll(RegExp(r'[ \t]+'), ' ');
    result = result.replaceAll(RegExp(r'\n{3,}'), '\n\n');
    return result.trim();
  }

  static List<String> _sentences(String text) {
    final compact = text.replaceAll(RegExp(r'\s+'), ' ').trim();
    if (compact.isEmpty) return const [];
    return compact
        .split(RegExp(r'(?<=[.!?])\s+|\s*[•]\s*'))
        .map((s) => s.trim())
        .where((s) => s.isNotEmpty)
        .toList();
  }

  static List<String> _words(String text) => RegExp(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9'-]+")
      .allMatches(text)
      .map((m) => m.group(0)!.toLowerCase())
      .toList();

  static String? _bestKeyword(String sentence) {
    final originalWords = RegExp(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9'-]{5,}")
        .allMatches(sentence)
        .map((m) => m.group(0)!)
        .where((word) => !_stopWords.contains(word.toLowerCase()))
        .toList();
    if (originalWords.isEmpty) return null;
    originalWords.sort((a, b) => b.length.compareTo(a.length));
    return originalWords.first;
  }
}
