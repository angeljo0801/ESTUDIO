package com.angelapps.local_ai_manager

import android.app.ActivityManager
import android.content.Context
import android.os.Process
import io.flutter.FlutterInjector
import io.flutter.app.FlutterApplication
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.embedding.engine.dart.DartExecutor

class ManagerApplication : FlutterApplication() {
    lateinit var sharedFlutterEngine: FlutterEngine
        private set

    private fun currentProcessName(): String {
        val manager = getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        return manager.runningAppProcesses
            ?.firstOrNull { it.pid == Process.myPid() }
            ?.processName
            .orEmpty()
    }

    override fun onCreate() {
        super.onCreate()

        val loader = FlutterInjector.instance().flutterLoader()
        loader.startInitialization(this)
        loader.ensureInitializationComplete(this, null)

        sharedFlutterEngine = FlutterEngine(this)
        val processName = currentProcessName()
        val entrypoint = if (processName.endsWith(":ai_engine")) {
            DartExecutor.DartEntrypoint(
                loader.findAppBundlePath(),
                "sharedServiceMain"
            )
        } else {
            DartExecutor.DartEntrypoint.createDefault()
        }
        sharedFlutterEngine.dartExecutor.executeDartEntrypoint(entrypoint)
    }
}
