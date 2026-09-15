package com.memora.memora

import android.net.Uri
import android.os.ParcelFileDescriptor
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private var sharedModelDescriptor: ParcelFileDescriptor? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
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
