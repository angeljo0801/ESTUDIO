from pathlib import Path
p = Path('lib/daily_exam_page.dart')
s = p.read_text()
old = "  static const _storageKey = 'memora_tutor_exams_v1';"
new = "  static const _storageKey = 'memora_tutor_exams_v2';"
if old not in s:
    raise RuntimeError('Exam storage key anchor not found')
p.write_text(s.replace(old, new, 1))
print('Memora v1.8 exam storage reset applied successfully')
