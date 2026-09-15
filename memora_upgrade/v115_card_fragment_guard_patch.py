from pathlib import Path

# Memora v1.15
# Reject malformed/fragmented legacy study cards inside the daily exam engine,
# and invalidate previously saved exam sessions that may already contain them.

p = Path('lib/daily_exam_page.dart')
s = p.read_text()

old = "  static const _storageKey = 'memora_tutor_exams_v2';"
new = "  static const _storageKey = 'memora_tutor_exams_v3';"
if old not in s:
    raise RuntimeError('Daily exam v2 storage key anchor not found')
s = s.replace(old, new, 1)

old = """    var q = card.question.trim();
    var a = card.answer.trim();
    if (q.isEmpty || a.isEmpty) return null;

"""
new = """    var q = card.question.trim();
    var a = card.answer.trim();
    if (q.isEmpty || a.isEmpty) return null;
    if (!StudyEngine.isCardUsable(card)) return null;

"""
if old not in s:
    raise RuntimeError('Daily exam card quality guard anchor not found')
s = s.replace(old, new, 1)

p.write_text(s)
print('Memora v1.15 fragmented-card guard and exam reset applied successfully')
