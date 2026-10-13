#!/usr/bin/env python3
"""FocoQuiz v0.6.16: adapt verifiable old arithmetic and rotate different numeric answers."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"app/src/main/java/com/focoquiz/app"
f=p/"NumericQuizVariants.kt"
s=f.read_text(encoding="utf-8")
def change(a,b):
    global s
    if a not in s:raise RuntimeError("v0.6.16 variant patch mismatch: "+a[:110])
    s=s.replace(a,b,1)

change('''    private val numericResponse = Regex''',
'''    private val recentValues = java.util.Collections.synchronizedMap(
        mutableMapOf<String, String>())
    private val recentAnswers = java.util.Collections.synchronizedMap(
        mutableMapOf<String, String>())

    // Old fixed-value exams may not include numeric_variation. Automatically
    // upgrade ONLY arithmetical expressions we can re-evaluate and verify,
    // rather than risk fabricating wrong answers for physics/word problems.
    private val legacyArithmetic = Regex(
        """^\\s*[¿?]?\\s*(?:¿?cu[aá]nto es|calcula|resuelve|what is|compute)\\s+""" +
        """([+-]?\\d+(?:[.,]\\d+)?)\\s*([+−\\-×*/÷])\\s*([+-]?\\d+(?:[.,]\\d+)?)\\s*[?？]?\\s*$""",
        RegexOption.IGNORE_CASE)

    fun tryUpgradeOldArithmetic(question: StudyQuestion): StudyQuestion {
        if (question.numericVariation != null) return question
        val found = legacyArithmetic.matchEntire(question.prompt) ?: return question
        val rawA = found.groupValues[1].replace(',','.')
        val op = found.groupValues[2]
        val rawB = found.groupValues[3].replace(',','.')
        val a = rawA.toDoubleOrNull() ?: return question
        val b = rawB.toDoubleOrNull() ?: return question
        if (!a.isFinite() || !b.isFinite() || kotlin.math.abs(a) > 100000 ||
            kotlin.math.abs(b) > 100000 || (op in listOf("÷","/") && b == 0.0))
            return question
        val expected = question.answer.substringBefore('|').trim()
            .replace(',','.').toDoubleOrNull() ?: return question
        val expression = when(op) {
            "+" -> "{a}+{b}"
            "-", "−" -> "{a}-{b}"
            "×", "*" -> "{a}*{b}"
            "÷", "/" -> "{a}/{b}"
            else -> return question
        }
        val evaluated = runCatching {
            CalculatorEngine.evaluate("$rawA"+op+"$rawB").toDouble()
        }.getOrNull() ?: return question
        if (kotlin.math.abs(evaluated-expected) >
            1e-7 * maxOf(1.0,kotlin.math.abs(expected))) return question
        fun variable(name: String, value: Double) : NumericVariable {
            val step = if (value % 1.0 == 0.0) 1.0 else 0.25
            val centre = if (value % 1.0 == 0.0) kotlin.math.abs(value).toInt()
                .coerceAtLeast(2).toDouble() else kotlin.math.abs(value).coerceAtLeast(1.0)
            var low = maxOf(if (value > 0) 1.0 else -1000.0, value - centre)
            var high = minOf(1000.0, value + centre)
            if (name=="b" && op in listOf("÷","/")) low = maxOf(1.0,low)
            if (high - low < step) high=low+step
            return NumericVariable(name,low,high,step)
        }
        val prettyOp = if (op=="*" || op=="×") "×"
            else if (op=="/" || op=="÷") "÷" else op
        val stableId = question.questionId.ifBlank {
            question.prompt.trim().lowercase(java.util.Locale.ROOT)
        }
        val resultDecimals = if (op in listOf("÷", "/")) 2
            else if (a%1.0==0.0 && b%1.0==0.0) 0 else 2
        return question.copy(
            prompt = "¿Cuánto es {a} "+prettyOp+" {b}?",
            questionId = stableId,
            numericVariation = NumericVariation(
                listOf(variable("a",a),variable("b",b)),
                expression, resultDecimals))
    }

    private val numericResponse = Regex''')

change('''        val spec=question.numericVariation ?: return question
        for (attempt in 1..90) {
            val variation=runCatching {
                val values=makeValues(spec,random)
                val target''',
'''        val base=tryUpgradeOldArithmetic(question)
        val spec=base.numericVariation ?: return base
        var backup: Pair<String, StudyQuestion>? = null
        val previous=recentValues[base.key]
        val previousAnswer=recentAnswers[base.key]
        for (attempt in 1..90) {
            val variation=runCatching {
                val values=makeValues(spec,random)
                val fingerprint=values.entries.sortedBy { it.key }
                    .joinToString("|") { it.key+"="+it.value }
                require(fingerprint != previous) { "Repetición de valores" }
                val target''')
change('''                question.copy(
                    prompt=render(question.prompt, values),
                    answer=correct,
                    options=newOptions,
                    explanation=render(question.explanation,values))
            }.getOrNull()
            if (variation != null) return variation
        }''',
'''                fingerprint to base.copy(
                    prompt=render(base.prompt, values),
                    answer=correct,
                    options=newOptions,
                    explanation=render(base.explanation,values))
            }.getOrNull()
            if (variation != null) {
                if (backup == null) backup = variation
                if (previousAnswer == null || previousAnswer != variation.second.answer) {
                    recentValues[base.key] = variation.first
                    recentAnswers[base.key] = variation.second.answer
                    return variation.second
                }
            }
        }
        if (backup != null) {
            recentValues[base.key] = backup.first
            recentAnswers[base.key] = backup.second.answer
            return backup.second
        }''')
change('''        return question.copy(numericVariation = null)''',
'''        return base.copy(numericVariation = null)''')
f.write_text(s,encoding="utf-8")

# Tag older number-based questions so users see why a complex old exam retains
# fixed data (and how to regenerate it), without changing the curriculum.
helper=p/"NumericQuestionHints.kt"
helper.write_text('''package com.focoquiz.app

internal object NumericQuestionHints {
    fun label(question: StudyQuestion): String? {
        if (question.numericVariation != null) return "↻ Cálculo con números nuevos por intento"
        val hasDigits=question.prompt.any { it.isDigit() }
        val typicalMath=Regex(
            """(?i)(calcul|cu[aá]nto|volt|corriente|resistencia|potencia|velocidad|precio|inter[eé]s|solve|compute|calculate|equation|ohm|percent|[+×÷=])"""
        ).containsMatchIn(question.prompt)
        return if (hasDigits && typicalMath)
            "Datos fijos en esta pregunta. Regenera el examen con el prompt nuevo para variarlos."
        else null
    }
}
''',encoding="utf-8")

for file,variable,anchor in [
 ("BlockAccessibilityService.kt", "question",
  "        box.addView(Style.label(this, question.prompt, 20f, Style.text, true))"),
 ("StudyGateActivity.kt", "q",
  "        addInfo(\"Pregunta")
]:
    f=p/file
    t=f.read_text(encoding="utf-8")
    if anchor not in t: raise RuntimeError(file+" missing question label anchor")
    if file=="BlockAccessibilityService.kt":
        t=t.replace(anchor,anchor+'''
        NumericQuestionHints.label(question)?.let {
            box.addView(Style.label(this, it, 12f, Style.subtle))
        }''',1)
    else:
        # Only display after the question prompt label, rather than before it.
        a='''        content.addView(Style.label(this, q.prompt, 19f, Style.text, true))'''
        if a not in t: raise RuntimeError("StudyGate prompt anchor not found")
        t=t.replace(a,a+'''
        NumericQuestionHints.label(q)?.let {
            content.addView(Style.label(this, it, 12f, Style.subtle))
        }''',1)
    f.write_text(t,encoding="utf-8")
print("v0.6.16: simple historic arithmetic reuses original identity, new attempts avoid recent values/results; other fixed questions identified.")
