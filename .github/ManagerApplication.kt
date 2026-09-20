package com.angelapps.local_ai_manager

import io.flutter.FlutterInjector
import io.flutter.app.FlutterApplication
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.embedding.engine.dart.DartExecutor

class ManagerApplication : FlutterApplication() {
    lateinit var sharedFlutterEngine: FlutterEngine
        private set

    override fun onCreate() {
        super.onCreate()

        val loader = FlutterInjector.instance().flutterLoader()
        loader.startInitialization(this)
        loader.ensureInitializationComplete(this, null)

        sharedFlutterEngine = FlutterEngine(this)
        sharedFlutterEngine.dartExecutor.executeDartEntrypoint(
            DartExecutor.DartEntrypoint.createDefault()
        )
    }
}
