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

class MemoraForegroundService : Service() {
    companion object {
        const val ACTION_START = "com.memora.memora.action.BACKGROUND_START"
        const val ACTION_UPDATE = "com.memora.memora.action.BACKGROUND_UPDATE"
        const val ACTION_STOP = "com.memora.memora.action.BACKGROUND_STOP"
        const val EXTRA_TITLE = "title"
        const val EXTRA_BODY = "body"
        const val EXTRA_PROGRESS = "progress"
        const val EXTRA_MAX = "max"

        private const val CHANNEL_ID = "memora_background_tasks"
        private const val NOTIFICATION_ID = 1701

        @Volatile
        var running: Boolean = false
            private set
    }

    private var wakeLock: PowerManager.WakeLock? = null
    private var lastTitle = "Memora is working"
    private var lastBody = "Keeping this task active in the background…"
    private var lastProgress = -1
    private var lastMax = -1

    override fun onCreate() {
        super.onCreate()
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopServiceNow()
                return START_NOT_STICKY
            }
            ACTION_START, ACTION_UPDATE, null -> {
                lastTitle = intent?.getStringExtra(EXTRA_TITLE)?.takeIf { it.isNotBlank() } ?: lastTitle
                lastBody = intent?.getStringExtra(EXTRA_BODY)?.takeIf { it.isNotBlank() } ?: lastBody
                lastProgress = intent?.getIntExtra(EXTRA_PROGRESS, -1) ?: -1
                lastMax = intent?.getIntExtra(EXTRA_MAX, -1) ?: -1

                if (!running) {
                    running = true
                    acquireWakeLock()
                    startForeground(NOTIFICATION_ID, buildNotification())
                } else {
                    val manager = getSystemService(NotificationManager::class.java)
                    manager.notify(NOTIFICATION_ID, buildNotification())
                }
            }
        }
        return START_NOT_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onTaskRemoved(rootIntent: Intent?) {
        // Keep the foreground service alive if the user swipes Memora away from
        // Recents while an AI task is still running. Force Stop from Android
        // settings will still stop the process, as required by Android.
        super.onTaskRemoved(rootIntent)
    }

    override fun onDestroy() {
        releaseWakeLock()
        running = false
        super.onDestroy()
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_ID,
                    "Memora background work",
                    NotificationManager.IMPORTANCE_LOW
                ).apply {
                    description = "Keeps long Memora AI tasks running while the app is in the background."
                    setShowBadge(false)
                }
            )
        }
    }

    private fun acquireWakeLock() {
        if (wakeLock?.isHeld == true) return
        val manager = getSystemService(POWER_SERVICE) as PowerManager
        wakeLock = manager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "Memora:LongAiTask"
        ).apply {
            setReferenceCounted(false)
            // Android 15 limits data-sync foreground services too; this timeout
            // is a safety net so a crashed task cannot hold the CPU forever.
            acquire(6L * 60L * 60L * 1000L)
        }
    }

    private fun releaseWakeLock() {
        try {
            if (wakeLock?.isHeld == true) wakeLock?.release()
        } catch (_: Exception) {
        } finally {
            wakeLock = null
        }
    }

    private fun buildNotification(): Notification {
        val launchIntent = packageManager.getLaunchIntentForPackage(packageName)
        val pendingIntent = launchIntent?.let {
            PendingIntent.getActivity(
                this,
                1701,
                it,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
        }

        val builder = Notification.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stat_memora)
            .setContentTitle(lastTitle)
            .setContentText(lastBody)
            .setStyle(Notification.BigTextStyle().bigText(lastBody))
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setCategory(Notification.CATEGORY_SERVICE)
            .setVisibility(Notification.VISIBILITY_PUBLIC)

        if (lastProgress >= 0 && lastMax > 0) {
            builder.setProgress(lastMax, lastProgress.coerceIn(0, lastMax), false)
        } else {
            builder.setProgress(0, 0, true)
        }
        if (pendingIntent != null) builder.setContentIntent(pendingIntent)
        return builder.build()
    }

    private fun stopServiceNow() {
        releaseWakeLock()
        running = false
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            @Suppress("DEPRECATION")
            stopForeground(true)
        }
        stopSelf()
    }
}
