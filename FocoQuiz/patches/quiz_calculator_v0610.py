#!/usr/bin/env python3
"""FocoQuiz 0.6.10 - small in-quiz calculator, available in blockers and study plans."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = root / "app/src/main/java/com/focoquiz/app"
gradle = root / "app/build.gradle.kts"

(src / "CalculatorEngine.kt").write_text('''package com.focoquiz.app

import java.math.BigDecimal
import kotlin.math.sqrt

/** Safe, local arithmetic parser. No eval, network access, or persistence. */
internal object CalculatorEngine {
    fun evaluate(input: String): String {
        if (input.length > 100 || input.isBlank()) throw IllegalArgumentException("Operación vacía o demasiado larga")
        val evaluator = Parser(input)
        val value = evaluator.expression()
        evaluator.skipSpaces()
        if (!evaluator.atEnd()) throw IllegalArgumentException("Revisa la operación")
        if (!value.isFinite()) throw IllegalArgumentException("Resultado inválido")
        val printed = BigDecimal.valueOf(value).stripTrailingZeros().toPlainString()
        return if (printed == "-0") "0" else printed
    }

    private class Parser(private val source: String) {
        private var index = 0
        fun atEnd() = index >= source.length
        fun skipSpaces() {
            while (!atEnd() && source[index].isWhitespace()) index++
        }
        private fun take(vararg tokens: Char): Boolean {
            skipSpaces()
            if (!atEnd() && source[index] in tokens) {
                index++
                return true
            }
            return false
        }
        fun expression(): Double {
            var result = term()
            while (true) {
                result = when {
                    take('+') -> result + term()
                    take('-', '−') -> result - term()
                    else -> return result
                }
            }
        }
        private fun term(): Double {
            var result = unary()
            while (true) {
                result = when {
                    take('*', '×') -> result * unary()
                    take('/', '÷') -> {
                        val denominator = unary()
                        if (denominator == 0.0) throw IllegalArgumentException("No se puede dividir entre cero")
                        result / denominator
                    }
                    else -> return result
                }
            }
        }
        private fun unary(): Double {
            skipSpaces()
            return when {
                take('+') -> unary()
                take('-', '−') -> -unary()
                take('√') -> {
                    val x = unary()
                    if (x < 0.0) throw IllegalArgumentException("Raíz de número negativo")
                    sqrt(x)
                }
                else -> percent()
            }
        }
        private fun percent(): Double {
            var value = primary()
            while (take('%')) value /= 100.0
            return value
        }
        private fun primary(): Double {
            if (take('(')) {
                val value = expression()
                if (!take(')')) throw IllegalArgumentException("Falta cerrar paréntesis")
                return value
            }
            skipSpaces()
            val start = index
            var dot = false
            while (!atEnd() && (source[index].isDigit() || source[index] == '.')) {
                if (source[index] == '.') {
                    if (dot) break
                    dot = true
                }
                index++
            }
            if (start == index) throw IllegalArgumentException("Número incompleto")
            return source.substring(start, index).toDoubleOrNull()
                ?: throw IllegalArgumentException("Número inválido")
        }
    }
}
''', encoding="utf-8")

(src / "QuizCalculator.kt").write_text('''package com.focoquiz.app

import android.content.Context
import android.graphics.Color
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.InputMethodManager
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast

/** Small collapsible calculator embedded in the current quiz, not another window. */
internal object QuizCalculator {
    fun attach(context: Context, parent: LinearLayout, answerInput: EditText?) {
        val toggle = TextView(context).apply {
            text = "▦  Calculadora"
            textSize = 15f
            setTextColor(Style.text)
            gravity = Gravity.CENTER
            setPadding(Style.dp(context, 12), Style.dp(context, 7),
                Style.dp(context, 12), Style.dp(context, 7))
            background = Style.shape(Color.rgb(51, 65, 85), 12, context)
            isClickable = true
            isFocusable = true
            contentDescription = "Abrir o cerrar calculadora"
        }
        val toggleRow = LinearLayout(context).apply {
            gravity = Gravity.END
            orientation = LinearLayout.HORIZONTAL
        }
        toggleRow.addView(toggle, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT, Style.dp(context, 42)))
        parent.addView(toggleRow)
        Style.addSpace(parent, 6)

        val calculator = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            background = Style.shape(Style.panel, 14, context)
            setPadding(Style.dp(context, 10), Style.dp(context, 10),
                Style.dp(context, 10), Style.dp(context, 10))
            visibility = View.GONE
        }
        val expression = TextView(context).apply {
            text = "0"
            setTextColor(Style.text)
            textSize = 24f
            gravity = Gravity.END or Gravity.CENTER_VERTICAL
            minHeight = Style.dp(context, 45)
            maxLines = 2
        }
        calculator.addView(expression)
        val resultText = TextView(context).apply {
            text = "Calcula sin salir de la pregunta"
            setTextColor(Style.subtle)
            textSize = 13f
            gravity = Gravity.END
        }
        calculator.addView(resultText)
        Style.addSpace(calculator, 5)

        var buffer = ""
        var result: String? = null
        var finished = false
        val keys = listOf(
            listOf("AC", "(", ")", "⌫"),
            listOf("7", "8", "9", "÷"),
            listOf("4", "5", "6", "×"),
            listOf("1", "2", "3", "−"),
            listOf("0", ".", "%", "+"),
            listOf("√", "=")
        )
        fun redraw() {
            expression.text = if (buffer.isEmpty()) "0" else buffer
        }
        fun compute() {
            try {
                val value = CalculatorEngine.evaluate(buffer)
                result = value
                expression.text = value
                buffer = value
                finished = true
                resultText.text = "Resultado"
                resultText.setTextColor(Style.accent)
            } catch (e: IllegalArgumentException) {
                result = null
                resultText.text = e.message ?: "Operación inválida"
                resultText.setTextColor(Color.rgb(255, 180, 160))
            }
        }
        keys.forEach { line ->
            val row = LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
            }
            line.forEach { label ->
                val key = TextView(context).apply {
                    text = label
                    gravity = Gravity.CENTER
                    textSize = 19f
                    setTextColor(Style.text)
                    background = Style.shape(if (label == "=") Color.rgb(16, 120, 110)
                        else Color.rgb(51, 65, 85), 9, context)
                    isClickable = true
                    isFocusable = true
                    contentDescription = when (label) {
                        "AC" -> "Borrar todo"
                        "⌫" -> "Borrar último dígito"
                        "=" -> "Calcular"
                        else -> label
                    }
                }
                key.setOnClickListener {
                    when (label) {
                        "AC" -> {
                            buffer = ""
                            result = null
                            finished = false
                            resultText.text = "Calcula sin salir de la pregunta"
                            resultText.setTextColor(Style.subtle)
                            redraw()
                        }
                        "⌫" -> {
                            buffer = buffer.dropLast(1)
                            result = null
                            finished = false
                            resultText.text = ""
                            redraw()
                        }
                        "=" -> compute()
                        else -> {
                            if (finished && (label.first().isDigit() || label == "." || label == "√" ||
                                        label == "(")) buffer = ""
                            if (buffer.length < 100) buffer += label
                            result = null
                            finished = false
                            resultText.text = ""
                            redraw()
                        }
                    }
                }
                row.addView(key, LinearLayout.LayoutParams(0, Style.dp(context, 47), 1f).apply {
                    setMargins(Style.dp(context, 2), Style.dp(context, 2),
                        Style.dp(context, 2), Style.dp(context, 2))
                })
            }
            calculator.addView(row)
        }
        if (answerInput != null) {
            val use = TextView(context).apply {
                text = "Usar resultado en mi respuesta"
                gravity = Gravity.CENTER
                textSize = 15f
                setTextColor(Style.text)
                minHeight = Style.dp(context, 44)
                background = Style.shape(Color.rgb(16, 120, 110), 10, context)
                isClickable = true
                isFocusable = true
            }
            use.setOnClickListener {
                val value = result ?: runCatching { CalculatorEngine.evaluate(buffer) }.getOrNull()
                if (value == null) {
                    Toast.makeText(context, "Primero calcula un resultado", Toast.LENGTH_SHORT).show()
                } else {
                    answerInput.setText(value)
                    answerInput.setSelection(answerInput.text.length)
                    result = value
                    calculator.visibility = View.GONE
                    toggle.text = "▦  Calculadora"
                }
            }
            Style.addSpace(calculator, 7)
            calculator.addView(use)
        }
        parent.addView(calculator)

        toggle.setOnClickListener {
            val opening = calculator.visibility != View.VISIBLE
            calculator.visibility = if (opening) View.VISIBLE else View.GONE
            toggle.text = if (opening) "▦  Cerrar calculadora" else "▦  Calculadora"
            if (opening) {
                val im = context.getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
                answerInput?.let {
                    im.hideSoftInputFromWindow(it.windowToken, 0)
                    it.clearFocus()
                }
                toggle.requestFocus()
            }
        }
    }
}
''', encoding="utf-8")

for name, parent, anchor in [
    ("BlockAccessibilityService.kt", "box",
        '        val feedback = Style.label(this, "", 15f, Style.subtle)'),
    ("StudyGateActivity.kt", "content",
        '        val feedback = Style.label(this, "", 14f, Style.subtle)')
]:
    p = src / name
    s = p.read_text(encoding="utf-8")
    if anchor not in s:
        raise RuntimeError("Cannot find quiz answer section in "+name)
    s = s.replace(anchor, "        QuizCalculator.attach(this, "+parent+", answerInput)\\n" + anchor, 1)
    p.write_text(s, encoding="utf-8")

v = gradle.read_text(encoding="utf-8")
if 'versionName = "0.6.9"' not in v or 'versionCode = 15' not in v:
    raise RuntimeError("Expected FocoQuiz 0.6.9 signed source")
gradle.write_text(v.replace('versionName = "0.6.9"', 'versionName = "0.6.10"')
                   .replace('versionCode = 15', 'versionCode = 16'), encoding="utf-8")
test = root / "tests/CalculatorEngineSmoke.kt"
test.parent.mkdir(parents=True, exist_ok=True)
test.write_text('''package com.focoquiz.app
fun main() {
    val examples = mapOf(
        "2+3*4" to "14",
        "(2+3)*4" to "20",
        "10÷4" to "2.5",
        "50%" to "0.5",
        "√9+1" to "4",
        "-8+2" to "-6",
        "7−9" to "-2",
        "3.14×2" to "6.28")
    for ((input, expected) in examples) {
        check(CalculatorEngine.evaluate(input) == expected) {
            input + " should be " + expected
        }
    }
    for (invalid in listOf("3÷0", "√-1", "1+(", "abc", "")) {
        check(runCatching { CalculatorEngine.evaluate(invalid) }.isFailure)
    }
    println("CalculatorEngine smoke tests passed")
}
''', encoding="utf-8")
print("FocoQuiz v0.6.10 calculator installed in blocker and study gate")
