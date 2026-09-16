from pathlib import Path

# Memora v1.45: on-demand exam explanations + visible tutor response timer.

# --- Exam answer explanations, generated only when requested and cached in-memory per question ---
p = Path('lib/daily_exam_page.dart')
s = p.read_text()
old = """  late TutorExamSession exam;
  bool reveal = false;
"""
new = """  late TutorExamSession exam;
  bool reveal = false;
  final Map<int, String> explanationCache = <int, String>{};
  bool explaining = false;
"""
if 'explanationCache' not in s:
    if old not in s: raise RuntimeError('v1.45 exam state anchor not found')
    s = s.replace(old, new, 1)

anchor = """  Future<void> _answer(bool knew) async {
"""
method = r'''  Future<void> _explainCurrent() async {
    if (explaining || exam.currentIndex >= exam.questions.length) return;
    final index = exam.currentIndex;
    if (explanationCache.containsKey(index)) {
      if (mounted) setState(() {});
      return;
    }
    final q = exam.questions[index];
    setState(() => explaining = true);
    try {
      final result = await AiService.askCascade(
        task: 'explanation',
        responseMode: 'normal',
        prompt: """Explain this exam answer clearly and concisely using only the supplied question/answer context.
Difficulty: ${exam.difficulty}
Question: ${q.question}
Correct answer: ${q.answer}
Source/topic: ${q.sourceTitle}
Explain why the answer is correct and the key idea the student should remember. Do not invent facts outside this context.""",
      );
      if (mounted) setState(() => explanationCache[index] = result.trim());
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AiService.userFacingError(e))),
        );
      }
    } finally {
      if (mounted) setState(() => explaining = false);
    }
  }

'''
if '_explainCurrent()' not in s:
    if anchor not in s: raise RuntimeError('v1.45 answer method anchor not found')
    s = s.replace(anchor, method + anchor, 1)

old_ui = """                          SelectableText(question.answer, style: const TextStyle(fontSize: 17)),
                        ],
"""
new_ui = """                          SelectableText(question.answer, style: const TextStyle(fontSize: 17)),
                          const SizedBox(height: 12),
                          OutlinedButton.icon(
                            onPressed: explaining ? null : _explainCurrent,
                            icon: explaining
                                ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                                : const Icon(Icons.auto_awesome),
                            label: Text(explaining ? 'Explicando…' : 'Explicar respuesta con IA'),
                          ),
                          if (explanationCache[exam.currentIndex]?.isNotEmpty == true) ...[
                            const SizedBox(height: 12),
                            Text('Explicación de IA', style: Theme.of(context).textTheme.labelLarge),
                            const SizedBox(height: 6),
                            SelectableText(explanationCache[exam.currentIndex]!),
                          ],
                        ],
"""
if 'Explicar respuesta con IA' not in s:
    if old_ui not in s: raise RuntimeError('v1.45 exam explanation UI anchor not found')
    s = s.replace(old_ui, new_ui, 1)
p.write_text(s)

# --- Tutor response timer: live while generating, retained after completion ---
p = Path('lib/tutor_page.dart')
s = p.read_text()
if "import 'dart:async';" not in s:
    s = s.replace("import 'dart:convert';\n", "import 'dart:async';\nimport 'dart:convert';\n", 1)
state_anchor = """  Future<void> _cancel() async {
"""
# Add fields before cancel; these live in the state class.
fields = """  Timer? _responseTimer;
  DateTime? _responseStartedAt;
  double _responseSeconds = 0;

  void _startResponseTimer() {
    _responseTimer?.cancel();
    _responseStartedAt = DateTime.now();
    _responseSeconds = 0;
    _responseTimer = Timer.periodic(const Duration(milliseconds: 100), (_) {
      if (!mounted || _responseStartedAt == null) return;
      setState(() {
        _responseSeconds = DateTime.now().difference(_responseStartedAt!).inMilliseconds / 1000.0;
      });
    });
  }

  void _stopResponseTimer() {
    if (_responseStartedAt != null) {
      _responseSeconds = DateTime.now().difference(_responseStartedAt!).inMilliseconds / 1000.0;
    }
    _responseTimer?.cancel();
    _responseTimer = null;
  }

"""
if '_startResponseTimer()' not in s:
    if state_anchor not in s: raise RuntimeError('v1.45 tutor timer state anchor not found')
    s = s.replace(state_anchor, fields + state_anchor, 1)

start_anchor = """    setState(() {
      busy = true;
      answer = 'Preparando respuesta…';
    });

    try {
"""
start_new = """    setState(() {
      busy = true;
      answer = 'Preparando respuesta…';
    });
    _startResponseTimer();

    try {
"""
if '_startResponseTimer();' not in s:
    if start_anchor not in s: raise RuntimeError('v1.45 timer start anchor not found')
    s = s.replace(start_anchor, start_new, 1)

finally_old = """    } finally {
      if (mounted) setState(() => busy = false);
    }
  }
"""
finally_new = """    } finally {
      _stopResponseTimer();
      if (mounted) setState(() => busy = false);
    }
  }
"""
# First occurrence after _ask.
pos = s.find('  Future<void> _ask() async {')
idx = s.find(finally_old, pos)
if idx >= 0 and '_stopResponseTimer();' not in s[pos:idx+len(finally_old)]:
    s = s[:idx] + s[idx:].replace(finally_old, finally_new, 1)

answer_ui = """                          SelectableText(answer),
"""
timer_ui = """                          SelectableText(answer),
                          const SizedBox(height: 8),
                          Align(
                            alignment: Alignment.centerRight,
                            child: Text(
                              '${_responseSeconds.toStringAsFixed(1)} s',
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: busy
                                    ? Theme.of(context).colorScheme.secondary
                                    : const Color(0xFF7C4DFF),
                              ),
                            ),
                          ),
"""
if '_responseSeconds.toStringAsFixed' not in s:
    if answer_ui not in s: raise RuntimeError('v1.45 timer UI anchor not found')
    s = s.replace(answer_ui, timer_ui, 1)
p.write_text(s)

# Version bump after v1.44.
p = Path('pubspec.yaml')
s = p.read_text().replace('version: 1.44.0+57', 'version: 1.45.0+58')
p.write_text(s)

print('Memora v1.45 exam explanations + tutor response timer applied successfully')
