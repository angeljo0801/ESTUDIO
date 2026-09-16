from pathlib import Path

p = Path('v122_ai_cards_exam_grounding_patch.py')
s = p.read_text()

# The exam helper embeds a Dart triple-single-quoted prompt inside a Python raw
# triple-single-quoted block. Convert only that outer Python block to triple
# double quotes before compiling/executing the patch.
marker = "exam_helpers = r'''"
start = s.index(marker)
s = s[:start] + s[start:].replace(marker, 'exam_helpers = r"""', 1)

following = "\ns = s[:helper_start] + exam_helpers + s[helper_end:]"
end = s.index(following, start)
segment = s[start:end]
close = segment.rfind("'''")
if close < 0:
    raise RuntimeError('Could not find closing quote for exam_helpers')
segment = segment[:close] + '"""' + segment[close + 3:]
s = s[:start] + segment + s[end:]

exec(compile(s, 'v122_ai_cards_exam_grounding_patch.py', 'exec'))

# Compile fixes found by flutter analyze after the full patch chain is applied.
p = Path('lib/home_page.dart')
home = p.read_text()
if "import 'models.dart';\n" not in home:
    anchor = "import 'guide_store.dart';\n"
    if anchor not in home:
        raise RuntimeError('HomePage import anchor not found')
    home = home.replace(anchor, anchor + "import 'models.dart';\n", 1)
p.write_text(home)

p = Path('lib/daily_exam_page.dart')
exam = p.read_text()
broken = "'Each tutor tests you only on its assigned guides. Today's exam is saved and is not regenerated just by reopening this screen.'"
fixed = '"Each tutor tests you only on its assigned guides. Today\'s exam is saved and is not regenerated just by reopening this screen."'
if broken not in exam:
    raise RuntimeError('Daily exam apostrophe string not found')
exam = exam.replace(broken, fixed, 1)
p.write_text(exam)

print('Memora v1.22 runner and compile fixes applied successfully')
