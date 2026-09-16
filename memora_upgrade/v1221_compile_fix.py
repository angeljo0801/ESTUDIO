from pathlib import Path

# Memora v1.22.1 compile fixes discovered by flutter analyze.

p = Path('lib/home_page.dart')
s = p.read_text()
if "import 'models.dart';\n" not in s:
    anchor = "import 'guide_store.dart';\n"
    if anchor not in s:
        raise RuntimeError('HomePage import anchor not found')
    s = s.replace(anchor, anchor + "import 'models.dart';\n", 1)
p.write_text(s)

p = Path('lib/daily_exam_page.dart')
s = p.read_text()
broken = "'Each tutor tests you only on its assigned guides. Today's exam is saved and is not regenerated just by reopening this screen.'"
fixed = '"Each tutor tests you only on its assigned guides. Today\'s exam is saved and is not regenerated just by reopening this screen."'
if broken not in s:
    raise RuntimeError('Daily exam apostrophe string not found')
s = s.replace(broken, fixed, 1)
p.write_text(s)

print('Memora v1.22.1 compile fixes applied successfully')
