#!/usr/bin/env python3
"""FocoQuiz v0.6.1: clearer external AI quiz import and built-in sample."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
quiz = root / "app/src/main/java/com/focoquiz/app/QuizSettingsActivity.kt"
gradle = root / "app/build.gradle.kts"
source = quiz.read_text(encoding="utf-8")

def replace_once(old, new):
    global source
    if old in source:
        source = source.replace(old, new, 1)
    elif new not in source:
        raise SystemExit("FocoQuiz import patch mismatch: " + old[:80])

replace_once(
    'import android.os.Bundle\n',
    'import android.os.Bundle\nimport android.provider.OpenableColumns\n'
)
replace_once(
    'import android.widget.Toast\n',
    'import android.widget.Toast\nimport java.util.Locale\n'
)
replace_once(
    'root.addView(Style.action(this, "Importar examen de IA externa (.json)").apply {',
    '''root.addView(Style.label(this,
            "PASO 1: Descarga la plantilla .md y dásela a ChatGPT, Gemini u otra IA junto con tu guía. " +
                "PASO 2: Pide que te cree un EXAMEN .json. " +
                "PASO 3: Importa aquí ese .json. La plantilla .md NO es un examen.",
            14f, Style.subtle))
        Style.addSpace(root, 10)
        root.addView(Style.action(this, "Importar examen generado (.json)").apply {'''
)
replace_once(
    '        root.addView(Style.label(this,\n            "Las dos plantillas vienen incluidas en FocoQuiz y se guardan donde elijas en tu teléfono.",\n            13f, Style.subtle))',
    '''        root.addView(Style.action(this, "Probar importación con examen incluido").apply {
            setOnClickListener {
                try {
                    val raw = assets.open("ejemplo_examen.json").bufferedReader(Charsets.UTF_8).use { it.readText() }
                    val example = QuizFormat.parse(raw)
                    AlertDialog.Builder(this@QuizSettingsActivity)
                        .setTitle("Examen de ejemplo: " + example.title)
                        .setMessage("Puedes importar el examen de ejemplo y probar sus preguntas sin descargar ningún archivo.")
                        .setNegativeButton("Cancelar", null)
                        .setPositiveButton("Importar") { _, _ ->
                            val count = store.importQuiz(example)
                            drawQuestions()
                            Toast.makeText(this@QuizSettingsActivity,
                                count.toString() + " preguntas del ejemplo importadas",
                                Toast.LENGTH_LONG).show()
                        }.show()
                } catch (e: Exception) { showError("El ejemplo no pudo cargarse: " + e.message) }
            }
        })
        root.addView(Style.label(this,
            "El archivo .md es la plantilla para la IA. El archivo .json contiene las preguntas y sí se importa.",
            13f, Style.subtle))'''
)
replace_once(
    '    private fun importFromUri(uri: Uri) {\n        try {',
    '''    private fun importFromUri(uri: Uri) {
        val name = try {
            contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
                val column = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (column >= 0 && cursor.moveToFirst()) cursor.getString(column) else null
            }
        } catch (_: Exception) { null } ?: (uri.lastPathSegment ?: "")
        val ext = name.substringAfterLast('.', "").lowercase(Locale.ROOT)
        if (ext == "md" || ext == "markdown" || ext == "txt") {
            showTemplateInstructions()
            return
        }
        if (ext.isNotEmpty() && ext != "json") {
            showError("Seleccionaste un archivo de tipo ." + ext +
                ". Para importar un examen debes elegir el archivo .json generado por la IA.")
            return
        }
        try {'''
)
replace_once(
    '            val quiz = QuizFormat.parse(raw)',
    '''            val clean = raw.trimStart()
            if (clean.startsWith("#") || clean.contains("PROMPT PARA LA IA", ignoreCase = true)) {
                showTemplateInstructions()
                return
            }
            val quiz = QuizFormat.parse(raw)'''
)
replace_once(
    '        } catch (e: Exception) { showError(e.message ?: "JSON inválido") }\n    }\n\n    private fun showError',
    '''        } catch (e: Exception) {
            showError("No se pudo leer un examen .json válido. Asegúrate de importar el resultado " +
                "generado por la IA, no la plantilla .md. Detalle: " +
                (e.message ?: "archivo no disponible"))
        }
    }

    private fun showTemplateInstructions() {
        AlertDialog.Builder(this)
            .setTitle("Ese archivo es el prompt, no el examen")
            .setMessage("La plantilla .md debe compartirse con una IA externa junto con tu guía. " +
                "Después pide un examen en formato .json y selecciona ese archivo aquí. " +
                "También puedes probar el examen de ejemplo que viene incluido en FocoQuiz.")
            .setPositiveButton("Entendido", null).show()
    }

    private fun showError'''
)
quiz.write_text(source, encoding="utf-8")
g = gradle.read_text(encoding="utf-8")
g = g.replace("versionCode = 6", "versionCode = 7").replace('versionName = "0.6.0"', 'versionName = "0.6.1"')
gradle.write_text(g, encoding="utf-8")
print("FocoQuiz: import UX fixed, version bumped to 0.6.1")
