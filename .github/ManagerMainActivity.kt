package com.angelapps.local_ai_manager

import android.content.Context
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine

class MainActivity : FlutterActivity() {
    override fun provideFlutterEngine(context: Context): FlutterEngine? {
        return (application as ManagerApplication).sharedFlutterEngine
    }

    override fun shouldDestroyEngineWithHost(): Boolean = false
}
