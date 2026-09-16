from pathlib import Path

p = Path('lib/daily_exam_page.dart')
s = p.read_text()

old = """    ExamQuestionData? takeFrom(List<ExamQuestionData> group) {
      while (group.isNotEmpty) {
        final item = group.removeAt(0);
        if (selected.any((x) => _nearDuplicate(x.question, item.question))) continue;
        return item;
      }
      return null;
    }

    final selected = <ExamQuestionData>[];
"""

new = """    final selected = <ExamQuestionData>[];

    ExamQuestionData? takeFrom(List<ExamQuestionData> group) {
      while (group.isNotEmpty) {
        final item = group.removeAt(0);
        if (selected.any((x) => _nearDuplicate(x.question, item.question))) continue;
        return item;
      }
      return null;
    }
"""

if old not in s:
    raise RuntimeError('v1.35 selected/takeFrom compile-fix anchor not found')

s = s.replace(old, new, 1)
p.write_text(s)
print('Memora v1.35 exam variant compile fix applied successfully')
