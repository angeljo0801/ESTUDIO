#!/usr/bin/env python3
"""FocoQuiz v0.6.14: offline scientific calculator for all in-quiz modes."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
src=r/"app/src/main/java/com/focoquiz/app"
engine=src/"CalculatorEngine.kt"
ui=src/"QuizCalculator.kt"
gradle=r/"app/build.gradle.kts"
if not engine.is_file() or not ui.is_file():
    raise SystemExit("Scientific calculator requires base v0.6.10")
if "internal object CalculatorEngine" not in engine.read_text(encoding="utf-8"):
    raise SystemExit("Previous calculator engine missing")
if "internal object QuizCalculator" not in ui.read_text(encoding="utf-8"):
    raise SystemExit("Previous calculator UI missing")
engine.write_text('''package com.focoquiz.app

import java.math.BigDecimal
import java.math.MathContext
import java.math.RoundingMode
import kotlin.math.PI
import kotlin.math.E
import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.asin
import kotlin.math.atan
import kotlin.math.cos
import kotlin.math.ln
import kotlin.math.log10
import kotlin.math.pow
import kotlin.math.sin
import kotlin.math.sqrt
import kotlin.math.tan

/** Local math interpreter. Does not use network, JS evaluation or arbitrary code execution. */
internal object CalculatorEngine {
    fun evaluate(input: String, degrees: Boolean = true): String {
        require(input.length in 1..256) { "Operación vacía o demasiado larga" }
        val parser = Parser(input, degrees)
        val value = parser.expression()
        parser.skipSpaces()
        require(parser.atEnd()) { "Revisa la operación" }
        require(value.isFinite()) { "Resultado fuera de rango" }
        if (value == 0.0) return "0"
        val rounded = BigDecimal.valueOf(value)
            .round(MathContext(12, RoundingMode.HALF_UP)).stripTrailingZeros()
        // Avoid enormous result strings; parse the scientific notation again on next operation.
        return if (abs(value) >= 1.0e12 || abs(value) < 1.0e-8)
            rounded.toString().replace("E+", "E+")
        else rounded.toPlainString()
    }

    private class Parser(val source: String, val degrees: Boolean) {
        var pos = 0
        fun atEnd() = pos >= source.length
        fun skipSpaces() { while (!atEnd() && source[pos].isWhitespace()) pos++ }
        private fun eat(vararg tokens: Char): Boolean {
            skipSpaces()
            if (!atEnd() && source[pos] in tokens) { pos++; return true }
            return false
        }
        private fun word(name: String): Boolean {
            skipSpaces()
            if (!source.regionMatches(pos, name, 0, name.length, ignoreCase = false))
                return false
            pos += name.length
            return true
        }
        private fun check(value: Double): Double {
            require(value.isFinite()) { "Resultado fuera de rango" }
            return value
        }

        fun expression(): Double {
            var left = product()
            while (true) {
                left = when {
                    eat('+') -> check(left + product())
                    eat('-', '−') -> check(left - product())
                    else -> return left
                }
            }
        }
        private fun product(): Double {
            var left = unary()
            while (true) {
                left = when {
                    eat('×', '*') -> check(left * unary())
                    eat('÷', '/') -> {
                        val denominator = unary()
                        require(denominator != 0.0) { "No se puede dividir entre cero" }
                        check(left / denominator)
                    }
                    else -> return left
                }
            }
        }
        private fun unary(): Double {
            if (eat('+')) return unary()
            if (eat('-', '−')) return -unary()
            if (eat('√')) {
                val operand = unary()
                require(operand >= 0.0) { "Raíz de número negativo" }
                return sqrt(operand)
            }
            // Longest names first so asin does not get consumed as sin.
            for (name in listOf("asin", "acos", "atan", "sin", "cos", "tan",
                    "log", "ln", "abs", "sqrt")) {
                val initial = pos
                if (word(name)) {
                    require(eat('(')) { "Abre un paréntesis después de " + name }
                    val argument = expression()
                    require(eat(')')) { "Falta cerrar paréntesis" }
                    val value = when (name) {
                        "sin" -> sin(angle(argument))
                        "cos" -> cos(angle(argument))
                        "tan" -> {
                            require(abs(cos(angle(argument))) > 1.0e-12) {
                                "Tangente indefinida para este ángulo"
                            }
                            tan(angle(argument))
                        }
                        "asin" -> {
                            require(argument in -1.0..1.0) { "asin requiere un valor entre -1 y 1" }
                            reverseAngle(asin(argument))
                        }
                        "acos" -> {
                            require(argument in -1.0..1.0) { "acos requiere un valor entre -1 y 1" }
                            reverseAngle(acos(argument))
                        }
                        "atan" -> reverseAngle(atan(argument))
                        "log" -> {
                            require(argument > 0.0) { "log requiere un número positivo" }
                            log10(argument)
                        }
                        "ln" -> {
                            require(argument > 0.0) { "ln requiere un número positivo" }
                            ln(argument)
                        }
                        "abs" -> abs(argument)
                        "sqrt" -> {
                            require(argument >= 0.0) { "Raíz de número negativo" }
                            sqrt(argument)
                        }
                        else -> error("Función desconocida")
                    }
                    // cos(90°), sin(180°), etc. should display 0, not tiny artifacts.
                    return if (abs(value) < 1.0e-14 && name in setOf("sin","cos","tan")) 0.0
                           else check(value)
                }
                pos = initial
            }
            return power()
        }
        private fun angle(value: Double) = if (degrees) Math.toRadians(value) else value
        private fun reverseAngle(value: Double) = if (degrees) Math.toDegrees(value) else value
        private fun power(): Double {
            var base = postfix()
            // Right-associative; 2^3^2 = 512, and 2^-2 = 0.25.
            if (eat('^')) base = check(base.pow(unary()))
            return base
        }
        private fun postfix(): Double {
            var base = primary()
            while (true) {
                base = when {
                    eat('%') -> base / 100.0
                    eat('!') -> {
                        require(base >= 0.0 && base <= 170.0 && base % 1.0 == 0.0) {
                            "El factorial requiere un entero entre 0 y 170"
                        }
                        var result = 1.0
                        for (i in 2..base.toInt()) result *= i.toDouble()
                        check(result)
                    }
                    else -> return base
                }
            }
        }
        private fun primary(): Double {
            if (eat('(')) {
                val inner = expression()
                require(eat(')')) { "Falta cerrar paréntesis" }
                return inner
            }
            if (eat('π')) return PI
            if (eat('e')) return E
            skipSpaces()
            val start = pos
            var digits = 0
            while (!atEnd() && source[pos].isDigit()) { pos++; digits++ }
            if (eat('.')) {
                while (!atEnd() && source[pos].isDigit()) { pos++; digits++ }
            }
            require(digits > 0) { "Número o expresión incompleta" }
            // EE key inserts E for scientific notation: 1.5E-3.
            if (!atEnd() && source[pos] == 'E') {
                pos++
                if (!atEnd() && source[pos] in listOf('+','-','−')) pos++
                val exponentStart = pos
                while (!atEnd() && source[pos].isDigit()) pos++
                require(pos > exponentStart) { "Falta exponente después de EE" }
            }
            val parsed = source.substring(start, pos).replace('−','-').toDoubleOrNull()
                ?: throw IllegalArgumentException("Número inválido")
            return check(parsed)
        }
    }
}
''', encoding="utf-8")

ui.write_text('''package com.focoquiz.app

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

/** Compact, accessible and offline scientific calculator inside the same quiz view. */
internal object QuizCalculator {
    fun attach(context: Context, parent: LinearLayout, answerInput: EditText?) {
        val toggle = TextView(context).apply {
            text = "▦  Calculadora científica"
            textSize = 15f
            setTextColor(Style.text)
            gravity = Gravity.CENTER
            setPadding(Style.dp(context, 10), Style.dp(context, 7),
                Style.dp(context, 10), Style.dp(context, 7))
            background = Style.shape(Color.rgb(51, 65, 85), 12, context)
            minHeight = Style.dp(context, 42)
            isClickable = true
            isFocusable = true
            contentDescription = "Abrir o cerrar calculadora científica"
        }
        val toggleRow = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.END
        }
        toggleRow.addView(toggle, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        parent.addView(toggleRow)
        Style.addSpace(parent, 6)
        val calculator = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            background = Style.shape(Style.panel, 14, context)
            setPadding(Style.dp(context, 8), Style.dp(context, 9),
                Style.dp(context, 8), Style.dp(context, 9))
            visibility = View.GONE
        }
        val expression = TextView(context).apply {
            text = "0"
            setTextColor(Style.text)
            textSize = 22f
            gravity = Gravity.END or Gravity.CENTER_VERTICAL
            minHeight = Style.dp(context, 48)
            maxLines = 3
        }
        calculator.addView(expression)
        val resultText = TextView(context).apply {
            text = "Modo: DEG · potencias, trigonometría y logaritmos"
            setTextColor(Style.subtle)
            textSize = 13f
            gravity = Gravity.END
            maxLines = 2
        }
        calculator.addView(resultText)
        Style.addSpace(calculator, 5)

        var buffer = ""
        var result: String? = null
        var finished = false
        var degrees = true
        val keys = listOf(
            listOf("DEG", "AC", "⌫", "(", ")"),
            listOf("sin", "cos", "tan", "π", "e"),
            listOf("asin", "acos", "atan", "ln", "log"),
            listOf("x²", "xʸ", "√", "1/x", "!"),
            listOf("7", "8", "9", "÷", "%"),
            listOf("4", "5", "6", "×", "EE"),
            listOf("1", "2", "3", "−", "±"),
            listOf("0", ".", "+", "=", "x³")
        )
        fun redraw() { expression.text = if (buffer.isBlank()) "0" else buffer }
        fun showResult() {
            try {
                val value = CalculatorEngine.evaluate(buffer, degrees)
                result = value
                buffer = value
                finished = true
                redraw()
                resultText.text = "Resultado · " + if (degrees) "DEG" else "RAD"
                resultText.setTextColor(Style.accent)
            } catch (e: IllegalArgumentException) {
                result = null
                resultText.text = e.message ?: "Operación inválida"
                resultText.setTextColor(Color.rgb(255, 180, 160))
            }
        }
        fun invalidate() {
            result = null
            finished = false
            resultText.text = if (degrees) "Modo: DEG" else "Modo: RAD"
            resultText.setTextColor(Style.subtle)
            redraw()
        }
        keys.forEach { line ->
            val row = LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }
            line.forEach { label ->
                val key = TextView(context).apply {
                    text = label
                    gravity = Gravity.CENTER
                    textSize = if (label.length > 3) 14f else 18f
                    setTextColor(Style.text)
                    background = Style.shape(
                        if (label == "=") Color.rgb(16, 120, 110)
                        else if (label == "DEG") Color.rgb(63, 75, 96)
                        else Color.rgb(51, 65, 85), 8, context)
                    isClickable = true
                    isFocusable = true
                    minHeight = Style.dp(context, 43)
                    contentDescription = when (label) {
                        "DEG" -> "Cambiar modo entre grados y radianes"
                        "AC" -> "Borrar todo"
                        "⌫" -> "Borrar último carácter"
                        "x²" -> "Elevar al cuadrado"
                        "x³" -> "Elevar al cubo"
                        "xʸ" -> "Elevar a una potencia"
                        "1/x" -> "Inverso"
                        "EE" -> "Notación científica por diez elevado a"
                        "!" -> "Factorial"
                        "±" -> "Cambiar signo"
                        "=" -> "Calcular resultado"
                        else -> label
                    }
                }
                key.setOnClickListener {
                    when (label) {
                        "DEG" -> {
                            degrees = !degrees
                            key.text = if (degrees) "DEG" else "RAD"
                            invalidate()
                        }
                        "AC" -> {
                            buffer = ""
                            invalidate()
                        }
                        "⌫" -> {
                            buffer = buffer.dropLast(1)
                            invalidate()
                        }
                        "=" -> showResult()
                        "x²", "x³" -> {
                            buffer = if (buffer.isBlank()) "" else "(" + buffer + ")^" +
                                (if (label == "x²") "2" else "3")
                            invalidate()
                        }
                        "1/x" -> {
                            buffer = if (buffer.isBlank()) "1/(" else "1/(" + buffer + ")"
                            invalidate()
                        }
                        "±" -> {
                            buffer = if (buffer.isBlank()) "−"
                                else if (buffer.startsWith("−(") && buffer.endsWith(")"))
                                    buffer.substring(2, buffer.length-1)
                                else "−(" + buffer + ")"
                            invalidate()
                        }
                        else -> {
                            val part = when (label) {
                                "sin", "cos", "tan", "asin", "acos", "atan",
                                "ln", "log" -> label + "("
                                "√" -> "√("
                                "xʸ" -> "^"
                                "EE" -> "E"
                                else -> label
                            }
                            val beginsFresh = label.firstOrNull()?.isDigit() == true ||
                                label in listOf(".", "π", "e", "√", "sin", "cos", "tan",
                                    "asin", "acos", "atan", "ln", "log", "(")
                            if (finished && beginsFresh) buffer = ""
                            if (buffer.length + part.length <= 256) buffer += part
                            invalidate()
                        }
                    }
                }
                row.addView(key, LinearLayout.LayoutParams(0, Style.dp(context, 44), 1f).apply {
                    setMargins(Style.dp(context, 2), Style.dp(context, 2),
                        Style.dp(context, 2), Style.dp(context, 2))
                })
            }
            calculator.addView(row)
        }
        calculator.addView(Style.label(context,
            "DEG/RAD: ángulos · EE: notación científica · % = ÷100 · " +
                "Cierra paréntesis después de las funciones.", 12f, Style.subtle))

        if (answerInput != null) {
            Style.addSpace(calculator, 7)
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
                val value = result ?: runCatching {
                    CalculatorEngine.evaluate(buffer, degrees)
                }.getOrNull()
                if (value == null) {
                    Toast.makeText(context, "Primero calcula un resultado", Toast.LENGTH_SHORT).show()
                } else {
                    answerInput.setText(value)
                    answerInput.setSelection(answerInput.text.length)
                    result = value
                    calculator.visibility = View.GONE
                    toggle.text = "▦  Calculadora científica"
                }
            }
            calculator.addView(use)
        }
        parent.addView(calculator)
        toggle.setOnClickListener {
            val opening = calculator.visibility != View.VISIBLE
            calculator.visibility = if (opening) View.VISIBLE else View.GONE
            toggle.text = if (opening) "▦  Cerrar calculadora" else "▦  Calculadora científica"
            if (opening) {
                val manager = context.getSystemService(Context.INPUT_METHOD_SERVICE)
                    as InputMethodManager
                answerInput?.let {
                    manager.hideSoftInputFromWindow(it.windowToken, 0)
                    it.clearFocus()
                }
                toggle.requestFocus()
            }
        }
    }
}
''', encoding="utf-8")

test=r/"tests/ScientificCalculatorEngineSmoke.kt"
test.parent.mkdir(parents=True, exist_ok=True)
test.write_text('''package com.focoquiz.app

import kotlin.math.abs
import kotlin.math.PI
fun main() {
    val examples = mapOf(
        "2+3×4" to 14.0,
        "(2+3)^2" to 25.0,
        "2^3^2" to 512.0,
        "2^-2" to 0.25,
        "-2^2" to -4.0,
        "√(49)" to 7.0,
        "50%" to 0.5,
        "5!" to 120.0,
        "log(100)" to 2.0,
        "ln(e)" to 1.0,
        "sin(30)" to 0.5,
        "cos(90)" to 0.0,
        "tan(45)" to 1.0,
        "asin(0.5)" to 30.0,
        "1.2E-3" to 0.0012,
        "π" to PI
    )
    for ((expression, expected) in examples) {
        val actual = CalculatorEngine.evaluate(expression).toDouble()
        check(abs(actual-expected) < 1e-8) {
            expression + " yielded " + actual + " instead of " + expected
        }
    }
    check(abs(CalculatorEngine.evaluate("sin(π/2)", false).toDouble()-1.0) < 1e-9)
    check(abs(CalculatorEngine.evaluate("asin(1)", false).toDouble()-PI/2) < 1e-9)
    val invalid = listOf("3/0", "sqrt(-1)", "tan(90)", "log(-2)",
        "ln(0)", "asin(2)", "1+", "3.5!", "171!", "2^1024", "1E-", "")
    for (input in invalid) check(runCatching { CalculatorEngine.evaluate(input) }.isFailure) {
        "Should reject: " + input
    }
    println("Scientific calculator smoke tests passed: " + examples.size + " valid and " +
        invalid.size + " invalid expressions.")
}
''', encoding="utf-8")

b=gradle.read_text(encoding="utf-8")
if 'versionName = "0.6.13"' not in b or 'versionCode = 19' not in b:
    raise SystemExit("Expected v0.6.13 app version")
gradle.write_text(b.replace('versionName = "0.6.13"','versionName = "0.6.14"')
                   .replace('versionCode = 19','versionCode = 20'),encoding="utf-8")
print("FocoQuiz v0.6.14: scientific calculator ready.")
