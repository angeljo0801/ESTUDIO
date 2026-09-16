from pathlib import Path


def required(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f'{label} anchor not found')
    return text.replace(old, new, 1)


def wrap_async_method(
    text: str,
    start_marker: str,
    end_marker: str,
    generic_type: str,
    title_expr: str,
    body_expr: str,
    label: str,
) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    segment = text[start:end]
    if 'BackgroundTaskService.run<' in segment:
        return text

    opening = '  }) async {\n'
    pos = segment.find(opening)
    if pos < 0:
        raise RuntimeError(f'{label} async opening not found')
    insert_at = pos + len(opening)
    prefix = (
        f'    return BackgroundTaskService.run<{generic_type}>(\n'
        f'      title: {title_expr},\n'
        f'      body: {body_expr},\n'
        f'      task: () async {{\n'
    )
    segment = segment[:insert_at] + prefix + segment[insert_at:]

    close = segment.rfind('\n  }')
    if close < 0:
        raise RuntimeError(f'{label} closing brace not found')
    segment = segment[:close] + '\n      },\n    );' + segment[close:]
    return text[:start] + segment + text[end:]


# -----------------------------------------------------------------------------
# Every model request enters an Android foreground service. This protects tutor
# replies, plans, guide creation/translation, exams and local GGUF/Ollama work
# when Memora is minimized or the screen turns off.
# -----------------------------------------------------------------------------
p = Path('lib/ai_service.dart')
s = p.read_text()
if "import 'background_task_service.dart';" not in s:
    s = required(
        s,
        "import 'device_llm_service.dart';\n",
        "import 'background_task_service.dart';\nimport 'device_llm_service.dart';\n",
        'AiService background import',
    )

s = wrap_async_method(
    s,
    '  static Future<String> askConfigured({\n',
    '\n  static bool looksLikeTask(',
    'String',
    "'Memora AI is working'",
    "'Generating with the selected AI…'",
    'AiService askConfigured',
)
s = wrap_async_method(
    s,
    '  static Future<String> askTaskConfigured({\n',
    '\n  static Future<String> askGemini({',
    'String',
    "'Memora AI is working'",
    "'Generating with the selected AI…'",
    'AiService askTaskConfigured',
)
p.write_text(s)

# -----------------------------------------------------------------------------
# Study-card generation stays foreground for the complete multi-batch job and
# reports live card progress in the persistent notification.
# -----------------------------------------------------------------------------
p = Path('lib/ai_card_service.dart')
s = p.read_text()
if "import 'background_task_service.dart';" not in s:
    s = required(
        s,
        "import 'ai_service.dart';\n",
        "import 'ai_service.dart';\nimport 'background_task_service.dart';\n",
        'AI card background import',
    )
s = wrap_async_method(
    s,
    '  static Future<List<StudyCard>> generateCards(\n',
    '\n  static List<String> _chunks(',
    'List<StudyCard>',
    "'Memora is creating study cards'",
    "'Preparing up to $target cards…'",
    'AI card generation',
)
progress_anchor = "        cards.add(card);\n        onProgress?.call(cards.length, safeTarget);\n"
progress_replacement = """        cards.add(card);
        onProgress?.call(cards.length, safeTarget);
        await BackgroundTaskService.update(
          title: 'Memora is creating study cards',
          body: '${cards.length} of $safeTarget cards ready',
          progress: cards.length,
          max: safeTarget,
        );
"""
s = required(s, progress_anchor, progress_replacement, 'AI card progress')
p.write_text(s)

# -----------------------------------------------------------------------------
# Exam generation also remains one foreground job across its AI batches and
# reports how many validated questions are ready.
# -----------------------------------------------------------------------------
p = Path('lib/daily_exam_page.dart')
s = p.read_text()
if "import 'background_task_service.dart';" not in s:
    s = required(
        s,
        "import 'ai_service.dart';\n",
        "import 'ai_service.dart';\nimport 'background_task_service.dart';\n",
        'Exam background import',
    )
s = wrap_async_method(
    s,
    '  Future<List<ExamQuestionData>> _generateAiExamQuestions({\n',
    '\n  Future<TutorExamSession> _buildExam({',
    'List<ExamQuestionData>',
    "'Memora is creating an exam'",
    "'0 of $count questions ready'",
    'Exam batch generation',
)
exam_progress_anchor = """        out.add(item);
        if (mounted) setState(() => examGeneratedQuestions = out.length);
      }
      attempt++;
"""
exam_progress_replacement = """        out.add(item);
        if (mounted) setState(() => examGeneratedQuestions = out.length);
      }
      await BackgroundTaskService.update(
        title: 'Memora is creating an exam',
        body: '${out.length} of $count questions ready',
        progress: out.length,
        max: count,
      );
      attempt++;
"""
s = required(s, exam_progress_anchor, exam_progress_replacement, 'Exam progress notification')
p.write_text(s)

print('Memora v1.23 foreground background execution patch applied successfully')

# Keep later source-tree patches chained here so the existing build workflow
# receives them without needing another workflow migration step.
import os
_v124 = Path(os.environ['GITHUB_WORKSPACE']) / 'memora_upgrade' / 'v124_fast_progressive_cards_patch.py'
exec(compile(_v124.read_text(), str(_v124), 'exec'))
_v125 = Path(os.environ['GITHUB_WORKSPACE']) / 'memora_upgrade' / 'v125_fast_tutor_response_patch.py'
exec(compile(_v125.read_text(), str(_v125), 'exec'))
_v127 = Path(os.environ['GITHUB_WORKSPACE']) / 'memora_upgrade' / 'v127_fast_exam_batches_patch.py'
exec(compile(_v127.read_text(), str(_v127), 'exec'))
_v128 = Path(os.environ['GITHUB_WORKSPACE']) / 'memora_upgrade' / 'v128_ai_card_bank_exam_patch.py'
exec(compile(_v128.read_text(), str(_v128), 'exec'))
_v129 = Path(os.environ['GITHUB_WORKSPACE']) / 'memora_upgrade' / 'v129_varied_exam_from_cards_patch.py'
exec(compile(_v129.read_text(), str(_v129), 'exec'))
_v130 = Path(os.environ['GITHUB_WORKSPACE']) / 'memora_upgrade' / 'v130_random_tutor_novelty_patch.py'
exec(compile(_v130.read_text(), str(_v130), 'exec'))
