package com.angelapps.local_ai_manager

import android.app.Service
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.Message
import android.os.Messenger
import androidx.core.app.NotificationCompat
import io.flutter.plugin.common.MethodChannel
import java.util.ArrayDeque

class SharedAiService : Service() {
    companion object {
        const val MSG_ASK = 1
        const val MSG_UNLOAD = 2
        const val MSG_PING = 3
        const val MSG_RESPONSE = 100
        const val CHANNEL = "com.angelapps.local_ai_manager/service_engine"
        private const val NOTIFICATION_CHANNEL = "local_ai_manager_engine"
        private const val NOTIFICATION_ID = 1101
    }

    private data class PendingRequest(
        val what: Int,
        val id: String,
        val data: Bundle,
        val replyTo: Messenger,
        val clientPackage: String
    )

    private lateinit var channel: MethodChannel
    private var channelReady = false
    private val queue = ArrayDeque<PendingRequest>()
    private val handler = Handler(Looper.getMainLooper())

    private val incoming = Messenger(object : Handler(Looper.getMainLooper()) {
        override fun handleMessage(msg: Message) {
            val reply = msg.replyTo ?: return
            val id = msg.data.getString("id") ?: System.nanoTime().toString()
            val packages = packageManager.getPackagesForUid(msg.sendingUid).orEmpty()
            val clientPackage = packages.firstOrNull {
                it == "com.memora.memora" ||
                    it == "com.whatsbot.whatsbot" ||
                    it.contains("finanz", ignoreCase = true)
            } ?: packages.firstOrNull().orEmpty()
            val request = PendingRequest(
                msg.what,
                id,
                Bundle(msg.data),
                reply,
                clientPackage
            )

            if (msg.what == MSG_PING) {
                sendReply(request, true, "OK", null)
                return
            }

            queue.add(request)
            flushQueue()
        }
    })

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(
            NOTIFICATION_ID,
            buildNotification("Motor de IA listo")
        )

        val engine =
            (application as ManagerApplication).sharedFlutterEngine

        channel = MethodChannel(
            engine.dartExecutor.binaryMessenger,
            CHANNEL
        )

        // Dart can announce readiness. If that announcement happened before the
        // service was created, the retry loop below still handles the race.
        channel.setMethodCallHandler { call, result ->
            if (call.method == "ready") {
                channelReady = true
                flushQueue()
                result.success(true)
            } else {
                result.notImplemented()
            }
        }

        // The main Dart isolate normally installs its handler almost instantly.
        handler.postDelayed({
            channelReady = true
            flushQueue()
        }, 350)
    }

    override fun onBind(intent: Intent?): IBinder = incoming.binder

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }

    private fun flushQueue() {
        if (!channelReady || queue.isEmpty()) return
        val pendingItems = mutableListOf<PendingRequest>()
        while (queue.isNotEmpty()) {
            pendingItems.add(queue.removeFirst())
        }
        for (request in pendingItems) {
            dispatch(request, 0)
        }
    }

    private fun dispatch(request: PendingRequest, attempt: Int) {
        when (request.what) {
            MSG_ASK -> {
                updateNotification(
                    "Procesando para " + clientLabel(request.clientPackage)
                )
                val args = hashMapOf<String, Any?>(
                    "prompt" to request.data.getString("prompt").orEmpty(),
                    "system" to request.data.getString("system").orEmpty(),
                    "maxTokens" to request.data.getInt("maxTokens", 320),
                    "temperature" to request.data.getDouble("temperature", 0.2)
                )
                invokeWithRetry(request, "ask", args, attempt)
            }

            MSG_UNLOAD -> {
                invokeWithRetry(request, "unload", null, attempt)
            }

            else -> {
                sendReply(request, false, null, "Solicitud desconocida.")
            }
        }
    }

    private fun invokeWithRetry(
        request: PendingRequest,
        method: String,
        args: Any?,
        attempt: Int
    ) {
        try {
            channel.invokeMethod(
                method,
                args,
                object : MethodChannel.Result {
                    override fun success(result: Any?) {
                        sendReply(
                            request,
                            true,
                            result?.toString().orEmpty(),
                            null
                        )
                    }

                    override fun error(
                        code: String,
                        message: String?,
                        details: Any?
                    ) {
                        if (attempt < 60 &&
                            (code == "channel-error" ||
                             code == "missing-plugin")) {
                            retry(request, attempt + 1)
                        } else {
                            sendReply(
                                request,
                                false,
                                null,
                                message ?: code
                            )
                        }
                    }

                    override fun notImplemented() {
                        if (attempt < 60) {
                            retry(request, attempt + 1)
                        } else {
                            sendReply(
                                request,
                                false,
                                null,
                                "El motor compartido del Manager no inició."
                            )
                        }
                    }
                }
            )
        } catch (e: Exception) {
            if (attempt < 60) {
                retry(request, attempt + 1)
            } else {
                sendReply(
                    request,
                    false,
                    null,
                    e.message ?: "Error interno del Manager."
                )
            }
        }
    }

    private fun retry(request: PendingRequest, attempt: Int) {
        handler.postDelayed(
            { dispatch(request, attempt) },
            500L
        )
    }

    private fun clientLabel(packageName: String): String {
        return when (packageName) {
            "com.memora.memora" -> "Memora"
            "com.whatsbot.whatsbot" -> "WhatsBot"
            else -> if (packageName.contains("finanz", ignoreCase = true)) {
                "Finanzas"
            } else if (packageName.isNotBlank()) {
                packageName.substringAfterLast('.')
            } else {
                "una aplicación"
            }
        }
    }

    private fun sendReply(
        request: PendingRequest,
        ok: Boolean,
        text: String?,
        error: String?
    ) {
        updateNotification("Motor de IA listo")
        try {
            val msg = Message.obtain(null, MSG_RESPONSE)
            msg.data = Bundle().apply {
                putString("id", request.id)
                putBoolean("ok", ok)
                if (text != null) putString("result", text)
                if (error != null) putString("error", error)
            }
            request.replyTo.send(msg)
        } catch (_: Exception) {}
    }
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(NotificationManager::class.java)
            val channel = NotificationChannel(
                NOTIFICATION_CHANNEL,
                "Local AI Manager",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Mantiene disponible el modelo local para Memora, Finanzas y WhatsBot."
                setShowBadge(false)
            }
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(text: String): Notification {
        return NotificationCompat.Builder(this, NOTIFICATION_CHANNEL)
            .setSmallIcon(android.R.drawable.stat_sys_download_done)
            .setContentTitle("Local AI Manager")
            .setContentText(text)
            .setOngoing(true)
            .setSilent(true)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .build()
    }

    private fun updateNotification(text: String) {
        try {
            val manager = getSystemService(NotificationManager::class.java)
            manager.notify(NOTIFICATION_ID, buildNotification(text))
        } catch (_: Exception) {}
    }

}
