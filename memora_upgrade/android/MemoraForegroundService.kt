package com.memora.memora

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import io.flutter.FlutterInjector
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.embedding.engine.dart.DartExecutor
import io.flutter.plugin.common.MethodChannel

class MemoraForegroundService : Service() {
    companion object {
        const val ACTION_START = "com.memora.memora.action.BACKGROUND_START"
        const val ACTION_UPDATE = "com.memora.memora.action.BACKGROUND_UPDATE"
        const val ACTION_STOP = "com.memora.memora.action.BACKGROUND_STOP"
        const val ACTION_DAILY_EXAM = "com.memora.memora.action.DAILY_EXAM"
        const val EXTRA_TITLE = "title"
        const val EXTRA_BODY = "body"
        const val EXTRA_PROGRESS = "progress"
        const val EXTRA_MAX = "max"
        private const val CHANNEL_ID = "memora_background_tasks"
        private const val NOTIFICATION_ID = 1701
        @Volatile var running:Boolean=false; private set
    }
    private var wakeLock:PowerManager.WakeLock?=null
    private var headlessEngine:FlutterEngine?=null
    private var lastTitle="Memora is working"; private var lastBody="Keeping this task active in the background…"; private var lastProgress=-1; private var lastMax=-1
    override fun onCreate(){super.onCreate();createChannel()}
    override fun onStartCommand(intent:Intent?,flags:Int,startId:Int):Int{
        when(intent?.action){
            ACTION_STOP->{stopServiceNow();return START_NOT_STICKY}
            ACTION_DAILY_EXAM->{lastTitle="Memora Daily Exams";lastBody="Generating today's tutor exams…";ensureForeground();startDailyExamEngine();return START_NOT_STICKY}
            ACTION_START,ACTION_UPDATE,null->{lastTitle=intent?.getStringExtra(EXTRA_TITLE)?.takeIf{it.isNotBlank()}?:lastTitle;lastBody=intent?.getStringExtra(EXTRA_BODY)?.takeIf{it.isNotBlank()}?:lastBody;lastProgress=intent?.getIntExtra(EXTRA_PROGRESS,-1)?:-1;lastMax=intent?.getIntExtra(EXTRA_MAX,-1)?:-1;ensureForeground()}
        };return START_NOT_STICKY
    }
    private fun ensureForeground(){if(!running){running=true;acquireWakeLock();startForeground(NOTIFICATION_ID,buildNotification())}else getSystemService(NotificationManager::class.java).notify(NOTIFICATION_ID,buildNotification())}
    private fun startDailyExamEngine(){
        if(headlessEngine!=null)return
        try{
            val loader=FlutterInjector.instance().flutterLoader();loader.startInitialization(applicationContext);loader.ensureInitializationComplete(applicationContext,null)
            val engine=FlutterEngine(applicationContext);headlessEngine=engine
            MethodChannel(engine.dartExecutor.binaryMessenger,"com.memora/daily_exam_headless").setMethodCallHandler{call,result->when(call.method){"complete"->{result.success(null);finishDailyExam()};else->result.notImplemented()}}
            val bundle=loader.findAppBundlePath();val entry=DartExecutor.DartEntrypoint(bundle,"dailyExamHeadlessMain");engine.dartExecutor.executeDartEntrypoint(entry)
        }catch(e:Exception){lastBody="Daily Exam generation is pending and will retry when Memora opens.";getSystemService(NotificationManager::class.java).notify(NOTIFICATION_ID,buildNotification());finishDailyExam(false)}
    }
    private fun finishDailyExam(stop:Boolean=true){headlessEngine?.destroy();headlessEngine=null;if(stop)stopServiceNow() else {releaseWakeLock();running=false;stopForeground(STOP_FOREGROUND_REMOVE);stopSelf()}}
    override fun onBind(intent:Intent?):IBinder?=null
    override fun onDestroy(){headlessEngine?.destroy();headlessEngine=null;releaseWakeLock();running=false;super.onDestroy()}
    private fun createChannel(){if(Build.VERSION.SDK_INT>=Build.VERSION_CODES.O)getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel(CHANNEL_ID,"Memora background work",NotificationManager.IMPORTANCE_LOW))}
    private fun acquireWakeLock(){if(wakeLock?.isHeld==true)return;val pm=getSystemService(POWER_SERVICE) as PowerManager;wakeLock=pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"Memora:LongAiTask").apply{setReferenceCounted(false);acquire(6L*60L*60L*1000L)}}
    private fun releaseWakeLock(){try{if(wakeLock?.isHeld==true)wakeLock?.release()}catch(_:Exception){}finally{wakeLock=null}}
    private fun buildNotification():Notification{val launch=packageManager.getLaunchIntentForPackage(packageName);val pi=launch?.let{PendingIntent.getActivity(this,1701,it,PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)};val b=Notification.Builder(this,CHANNEL_ID).setSmallIcon(R.drawable.ic_stat_memora).setContentTitle(lastTitle).setContentText(lastBody).setStyle(Notification.BigTextStyle().bigText(lastBody)).setOngoing(true).setOnlyAlertOnce(true).setCategory(Notification.CATEGORY_SERVICE).setVisibility(Notification.VISIBILITY_PUBLIC);if(lastProgress>=0&&lastMax>0)b.setProgress(lastMax,lastProgress.coerceIn(0,lastMax),false)else b.setProgress(0,0,true);if(pi!=null)b.setContentIntent(pi);return b.build()}
    private fun stopServiceNow(){releaseWakeLock();running=false;if(Build.VERSION.SDK_INT>=Build.VERSION_CODES.N)stopForeground(STOP_FOREGROUND_REMOVE)else @Suppress("DEPRECATION") stopForeground(true);stopSelf()}
}
