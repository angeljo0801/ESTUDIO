package com.memora.memora

import android.Manifest
import android.app.AlarmManager
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.ParcelFileDescriptor
import java.util.Calendar
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    companion object { @Volatile private var retainedEngine: FlutterEngine? = null }
    private var sharedModelDescriptor: ParcelFileDescriptor? = null
    private val notificationChannelId = "memora_tasks"
    private val notificationPermissionRequest = 4317
    private var pendingNotification: Triple<Int,String,String>? = null
    override fun provideFlutterEngine(context:Context):FlutterEngine?=retainedEngine
    override fun shouldDestroyEngineWithHost():Boolean=!MemoraForegroundService.running
    override fun configureFlutterEngine(flutterEngine:FlutterEngine){
        super.configureFlutterEngine(flutterEngine); retainedEngine=flutterEngine; createTaskNotificationChannel(); val appContext=applicationContext
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger,"com.memora/shared_model").setMethodCallHandler{call,result->when(call.method){
            "openSharedModel"->{val raw=call.argument<String>("uri");if(raw.isNullOrBlank()){result.error("INVALID_URI","No shared model URI was provided.",null);return@setMethodCallHandler};try{sharedModelDescriptor?.close();sharedModelDescriptor=null;val uri=Uri.parse(raw);if(uri.scheme=="file"){result.success(uri.path);return@setMethodCallHandler};val d=contentResolver.openFileDescriptor(uri,"r");if(d==null){result.error("OPEN_FAILED","Android could not open the shared model.",null);return@setMethodCallHandler};sharedModelDescriptor=d;result.success("/proc/self/fd/${d.fd}")}catch(e:Exception){result.error("OPEN_FAILED",e.message,null)}}
            "closeSharedModel"->{try{sharedModelDescriptor?.close()}catch(_:Exception){}finally{sharedModelDescriptor=null};result.success(null)}
            else->result.notImplemented()}}
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger,"com.memora/notifications").setMethodCallHandler{call,result->when(call.method){
            "ensurePermission"->{ensureNotificationPermission();result.success(null)}
            "notify"->{val id=call.argument<Int>("id")?:2001;val title=call.argument<String>("title")?.trim().orEmpty();val body=call.argument<String>("body")?.trim().orEmpty();if(title.isEmpty()||body.isEmpty()){result.error("INVALID_NOTIFICATION","Title and body are required.",null);return@setMethodCallHandler};if(canPostNotifications())postTaskNotification(id,title,body)else{pendingNotification=Triple(id,title,body);ensureNotificationPermission()};result.success(null)}
            else->result.notImplemented()}}
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger,"com.memora/daily_exam_alarm").setMethodCallHandler{call,result->
            val prefs=appContext.getSharedPreferences("FlutterSharedPreferences",Context.MODE_PRIVATE)
            when(call.method){"schedule"->{val h=call.argument<Int>("hour")?:6;val m=call.argument<Int>("minute")?:0;prefs.edit().putBoolean("flutter.daily_exam_auto_enabled",true).putLong("flutter.daily_exam_auto_hour",h.toLong()).putLong("flutter.daily_exam_auto_minute",m.toLong()).apply();DailyExamAlarm.schedule(appContext,h,m);result.success(null)};"cancel"->{prefs.edit().putBoolean("flutter.daily_exam_auto_enabled",false).putBoolean("flutter.daily_exam_auto_pending",false).apply();DailyExamAlarm.cancel(appContext);result.success(null)};else->result.notImplemented()}}
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger,"com.memora/background_tasks").setMethodCallHandler{call,result->when(call.method){
            "start","update"->{val intent=Intent(appContext,MemoraForegroundService::class.java).apply{action=if(call.method=="start")MemoraForegroundService.ACTION_START else MemoraForegroundService.ACTION_UPDATE;putExtra(MemoraForegroundService.EXTRA_TITLE,call.argument<String>("title")?.trim().orEmpty());putExtra(MemoraForegroundService.EXTRA_BODY,call.argument<String>("body")?.trim().orEmpty());putExtra(MemoraForegroundService.EXTRA_PROGRESS,call.argument<Int>("progress")?:-1);putExtra(MemoraForegroundService.EXTRA_MAX,call.argument<Int>("max")?:-1)};try{if(Build.VERSION.SDK_INT>=Build.VERSION_CODES.O)appContext.startForegroundService(intent)else appContext.startService(intent);result.success(null)}catch(e:Exception){result.error("BACKGROUND_SERVICE",e.message,null)}}
            "stop"->{try{appContext.stopService(Intent(appContext,MemoraForegroundService::class.java));result.success(null)}catch(e:Exception){result.error("BACKGROUND_SERVICE",e.message,null)}};else->result.notImplemented()}}
    }
    private fun createTaskNotificationChannel(){if(Build.VERSION.SDK_INT>=Build.VERSION_CODES.O)getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel(notificationChannelId,"Memora notifications",NotificationManager.IMPORTANCE_DEFAULT))}
    private fun canPostNotifications()=Build.VERSION.SDK_INT<Build.VERSION_CODES.TIRAMISU||checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)==PackageManager.PERMISSION_GRANTED
    private fun ensureNotificationPermission(){if(Build.VERSION.SDK_INT>=Build.VERSION_CODES.TIRAMISU&&!canPostNotifications())requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS),notificationPermissionRequest)}
    private fun postTaskNotification(id:Int,title:String,body:String){val manager=getSystemService(NotificationManager::class.java);val launch=packageManager.getLaunchIntentForPackage(packageName);val pi=launch?.let{PendingIntent.getActivity(this,0,it,PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)};val b=Notification.Builder(this,notificationChannelId).setSmallIcon(R.drawable.ic_stat_memora).setContentTitle(title).setContentText(body).setStyle(Notification.BigTextStyle().bigText(body)).setAutoCancel(true).setOnlyAlertOnce(true);if(pi!=null)b.setContentIntent(pi);manager.notify(id,b.build())}
    override fun onRequestPermissionsResult(requestCode:Int,permissions:Array<out String>,grantResults:IntArray){super.onRequestPermissionsResult(requestCode,permissions,grantResults);if(requestCode==notificationPermissionRequest){val p=pendingNotification;pendingNotification=null;if(grantResults.isNotEmpty()&&grantResults[0]==PackageManager.PERMISSION_GRANTED&&p!=null)postTaskNotification(p.first,p.second,p.third)}}
    override fun onDestroy(){try{sharedModelDescriptor?.close()}catch(_:Exception){}finally{sharedModelDescriptor=null};if(!MemoraForegroundService.running)retainedEngine=null;super.onDestroy()}
}

object DailyExamAlarm {
    private const val REQUEST=4610
    fun schedule(context:Context,hour:Int,minute:Int){
        val alarm=context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val pi=PendingIntent.getBroadcast(context,REQUEST,Intent(context,DailyExamAlarmReceiver::class.java),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val c=Calendar.getInstance().apply{set(Calendar.HOUR_OF_DAY,hour);set(Calendar.MINUTE,minute);set(Calendar.SECOND,0);set(Calendar.MILLISECOND,0);if(timeInMillis<=System.currentTimeMillis())add(Calendar.DAY_OF_YEAR,1)}
        if(Build.VERSION.SDK_INT>=Build.VERSION_CODES.S && !alarm.canScheduleExactAlarms()) alarm.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,c.timeInMillis,pi)
        else if(Build.VERSION.SDK_INT>=Build.VERSION_CODES.M) alarm.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,c.timeInMillis,pi)
        else alarm.setExact(AlarmManager.RTC_WAKEUP,c.timeInMillis,pi)
    }
    fun cancel(context:Context){val alarm=context.getSystemService(Context.ALARM_SERVICE) as AlarmManager;val pi=PendingIntent.getBroadcast(context,REQUEST,Intent(context,DailyExamAlarmReceiver::class.java),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE);alarm.cancel(pi)}
}
class DailyExamAlarmReceiver:BroadcastReceiver(){override fun onReceive(context:Context,intent:Intent?){
    val p=context.getSharedPreferences("FlutterSharedPreferences",Context.MODE_PRIVATE);if(!p.getBoolean("flutter.daily_exam_auto_enabled",false))return
    p.edit().putBoolean("flutter.daily_exam_auto_pending",true).apply()
    DailyExamAlarm.schedule(context,p.getLong("flutter.daily_exam_auto_hour",6).toInt(),p.getLong("flutter.daily_exam_auto_minute",0).toInt())
    val launch=context.packageManager.getLaunchIntentForPackage(context.packageName);val pi=launch?.let{PendingIntent.getActivity(context,4611,it,PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)};val nm=context.getSystemService(NotificationManager::class.java);if(Build.VERSION.SDK_INT>=Build.VERSION_CODES.O)nm.createNotificationChannel(NotificationChannel("memora_daily_exam","Memora Daily Exams",NotificationManager.IMPORTANCE_DEFAULT));if(Build.VERSION.SDK_INT<Build.VERSION_CODES.TIRAMISU||context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)==PackageManager.PERMISSION_GRANTED){val b=Notification.Builder(context,"memora_daily_exam").setSmallIcon(R.drawable.ic_stat_memora).setContentTitle("Daily Exams pending").setContentText("Memora marked today's tutor exams for generation.").setAutoCancel(true);if(pi!=null)b.setContentIntent(pi);nm.notify(4610,b.build())}
}}
class DailyExamBootReceiver:BroadcastReceiver(){override fun onReceive(context:Context,intent:Intent?){if(intent?.action!=Intent.ACTION_BOOT_COMPLETED&&intent?.action!=Intent.ACTION_TIME_CHANGED&&intent?.action!=Intent.ACTION_TIMEZONE_CHANGED&&intent?.action!=Intent.ACTION_MY_PACKAGE_REPLACED)return;val p=context.getSharedPreferences("FlutterSharedPreferences",Context.MODE_PRIVATE);if(p.getBoolean("flutter.daily_exam_auto_enabled",false))DailyExamAlarm.schedule(context,p.getLong("flutter.daily_exam_auto_hour",6).toInt(),p.getLong("flutter.daily_exam_auto_minute",0).toInt())}}
