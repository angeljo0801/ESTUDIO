package com.angelapps.local_ai_manager

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.os.Bundle
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.Message
import android.os.Messenger
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.MethodChannel
import java.util.ArrayDeque
import java.util.UUID

object ManagerSelfBridge {
    private const val CHANNEL = "com.angelapps.local_ai_manager/self_client"
    private const val SERVICE = "com.angelapps.local_ai_manager.SharedAiService"
    private const val MSG_ASK = 1
    private const val MSG_UNLOAD = 2
    private const val MSG_PING = 3
    private const val MSG_RESPONSE = 100

    private data class Outbound(
        val what: Int,
        val id: String,
        val data: Bundle
    )

    private var appContext: Context? = null
    private var service: Messenger? = null
    private var binding = false
    private val queue = ArrayDeque<Outbound>()
    private val pending = mutableMapOf<String, MethodChannel.Result>()
    private val handler = Handler(Looper.getMainLooper())

    private val replies = Messenger(object : Handler(Looper.getMainLooper()) {
        override fun handleMessage(msg: Message) {
            if (msg.what != MSG_RESPONSE) return
            val id = msg.data.getString("id") ?: return
            val result = pending.remove(id) ?: return
            if (msg.data.getBoolean("ok", false)) {
                result.success(msg.data.getString("result").orEmpty())
            } else {
                result.error(
                    "LOCAL_AI_ENGINE",
                    msg.data.getString("error")
                        ?: "El proceso de IA se cerró durante la prueba.",
                    null
                )
            }
        }
    })

    private val connection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
            service = Messenger(binder)
            binding = false
            flushQueue()
        }

        override fun onServiceDisconnected(name: ComponentName?) {
            service = null
            binding = false
            failAll(
                "El motor de IA se cerró durante la carga. " +
                    "La pantalla del Manager seguirá abierta para poder diagnosticarlo."
            )
        }

        override fun onBindingDied(name: ComponentName?) {
            service = null
            binding = false
            failAll(
                "Android reinició el proceso de IA. Vuelve a tocar Probar."
            )
        }

        override fun onNullBinding(name: ComponentName?) {
            service = null
            binding = false
            failAll("El proceso de IA no aceptó la conexión.")
        }
    }

    fun register(context: Context, messenger: BinaryMessenger) {
        appContext = context.applicationContext
        MethodChannel(messenger, CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "ask" -> {
                    val prompt = call.argument<String>("prompt").orEmpty()
                    if (prompt.isBlank()) {
                        result.error("INVALID_PROMPT", "La pregunta está vacía.", null)
                        return@setMethodCallHandler
                    }
                    val data = Bundle().apply {
                        putString("prompt", prompt)
                        putString("system", call.argument<String>("system").orEmpty())
                        putInt("maxTokens", call.argument<Int>("maxTokens") ?: 64)
                        putDouble(
                            "temperature",
                            call.argument<Double>("temperature") ?: 0.0
                        )
                    }
                    enqueue(MSG_ASK, data, result)
                }

                "unload" -> enqueue(MSG_UNLOAD, Bundle(), result)
                "ping" -> enqueue(MSG_PING, Bundle(), result)
                else -> result.notImplemented()
            }
        }
    }

    private fun enqueue(
        what: Int,
        data: Bundle,
        result: MethodChannel.Result
    ) {
        val id = UUID.randomUUID().toString()
        pending[id] = result
        queue.add(Outbound(what, id, data))
        handler.postDelayed({
            val timedOut = pending.remove(id)
            if (timedOut != null) {
                queue.removeAll { it.id == id }
                timedOut.error(
                    "LOCAL_AI_TIMEOUT",
                    "El proceso de IA tardó demasiado en responder.",
                    null
                )
            }
        }, 3 * 60 * 1000L)

        if (service != null) flushQueue() else ensureBound()
    }

    private fun ensureBound() {
        if (binding || service != null) return
        val context = appContext ?: run {
            failAll("No pude iniciar el proceso de IA.")
            return
        }
        binding = true
        try {
            val intent = Intent().apply {
                component = ComponentName(context.packageName, SERVICE)
            }
            val flags =
                Context.BIND_AUTO_CREATE or
                    Context.BIND_IMPORTANT or
                    Context.BIND_ABOVE_CLIENT
            val ok = context.bindService(intent, connection, flags)
            if (!ok) {
                binding = false
                failAll("No pude iniciar el proceso aislado de IA.")
            }
        } catch (e: Exception) {
            binding = false
            failAll("No pude abrir el motor de IA: ${e.message ?: "error"}")
        }
    }

    private fun flushQueue() {
        val target = service ?: return
        while (queue.isNotEmpty()) {
            val item = queue.removeFirst()
            if (!pending.containsKey(item.id)) continue
            try {
                val msg = Message.obtain(null, item.what)
                msg.replyTo = replies
                msg.data = Bundle(item.data).apply {
                    putString("id", item.id)
                }
                target.send(msg)
            } catch (e: Exception) {
                service = null
                pending.remove(item.id)?.error(
                    "LOCAL_AI_ENGINE",
                    "Se perdió la conexión con el proceso de IA.",
                    null
                )
                ensureBound()
                return
            }
        }
    }

    private fun failAll(message: String) {
        val items = pending.values.toList()
        pending.clear()
        queue.clear()
        for (result in items) {
            result.error("LOCAL_AI_ENGINE", message, null)
        }
    }
}
