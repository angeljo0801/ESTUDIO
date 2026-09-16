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
