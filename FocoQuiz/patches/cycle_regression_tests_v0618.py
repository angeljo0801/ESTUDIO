#!/usr/bin/env python3
"""Run actual Kotlin unit tests for FocoQuiz v0.6.18 bank behavior."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
g=root/"app/build.gradle.kts"
s=g.read_text(encoding="utf-8")
if 'dependencies {' not in s:raise RuntimeError("Expected app dependencies")
if 'testImplementation("junit:junit:4.13.2")' not in s:
    s=s.replace("dependencies {",
        'dependencies {\n    testImplementation("junit:junit:4.13.2")',1)
g.write_text(s,encoding="utf-8")
test=root/"app/src/test/java/com/focoquiz/app/QuestionCycleRegressionTest.kt"
test.parent.mkdir(parents=True,exist_ok=True)
test.write_text('''package com.focoquiz.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class QuestionCycleRegressionTest {
    private fun questions(): List<StudyQuestion> = (1..12).map { number ->
        StudyQuestion("Pregunta $number", number.toString(),
            packId = if (number <= 6) "A" else "B",
            questionId = "q$number")
    }

    @Test fun answeredQuestionsNotRepeatedAcrossDifferentPools() {
        val data = questions()
        val onlyA = QuestionCycle.eligible(data,
            AppRule("app", packIds = setOf("A"), questionCount = 5))
        val both = QuestionCycle.eligible(data, AppRule("other", questionCount = 5))
        assertEquals(6, onlyA.size)
        assertEquals(12, both.size)
        var answered = emptySet<String>()
        fun choose(pool: List<StudyQuestion>, n: Int) =
            QuestionCycle.choose(pool, answered, n) { options, count ->
                options.take(count)
            }
        val first = choose(onlyA, 5)
        first.forEach { answered = answered + it.key }
        val second = choose(both, 5)
        assertTrue(second.none { it.key in first.map { q -> q.key } })
        second.forEach { answered = answered + it.key }
        assertEquals(10, answered.size)
        val third = choose(both, 5)
        assertEquals(5, third.size)
        assertEquals(5, third.map { it.key }.distinct().size)
        // The final two unseen questions MUST appear first.
        assertTrue(third.take(2).none { it.key in answered })
        assertTrue(third.drop(2).all { it.key in answered })
    }

    @Test fun merelySelectedQuestionIsStillAvailableNextAttempt() {
        val pool = QuestionCycle.eligible(questions(), AppRule("x", questionCount = 4))
        val selected = QuestionCycle.choose(pool, emptySet(), 4) { q, n -> q.take(n) }
        val answered = setOf(selected[0].key)
        val next = QuestionCycle.choose(pool, answered, 4) { q, n -> q.take(n) }
        assertFalse(next.any { it.key == selected[0].key })
        // Nothing else was answered, so those questions remain available.
        assertTrue(selected.drop(1).all { old -> next.any { it.key == old.key } })
    }

    @Test fun numericTemplateHasStableIdAcrossDifferentNumbers() {
        val base = StudyQuestion("Calcula {x} por {y}", "12",
            numericVariation = NumericVariation(
                listOf(NumericVariable("x", 2.0, 9.0, 1.0),
                       NumericVariable("y", 2.0, 9.0, 1.0)),
                "{x}*{y}", 0))
        val stable = QuestionCycle.eligible(listOf(base), AppRule("math")).single()
        assertTrue(stable.questionId.isNotEmpty())
        val varied = stable.copy(prompt = "Calcula 4 por 7", answer = "28")
        assertEquals(stable.key, varied.key)
        val different = stable.copy(prompt = "Calcula 7 por 8", answer = "56")
        assertEquals(stable.key, different.key)
    }

    @Test fun equivalentPromptFromTwoImportedPacksDoesNotRepeatInSameQuiz() {
        val a = StudyQuestion("¿Qué es una LAN?", "Red local",
            packId = "A", questionId = "q1")
        val b = StudyQuestion("  ¿QUÉ es una lan?  ", "Red local",
            packId = "B", questionId = "q75")
        val unique = QuestionCycle.eligible(listOf(a, b), AppRule("all"))
        assertEquals(1, unique.size)
    }
}
''', encoding="utf-8")
print("FocoQuiz 0.6.18: four executable Kotlin regression tests added.")
