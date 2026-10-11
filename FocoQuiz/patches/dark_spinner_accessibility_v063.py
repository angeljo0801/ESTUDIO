#!/usr/bin/env python3
"""FocoQuiz v0.6.3: accessible spinners and permission troubleshooting."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
main = root / 'app/src/main/java/com/focoquiz/app/MainActivity.kt'
gradle = root / 'app/build.gradle.kts'
s = main.read_text(encoding='utf-8')

def change(old, new):
    global s
    if old not in s:
        if new in s:
            return
        raise SystemExit('v0.6.3 patch mismatch: ' + old[:100])
    s=s.replace(old,new,1)

change('import android.app.TimePickerDialog\n',
       'import android.app.TimePickerDialog\nimport android.content.res.ColorStateList\n')
change('import android.os.Bundle\n',
       'import android.os.Bundle\nimport android.os.Build\n')
change('import android.view.ViewGroup\n',
       'import android.view.ViewGroup\nimport android.view.WindowInsets\n')

scroll_start = s.find('        val scroll = ScrollView(this)')
scroll_end = s.find('        root = LinearLayout(this).apply', scroll_start)
if scroll_start < 0 or scroll_end < 0:
    raise SystemExit('v0.6.3: cannot find main screen scroll container')
s = s[:scroll_start] + '''        val scroll = ScrollView(this).apply {
            setBackgroundColor(Style.bg)
            fillViewport = true
            setOnApplyWindowInsetsListener { view, insets ->
                if (Build.VERSION.SDK_INT >= 30) {
                    val bars = insets.getInsets(WindowInsets.Type.systemBars())
                    view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
                } else {
                    @Suppress("DEPRECATION")
                    view.setPadding(insets.systemWindowInsetLeft,
                        insets.systemWindowInsetTop,
                        insets.systemWindowInsetRight,
                        insets.systemWindowInsetBottom)
                }
                insets
            }
        }
''' + s[scroll_end:]

change(
'''        serviceCard.addView(activate)
        root.addView(serviceCard)''',
'''        serviceCard.addView(activate)
        Style.addSpace(serviceCard, 12)
        serviceCard.addView(Style.label(this,
            "¿Android te deniega el permiso? Puede tratarse de un ajuste restringido por instalar una APK.",
            15f, Style.subtle))
        Style.addSpace(serviceCard, 8)
        serviceCard.addView(Style.action(this, "Ayuda: permitir Accesibilidad en Samsung").apply {
            setOnClickListener { showAccessibilityHelp() }
        })
        root.addView(serviceCard)''')

a=s.index('    private fun selector(values: List<String>) = Spinner(this).apply {')
b=s.index('    private fun selectionListener(',a)
s=s[:a]+'''    private fun selector(values: List<String>) = Spinner(this).apply {
        // Native Android spinner text is black in a Light theme. This app uses
        // a dark background, so explicitly style selected and expanded options.
        val host = this@MainActivity
        val prefs = getSharedPreferences("focoquiz_display", MODE_PRIVATE)
        val large = prefs.getBoolean("large_text", true)
        adapter = object : ArrayAdapter<String>(host, android.R.layout.simple_spinner_item, values) {
            override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
                return TextView(host).apply {
                    text = getItem(position) ?: ""
                    textSize = if (large) 20f else 18f
                    setTextColor(Style.text)
                    gravity = Gravity.CENTER_VERTICAL
                    minHeight = Style.dp(host, 58)
                    setPadding(Style.dp(host, 14), Style.dp(host, 8),
                        Style.dp(host, 22), Style.dp(host, 8))
                    setSingleLine(false)
                }
            }

            override fun getDropDownView(position: Int, convertView: View?, parent: ViewGroup): View {
                return TextView(host).apply {
                    text = getItem(position) ?: ""
                    textSize = if (large) 19f else 17f
                    setTextColor(Style.text)
                    setBackgroundColor(Style.panel)
                    gravity = Gravity.CENTER_VERTICAL
                    minHeight = Style.dp(host, 56)
                    setPadding(Style.dp(host, 16), Style.dp(host, 12),
                        Style.dp(host, 16), Style.dp(host, 12))
                }
            }
        }
        // The spinner's dropdown arrow / underline must also be visible.
        backgroundTintList = ColorStateList.valueOf(Style.accent)
        minimumHeight = Style.dp(this@MainActivity, 58)
    }

    private fun showAccessibilityHelp() {
        AlertDialog.Builder(this)
            .setTitle("Permiso de Accesibilidad en Samsung")
            .setMessage(
                "1. En Ajustes > Accesibilidad > Aplicaciones instaladas, toca FocoQuiz e intenta activarlo.\\n\\n" +
                "2. Si Android indica que es un ajuste restringido, abre Ajustes > Aplicaciones > FocoQuiz. " +
                "Toca los tres puntos (⋮) y, si aparece, selecciona 'Permitir ajustes restringidos'.\\n\\n" +
                "3. Vuelve a Accesibilidad y activa FocoQuiz.\\n\\n" +
                "Es una medida de seguridad de Android para APK instaladas fuera de tiendas. " +
                "Solo autorízalo si confías en la app. FocoQuiz no puede concederse ese permiso por sí sola.\\n\\n" +
                "Si no aparece la opción o sigue denegado, envíame una captura del mensaje exacto. " +
                "No necesitas desinstalar la app."
            )
            .setNeutralButton("Información de FocoQuiz") { _, _ ->
                startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                    data = Uri.parse("package:$packageName")
                })
            }
            .setPositiveButton("Abrir Accesibilidad") { _, _ ->
                startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
            }
            .setNegativeButton("Cerrar", null)
            .show()
    }

'''+s[b:]
main.write_text(s,encoding='utf-8')

g=gradle.read_text(encoding='utf-8')
if 'versionName = "0.6.2"' not in g:
    raise SystemExit('v0.6.3 patch expected Gradle v0.6.2')
g=g.replace('versionCode = 8','versionCode = 9')
g=g.replace('versionName = "0.6.2"','versionName = "0.6.3"')
gradle.write_text(g,encoding='utf-8')
print('FocoQuiz 0.6.3: readable dark-theme selectors, safe insets, accessibility help')
