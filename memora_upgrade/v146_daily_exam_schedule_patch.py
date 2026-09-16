from pathlib import Path

# Memora v1.46: Daily Exam UI/preferences. Native Android alarm code is installed
# from memora_upgrade/android after flutter regenerates the Android project.
p=Path('lib/daily_exam_page.dart'); s=p.read_text()
if "package:flutter/services.dart" not in s: s=s.replace("import 'package:flutter/material.dart';\n","import 'package:flutter/material.dart';\nimport 'package:flutter/services.dart';\n",1)
state="  String? busyTutorId;\n"
fields="""  bool autoDailyEnabled = false;
  TimeOfDay autoDailyTime = const TimeOfDay(hour: 6, minute: 0);
  String autoDailyLastRun = '';
  bool autoDailyRunning = false;
  static const MethodChannel _dailyAlarm = MethodChannel('com.memora/daily_exam_alarm');
"""
if 'bool autoDailyEnabled' not in s:
    if state not in s: raise RuntimeError('v1.46 state anchor not found')
    s=s.replace(state,state+fields,1)
load_anchor="    final raw = prefs.getString(_storageKey);\n"
load="""    autoDailyEnabled = prefs.getBool('daily_exam_auto_enabled') ?? false;
    autoDailyTime = TimeOfDay(hour: prefs.getInt('daily_exam_auto_hour') ?? 6, minute: prefs.getInt('daily_exam_auto_minute') ?? 0);
    autoDailyLastRun = prefs.getString('daily_exam_auto_last_run') ?? '';
"""
if "daily_exam_auto_enabled" not in s:
    if load_anchor not in s: raise RuntimeError('v1.46 load anchor not found')
    s=s.replace(load_anchor,load_anchor+load,1)
helper_anchor="  Future<void> _saveSessions() async {\n"
helpers=r'''  String _clock(TimeOfDay t) { final h=t.hourOfPeriod==0?12:t.hourOfPeriod; return '$h:${t.minute.toString().padLeft(2,'0')} ${t.period==DayPeriod.am?'AM':'PM'}'; }
  DateTime _nextAutomaticRun() { final n=DateTime.now(); var x=DateTime(n.year,n.month,n.day,autoDailyTime.hour,autoDailyTime.minute); if(!x.isAfter(n))x=x.add(const Duration(days:1)); return x; }
  Future<void> _syncNativeAlarm() async { try { await _dailyAlarm.invokeMethod(autoDailyEnabled?'schedule':'cancel',{'hour':autoDailyTime.hour,'minute':autoDailyTime.minute}); } catch(_){} }
  Future<void> _saveAutomaticSettings() async { final p=await SharedPreferences.getInstance(); await p.setBool('daily_exam_auto_enabled',autoDailyEnabled); await p.setInt('daily_exam_auto_hour',autoDailyTime.hour); await p.setInt('daily_exam_auto_minute',autoDailyTime.minute); await _syncNativeAlarm(); }
  Future<void> _chooseAutomaticTime() async { final picked=await showTimePicker(context:context,initialTime:autoDailyTime); if(picked==null)return; setState(()=>autoDailyTime=picked); await _saveAutomaticSettings(); await _runAutomaticDailyIfDue(); }
  Future<void> _runAutomaticDailyIfDue() async { if(!autoDailyEnabled||autoDailyRunning)return; final now=DateTime.now(); final scheduled=DateTime(now.year,now.month,now.day,autoDailyTime.hour,autoDailyTime.minute); if(now.isBefore(scheduled)||autoDailyLastRun==today)return; autoDailyRunning=true; try { for(final tutor in tutors){if(_dailyFor(tutor.id)!=null||TutorContextService.guidesFor(widget.store,tutor).isEmpty)continue;try{final exam=await _buildExam(tutor:tutor,count:10,difficulty:'Adaptativa',generatorMode:dailyGenerator,daily:true);final copy=List<TutorExamSession>.from(sessions)..removeWhere((e)=>e.isDaily&&e.tutorId==tutor.id&&e.dateKey==today)..insert(0,exam);sessions=copy;await _saveSessions();}catch(_){}} final missing=tutors.any((t)=>TutorContextService.guidesFor(widget.store,t).isNotEmpty&&_dailyFor(t.id)==null);if(!missing){autoDailyLastRun=today;final p=await SharedPreferences.getInstance();await p.setString('daily_exam_auto_last_run',today);}if(mounted)setState((){});}finally{autoDailyRunning=false;} }

'''
if '_runAutomaticDailyIfDue()' not in s:
    if helper_anchor not in s: raise RuntimeError('v1.46 helper anchor not found')
    s=s.replace(helper_anchor,helpers+helper_anchor,1)
load_end="""      loading = false;
    });
  }
"""
if 'await _runAutomaticDailyIfDue();' not in s:
    if load_end not in s: raise RuntimeError('v1.46 load completion anchor not found')
    s=s.replace(load_end,"""      loading = false;
    });
    await _syncNativeAlarm();
    await _runAutomaticDailyIfDue();
  }
""",1)
ui_anchor="""                const SizedBox(height: 14),
                _generatorDropdown(
                  value: dailyGenerator,
"""
ui=r'''                const SizedBox(height: 14),
                SwitchListTile.adaptive(contentPadding:EdgeInsets.zero,title:const Text('Generate automatically every day'),subtitle:Text(autoDailyEnabled?'Scheduled for ${_clock(autoDailyTime)}':'Automatic generation is off'),value:autoDailyEnabled,onChanged:(value) async {setState(()=>autoDailyEnabled=value);await _saveAutomaticSettings();if(value)await _runAutomaticDailyIfDue();}),
                if(autoDailyEnabled)...[ListTile(contentPadding:EdgeInsets.zero,leading:const Icon(Icons.schedule),title:const Text('Daily generation time'),subtitle:Text(_clock(autoDailyTime)),trailing:const Icon(Icons.edit),onTap:_chooseAutomaticTime),Text('Last generation: ${autoDailyLastRun.isEmpty?'Not generated yet':autoDailyLastRun}'),const SizedBox(height:4),Text('Next generation: ${_nextAutomaticRun()}')],
                const SizedBox(height:14),
                _generatorDropdown(
                  value: dailyGenerator,
'''
if 'Generate automatically every day' not in s:
    if ui_anchor not in s: raise RuntimeError('v1.46 UI anchor not found')
    s=s.replace(ui_anchor,ui,1)
p.write_text(s)
p=Path('pubspec.yaml'); p.write_text(p.read_text().replace('version: 1.45.0+58','version: 1.46.0+59'))
print('Memora v1.46 Daily Exam Dart scheduling applied successfully')
