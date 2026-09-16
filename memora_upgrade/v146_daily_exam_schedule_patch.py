from pathlib import Path

# Memora v1.46: automatic Daily Exam schedule preferences + duplicate-safe catch-up.
p = Path('lib/daily_exam_page.dart')
s = p.read_text()

state = "  String? busyTutorId;\n"
fields = """  bool autoDailyEnabled = false;
  TimeOfDay autoDailyTime = const TimeOfDay(hour: 6, minute: 0);
  String autoDailyLastRun = '';
  bool autoDailyRunning = false;
"""
if 'bool autoDailyEnabled' not in s:
    if state not in s: raise RuntimeError('v1.46 daily state anchor not found')
    s = s.replace(state, state + fields, 1)

load_anchor = "    final raw = prefs.getString(_storageKey);\n"
load = """    autoDailyEnabled = prefs.getBool('daily_exam_auto_enabled') ?? false;
    autoDailyTime = TimeOfDay(
      hour: prefs.getInt('daily_exam_auto_hour') ?? 6,
      minute: prefs.getInt('daily_exam_auto_minute') ?? 0,
    );
    autoDailyLastRun = prefs.getString('daily_exam_auto_last_run') ?? '';
"""
if "daily_exam_auto_enabled" not in s:
    if load_anchor not in s: raise RuntimeError('v1.46 load anchor not found')
    s = s.replace(load_anchor, load_anchor + load, 1)

helper_anchor = "  Future<void> _saveSessions() async {\n"
helpers = r'''  String _clock(TimeOfDay t) {
    final h = t.hourOfPeriod == 0 ? 12 : t.hourOfPeriod;
    final m = t.minute.toString().padLeft(2, '0');
    return '$h:$m ${t.period == DayPeriod.am ? 'AM' : 'PM'}';
  }

  DateTime _nextAutomaticRun() {
    final now = DateTime.now();
    var next = DateTime(now.year, now.month, now.day, autoDailyTime.hour, autoDailyTime.minute);
    if (!next.isAfter(now)) next = next.add(const Duration(days: 1));
    return next;
  }

  Future<void> _saveAutomaticSettings() async {
    final p = await SharedPreferences.getInstance();
    await p.setBool('daily_exam_auto_enabled', autoDailyEnabled);
    await p.setInt('daily_exam_auto_hour', autoDailyTime.hour);
    await p.setInt('daily_exam_auto_minute', autoDailyTime.minute);
  }

  Future<void> _chooseAutomaticTime() async {
    final picked = await showTimePicker(context: context, initialTime: autoDailyTime);
    if (picked == null) return;
    setState(() => autoDailyTime = picked);
    await _saveAutomaticSettings();
    await _runAutomaticDailyIfDue();
  }

  Future<void> _runAutomaticDailyIfDue() async {
    if (!autoDailyEnabled || autoDailyRunning) return;
    final now = DateTime.now();
    final scheduled = DateTime(now.year, now.month, now.day, autoDailyTime.hour, autoDailyTime.minute);
    if (now.isBefore(scheduled) || autoDailyLastRun == today) return;
    autoDailyRunning = true;
    try {
      for (final tutor in tutors) {
        if (_dailyFor(tutor.id) != null) continue;
        if (TutorContextService.guidesFor(widget.store, tutor).isEmpty) continue;
        try {
          final exam = await _buildExam(
            tutor: tutor,
            count: 10,
            difficulty: 'Adaptativa',
            generatorMode: dailyGenerator,
            daily: true,
          );
          final copy = List<TutorExamSession>.from(sessions)
            ..removeWhere((e) => e.isDaily && e.tutorId == tutor.id && e.dateKey == today)
            ..insert(0, exam);
          sessions = copy;
          await _saveSessions();
        } catch (_) {
          // Keep this tutor pending so a later foreground/background retry can create it.
        }
      }
      final missing = tutors.any((t) =>
          TutorContextService.guidesFor(widget.store, t).isNotEmpty && _dailyFor(t.id) == null);
      if (!missing) {
        autoDailyLastRun = today;
        final p = await SharedPreferences.getInstance();
        await p.setString('daily_exam_auto_last_run', today);
      }
      if (mounted) setState(() {});
    } finally {
      autoDailyRunning = false;
    }
  }

'''
if '_runAutomaticDailyIfDue()' not in s:
    if helper_anchor not in s: raise RuntimeError('v1.46 helper anchor not found')
    s = s.replace(helper_anchor, helpers + helper_anchor, 1)

# Catch up whenever the page is opened after the configured time. Existing exams
# are never duplicated. Android background execution remains handled by Memora's
# existing foreground/background task service when generation actually runs.
load_end = """      loading = false;
    });
  }
"""
load_end_new = """      loading = false;
    });
    await _runAutomaticDailyIfDue();
  }
"""
if 'await _runAutomaticDailyIfDue();' not in s:
    if load_end not in s: raise RuntimeError('v1.46 load completion anchor not found')
    s = s.replace(load_end, load_end_new, 1)

ui_anchor = """                const SizedBox(height: 14),
                _generatorDropdown(
                  value: dailyGenerator,
"""
ui = r'''                const SizedBox(height: 14),
                SwitchListTile.adaptive(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Generate automatically every day'),
                  subtitle: Text(autoDailyEnabled
                      ? 'Scheduled for ${_clock(autoDailyTime)}'
                      : 'Automatic generation is off'),
                  value: autoDailyEnabled,
                  onChanged: (value) async {
                    setState(() => autoDailyEnabled = value);
                    await _saveAutomaticSettings();
                    if (value) await _runAutomaticDailyIfDue();
                  },
                ),
                if (autoDailyEnabled) ...[
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.schedule),
                    title: const Text('Daily generation time'),
                    subtitle: Text(_clock(autoDailyTime)),
                    trailing: const Icon(Icons.edit),
                    onTap: _chooseAutomaticTime,
                  ),
                  Text('Last generation: ${autoDailyLastRun.isEmpty ? 'Not generated yet' : autoDailyLastRun}'),
                  const SizedBox(height: 4),
                  Text('Next generation: ${_nextAutomaticRun()}'),
                ],
                const SizedBox(height: 14),
                _generatorDropdown(
                  value: dailyGenerator,
'''
if 'Generate automatically every day' not in s:
    if ui_anchor not in s: raise RuntimeError('v1.46 daily UI anchor not found')
    s = s.replace(ui_anchor, ui, 1)

p.write_text(s)

p = Path('pubspec.yaml')
s = p.read_text().replace('version: 1.45.0+58', 'version: 1.46.0+59')
p.write_text(s)
print('Memora v1.46 automatic Daily Exam scheduling patch applied successfully')
