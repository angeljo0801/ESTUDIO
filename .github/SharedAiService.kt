package com.angelapps.local_ai_manager

import android.app.Service
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.Message
import android.os.Messenger
import io.flutter.FlutterInjector
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.embedding.engine.dart.DartExecutor
import io.flutter.plugin.common.MethodChannel
import io.flutter.plugins.GeneratedPluginRegistrant
import java.util.ArrayDeque

class SharedAiService : Service() {
    companion object {
        const val MSG_ASK = 1
        const val MSG_UNLOAD = 2
        const val MSG_PING = 3
        const val MSG_RESPONSE = 100
        const val CHANNEL = "com.angelapps.local_ai_manager/service_engine"
    }

    private data class PendingRequest(
        val what: Int,
        val id: String,
        val data: Bundle,
        val replyTo: Messenger
    )

    private lateinit var flutterEngine: FlutterEngine
    private lateinit var channel: MethodChannel
    private var dartReady = false
    private val queue = ArrayDeque<PendingRequest>()

    private val incoming = Messenger(object : Handler(Looper.getMainLooper()) {
        override fun handleMessage(msg: Message) {
            val reply = msg.replyTo ?: return
            val id = msg.data.getString("id") ?: System.nanoTime().toString()
            val request = PendingRequest(msg.what, id, Bundle(msg.data), reply)
            if (!dartReady) {
                queue.add(request)
                return
            }
            dispatch(request)
        }
    })

    override fun onCreate() {
        super.onCreate()
        val loader = FlutterInjector.instance().flutterLoader()
        loader.startInitialization(this)
        loader.ensureInitializationComplete(this, null)

        flutterEngine = FlutterEngine(this)
        GeneratedPluginRegistrant.registerWith(flutterEngine)
        channel = MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            CHANNEL
        )
        channel.setMethodCallHandler { call, result ->
            if (call.method == "ready") {
                dartReady = true
                while (queue.isNotEmpty()) dispatch(queue.removeFirst())
                result.success(true)
            } else {
                result.notImplemented()
            }
        }

        val entrypoint = DartExecutor.DartEntrypoint(
            loader.findAppBundlePath(),
            "managerServiceMain"
        )
        flutterEngine.dartExecutor.executeDartEntrypoint(entrypoint)
    }

    override fun onBind(intent: Intent?): IBinder = incoming.binder

    override fun onDestroy() {
        try {
            channel.invokeMethod("unload", null)
        } catch (_: Exception) {}
        try {
            flutterEngine.destroy()
        } catch (_: Exception) {}
        super.onDestroy()
    }

    private fun dispatch(request: PendingRequest) {
        when (request.what) {
            MSG_ASK -> {
                val args = hashMapOf<String, Any?>(
                    "prompt" to request.data.getString("prompt").orEmpty(),
                    "system" to request.data.getString("system").orEmpty(),
                    "maxTokens" to request.data.getInt("maxTokens", 320),
                    "temperature" to request.data.getDouble("temperature", 0.2)
                )
                channel.invokeMethod("ask", args, object : MethodChannel.Result {
                    override fun success(result: Any?) {
                        sendReply(request, true, result?.toString().orEmpty(), null)
                    }

                    override fun error(code: String, message: String?, details: Any?) {
                        sendReply(
                            request,
                            false,
                            null,
                            message ?: code
                        )
                    }

                    override fun notImplemented() {
                        sendReply(
                            request,
                            false,
                            null,
                            "El servicio de Local AI Manager no está listo."
                        )
                    }
                })
            }

            MSG_UNLOAD -> {
                channel.invokeMethod("unload", null, object : MethodChannel.Result {
                    override fun success(result: Any?) {
                        sendReply(request, true, "OK", null)
                    }

                    override fun error(code: String, message: String?, details: Any?) {
                        sendReply(request, false, null, message ?: code)
                    }

                    override fun notImplemented() {
                        sendReply(request, false, null, "Unload no disponible.")
                    }
                })
            }

            MSG_PING -> sendReply(request, true, "OK", null)
            else -> sendReply(request, false, null, "Solicitud desconocida.")
        }
    }

    private fun sendReply(
        request: PendingRequest,
        ok: Boolean,
        text: String?,
        error: String?
    ) {
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
}
