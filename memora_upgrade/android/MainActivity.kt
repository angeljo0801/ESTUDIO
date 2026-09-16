package com.memora.memora

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.ParcelFileDescriptor
import com.google.mlkit.common.model.DownloadConditions
import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.Translator
import com.google.mlkit.nl.translate.TranslatorOptions
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    companion object {
        @Volatile
        private var retainedEngine: FlutterEngine? = null
    }

    private var sharedModelDescriptor: ParcelFileDescriptor? = null
    private val notificationChannelId = "memora_tasks"
    private val notificationPermissionRequest = 4317
    private var pendingNotification: Triple<Int, String, String>? = null

    private val spanishTranslator: Translator by lazy {
        val options = TranslatorOptions.Builder()
            .setSourceLanguage(TranslateLanguage.ENGLISH)
            .setTargetLanguage(TranslateLanguage.SPANISH)
            .build()
        Translation.getClient(options)
    }

    override fun provideFlutterEngine(context: Context): FlutterEngine? = retainedEngine

    override fun shouldDestroyEngineWithHost(): Boolean = !MemoraForegroundService.running

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        retainedEngine = flutterEngine
        createTaskNotificationChannel()
        val appContext = applicationContext

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
            "com.memora/translation"
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "prepareSpanish" -> prepareSpanishTranslator(result)
                "translateToSpanish" -> {
                    val text = call.argument<String>("text")?.trim().orEmpty()
                    if (text.isEmpty()) {
                        result.success("")
                    } else {
                        translateToSpanish(text, result)
                    }
                }
                else -> result.notImplemented()
            }
        }

        // Warm up the offline translator in the background. The model is only
        // downloaded once; later translations work without an internet connection.
        spanishTranslator.downloadModelIfNeeded(DownloadConditions.Builder().build())

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

        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            "com.memora/background_tasks"
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "start", "update" -> {
                    val title = call.argument<String>("title")?.trim().orEmpty()
                    val body = call.argument<String>("body")?.trim().orEmpty()
                    val progress = call.argument<Int>("progress") ?: -1
                    val max = call.argument<Int>("max") ?: -1
                    val intent = Intent(appContext, MemoraForegroundService::class.java).apply {
                        action = if (call.method == "start") {
                            MemoraForegroundService.ACTION_START
                        } else {
                            MemoraForegroundService.ACTION_UPDATE
                        }
                        putExtra(MemoraForegroundService.EXTRA_TITLE, title)
                        putExtra(MemoraForegroundService.EXTRA_BODY, body)
                        putExtra(MemoraForegroundService.EXTRA_PROGRESS, progress)
                        putExtra(MemoraForegroundService.EXTRA_MAX, max)
                    }
                    try {
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                            appContext.startForegroundService(intent)
                        } else {
                            appContext.startService(intent)
                        }
                        result.success(null)
                    } catch (e: Exception) {
                        result.error("BACKGROUND_SERVICE", e.message, null)
                    }
                }

                "stop" -> {
                    try {
                        appContext.stopService(Intent(appContext, MemoraForegroundService::class.java))
                        result.success(null)
                    } catch (e: Exception) {
                        result.error("BACKGROUND_SERVICE", e.message, null)
                    }
                }

                else -> result.notImplemented()
            }
        }
    }

    private fun prepareSpanishTranslator(result: MethodChannel.Result) {
        val conditions = DownloadConditions.Builder().build()
        spanishTranslator.downloadModelIfNeeded(conditions)
            .addOnSuccessListener { result.success(null) }
            .addOnFailureListener { error ->
                result.error(
                    "TRANSLATION_MODEL",
                    error.message ?: "Could not download the offline Spanish translator.",
                    null
                )
            }
    }

    private fun translateToSpanish(text: String, result: MethodChannel.Result) {
        val conditions = DownloadConditions.Builder().build()
        spanishTranslator.downloadModelIfNeeded(conditions)
            .addOnSuccessListener {
                spanishTranslator.translate(text)
                    .addOnSuccessListener { translated -> result.success(translated) }
                    .addOnFailureListener { error ->
                        result.error(
                            "TRANSLATION_FAILED",
                            error.message ?: "The offline translator could not translate this response.",
                            null
                        )
                    }
            }
            .addOnFailureListener { error ->
                result.error(
                    "TRANSLATION_MODEL",
                    error.message ?: "Could not download the offline Spanish translator.",
                    null
                )
            }
    }

    private fun createTaskNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(NotificationManager::class.java)
            val channel = NotificationChannel(
                notificationChannelId,
                "Memora notifications",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "Notifications when Memora finishes tutor replies, exams, plans, guides, and other tasks."
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
            .setSmallIcon(R.drawable.ic_stat_memora)
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
        if (!MemoraForegroundService.running) retainedEngine = null
        super.onDestroy()
    }
}
