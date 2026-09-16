import 'models.dart';

class KnowledgeRetriever {
  static String buildContext({
    required List<StudyGuide> guides,
    required String query,
    int maxChars = 12000,
    int maxChunks = 10,
    bool allowUnmatchedFallback = true,
  }) {
    if (guides.isEmpty) return '(No assigned knowledge bases)';

    final terms = _terms(query);
    final chunks = <_Chunk>[];

    for (final guide in guides) {
      final normalized = guide.text.replaceAll('\r\n', '\n').trim();
      if (normalized.isEmpty) continue;
      final parts = _chunk(normalized, 900);
      for (final raw in parts) {
        final text = raw.trim();
        if (text.isEmpty) continue;
        var score = 0.0;
        final lower = text.toLowerCase();
        final title = guide.title.toLowerCase();
        for (final term in terms) {
          if (title.contains(term)) score += 3;
          final matches = term.allMatches(lower).length;
          if (matches > 0) score += 1 + matches.clamp(0, 4).toDouble();
        }
        if (terms.isEmpty) score = 1;
        chunks.add(_Chunk(guide: guide, text: text, score: score));
      }
    }

    if (chunks.isEmpty) return '(The assigned guides contain no usable text)';
    chunks.sort((a, b) => b.score.compareTo(a.score));

    var selected = chunks.where((c) => c.score > 0).take(maxChunks).toList();
    if (selected.isEmpty && allowUnmatchedFallback) {
      selected = chunks.take(maxChunks).toList();
    }
    if (selected.isEmpty) return '(No matching evidence found in the assigned guides)';

    final out = StringBuffer();
    var used = 0;
    for (final chunk in selected) {
      final header = '\n=== ${chunk.guide.title} [${chunk.guide.sourceType}] ===\n';
      final remaining = maxChars - used - header.length;
      if (remaining <= 200) break;
      final body = chunk.text.length > remaining
          ? chunk.text.substring(0, remaining)
          : chunk.text;
      out.write(header);
      out.write(body);
      used += header.length + body.length;
      if (used >= maxChars) break;
    }
    return out.toString().trim();
  }

  static List<String> _chunk(String text, int size) {
    final paragraphs = text
        .split(RegExp(r'\n{2,}'))
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();
    final result = <String>[];
    var current = StringBuffer();
    for (final paragraph in paragraphs) {
      if (current.isNotEmpty && current.length + paragraph.length + 2 > size) {
        result.add(current.toString());
        current = StringBuffer();
      }
      if (paragraph.length > size * 2) {
        if (current.isNotEmpty) {
          result.add(current.toString());
          current = StringBuffer();
        }
        for (var start = 0; start < paragraph.length; start += size) {
          final end = (start + size).clamp(0, paragraph.length).toInt();
          result.add(paragraph.substring(start, end));
        }
      } else {
        if (current.isNotEmpty) current.write('\n\n');
        current.write(paragraph);
      }
    }
    if (current.isNotEmpty) result.add(current.toString());
    return result;
  }

  static Set<String> _terms(String query) {
    const stop = {
      'para','como','que','qué','con','del','las','los','una','uno','unos','unas',
      'por','porque','sobre','desde','hasta','esto','esta','este','algo','quiero',
      'dime','decir','hacer','cuál','cual','cuando','donde','dónde','the','and','for',
      'with','from','this','that','what','how','are','you','your','tell','give','something',
      'random','guide','content','please','about','mention'
    };
    return query
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-záéíóúüñ0-9:_-]+'), ' ')
        .split(RegExp(r'\s+'))
        .where((e) => e.length >= 3 && !stop.contains(e))
        .take(20)
        .toSet();
  }
}

class _Chunk {
  const _Chunk({required this.guide, required this.text, required this.score});
  final StudyGuide guide;
  final String text;
  final double score;
}
