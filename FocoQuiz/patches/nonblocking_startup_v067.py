#!/usr/bin/env python3
"""FocoQuiz v0.6.7: non-blocking startup, paged app list and off-main icons/alarms."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
p=r/'app/src/main/java/com/focoquiz/app/MainActivity.kt'
g=r/'app/build.gradle.kts'
s=p.read_text(encoding='utf-8')
def change(old,new):
    global s
    if old not in s: raise SystemExit("0.6.7 patch mismatch: " + old[:150])
    s=s.replace(old,new,1)

change('import android.os.Bundle\n','import android.os.Bundle\nimport android.os.Handler\nimport android.os.Looper\n')
change('import java.util.Locale\n','import java.util.Locale\nimport java.util.concurrent.Executors\n')

change('''    private val allApps by lazy { queryApps() }''',
'''    // App discovery, icon decoding and alarm scheduling must NEVER run on the UI thread.
    private val io = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())
    private var searchTask: Runnable? = null
    private var allApps: List<InstalledApp> = emptyList()
    private var appsLoaded = false
    private var visibleLimit = 24
    private var listRevision = 0''')

change('''        StudyPlanStore(this).seedSocialRules(store, allApps.map { it.packageName }, packageName)
        StudyAlarmScheduler.refresh(this)
        window.statusBarColor''',
'''        window.statusBarColor''')
change('''        render()
        handleSharedQuiz(intent)
    }''',
'''        render()
        handleSharedQuiz(intent)
        // Show the interactive screen immediately; load system information afterwards.
        io.execute {
            val apps = runCatching { queryApps() }.getOrElse { emptyList() }
            runCatching {
                StudyPlanStore(applicationContext).seedSocialRules(
                    store, apps.map { it.packageName }, packageName)
            }
            // Rescheduling alarms can involve many synchronous binder calls.
            runCatching { StudyAlarmScheduler.refresh(applicationContext) }
            runOnUiThread {
                if (!isFinishing && !isDestroyed) {
                    allApps = apps
                    appsLoaded = true
                    updateAppList(if (::searchField.isInitialized) searchField.text.toString() else "")
                    updateServiceStatus()
                }
            }
        }
    }''')

change('''            updateServiceStatus()
            updateAppList(searchField.text.toString())
        }
    }

    private fun render()''',
'''            updateServiceStatus()
            if (appsLoaded) updateAppList(searchField.text.toString())
        }
    }

    override fun onDestroy() {
        searchTask?.let(mainHandler::removeCallbacks)
        listRevision++
        io.shutdownNow()
        super.onDestroy()
    }

    private fun render()''')

change('''                updateAppList(s.toString())
            }
            override fun afterTextChanged''',
'''                visibleLimit = 24
                searchTask?.let(mainHandler::removeCallbacks)
                val task = Runnable { updateAppList(s?.toString() ?: "") }
                searchTask = task
                mainHandler.postDelayed(task, 180L)
            }
            override fun afterTextChanged''')

start=s.index('    private fun updateServiceStatus() {')
end=s.index('    private fun queryApps()',start)
s=s[:start]+'''    private fun updateServiceStatus() {
        val active = serviceEnabled()
        // Never parse study plans on the activity's render path.
        statusLabel.text = if (active) "● Protección activa" else "○ Protección desactivada"
        statusLabel.setTextColor(if (active) Style.accent else Color.rgb(255, 182, 116))
        if (active && !io.isShutdown) {
            io.execute {
                val due = runCatching { StudyPlanStore(applicationContext).pending() }.getOrNull()
                runOnUiThread {
                    if (!isFinishing && !isDestroyed && ::statusLabel.isInitialized && serviceEnabled()) {
                        statusLabel.text = if (due == null) "● Protección activa"
                            else "● Plan pendiente: " + due.task.name
                    }
                }
            }
        }
    }

'''+s[end:]

start=s.index('    private fun updateAppList(filter: String) {')
end=s.index('    private fun editRule(app: InstalledApp)',start)
s=s[:start]+'''    private fun updateAppList(filter: String) {
        if (!::appList.isInitialized) return
        val revision = ++listRevision
        appList.removeAllViews()
        if (!appsLoaded) {
            appList.addView(Style.label(this,
                "Cargando aplicaciones en segundo plano… Puedes usar los demás botones.",
                16f, Style.subtle))
            return
        }
        val existing = store.rules()
        val result = allApps.filter {
            filter.isBlank() || it.title.contains(filter, ignoreCase = true) ||
                it.packageName.contains(filter, ignoreCase = true)
        }.sortedWith(compareByDescending<InstalledApp> { existing.containsKey(it.packageName) }
            .thenBy { if (isSocial(it.packageName)) 0 else 1 }
            .thenBy { it.title.lowercase(Locale.getDefault()) })

        // Rendering hundreds of rows and reading all package icons at once caused
        // multi-second freezes. Render a page and fetch icons in the worker queue.
        result.take(visibleLimit).forEach { app ->
            val rule = existing[app.packageName]
            val tile = card()
            val horizontal = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }
            val icon = ImageView(this).apply {
                setImageResource(android.R.drawable.sym_def_app_icon)
            }
            horizontal.addView(icon, LinearLayout.LayoutParams(Style.dp(this, 36), Style.dp(this, 36)))
            if (!io.isShutdown) io.execute {
                val drawable = runCatching {
                    packageManager.getApplicationIcon(app.packageName)
                }.getOrNull()
                if (drawable != null) runOnUiThread {
                    if (!isFinishing && !isDestroyed && revision == listRevision && icon.parent != null)
                        icon.setImageDrawable(drawable)
                }
            }
            val labelArea = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(Style.dp(this@MainActivity, 10), 0, 0, 0)
            }
            labelArea.addView(Style.label(this, app.title, 16f, Style.text, true))
            labelArea.addView(Style.label(this,
                if (rule == null) "Sin protección" else
                    rule.mode.displayName + " · " + rule.questionCount +
                    " preguntas · " + rule.difficulty.displayName, 12f, Style.subtle))
            horizontal.addView(labelArea,
                LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            val enabledSwitch = Switch(this).apply { isChecked = rule != null }
            horizontal.addView(enabledSwitch)
            tile.addView(horizontal)
            enabledSwitch.setOnCheckedChangeListener { _, checked ->
                if (checked) store.putRule(AppRule(app.packageName,
                    questionCount = store.questionTarget()))
                else store.removeRule(app.packageName)
                updateAppList(searchField.text.toString())
            }
            if (rule != null) {
                val configure = Style.action(this, "Configurar acceso, exámenes y cámara")
                configure.setOnClickListener { editRule(app) }
                tile.addView(configure)
            }
            appList.addView(tile)
            Style.addSpace(appList, 8)
        }
        if (result.size > visibleLimit) {
            appList.addView(Style.action(this, "Mostrar más aplicaciones (" +
                    (result.size - visibleLimit) + " restantes)").apply {
                setOnClickListener {
                    visibleLimit += 24
                    updateAppList(filter)
                }
            })
        }
        if (result.isEmpty())
            appList.addView(Style.label(this, "No hay apps con ese nombre", 14f, Style.subtle))
    }

'''+s[end:]

p.write_text(s,encoding="utf-8")
v=g.read_text(encoding="utf-8")
if 'versionName = "0.6.6"' not in v or 'versionCode = 12' not in v:
    raise SystemExit("Expected FocoQuiz 0.6.6")
g.write_text(v.replace('versionName = "0.6.6"','versionName = "0.6.7"')
              .replace('versionCode = 12','versionCode = 13'),encoding="utf-8")
assert "StudyAlarmScheduler.refresh(this)" not in s[s.index("override fun onCreate"):s.index("override fun onNewIntent")]
assert "private val allApps by lazy" not in s
assert "result.take(visibleLimit)" in s
print("v0.6.7: deferred app discovery/social seeding/alarms; paged list, lazy icons.")
