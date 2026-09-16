from pathlib import Path

# Memora v1.46: automatic Daily Exam schedule preferences + Android exact alarm bridge.
p = Path('lib/daily_exam_page.dart')
s = p.read_text()
if "package:flutter/services.dart" not in s:
    s = s.replace("import 'package:flutter/material.dart';\n", "import 'package:flutter/material.dart';\nimport 'package:flutter/services.dart';\n", 1)
state = "  String? busyTutorId;\n"
fields = """  bool autoDailyEnabled = false;
  TimeOfDay autoDailyTime = const TimeOfDay(hour: 6, minute: 0);
  String autoDailyLastRun = '';
  bool autoDailyRunning = false;
  static const MethodChannel _dailyAlarm = MethodChannel('com.memora/daily_exam_alarm');
"""
if 'bool autoDailyEnabled' not in s:
    if state not in s: raise RuntimeError('v1.46 daily state anchor not found')
    s = s.replace(state, state + fields, 1)
load_anchor = "    final raw = prefs.getString(_storageKey);\n"
load = """    autoDailyEnabled = prefs.getBool('daily_exam_auto_enabled') ?? false;
    autoDailyTime = TimeOfDay(hour: prefs.getInt('daily_exam_auto_hour') ?? 6, minute: prefs.getInt('daily_exam_auto_minute') ?? 0);
    autoDailyLastRun = prefs.getString('daily_exam_auto_last_run') ?? '';
"""
if "daily_exam_auto_enabled" not in s:
    if load_anchor not in s: raise RuntimeError('v1.46 load anchor not found')
    s = s.replace(load_anchor, load_anchor + load, 1)
helper_anchor = "  Future<void> _saveSessions() async {\n"
helpers = r'''  String _clock(TimeOfDay t) { final h=t.hourOfPeriod==0?12:t.hourOfPeriod; return '$h:${t.minute.toString().padLeft(2,'0')} ${t.period==DayPeriod.am?'AM':'PM'}'; }
  DateTime _nextAutomaticRun() { final n=DateTime.now(); var x=DateTime(n.year,n.month,n.day,autoDailyTime.hour,autoDailyTime.minute); if(!x.isAfter(n)) x=x.add(const Duration(days:1)); return x; }
  Future<void> _syncNativeAlarm() async {
    try { await _dailyAlarm.invokeMethod(autoDailyEnabled ? 'schedule' : 'cancel', {'hour': autoDailyTime.hour, 'minute': autoDailyTime.minute}); } catch (_) {}
  }
  Future<void> _saveAutomaticSettings() async { final p=await SharedPreferences.getInstance(); await p.setBool('daily_exam_auto_enabled',autoDailyEnabled); await p.setInt('daily_exam_auto_hour',autoDailyTime.hour); await p.setInt('daily_exam_auto_minute',autoDailyTime.minute); await _syncNativeAlarm(); }
  Future<void> _chooseAutomaticTime() async { final picked=await showTimePicker(context:context,initialTime:autoDailyTime); if(picked==null)return; setState(()=>autoDailyTime=picked); await _saveAutomaticSettings(); await _runAutomaticDailyIfDue(); }
  Future<void> _runAutomaticDailyIfDue() async {
    if(!autoDailyEnabled||autoDailyRunning)return; final now=DateTime.now(); final scheduled=DateTime(now.year,now.month,now.day,autoDailyTime.hour,autoDailyTime.minute); if(now.isBefore(scheduled)||autoDailyLastRun==today)return; autoDailyRunning=true;
    try { for(final tutor in tutors){ if(_dailyFor(tutor.id)!=null||TutorContextService.guidesFor(widget.store,tutor).isEmpty)continue; try { final exam=await _buildExam(tutor:tutor,count:10,difficulty:'Adaptativa',generatorMode:dailyGenerator,daily:true); final copy=List<TutorExamSession>.from(sessions)..removeWhere((e)=>e.isDaily&&e.tutorId==tutor.id&&e.dateKey==today)..insert(0,exam); sessions=copy; await _saveSessions(); } catch(_){} }
      final missing=tutors.any((t)=>TutorContextService.guidesFor(widget.store,t).isNotEmpty&&_dailyFor(t.id)==null); if(!missing){autoDailyLastRun=today; final p=await SharedPreferences.getInstance(); await p.setString('daily_exam_auto_last_run',today);} if(mounted)setState((){});
    } finally {autoDailyRunning=false;}
  }

'''
if '_runAutomaticDailyIfDue()' not in s:
    if helper_anchor not in s: raise RuntimeError('v1.46 helper anchor not found')
    s=s.replace(helper_anchor,helpers+helper_anchor,1)
load_end="""      loading = false;
    });
  }
"""
if 'await _runAutomaticDailyIfDue();' not in s:
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
                SwitchListTile.adaptive(contentPadding: EdgeInsets.zero,title: const Text('Generate automatically every day'),subtitle: Text(autoDailyEnabled?'Scheduled for ${_clock(autoDailyTime)}':'Automatic generation is off'),value:autoDailyEnabled,onChanged:(value) async {setState(()=>autoDailyEnabled=value);await _saveAutomaticSettings();if(value)await _runAutomaticDailyIfDue();}),
                if(autoDailyEnabled)...[
                  ListTile(contentPadding:EdgeInsets.zero,leading:const Icon(Icons.schedule),title:const Text('Daily generation time'),subtitle:Text(_clock(autoDailyTime)),trailing:const Icon(Icons.edit),onTap:_chooseAutomaticTime),
                  Text('Last generation: ${autoDailyLastRun.isEmpty?'Not generated yet':autoDailyLastRun}'), const SizedBox(height:4), Text('Next generation: ${_nextAutomaticRun()}'),
                ],
                const SizedBox(height:14),
                _generatorDropdown(
                  value: dailyGenerator,
'''
if 'Generate automatically every day' not in s:
    if ui_anchor not in s: raise RuntimeError('v1.46 daily UI anchor not found')
    s=s.replace(ui_anchor,ui,1)
p.write_text(s)

# Native bridge: exact daily AlarmManager event. Receiver opens a lightweight
# notification and re-arms itself; Memora performs duplicate-safe generation on
# the retained/next Flutter execution. This survives reboot through BootReceiver.
p=Path('android/MainActivity.kt'); a=p.read_text()
imports="""import android.app.AlarmManager
import android.content.BroadcastReceiver
import java.util.Calendar
"""
if 'android.app.AlarmManager' not in a: a=a.replace('import android.app.Notification\n','import android.app.Notification\n'+imports,1)
channel_anchor='        MethodChannel(\n            flutterEngine.dartExecutor.binaryMessenger,\n            "com.memora/background_tasks"\n'
bridge=r'''        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "com.memora/daily_exam_alarm").setMethodCallHandler { call, result ->
            val prefs = appContext.getSharedPreferences("FlutterSharedPreferences", Context.MODE_PRIVATE)
            when (call.method) {
                "schedule" -> {
                    val hour = call.argument<Int>("hour") ?: 6; val minute = call.argument<Int>("minute") ?: 0
                    prefs.edit().putBoolean("flutter.daily_exam_auto_enabled", true).putLong("flutter.daily_exam_auto_hour", hour.toLong()).putLong("flutter.daily_exam_auto_minute", minute.toLong()).apply()
                    DailyExamAlarm.schedule(appContext, hour, minute); result.success(null)
                }
                "cancel" -> { prefs.edit().putBoolean("flutter.daily_exam_auto_enabled", false).apply(); DailyExamAlarm.cancel(appContext); result.success(null) }
                else -> result.notImplemented()
            }
        }

'''
if 'com.memora/daily_exam_alarm' not in a:
    if channel_anchor not in a: raise RuntimeError('v1.46 MainActivity channel anchor not found')
    a=a.replace(channel_anchor,bridge+channel_anchor,1)
a += r'''

object DailyExamAlarm {
    private const val REQUEST = 4610
    fun schedule(context: Context, hour: Int, minute: Int) {
        val alarm=context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val intent=Intent(context, DailyExamAlarmReceiver::class.java)
        val pi=PendingIntent.getBroadcast(context,REQUEST,intent,PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val c=Calendar.getInstance().apply { set(Calendar.HOUR_OF_DAY,hour);set(Calendar.MINUTE,minute);set(Calendar.SECOND,0);set(Calendar.MILLISECOND,0);if(timeInMillis<=System.currentTimeMillis())add(Calendar.DAY_OF_YEAR,1) }
        if(Build.VERSION.SDK_INT>=Build.VERSION_CODES.M) alarm.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,c.timeInMillis,pi) else alarm.setExact(AlarmManager.RTC_WAKEUP,c.timeInMillis,pi)
    }
    fun cancel(context:Context){ val alarm=context.getSystemService(Context.ALARM_SERVICE) as AlarmManager; val pi=PendingIntent.getBroadcast(context,REQUEST,Intent(context,DailyExamAlarmReceiver::class.java),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE); alarm.cancel(pi) }
}
class DailyExamAlarmReceiver: BroadcastReceiver(){ override fun onReceive(context:Context,intent:Intent?){
    val p=context.getSharedPreferences("FlutterSharedPreferences",Context.MODE_PRIVATE); if(!p.getBoolean("flutter.daily_exam_auto_enabled",false))return
    val h=p.getLong("flutter.daily_exam_auto_hour",6).toInt(); val m=p.getLong("flutter.daily_exam_auto_minute",0).toInt(); DailyExamAlarm.schedule(context,h,m)
    val launch=context.packageManager.getLaunchIntentForPackage(context.packageName); val pi=launch?.let{PendingIntent.getActivity(context,4611,it,PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)}
    val nm=context.getSystemService(NotificationManager::class.java); if(Build.VERSION.SDK_INT>=Build.VERSION_CODES.O) nm.createNotificationChannel(NotificationChannel("memora_daily_exam","Memora Daily Exams",NotificationManager.IMPORTANCE_DEFAULT))
    val n=Notification.Builder(context,"memora_daily_exam").setSmallIcon(R.drawable.ic_stat_memora).setContentTitle("Daily Exams scheduled").setContentText("Memora is ready to generate today's tutor exams.").setAutoCancel(true).apply{if(pi!=null)setContentIntent(pi)}.build(); nm.notify(4610,n)
}}
class DailyExamBootReceiver: BroadcastReceiver(){ override fun onReceive(context:Context,intent:Intent?){ if(intent?.action!=Intent.ACTION_BOOT_COMPLETED)return; val p=context.getSharedPreferences("FlutterSharedPreferences",Context.MODE_PRIVATE); if(p.getBoolean("flutter.daily_exam_auto_enabled",false)) DailyExamAlarm.schedule(context,p.getLong("flutter.daily_exam_auto_hour",6).toInt(),p.getLong("flutter.daily_exam_auto_minute",0).toInt()) }}
'''
p.write_text(a)

# Manifest additions.
p=Path('android/AndroidManifest.xml'); m=p.read_text()
if 'android.permission.SCHEDULE_EXACT_ALARM' not in m: m=m.replace('<manifest','<manifest',1).replace('>\n', '>\n    <uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" />\n    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />\n',1)
app_end='    </application>'
receivers='''        <receiver android:name=".DailyExamAlarmReceiver" android:exported="false" />
        <receiver android:name=".DailyExamBootReceiver" android:enabled="true" android:exported="false">
            <intent-filter><action android:name="android.intent.action.BOOT_COMPLETED" /></intent-filter>
        </receiver>
'''
if '.DailyExamAlarmReceiver' not in m: m=m.replace(app_end,receivers+app_end,1)
p.write_text(m)

p=Path('pubspec.yaml'); v=p.read_text().replace('version: 1.45.0+58','version: 1.46.0+59'); p.write_text(v)
print('Memora v1.46 automatic Daily Exam scheduling + Android exact alarm applied successfully')
