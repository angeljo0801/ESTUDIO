from pathlib import Path

p = Path('v121_tutor_plan_models_patch.py')
s = p.read_text()

# The v1.21 patch embeds Dart multiline strings inside Python raw multiline
# strings. Convert only the three outer Python blocks that themselves contain
# Dart ''' strings to raw triple-double quotes before executing the patch.
def convert_outer(marker: str, following: str):
    global s
    opening = marker + " = r'''"
    start = s.index(opening)
    s = s[:start] + s[start:].replace(opening, marker + ' = r"""', 1)
    end = s.index(following, start)
    segment = s[start:end]
    close = segment.rfind("'''")
    if close < 0:
        raise RuntimeError(f'Could not find closing quote for {marker}')
    segment = segment[:close] + '"""' + segment[close + 3:]
    s = s[:start] + segment + s[end:]

convert_outer('new_ask', '\ns = replace_regex(')
convert_outer('new_build_exam', '\ns = replace_regex(')
convert_outer('plan_helpers', '\nif helper_anchor not in s:')

exec(compile(s, 'v121_tutor_plan_models_patch.py', 'exec'))
