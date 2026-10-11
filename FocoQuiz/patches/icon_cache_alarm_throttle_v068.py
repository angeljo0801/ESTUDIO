#!/usr/bin/env python3
"""FocoQuiz v0.6.8: reuse icons and avoid unnecessary alarm rescheduling at startup."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
p=r/'app/src/main/java/com/focoquiz/app/MainActivity.kt'
g=r/'app/build.gradle.kts'
s=p.read_text(encoding="utf-8")
def replace(a,b):
 global s
 if a not in s:raise SystemExit("v0.6.8 patch mismatch: "+a[:100])
 s=s.replace(a,b,1)

replace('import android.os.Looper\n',
        'import android.os.Looper\nimport android.graphics.drawable.Drawable\nimport android.util.LruCache\n')
replace('''    private val mainHandler = Handler(Looper.getMainLooper())''',
'''    private val mainHandler = Handler(Looper.getMainLooper())
    // Icons are cached only in RAM, never in the user's storage.
    private val appIconCache = LruCache<String, Drawable>(64)''')
replace('''            // Rescheduling alarms can involve many synchronous binder calls.
            runCatching { StudyAlarmScheduler.refresh(applicationContext) }''',
'''            // Android keeps scheduled alarms when the app process closes.
            // Plans changes, boot and system time changes already trigger refresh.
            // Avoid cancelling/recreating every alarm at EACH app launch.
            runCatching {
                val appContext = applicationContext
                val preferences = appContext.getSharedPreferences("focoquiz_startup", MODE_PRIVATE)
                val now = System.currentTimeMillis()
                val last = preferences.getLong("last_alarm_refresh", 0L)
                if (last <= 0L || now < last || now - last > 60L * 60L * 1000L) {
                    StudyAlarmScheduler.refresh(appContext)
                    preferences.edit().putLong("last_alarm_refresh", now).apply()
                }
            }''')
replace('''            if (!io.isShutdown) io.execute {
                val drawable = runCatching {
                    packageManager.getApplicationIcon(app.packageName)
                }.getOrNull()
                if (drawable != null) runOnUiThread {
                    if (!isFinishing && !isDestroyed && revision == listRevision && icon.parent != null)
                        icon.setImageDrawable(drawable)
                }
            }''',
'''            val cachedIcon = appIconCache.get(app.packageName)
            if (cachedIcon != null) {
                icon.setImageDrawable(cachedIcon.constantState?.newDrawable(resources) ?: cachedIcon)
            } else if (!io.isShutdown) {
                io.execute {
                    val drawable = runCatching {
                        packageManager.getApplicationIcon(app.packageName)
                    }.getOrNull()
                    if (drawable != null) {
                        appIconCache.put(app.packageName, drawable)
                        runOnUiThread {
                            if (!isFinishing && !isDestroyed &&
                                revision == listRevision && icon.parent != null) {
                                icon.setImageDrawable(drawable.constantState?.newDrawable(resources)
                                    ?: drawable)
                            }
                        }
                    }
                }
            }''')
p.write_text(s,encoding="utf-8")
v=g.read_text(encoding="utf-8")
if 'versionName = "0.6.7"' not in v or 'versionCode = 13' not in v:
 raise SystemExit("Expected signed release v0.6.7")
g.write_text(v.replace('versionName = "0.6.7"','versionName = "0.6.8"')
              .replace('versionCode = 13','versionCode = 14'),encoding="utf-8")
assert "LruCache<String, Drawable>" in s
assert "last_alarm_refresh" in s
print("v0.6.8: reuse app icons and throttle unnecessary startup alarm refresh.")
