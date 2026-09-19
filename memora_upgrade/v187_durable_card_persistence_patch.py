from pathlib import Path

# v187: durable card persistence.
# Final AI-reviewed batches are already saved after every batch. This hardens
# that storage so leaving Memora or an abrupt Android process stop cannot wipe
# cards that already finished creation.

p = Path('lib/guide_store.dart')
s = p.read_text()

old = """    } catch (_) {
      guides.clear();
    }
  }
"""
new = """    } catch (_) {
      final backup = File('${_storageFile!.path}.bak');
      try {
        if (!await backup.exists()) {
          guides.clear();
          return;
        }
        final raw = await backup.readAsString();
        final decoded = jsonDecode(raw) as List<dynamic>;
        guides
          ..clear()
          ..addAll(
            decoded.map(
              (item) =>
                  StudyGuide.fromJson(Map<String, dynamic>.from(item as Map)),
            ),
          );
        guides.sort((a, b) => b.createdAt.compareTo(a.createdAt));
      } catch (_) {
        guides.clear();
      }
    }
  }
"""
if old not in s:
    raise SystemExit('v187 GuideStore load recovery anchor missing')
s = s.replace(old, new, 1)

start = s.find("  Future<void> _persist() async {")
if start < 0:
    raise SystemExit('v187 GuideStore persist start missing')
end = s.find("\n  }\n}", start)
if end < 0:
    raise SystemExit('v187 GuideStore persist end missing')
end += len("\n  }")

method = r'''  Future<void> _persist() async {
    if (_storageFile == null) {
      final directory = await getApplicationDocumentsDirectory();
      _storageFile = File('${directory.path}/memora_guides_v3.json');
    }

    final payload = jsonEncode(
      guides.map((guide) => guide.toJson()).toList(),
    );
    final primary = _storageFile!;
    final temp = File('${primary.path}.tmp');
    final backup = File('${primary.path}.bak');

    await temp.writeAsString(payload, flush: true);

    if (await primary.exists()) {
      try {
        if (await backup.exists()) await backup.delete();
        await primary.copy(backup.path);
      } catch (_) {}
    }

    try {
      if (await primary.exists()) await primary.delete();
      await temp.rename(primary.path);
    } catch (_) {
      try {
        if (!await primary.exists() && await backup.exists()) {
          await backup.copy(primary.path);
        }
      } catch (_) {}
      rethrow;
    }

    try {
      if (await backup.exists()) await backup.delete();
      await primary.copy(backup.path);
    } catch (_) {}
  }'''

s = s[:start] + method + s[end:]
p.write_text(s)

print('v187 applied: final study-card batches survive app exit/process interruption')
