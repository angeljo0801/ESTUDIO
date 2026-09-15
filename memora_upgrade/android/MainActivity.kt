package com.memora.memora

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.ParcelFileDescriptor
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private var sharedModelDescriptor: ParcelFileDescriptor? = null
    private val notificationChannelId = "memora_tasks"
    private val notificationPermissionRequest = 4317
    private var pendingNotification: Triple<Int, String, String>? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        createTaskNotificationChannel()

        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            "com.memora/shared_model"
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "openSharedModel" -> {
                    val rawUri = call.argument<String>("uri")
                    if (rawUri.isNullOrBlank()) {
                        result.error("INVALID_URI", "No shared model URI was provided.", null)
                        return@setMethodCallHandler
                    }
                    try {
                        sharedModelDescriptor?.close()
                        sharedModelDescriptor = null

                        val uri = Uri.parse(rawUri)
                        if (uri.scheme == "file") {
                            result.success(uri.path)
                            return@setMethodCallHandler
                        }

                        val descriptor = contentResolver.openFileDescriptor(uri, "r")
                        if (descriptor == null) {
                            result.error("OPEN_FAILED", "Android could not open the shared model.", null)
                            return@setMethodCallHandler
                        }
                        sharedModelDescriptor = descriptor
                        result.success("/proc/self/fd/${descriptor.fd}")
                    } catch (e: Exception) {
                        result.error("OPEN_FAILED", e.message, null)
                    }
                }

                "closeSharedModel" -> {
                    try {
                        sharedModelDescriptor?.close()
                    } catch (_: Exception) {
                    } finally {
                        sharedModelDescriptor = null
                    }
                    result.success(null)
                }

                else -> result.notImplemented()
            }
        }

        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            "com.memora/notifications"
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "ensurePermission" -> {
                    ensureNotificationPermission()
                    result.success(null)
                }

                "notify" -> {
                    val id = call.argument<Int>("id") ?: 2001
                    val title = call.argument<String>("title")?.trim().orEmpty()
                    val body = call.argument<String>("body")?.trim().orEmpty()
                    if (title.isEmpty() || body.isEmpty()) {
                        result.error("INVALID_NOTIFICATION", "Title and body are required.", null)
                        return@setMethodCallHandler
                    }
                    if (canPostNotifications()) {
                        postTaskNotification(id, title, body)
                    } else {
                        pendingNotification = Triple(id, title, body)
                        ensureNotificationPermission()
                    }
                    result.success(null)
                }

                else -> result.notImplemented()
            }
        }
    }

    private fun createTaskNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(NotificationManager::class.java)
            val channel = NotificationChannel(
                notificationChannelId,
                "Tareas terminadas",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "Avisos cuando Memora termina exámenes, planes, guías y otras tareas."
            }
            manager.createNotificationChannel(channel)
        }
    }

    private fun canPostNotifications(): Boolean {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
    }

    private fun ensureNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && !canPostNotifications()) {
            requestPermissions(
                arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                notificationPermissionRequest
            )
        }
    }

    private fun postTaskNotification(id: Int, title: String, body: String) {
        val manager = getSystemService(NotificationManager::class.java)
        val launchIntent: Intent? = packageManager.getLaunchIntentForPackage(packageName)
        val pendingIntent = launchIntent?.let {
            PendingIntent.getActivity(
                this,
                0,
                it,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
        }

        val builder = Notification.Builder(this, notificationChannelId)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(Notification.BigTextStyle().bigText(body))
            .setAutoCancel(true)
            .setOnlyAlertOnce(true)

        if (pendingIntent != null) builder.setContentIntent(pendingIntent)
        manager.notify(id, builder.build())
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == notificationPermissionRequest) {
            val pending = pendingNotification
            pendingNotification = null
            if (grantResults.isNotEmpty() &&
                grantResults[0] == PackageManager.PERMISSION_GRANTED &&
                pending != null
            ) {
                postTaskNotification(pending.first, pending.second, pending.third)
            }
        }
    }

    override fun onDestroy() {
        try {
            sharedModelDescriptor?.close()
        } catch (_: Exception) {
        } finally {
            sharedModelDescriptor = null
        }
        super.onDestroy()
    }
}
