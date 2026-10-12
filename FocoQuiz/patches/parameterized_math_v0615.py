#!/usr/bin/env python3
"""FocoQuiz 0.6.15: numeric variation data, import validation, local generation and grading."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
src=r/"app/src/main/java/com/focoquiz/app"
def modify(file,operations):
    p=src/file
    s=p.read_text(encoding="utf-8")
    for a,b in operations:
        if a not in s:raise RuntimeError(file+" lacks anchor: "+a[:110])
        s=s.replace(a,b,1)
    p.write_text(s,encoding="utf-8")

modify("Policy.kt",[
('''data class QuestionProgress(''','''/** Generates new numbers per attempt; the mathematical identity remains fixed. */
data class NumericVariable(val name: String, val min: Double, val max: Double, val step: Double)

data class NumericVariation(
    val variables: List<NumericVariable>,
    val expression: String,
    val decimals: Int,
    val unit: String = "",
    val wrongExpressions: List<String> = emptyList()
)

data class QuestionProgress('''),
('''    val formulaIds: List<String> = emptyList()
) {
    val key''','''    val formulaIds: List<String> = emptyList(),
    val numericVariation: NumericVariation? = null
) {
    val key''')
])

(src/"NumericQuizVariants.kt").write_text('''package com.focoquiz.app

import java.math.BigDecimal
import java.math.MathContext
import java.math.RoundingMode
import kotlin.math.abs
import kotlin.math.floor
import kotlin.random.Random
import org.json.JSONArray
import org.json.JSONObject

/** Safe numeric quiz templates; evaluates with the same local engine as the scientific calculator. */
internal object NumericQuizVariants {
    private val variableName = Regex("[A-Za-z][A-Za-z0-9_]{0,16}")
    private val placeholder = Regex("\\\\{([A-Za-z][A-Za-z0-9_]*)\\\\}")
    private val numericResponse = Regex("^[+-]?(?:[0-9]+(?:[.,][0-9]*)?|[.,][0-9]+)(?:[eE][+-]?[0-9]+)?$")

    fun readConfig(config: JSONObject?, prompt: String, type: String,
                   validateSamples: Boolean = true): NumericVariation? {
        if (config == null) return null
        require(type == "short_answer" || type == "multiple_choice") {
            "La variante numérica requiere una pregunta del quiz"
        }
        require(placeholder.containsMatchIn(prompt)) {
            "El enunciado de una pregunta variable debe usar {nombre} para sus números"
        }
        val vars = config.optJSONArray("variables")
            ?: error("Faltan las variables de la pregunta numérica")
        require(vars.length() in 1..5) { "Usa entre 1 y 5 variables por pregunta" }
        val seen = mutableSetOf<String>()
        val parsed = (0 until vars.length()).map { index ->
            val obj = vars.optJSONObject(index) ?: error("Variable inválida")
            val name = obj.optString("name").trim()
            require(variableName.matches(name) && seen.add(name)) {
                "Cada variable debe tener un nombre único (letras, números, _)"
            }
            val minimum = obj.optDouble("min", Double.NaN)
            val maximum = obj.optDouble("max", Double.NaN)
            val step = obj.optDouble("step", Double.NaN)
            require(minimum.isFinite() && maximum.isFinite() && step.isFinite() &&
                abs(minimum) <= 1e7 && abs(maximum) <= 1e7 &&
                maximum > minimum && step > 0.0 &&
                floor((maximum-minimum)/step+1e-9) in 1.0..10000.0) {
                "Rango inválido: " + name + ". Debe permitir al menos dos valores"
            }
            NumericVariable(name, minimum, maximum, step)
        }
        val expression = config.optString("answer_expression").trim()
        require(expression.length in 1..200 && !expression.contains('|')) {
            "Falta answer_expression"
        }
        require(placeholder.containsMatchIn(expression)) {
            "answer_expression debe utilizar las variables para cambiar el resultado"
        }
        val decimals = config.optInt("decimals", 2)
        require(decimals in 0..6) { "decimals debe estar entre 0 y 6" }
        val unit = config.optString("unit").trim().take(24)
        val wrong = config.optJSONArray("wrong_expressions")
        val expressions = (0 until (wrong?.length() ?: 0)).map { i ->
            wrong!!.optString(i).trim()
        }
        require(expressions.size <= 3 && expressions.all { it.length in 1..200 }) {
            "Añade hasta tres expresiones incorrectas"
        }
        val references = placeholder.findAll(prompt + " " + expression + " " +
            expressions.joinToString(" ")).map { it.groupValues[1] }.toSet()
        require(references.isNotEmpty() && references.all { it in seen }) {
            "Se usa una variable que no existe en la lista"
        }
        require(parsed.all { "{"+it.name+"}" in prompt }) {
            "Cada variable necesita aparecer en el enunciado"
        }
        val spec = NumericVariation(parsed, expression, decimals, unit, expressions)
        // Validate with several seeds before the user can import this exam.
        if (validateSamples) for (seed in 1..20) {
            require(runCatching {
                instantiate(StudyQuestion(prompt,"0",type, listOf("a","b","c","d"),
                    numericVariation=spec), Random(seed)).answer.isNotBlank()
            }.isSuccess) {
                "Expresión o rango numérico inválido; revisa divisiones entre cero o funciones"
            }
        }
        return spec
    }

    fun toJson(spec: NumericVariation): JSONObject = JSONObject()
        .put("answer_expression", spec.expression)
        .put("decimals", spec.decimals)
        .put("unit", spec.unit)
        .put("wrong_expressions", JSONArray(spec.wrongExpressions))
        .put("variables", JSONArray().apply {
            spec.variables.forEach {
                put(JSONObject().put("name",it.name).put("min",it.min)
                    .put("max",it.max).put("step",it.step))
            }
        })

    private fun render(text: String, values: Map<String,String>): String =
        placeholder.replace(text) { match ->
            values[match.groupValues[1]] ?: error("Variable desconocida")
        }

    private fun format(value: Double, decimals: Int): String {
        require(value.isFinite() && abs(value) <= 1e10) { "Resultado fuera de rango" }
        val number= BigDecimal.valueOf(value).setScale(decimals,RoundingMode.HALF_UP)
            .stripTrailingZeros().toPlainString()
        return if (number=="-0") "0" else number
    }

    private fun makeValues(spec: NumericVariation, random: Random): Map<String,String> =
        spec.variables.associate { v ->
            val count=floor((v.max-v.min)/v.step+1e-9).toInt()
            val selected=random.nextInt(count+1)
            val sampled=BigDecimal.valueOf(v.min)
                .add(BigDecimal.valueOf(v.step).multiply(BigDecimal.valueOf(selected.toLong())))
                .round(MathContext(12,RoundingMode.HALF_UP))
            v.name to sampled.stripTrailingZeros().toPlainString()
        }

    fun instantiate(question: StudyQuestion, random: Random=Random.Default): StudyQuestion {
        val spec=question.numericVariation ?: return question
        for (attempt in 1..90) {
            val variation=runCatching {
                val values=makeValues(spec,random)
                val target=CalculatorEngine.evaluate(render(spec.expression,values)).toDouble()
                val answerValue=format(target,spec.decimals)
                val correct=answerValue+(if (spec.unit.isNotBlank()) " "+spec.unit else "")
                val newOptions=if (question.type=="multiple_choice") {
                    val distractors=mutableListOf<String>()
                    fun offer(amount: Double) {
                        if (!amount.isFinite()) return
                        val text=format(amount,spec.decimals)+
                            (if (spec.unit.isNotBlank()) " "+spec.unit else "")
                        if (text != correct && text !in distractors) distractors.add(text)
                    }
                    for (expression in spec.wrongExpressions) {
                        val bad=CalculatorEngine.evaluate(render(expression,values)).toDouble()
                        offer(bad)
                    }
                    if (distractors.size < 3) {
                        // Fallback plausible offsets/multipliers in random order.
                        listOf(target*1.25,target*0.75,target*2,
                            target/2,target+1,target-1,
                            target+10.0,target-10.0, target+0.5,
                            target-0.5, target+0.1, target-0.1)
                            .shuffled(random).forEach(::offer)
                    }
                    require(distractors.size >= 3) { "Opciones numéricas indistinguibles" }
                    (distractors.take(3)+correct).shuffled(random)
                } else emptyList()
                question.copy(
                    prompt=render(question.prompt, values),
                    answer=correct,
                    options=newOptions,
                    explanation=render(question.explanation,values))
            }.getOrNull()
            if (variation != null) return variation
        }
        // Keep the base question valid rather than hanging the accessibility blocker.
        // The import already validates expressions and range; this is a last resort.
        return question.copy(numericVariation = null)
    }

    fun accepted(question: StudyQuestion, response: String): Boolean {
        val accepted=question.answer.split('|')
        if (question.numericVariation == null) return accepted.any {
            it.trim().equals(response.trim(), ignoreCase=true)
        }
        // Text match for the answer chosen from randomized multiple-choice options.
        if (question.type=="multiple_choice")
            return accepted.any { it.trim().equals(response.trim(), ignoreCase=true) }
        val expectedText=question.answer.trim()
        if (expectedText.equals(response.trim(),ignoreCase=true)) return true
        val unit=question.numericVariation.unit
        val expectedNumber=if (unit.isBlank()) expectedText else
            expectedText.removeSuffix(" "+unit).trim()
        var given=response.trim()
        if (unit.isNotBlank() && given.endsWith(unit,ignoreCase=true))
            given=given.dropLast(unit.length).trim()
        if (!numericResponse.matches(given) || !numericResponse.matches(expectedNumber))
            return false
        val value=given.replace(',','.').toDoubleOrNull() ?: return false
        val expected=expectedNumber.replace(',','.').toDoubleOrNull() ?: return false
        return value.isFinite() && expected.isFinite() &&
            abs(value-expected) <= 1e-9*maxOf(1.0,abs(expected))
    }
}
''',encoding="utf-8")

modify("QuizFormat.kt",[
('''            StudyQuestion(
                prompt = prompt,''',
'''            val numericVariation = NumericQuizVariants.readConfig(
                node.optJSONObject("numeric_variation"), prompt, type)
            StudyQuestion(
                prompt = prompt,'''),
('''                formulaIds = formulaRefs,
                topic =''',
'''                formulaIds = formulaRefs,
                numericVariation = numericVariation,
                topic =''')
])

modify("LockStore.kt",[
('''                } ?: emptyList())
        }
        } catch''',
'''                } ?: emptyList(),
                item.optJSONObject("numericVariation")?.let { obj ->
                    NumericQuizVariants.readConfig(obj, prompt,
                        item.optString("type","short_answer"), validateSamples = false)
                })
        }
        } catch'''),
('''                .put("formulaIds", JSONArray(q.formulaIds)))''',
'''                .put("formulaIds", JSONArray(q.formulaIds))
                .put("numericVariation", q.numericVariation?.let {
                    NumericQuizVariants.toJson(it) } ?: JSONObject.NULL))''')
])

modify("QuizEngine.kt",[
('''        return chosen.shuffled(random)''',
'''        // Fresh independent numerical parameters and corrected answers/options per attempt.
        return chosen.shuffled(random).map { NumericQuizVariants.instantiate(it, random) }''')
])

# Written and multiple choice answers now compare against the freshly generated number.
for file in ("BlockAccessibilityService.kt","StudyGateActivity.kt"):
    p=src/file
    s=p.read_text(encoding="utf-8")
    if file=="BlockAccessibilityService.kt":
        a='''            val right = normalize(response) in accepted'''
        b='''            val right = if (question.numericVariation != null)
                NumericQuizVariants.accepted(question, response)
            else normalize(response) in accepted'''
    else:
        a='''            val right = normalize(response) in accepted'''
        b='''            val right = if (q.numericVariation != null)
                NumericQuizVariants.accepted(q, response)
            else normalize(response) in accepted'''
    if a not in s:raise RuntimeError(file+" missing answer check")
    s=s.replace(a,b,1)
    p.write_text(s,encoding="utf-8")

build=r/"app/build.gradle.kts"
s=build.read_text(encoding="utf-8")
if 'versionName = "0.6.14"' not in s or 'versionCode = 20' not in s:
    raise SystemExit("Expected stable signed v0.6.14")
build.write_text(s.replace('versionName = "0.6.14"','versionName = "0.6.15"')
              .replace('versionCode = 20','versionCode = 21'),encoding="utf-8")
print("FocoQuiz v0.6.15: parametric math questions, dynamic options and numeric marking")
