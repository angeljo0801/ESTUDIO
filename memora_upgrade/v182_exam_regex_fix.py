from pathlib import Path
p = Path('lib/daily_exam_page.dart')
s = p.read_text()
old = r"        '^${RegExp.escape(symbol)}\\s*=\\s*(.+)\\$',"
new = r"        '^${RegExp.escape(symbol)}\\s*=\\s*(.+)\$',"
if old not in s:
    raise RuntimeError('Exam regex escape anchor not found')
p.write_text(s.replace(old, new, 1))
print('Memora v1.8 exam regex escape fix applied successfully')
