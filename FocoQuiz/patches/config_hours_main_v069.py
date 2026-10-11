#!/usr/bin/env python3
"""FocoQuiz 0.6.9: lock configuration outside a user-defined daily window."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
src=root/"app/src/main/java/com/focoquiz/app"
main=src/"MainActivity.kt"
build=root/"app/build.gradle.kts"

(src/"ConfigurationHours.kt").write_text('''package com.focoquiz.app

import android.app.Activity
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.widget.Toast
import java.util.Calendar
import java.util.Locale

/** Restricted hours apply ONLY to configuration, never to the quiz/service. */
internal object ConfigurationHoursPolicy {
    fun allows(enabled: Boolean, start: Int, end: Int, minute: Int): Boolean {
        if (!enabled) return true
        if (start !in 0..1439 || end !in 0..1439 || start == end ||
            minute !in 0..1439) return false
        return if (start < end) minute in start until end
        else minute >= start || minute < end
    }
}

internal class ConfigurationHours(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences(
        "focoquiz_configuration_hours", Context.MODE_PRIVATE)
    val enabled: Boolean get() = prefs.getBoolean("enabled", false)
    val start: Int get() = prefs.getInt("start", 18*60).coerceIn(0, 1439)
    val end: Int get() = prefs.getInt("end", 20*60).coerceIn(0, 1439)

    fun canEdit(): Boolean {
        val c = Calendar.getInstance()
        val minute = c.get(Calendar.HOUR_OF_DAY)*60 + c.get(Calendar.MINUTE)
        return ConfigurationHoursPolicy.allows(enabled, start, end, minute)
    }

    fun save(newStart: Int, newEnd: Int, newEnabled: Boolean): Boolean {
        if (!canEdit()) return false
        if (newStart !in 0..1439 || newEnd !in 0..1439 ||
            (newEnabled && newStart == newEnd)) return false
        prefs.edit().putInt("start", newStart).putInt("end", newEnd)
            .putBoolean("enabled", newEnabled).apply()
        return true
    }
    fun format(minute: Int) = String.format(Locale.getDefault(), "%02d:%02d",
        minute/60, minute%60)
    fun description(): String = if (!enabled) "Sin horario de bloqueo de ajustes"
        else "Cada día de " + format(start) + " a " + format(end)
}

/** Closes an editor if allowed time ends while the screen is open. */
internal class ConfigurationHoursGuard(private val activity: Activity) {
    private val handler = Handler(Looper.getMainLooper())
    private val ticker = object : Runnable {
        override fun run() {
            if (!check()) return
            handler.postDelayed(this, 2000)
        }
    }
    fun check(): Boolean {
        if (ConfigurationHours(activity).canEdit()) return true
        Toast.makeText(activity, "Ajustes bloqueados fuera del horario", Toast.LENGTH_SHORT).show()
        activity.finish()
        return false
    }
    fun resume(): Boolean {
        if (!check()) return false
        handler.removeCallbacks(ticker)
        handler.postDelayed(ticker, 2000)
        return true
    }
    fun pause() { handler.removeCallbacks(ticker) }
}
''', encoding="utf-8")
s=main.read_text(encoding="utf-8")
def change(a,b):
    global s
    if a not in s: raise RuntimeError("v0.6.9 main patch mismatch: "+a[:120])
    s=s.replace(a,b,1)

change('''    private var listRevision = 0''','''    private var listRevision = 0
    private var configScreenAllowed: Boolean? = null
    private val configTicker = object : Runnable {
        override fun run() {
            showConfigurationForTime()
            mainHandler.postDelayed(this, 2000)
        }
    }
    private fun canChangeSettings(): Boolean = ConfigurationHours(this).canEdit()

    private fun showConfigurationForTime() {
        val allowed = canChangeSettings()
        if (configScreenAllowed == allowed) return
        configScreenAllowed = allowed
        if (allowed) render() else renderConfigLocked()
    }

    private fun renderConfigLocked() {
        val scroll = ScrollView(this).apply { setBackgroundColor(Style.bg) }
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(Style.dp(this@MainActivity, 20), Style.dp(this@MainActivity, 38),
                Style.dp(this@MainActivity, 20), Style.dp(this@MainActivity, 38))
        }
        scroll.addView(content)
        content.addView(Style.label(this, "FocoQuiz · ajustes bloqueados", 25f, Style.text, true))
        Style.addSpace(content, 15)
        content.addView(Style.label(this, "Podrás cambiar la configuración solamente en:", 18f, Style.subtle))
        Style.addSpace(content, 10)
        content.addView(Style.label(this, ConfigurationHours(this).description(), 22f, Style.accent, true))
        Style.addSpace(content, 20)
        content.addView(Style.label(this,
            "La protección de apps, los exámenes y las alarmas siguen funcionando. " +
                "Vuelve durante el horario autorizado para ajustar FocoQuiz.", 17f, Style.text))
        Style.addSpace(content, 16)
        content.addView(Style.action(this, "Ir al inicio del teléfono").apply {
            setOnClickListener {
                startActivity(Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            }
        })
        setContentView(scroll)
    }

    private fun configScheduleCard(): LinearLayout {
        val saved = ConfigurationHours(this)
        var start = saved.start
        var end = saved.end
        var enabled = saved.enabled
        val panel = card()
        panel.addView(Style.label(this, "Horario para configurar FocoQuiz", 21f, Style.text, true))
        panel.addView(Style.label(this,
            "Solo durante estas horas podrás modificar las reglas, preguntas, rutinas y planes. " +
                "Fuera del horario la protección continuará activa.", 16f, Style.subtle))
        Style.addSpace(panel, 12)
        val toggle = Switch(this).apply {
            text = "Activar restricción de horario"
            textSize = 17f
            setTextColor(Style.text)
            isChecked = enabled
        }
        panel.addView(toggle)
        val from = Style.action(this, "")
        val to = Style.action(this, "")
        fun updateLabels() {
            from.text = "Hora de inicio: " + saved.format(start)
            to.text = "Hora de fin: " + saved.format(end)
        }
        updateLabels()
        from.setOnClickListener {
            TimePickerDialog(this, { _, h, m ->
                start = h * 60 + m
                updateLabels()
            }, start/60, start%60, true).show()
        }
        to.setOnClickListener {
            TimePickerDialog(this, { _, h, m ->
                end = h * 60 + m
                updateLabels()
            }, end/60, end%60, true).show()
        }
        panel.addView(from)
        panel.addView(to)
        panel.addView(Style.label(this,
            "Se aplica todos los días y permite franjas que cruzan la medianoche. " +
                "Si activas una franja que no incluye la hora actual, los ajustes se bloquearán de inmediato.",
            14f, Style.subtle))
        toggle.setOnCheckedChangeListener { _, value -> enabled = value }
        Style.addSpace(panel, 10)
        panel.addView(Style.action(this, "Guardar horario").apply {
            setOnClickListener {
                if (enabled && start == end) {
                    Toast.makeText(this@MainActivity, "La hora inicial y final deben ser distintas",
                        Toast.LENGTH_LONG).show()
                    return@setOnClickListener
                }
                if (!ConfigurationHours(this@MainActivity).save(start, end, enabled)) {
                    Toast.makeText(this@MainActivity,
                        "No puedes cambiar el horario fuera de la franja permitida",
                        Toast.LENGTH_LONG).show()
                    showConfigurationForTime()
                    return@setOnClickListener
                }
                Toast.makeText(this@MainActivity, "Horario guardado", Toast.LENGTH_SHORT).show()
                showConfigurationForTime()
            }
        })
        return panel
    }''')

change('''        render()
        handleSharedQuiz(intent)
        // Show the interactive screen immediately; load system information afterwards.''',
'''        showConfigurationForTime()
        handleSharedQuiz(intent)
        // Show the interactive screen immediately; load system information afterwards.''')

change('''                    updateAppList(if (::searchField.isInitialized) searchField.text.toString() else "")
                    updateServiceStatus()''',
'''                    if (configScreenAllowed == true) {
                        updateAppList(if (::searchField.isInitialized) searchField.text.toString() else "")
                        updateServiceStatus()
                    }''')
change('''        if (incoming?.action != Intent.ACTION_SEND) return''',
'''        if (incoming?.action != Intent.ACTION_SEND || !canChangeSettings()) return''')
change('''    override fun onResume() {
        super.onResume()
        if (::statusLabel.isInitialized) {
            updateServiceStatus()
            if (appsLoaded) updateAppList(searchField.text.toString())
        }
    }''',
'''    override fun onResume() {
        super.onResume()
        showConfigurationForTime()
        if (configScreenAllowed == true && ::statusLabel.isInitialized) {
            updateServiceStatus()
            if (appsLoaded && ::searchField.isInitialized)
                updateAppList(searchField.text.toString())
        }
        mainHandler.removeCallbacks(configTicker)
        mainHandler.postDelayed(configTicker, 2000)
    }

    override fun onPause() {
        mainHandler.removeCallbacks(configTicker)
        super.onPause()
    }''')
change('''        searchTask?.let(mainHandler::removeCallbacks)
        listRevision++''',
'''        searchTask?.let(mainHandler::removeCallbacks)
        mainHandler.removeCallbacks(configTicker)
        listRevision++''')
change('''        val serviceCard = card()''','''        root.addView(configScheduleCard())
        Style.addSpace(root, 18)

        val serviceCard = card()''')
change('''countSpinner.onItemSelectedListener = selectionListener { store.setQuestionTarget(counts[it]) }''',
'''countSpinner.onItemSelectedListener = selectionListener {
            if (canChangeSettings()) store.setQuestionTarget(counts[it])
        }''')
change('''timeSpinner.onItemSelectedListener = selectionListener { store.setUnlockMinutes(minutes[it]) }''',
'''timeSpinner.onItemSelectedListener = selectionListener {
            if (canChangeSettings()) store.setUnlockMinutes(minutes[it])
        }''')
change('''            enabledSwitch.setOnCheckedChangeListener { _, checked ->
                if (checked) store.putRule''',
'''            enabledSwitch.setOnCheckedChangeListener { _, checked ->
                if (!canChangeSettings()) {
                    showConfigurationForTime()
                    return@setOnCheckedChangeListener
                }
                if (checked) store.putRule''')
change('''    private fun editRule(app: InstalledApp) {
        val current''',
'''    private fun editRule(app: InstalledApp) {
        if (!canChangeSettings()) { showConfigurationForTime(); return }
        val current''')
change('''            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val mode = modes''',
'''            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                if (!canChangeSettings()) {
                    dialog.dismiss()
                    showConfigurationForTime()
                    return@setOnClickListener
                }
                val mode = modes''')

main.write_text(s,encoding="utf-8")
v=build.read_text(encoding="utf-8")
if 'versionName = "0.6.8"' not in v or 'versionCode = 14' not in v:
    raise RuntimeError("Expected FocoQuiz 0.6.8 signed build")
build.write_text(v.replace('versionName = "0.6.8"','versionName = "0.6.9"')
    .replace('versionCode = 14','versionCode = 15'),encoding="utf-8")
print("v0.6.9: schedule card, read-only lock screen and daily timer installed")
