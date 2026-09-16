from pathlib import Path
import re

p = Path('lib/tutor_page.dart')
s = p.read_text()

# Make broad/random requests robust in Spanish and English.
old_broad = r'''  bool _isBroadGuideRequest(String value) {
    final text = value.toLowerCase();
    return RegExp(
      r'\b(random|anything|something|any fact|any concept|from the guide|from my guide|de la guía|de mi guía|algo random|algo al azar|cualquier cosa|mencióname algo|menciona algo)\b',
      caseSensitive: false,
    ).hasMatch(text);
  }
'''
new_broad = r'''  bool _isBroadGuideRequest(String value) {
    final text = value.toLowerCase().trim();
    return RegExp(
      r'\b(random|aleatorio|aleatoria|anything|something|any fact|any concept|from the guide|from my guide|de la guía|de mi guía|algo random|dato random|un dato random|algo al azar|dato al azar|un dato al azar|cualquier cosa|cualquier dato|cualquier concepto|dame un dato|dime un dato|dime algo|mencióname algo|menciona algo|sorpréndeme|sorprendeme)\b',
      caseSensitive: false,
    ).hasMatch(text);
  }
'''
if old_broad not in s:
    raise RuntimeError('v1.31 broad guide request helper not found')
s = s.replace(old_broad, new_broad, 1)

pattern = re.compile(
    r"  Future<String> _randomGuideContext\(List<StudyGuide> guides, \{int maxChars = 1200\}\) async \{.*?\n  \}\n\n  String _groundedFallback",
    re.S,
)

replacement = r'''  Future<String> _randomGuideContext(List<StudyGuide> guides, {int maxChars = 1200}) async {
    final candidates = <({StudyGuide guide, String text, String key})>[];
    final seenKeys = <String>{};

    void addCandidate(StudyGuide guide, String raw, String key) {
      final text = raw
          .replaceAll('\r', ' ')
          .replaceAll(RegExp(r'\s+'), ' ')
          .trim();
      if (text.length < 20) return;
      final clipped = text.length <= maxChars ? text : text.substring(0, maxChars).trim();
      if (!seenKeys.add(key)) return;
      candidates.add((guide: guide, text: clipped, key: key));
    }

    for (final guide in guides) {
      final clean = guide.text
          .replaceAll('\r', ' ')
          .replaceAll(RegExp(r'\s+'), ' ')
          .trim();

      if (clean.isNotEmpty) {
        final sentences = clean
            .split(RegExp(r'(?<=[.!?])\s+'))
            .map((e) => e.trim())
            .where((e) => e.length >= 35)
            .toList();

        final blocks = <String>[];
        if (sentences.length >= 2) {
          var current = '';
          for (final sentence in sentences) {
            if (current.isNotEmpty && current.length >= 180 &&
                current.length + sentence.length + 1 > 620) {
              blocks.add(current.trim());
              current = sentence;
            } else {
              current = current.isEmpty ? sentence : '$current $sentence';
            }
          }
          if (current.trim().length >= 60) blocks.add(current.trim());
        }

        if (blocks.isEmpty) {
          const target = 520;
          var start = 0;
          while (start < clean.length) {
            var end = min(start + target, clean.length);
            if (end < clean.length) {
              final space = clean.lastIndexOf(' ', end);
              if (space > start + 180) end = space;
            }
            final block = clean.substring(start, end).trim();
            if (block.length >= 60) blocks.add(block);
            start = end;
          }
        }

        for (var i = 0; i < blocks.length; i++) {
          final raw = blocks[i];
          final fingerprint = raw
              .toLowerCase()
              .replaceAll(RegExp(r'\s+'), ' ')
              .substring(0, min(180, raw.length));
          addCandidate(guide, raw, 'text:${guide.id}:$i:$fingerprint');
        }
      }

      // AI-generated study cards are a reliable secondary knowledge source.
      // This is especially important for imported PDFs whose extracted raw text
      // may later be unavailable while their generated cards remain persisted.
      for (final card in guide.cards) {
        final question = card.question.trim();
        final answer = card.answer.trim();
        if (answer.length < 12) continue;
        final cardBody = question.isEmpty
            ? answer
            : 'Topic: $question\nAnswer: $answer';
        addCandidate(guide, cardBody, 'card:${guide.id}:${card.id}');
      }
    }

    if (candidates.isEmpty) return '';

    final prefs = await SharedPreferences.getInstance();
    final historyKey = 'memora_random_excerpt_history_${activeTutor.id}';
    var recent = prefs.getStringList(historyKey) ?? <String>[];

    var available = candidates.where((c) => !recent.contains(c.key)).toList();
    if (available.isEmpty) {
      recent = <String>[];
      available = List.of(candidates);
    }

    available.shuffle(Random(DateTime.now().microsecondsSinceEpoch));
    final chosen = available.first;

    recent.remove(chosen.key);
    recent.add(chosen.key);
    final remember = min(36, max(1, candidates.length - 1));
    if (recent.length > remember) {
      recent = recent.sublist(recent.length - remember);
    }
    await prefs.setStringList(historyKey, recent);

    final sourceLabel = chosen.key.startsWith('card:') ? 'AI study card' : chosen.guide.sourceType;
    return '=== ${chosen.guide.title} [$sourceLabel] ===\n${chosen.text}';
  }

  String _groundedFallback'''

s, n = pattern.subn(lambda _m: replacement, s, count=1)
if n != 1:
    raise RuntimeError('v1.31 random guide context helper not found')

# If an AI card is used and the model fails/echoes, return the actual grounded
# card answer instead of the generic "could not find" message.
old_fallback = r'''    if (clean.isEmpty) return 'I could not find that in the assigned guides.';
    final sentences = clean
'''
new_fallback = r'''    if (clean.isEmpty) return 'I could not find that in the assigned guides.';
    final cardAnswer = RegExp(r'(?:^|\s)Answer:\s*(.+)$', caseSensitive: false)
        .firstMatch(clean)
        ?.group(1)
        ?.trim();
    if (cardAnswer != null && cardAnswer.isNotEmpty) {
      return cardAnswer;
    }
    final sentences = clean
'''
if old_fallback not in s:
    raise RuntimeError('v1.31 grounded fallback anchor not found')
s = s.replace(old_fallback, new_fallback, 1)

p.write_text(s)
print('Memora v1.31 random tutor AI-card fallback patch applied successfully')
