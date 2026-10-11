from pathlib import Path
p=Path(__file__).resolve().parents[1]
q=p/'app/src/main/java/com/focoquiz/app/QuizSettingsActivity.kt'
m=p/'app/src/main/java/com/focoquiz/app/MainActivity.kt'
g=p/'app/build.gradle.kts'
s=q.read_text()
start=s.index('        root.addView(Style.label(this, "Banco de preguntas",')
end=s.index('        val add = Style.action(this, "+ Nueva pregunta")',start)
new='''        root.addView(Style.label(this, "Banco de preguntas", 28f, Style.text, true))
        root.addView(Style.label(this, "Combina varias guías para tus exámenes. Sigue estos pasos para importar preguntas.",
            17f, Style.subtle))
        Style.addSpace(root, 16)
        val display = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = Style.shape(Style.panel, 14, this@QuizSettingsActivity)
            setPadding(Style.dp(this@QuizSettingsActivity, 16), Style.dp(this@QuizSettingsActivity, 12),
                Style.dp(this@QuizSettingsActivity, 16), Style.dp(this@QuizSettingsActivity, 12))
        }
        display.addView(Style.label(this, "Lectura accesible", 19f, Style.text, true))
        val prefs = getSharedPreferences("focoquiz_display", MODE_PRIVATE)
        display.addView(android.widget.CheckBox(this).apply {
            text = "Texto grande"
            setTextColor(Style.text)
            textSize = 18f
            isChecked = prefs.getBoolean("large_text", true)
            setOnCheckedChangeListener { _, v ->
                prefs.edit().putBoolean("large_text", v).apply()
                recreate()
            }
        })
        display.addView(android.widget.CheckBox(this).apply {
            text = "Alto contraste"
            setTextColor(Style.text)
            textSize = 18f
            isChecked = prefs.getBoolean("high_contrast", true)
            setOnCheckedChangeListener { _, v ->
                prefs.edit().putBoolean("high_contrast", v).apply()
                recreate()
            }
        })
        root.addView(display)
        Style.addSpace(root, 22)
        root.addView(Style.label(this, "Importar un examen en 3 pasos", 22f, Style.text, true))
        Style.addSpace(root, 12)
        stepCard("PASO 1", "Descarga la plantilla",
            "Este archivo .md contiene el prompt para la IA; no es un examen.",
            "Descargar plantilla + prompt (.md)") {
            startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                type = "text/plain"
                putExtra(Intent.EXTRA_TITLE, "PLANTILLA_Y_PROMPT_PARA_CUALQUIER_IA.md")
            }, requestTemplate)
        }
        stepCard("PASO 2", "Genera el examen con una IA",
            "Dale la plantilla y tu guía a ChatGPT, Gemini, Claude u otra IA. Pídele un examen .json. Puedes ver un ejemplo.",
            "Descargar examen de ejemplo (.json)") {
            startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                type = "application/json"
                putExtra(Intent.EXTRA_TITLE, "EJEMPLO_EXAMEN.json")
            }, requestExample)
        }
        stepCard("PASO 3", "Importa el examen",
            "Selecciona el .json generado por la IA; no selecciones la plantilla .md.",
            "Importar mi examen (.json)") {
            startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                type = "*/*"
                putExtra(Intent.EXTRA_MIME_TYPES,
                    arrayOf("application/json", "text/plain", "application/octet-stream"))
            }, requestImport)
        }
        root.addView(Style.label(this, "Prueba rápida (sin IA)", 22f, Style.text, true))
        root.addView(Style.label(this, "Puedes importar un examen de ejemplo sin descargar archivos.", 16f, Style.subtle))
        Style.addSpace(root, 8)
        root.addView(Style.action(this, "Probar importación con examen incluido").apply {
            setOnClickListener {
                try {
                    val raw = assets.open("ejemplo_examen.json").bufferedReader(Charsets.UTF_8).use { it.readText() }
                    val quiz = QuizFormat.parse(raw)
                    AlertDialog.Builder(this@QuizSettingsActivity)
                        .setTitle("Examen de ejemplo: " + quiz.title)
                        .setMessage("¿Añadir las preguntas de ejemplo a tu banco?")
                        .setNegativeButton("Cancelar", null)
                        .setPositiveButton("Importar") { _, _ ->
                            try {
                                val count = store.importQuiz(quiz)
                                drawQuestions()
                                Toast.makeText(this@QuizSettingsActivity,
                                    count.toString() + " preguntas importadas", Toast.LENGTH_LONG).show()
                            } catch (e: Exception) { showError(e.message ?: "Error al guardar") }
                        }.show()
                } catch (e: Exception) { showError(e.message ?: "No se pudo cargar el ejemplo") }
            }
        })
        Style.addSpace(root, 22)
        root.addView(Style.label(this, "Mis preguntas y exámenes", 22f, Style.text, true))
        Style.addSpace(root, 10)
'''
s=s[:start]+new+s[end:]
marker='    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {'
assert marker in s
helper='''    private fun stepCard(step: String, title: String, description: String,
                         buttonText: String, action: () -> Unit) {
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = Style.shape(Style.panel, 16, this@QuizSettingsActivity)
            setPadding(Style.dp(this@QuizSettingsActivity, 16), Style.dp(this@QuizSettingsActivity, 16),
                Style.dp(this@QuizSettingsActivity, 16), Style.dp(this@QuizSettingsActivity, 16))
        }
        card.addView(Style.label(this, step, 15f, Style.accent, true))
        Style.addSpace(card, 6)
        card.addView(Style.label(this, title, 20f, Style.text, true))
        Style.addSpace(card, 8)
        card.addView(Style.label(this, description, 16f, Style.subtle))
        Style.addSpace(card, 14)
        card.addView(Style.action(this, buttonText).apply { setOnClickListener { action() } })
        root.addView(card)
        Style.addSpace(root, 16)
    }

'''
s=s.replace(marker,helper+marker,1)
s=s.replace('panel.addView(Style.label(this, question.prompt, 16f','panel.addView(Style.label(this, question.prompt, 18f')
s=s.replace('root.addView(Style.label(this, "Bancos disponibles", 20f','root.addView(Style.label(this, "Bancos disponibles", 22f')
s=s.replace('root.addView(Style.label(this, "Preguntas del banco", 20f','root.addView(Style.label(this, "Preguntas del banco", 22f')
q.write_text(s)
t=m.read_text()
old='''    val subtle = Color.rgb(168, 184, 202)
    val accent = Color.rgb(53, 198, 184)'''
new='''    val subtle = Color.rgb(203, 213, 225)
    val accent = Color.rgb(83, 232, 204)
    private fun factor(c: android.content.Context): Float =
        if (c.getSharedPreferences("focoquiz_display", android.content.Context.MODE_PRIVATE)
              .getBoolean("large_text", true)) 1.18f else 1.06f
    private fun contrast(c: android.content.Context): Boolean =
        c.getSharedPreferences("focoquiz_display", android.content.Context.MODE_PRIVATE)
            .getBoolean("high_contrast", true)'''
assert old in t
t=t.replace(old,new,1)
old='''        text = content; textSize = size; setTextColor(color)
        if (bold) setTypeface(null, Typeface.BOLD)
    }
    fun action(context: android.content.Context, title: String): Button = Button(context).apply {
        text = title; isAllCaps = false
    }'''
new='''        text = content
        textSize = size * factor(context)
        setTextColor(if (color == subtle && contrast(context)) Style.text else color)
        setLineSpacing(dp(context, 2).toFloat(), 1.08f)
        if (bold) setTypeface(null, Typeface.BOLD)
    }
    fun action(context: android.content.Context, title: String): Button = Button(context).apply {
        text = title
        isAllCaps = false
        textSize = 17f * factor(context)
        minHeight = dp(context, 60)
        maxLines = 3
        setSingleLine(false)
        gravity = Gravity.CENTER
        setPadding(dp(context, 10), dp(context, 10), dp(context, 10), dp(context, 10))
    }'''
assert old in t
t=t.replace(old,new,1)
m.write_text(t)
v=g.read_text().replace('versionCode = 7','versionCode = 8').replace('versionName = "0.6.1"','versionName = "0.6.2"')
assert 'versionName = "0.6.2"' in v
g.write_text(v)
print("FocoQuiz 0.6.2: import steps + accessibility")
