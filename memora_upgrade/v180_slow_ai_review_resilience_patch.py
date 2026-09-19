from pathlib import Path

# v180: make mandatory Library-AI cleanup tolerant of slower models.
# Smaller batches + smaller evidence windows + a longer per-call timeout mean
# the first reviewed cards appear sooner and local models are much less likely
# to hit the timeout seen on device.

p = Path('lib/ai_card_review_service.dart')
s = p.read_text()

old = """JSON FORMAT:
[
  {"id":0,"action":"KEEP","question":"","answer":"","reason":"short reason"},
  {"id":1,"action":"FIX","question":"better question","answer":"better answer","reason":"short reason"},
  {"id":2,"action":"REJECT","question":"","answer":"","reason":"short reason"}
]
"""
new = """JSON FORMAT:
[
  {"id":0,"action":"KEEP","question":"","answer":""},
  {"id":1,"action":"FIX","question":"better question","answer":"better answer"},
  {"id":2,"action":"REJECT","question":"","answer":""}
]
"""
if old not in s:
    raise SystemExit('v180 compact JSON prompt anchor missing')
s = s.replace(old, new, 1)

old = """      ).timeout(
        const Duration(seconds: 90),
        onTimeout: () async {
"""
new = """      ).timeout(
        const Duration(seconds: 240),
        onTimeout: () async {
"""
if old not in s:
    raise SystemExit('v180 timeout anchor missing')
s = s.replace(old, new, 1)

old = """    var evidence = chunks.join('\\n');
    if (evidence.length > 2400) evidence = evidence.substring(0, 2400);
    return evidence;
"""
new = """    var evidence = chunks.join('\\n');
    if (evidence.length > 1400) evidence = evidence.substring(0, 1400);
    return evidence;
"""
if old not in s:
    raise SystemExit('v180 evidence-size anchor missing')
s = s.replace(old, new, 1)

p.write_text(s)

p = Path('lib/guide_detail_page.dart')
s = p.read_text()

old = """      const batchSize = 6;
"""
new = """      // Small batches make slow/local models return usable cards sooner.
      // Every completed pair is persisted before the next AI call starts.
      const batchSize = 2;
"""
if old not in s:
    raise SystemExit('v180 batch-size anchor missing')
s = s.replace(old, new, 1)

old = """                    'Memora reviews in batches. Each finished batch is saved immediately, so you can start Review while the AI keeps cleaning the remaining cards.',
"""
new = """                    'Memora reviews in small batches of 2. Each finished batch is saved immediately, so you can start Review while the AI keeps cleaning the remaining cards.',
"""
if old not in s:
    raise SystemExit('v180 batch UI text anchor missing')
s = s.replace(old, new, 1)

p.write_text(s)

print('v180 applied: slower AI models get 2-card batches, smaller evidence and longer timeout')
