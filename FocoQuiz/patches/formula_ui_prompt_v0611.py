#!/usr/bin/env python3
"""FocoQuiz v0.6.11: in-quiz formula sheet and updated external AI template."""
from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
src=root/"app/src/main/java/com/focoquiz/app"

(src/"QuizFormulas.kt").write_text('''package com.focoquiz.app

import android.content.Context
import android.graphics.Color
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.TextView

/** Offline formula reference embedded inside the quiz (no second overlay). */
internal object QuizFormulas {
    fun attach(context: Context, parent: LinearLayout, store: LockStore,
               question: StudyQuestion) {
        val toggle = TextView(context).apply {
            text = "ƒx  Fórmulas"
            textSize = 15f
            setTextColor(Style.text)
            gravity = Gravity.CENTER
            setPadding(Style.dp(context, 12), Style.dp(context, 7),
                Style.dp(context, 12), Style.dp(context, 7))
            minHeight = Style.dp(context, 42)
            background = Style.shape(Color.rgb(51, 65, 85), 12, context)
            isClickable = true
            isFocusable = true
            contentDescription = "Mostrar u ocultar fórmulas de mi guía"
        }
        val row = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.END
        }
        row.addView(toggle, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        parent.addView(row)
        Style.addSpace(parent, 5)

        val panel = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            background = Style.shape(Style.panel, 12, context)
            setPadding(Style.dp(context, 10), Style.dp(context, 10),
                Style.dp(context, 10), Style.dp(context, 10))
            visibility = View.GONE
        }
        parent.addView(panel)
        var loaded = false

        fun renderFormula(f: StudyFormula) {
            val card = LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                background = Style.shape(Color.rgb(39, 55, 74), 10, context)
                setPadding(Style.dp(context, 10), Style.dp(context, 9),
                    Style.dp(context, 10), Style.dp(context, 9))
            }
            card.addView(Style.label(context, f.name, 16f, Style.text, true))
            card.addView(Style.label(context, f.expression, 20f, Style.accent, true))
            if (f.variables.isNotBlank()) card.addView(Style.label(
                context, "Variables: " + f.variables, 14f, Style.text))
            if (f.whenToUse.isNotBlank()) card.addView(Style.label(
                context, "Cuándo usarla: " + f.whenToUse, 14f, Style.text))
            if (f.topic.isNotBlank()) card.addView(Style.label(
                context, "Tema: " + f.topic, 13f, Style.subtle))
            panel.addView(card)
            Style.addSpace(panel, 8)
        }
        toggle.setOnClickListener {
            val opening = panel.visibility != View.VISIBLE
            panel.visibility = if (opening) View.VISIBLE else View.GONE
            toggle.text = if (opening) "ƒx  Cerrar fórmulas" else "ƒx  Fórmulas"
            if (!opening || loaded) return@setOnClickListener
            loaded = true
            val all = store.formulasForPack(question.packId)
            if (all.isEmpty()) {
                panel.addView(Style.label(context,
                    "Esta guía todavía no tiene fórmulas importadas. En Banco de preguntas, " +
                    "descarga el prompt actualizado, úsalo con tu guía en una IA externa " +
                    "y vuelve a importar el examen .json.", 15f, Style.text))
                return@setOnClickListener
            }
            val related = all.filter { it.id in question.formulaIds }
            val ordered = related + all.filterNot { it.id in question.formulaIds }
            panel.addView(Style.label(context,
                if (related.isEmpty()) "Fórmulas de esta guía"
                else "Primero las fórmulas relacionadas con esta pregunta",
                17f, Style.text, true))
            Style.addSpace(panel, 6)
            var shown = 0
            val more = Style.action(context, "Ver más fórmulas")
            fun appendPage() {
                val end = (shown + 12).coerceAtMost(ordered.size)
                while (shown < end) renderFormula(ordered[shown++])
                more.visibility = if (shown < ordered.size) View.VISIBLE else View.GONE
                more.text = "Ver más fórmulas (" + (ordered.size - shown) + " restantes)"
            }
            more.setOnClickListener { appendPage() }
            panel.addView(more)
            // Keep the show-more button below the appended formulas.
            // This parent move is safe because each page is bounded at 12 formulas.
            appendPage()
        }
    }
}
''',encoding="utf-8")

# Ensure paging control is displayed below the last formula, not above it.
p=src/"QuizFormulas.kt"
s=p.read_text(encoding="utf-8")
s=s.replace('''                while (shown < end) renderFormula(ordered[shown++])
                more.visibility''',
'''                panel.removeView(more)
                while (shown < end) renderFormula(ordered[shown++])
                panel.addView(more)
                more.visibility''')
p.write_text(s,encoding="utf-8")

for file,needle,newline in [
    ("BlockAccessibilityService.kt",
     "QuizCalculator.attach(this, box, answerInput)",
     "QuizFormulas.attach(this, box, store, question)"),
    ("StudyGateActivity.kt",
     "QuizCalculator.attach(this, content, answerInput)",
     "QuizFormulas.attach(this, content, store, q)")
]:
    p=src/file
    s=p.read_text(encoding="utf-8")
    if needle not in s:raise RuntimeError("v0.6.11 missing calculator: "+file)
    s=s.replace(needle,needle+"\\n        "+newline,1)
    # Replace literal newline escape with a real newline before saving source.
    s=s.replace(needle+"\\n        "+newline,needle+"\n        "+newline,1)
    p.write_text(s,encoding="utf-8")

# Both downloadable versions of the prompt: bundled in the APK, and in the repo.
prompts=[root/"app/src/main/assets/plantilla_prompt_ia.md",
         root/"quiz-format/PLANTILLA_Y_PROMPT_PARA_CUALQUIER_IA.md"]
marker="- "+chr(96)+"explanation"+chr(96)+" debe explicar"
instructions="""- NUEVO: Extrae las FÓRMULAS que realmente aparecen en esta guía (matemáticas, electrónicas, físicas, financieras o similares); NUNCA inventes fórmulas ni traigas fórmulas de conocimiento externo.
- Agrega a la raíz un array opcional "formulas" de objetos con: "id" único (f1, f2…), "name", "expression", "variables", "when_to_use" y "topic". Si la guía no contiene fórmulas, usa [].
- Agrega en cada pregunta "formula_ids": ["f1"] con los IDs de las fórmulas útiles para esa pregunta, o [] si ninguna. Solo relaciona fórmulas que realmente hayas incluido en el array raíz.
- Las fórmulas deben estar en su forma GENERAL, fieles a la guía, con símbolos y unidades correctos; no incluyas los valores sustituidos ni la respuesta de la pregunta.
- Conserva format focoquiz.quiz y version 1, porque ambos campos de fórmulas son opcionales y compatibles con exámenes anteriores.
"""
for prompt in prompts:
    if not prompt.exists():continue
    s=prompt.read_text(encoding="utf-8")
    if marker in s:
        s=s.replace(marker,instructions+marker,1)
    else:
        # Some bundled guide revisions use a different explanation bullet.
        # Insert the formula contract inside the prompt, above its JSON example.
        # The bundled v0.6 prompt has an alternate sample heading.
        # The formula instructions belong BEFORE the JSON example.
        example_heading=s.find("Ejemplo de ESTRUCTURA")
        if example_heading < 0: example_heading=s.find("Ejemplo de la ESTRUCTURA")
        if example_heading < 0: example_heading=s.find("## FIN DEL PROMPT")
        if example_heading < 0: raise RuntimeError("No prompt example found: "+str(prompt))
        s=s[:example_heading]+instructions+"\n"+s[example_heading:]
    example='''  "questions": [
'''
    if example in s:
            s=s.replace(example,'''  "formulas": [
        {
          "id": "f1",
          "name": "Ley de Ohm",
          "expression": "V = I × R",
          "variables": "V: voltaje (V); I: corriente (A); R: resistencia (Ω)",
          "when_to_use": "Relacionar voltaje, corriente y resistencia",
          "topic": "Circuitos"
        }
  ],
  "questions": [
''',1)
    # Append question-level optional IDs to both sample questions.
    s=s.replace('''      "difficulty": "easy"
    }''',
'''      "difficulty": "easy",
      "formula_ids": []
    }''',1)
    s=s.replace('''      "difficulty": "easy"
    }
  ]''',
'''      "difficulty": "easy",
      "formula_ids": ["f1"]
    }
  ]''',1)
    prompt.write_text(s,encoding="utf-8")

for example in (root/"app/src/main/assets/ejemplo_examen.json",
                root/"quiz-format/EJEMPLO_EXAMEN.json"):
    if not example.exists():continue
    data=json.loads(example.read_text(encoding="utf-8"))
    data["formulas"]=[{
      "id":"f1", "name":"Ley de Ohm","expression":"V = I × R",
      "variables":"V: voltaje (V); I: corriente (A); R: resistencia (Ω)",
      "when_to_use":"Relacionar voltaje, corriente y resistencia",
      "topic":"Circuitos"
    }]
    for q in data["questions"]:
        q["formula_ids"]=["f1"] if "ohm" in (q.get("question","")+" "+q.get("explanation","")).lower() else []
    example.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

p=src/"QuizSettingsActivity.kt"
s=p.read_text(encoding="utf-8")
anchor='''        val banks = store.packs()'''
if anchor not in s: raise RuntimeError("Quiz bank screen anchor missing")
s=s.replace(anchor,'''        root.addView(Style.label(this,
            "El prompt nuevo también pide fórmulas de la guía. Se guardan con cada examen " +
                "para consultarlas sin Internet durante las preguntas.", 14f, Style.subtle))
        val banks = store.packs()''',1)
p.write_text(s,encoding="utf-8")

gradle=root/"app/build.gradle.kts"
s=gradle.read_text(encoding="utf-8")
if 'versionName = "0.6.10"' not in s or 'versionCode = 16' not in s:
    raise RuntimeError("Expected v0.6.10 build")
gradle.write_text(s.replace('versionName = "0.6.10"','versionName = "0.6.11"')
              .replace('versionCode = 16','versionCode = 17'),encoding="utf-8")
print("v0.6.11: inline formula sheet, updated AI prompt and examples.")
