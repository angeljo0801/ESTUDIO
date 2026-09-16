from pathlib import Path
import re

p = Path('lib/tutor_page.dart')
s = p.read_text()

pattern = re.compile(
    r"  String _randomGuideContext\(List<StudyGuide> guides, \{int maxChars = 4500\}\) \{.*?\n  \}\n\n  String _groundedFallback",
    re.S,
)
replacement = r'''  Future<String> _randomGuideContext(List<StudyGuide> guides, {int maxChars = 1200}) async {
    final candidates = <({StudyGuide guide, String text, String key})>[];
    final seenKeys = <String>{};

    for (final guide in guides) {
      final clean = guide.text
          .replaceAll('\r', ' ')
          .replaceAll(RegExp(r'\s+'), ' ')
          .trim();
      if (clean.isEmpty) continue;

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

      for (final raw in blocks) {
        final text = raw.length <= maxChars ? raw : raw.substring(0, maxChars).trim();
        if (text.length < 60) continue;
        final fingerprint = text
            .toLowerCase()
            .replaceAll(RegExp(r'\s+'), ' ')
            .substring(0, min(180, text.length));
        final key = '${guide.title}|$fingerprint';
        if (!seenKeys.add(key)) continue;
        candidates.add((guide: guide, text: text, key: key));
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
    final remember = min(18, max(1, candidates.length - 1));
    if (recent.length > remember) {
      recent = recent.sublist(recent.length - remember);
    }
    await prefs.setStringList(historyKey, recent);

    return '=== ${chosen.guide.title} [${chosen.guide.sourceType}] ===\n${chosen.text}';
  }

  String _groundedFallback'''

s, n = pattern.subn(lambda _m: replacement, s, count=1)
if n != 1:
    raise RuntimeError('v1.30 random guide context helper not found')

old_history = """    final history = (broadRequest || simpleRequest)
        ? current.conversationContext(maxChars: 700, maxMessages: 4)
        : _conversationHistory();
"""
new_history = """    final history = broadRequest
        ? ''
        : simpleRequest
            ? current.conversationContext(maxChars: 700, maxMessages: 4)
            : _conversationHistory();
"""
if old_history not in s:
    raise RuntimeError('v1.30 broad history anchor not found')
s = s.replace(old_history, new_history, 1)

old_context = "? _randomGuideContext(guides, maxChars: contextChars)"
new_context = "? await _randomGuideContext(guides, maxChars: contextChars)"
if old_context not in s:
    raise RuntimeError('v1.30 random context call not found')
s = s.replace(old_context, new_context, 1)

s = s.replace(
    "Answer in 1-2 concise sentences. Pick one concrete point from the supplied guide excerpt and explain it directly.",
    "Answer in 1-2 concise sentences. Use only the supplied guide excerpt. Pick one concrete point from this excerpt and do not default to a fact from an earlier random request.",
    1,
)

p.write_text(s)
print('Memora v1.30 non-repeating random tutor patch applied successfully')

import os
_v131 = Path(os.environ['GITHUB_WORKSPACE']) / 'memora_upgrade' / 'v131_random_tutor_card_fallback_patch.py'
exec(compile(_v131.read_text(), str(_v131), 'exec'))
