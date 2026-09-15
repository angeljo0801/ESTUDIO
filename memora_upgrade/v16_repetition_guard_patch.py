from pathlib import Path

p = Path('lib/device_llm_service.dart')
s = p.read_text()

anchor = "  static Future<String> _resolvePrivateModel(SharedPreferences p) async {"
helper = r'''  static bool _looksRepetitive(String text) {
    if (text.length < 40) return false;
    final lines = text
        .split('\n')
        .map((e) => e.trim().toLowerCase())
        .where((e) => e.isNotEmpty)
        .toList();
    if (lines.length >= 5) {
      final last = lines.last;
      if (last.length >= 3) {
        var same = 0;
        for (final line in lines.reversed.take(7)) {
          if (line == last) same++;
        }
        if (same >= 4) return true;
      }
    }

    final compact = text.toLowerCase().replaceAll(RegExp(r'\s+'), ' ').trim();
    if (compact.length >= 120) {
      for (final size in <int>[12, 18, 24, 32, 40]) {
        if (compact.length < size * 4) continue;
        final tail = compact.substring(compact.length - size);
        final a = compact.substring(compact.length - size * 2, compact.length - size);
        final b = compact.substring(compact.length - size * 3, compact.length - size * 2);
        final c = compact.substring(compact.length - size * 4, compact.length - size * 3);
        if (tail == a && tail == b && tail == c) return true;
      }
    }
    return false;
  }

  static String _cleanRepeatedLines(String text) {
    final lines = text.split('\n');
    final out = <String>[];
    String? previous;
    var repeated = 0;
    for (final line in lines) {
      final normalized = line.trim().toLowerCase();
      if (normalized.isNotEmpty && normalized == previous) {
        repeated++;
        if (repeated >= 1) continue;
      } else {
        repeated = 0;
      }
      out.add(line);
      if (normalized.isNotEmpty) previous = normalized;
    }
    return out.join('\n');
  }

'''
if anchor not in s:
    raise RuntimeError('device helper anchor not found')
s = s.replace(anchor, helper + anchor, 1)

old = """        buffer.write(token);\n        final now = DateTime.now();"""
new = """        buffer.write(token);\n        if (_looksRepetitive(buffer.toString())) {\n          break;\n        }\n        final now = DateTime.now();"""
if old not in s:
    raise RuntimeError('stream repetition anchor not found')
s = s.replace(old, new, 1)

old = "      final text = buffer.toString().trim();"
new = "      final text = _cleanRepeatedLines(buffer.toString()).trim();"
if old not in s:
    raise RuntimeError('clean text anchor not found')
s = s.replace(old, new, 1)

p.write_text(s)
print('Memora v1.6 repetition guard applied successfully')
