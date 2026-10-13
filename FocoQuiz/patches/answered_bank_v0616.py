#!/usr/bin/env python3
"""FocoQuiz 0.6.16 persistent question-bank cycles, auto-upgrade simple arithmetic."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
src=r/"app/src/main/java/com/focoquiz/app"
(src/"QuestionCycle.kt").write_text('''package com.focoquiz.app

import java.security.MessageDigest

/** Answered, not merely displayed, items are withheld until all are answered. */
internal object QuestionCycle {
    fun eligible(all: List<StudyQuestion>, rule: AppRule) =
        all.filter { q ->
            (rule.packIds.isEmpty() || q.packId in rule.packIds) &&
                (rule.difficulty == QuizDifficulty.MIXED || q.difficulty == rule.difficulty)
        }.distinctBy { it.key }

    fun id(items: List<StudyQuestion>): String {
        val bytes=items.map { it.key }.sorted().joinToString("\\n").toByteArray()
        return MessageDigest.getInstance("SHA-256").digest(bytes)
            .take(12).joinToString("") { "%02x".format(it) }
    }

    fun choose(
        eligible: List<StudyQuestion>, seen: Set<String>, count: Int,
        pick: (List<StudyQuestion>, Int) -> List<StudyQuestion>
    ): List<StudyQuestion> {
        val options=eligible.distinctBy { it.key }
        val wanted=count.coerceIn(0,options.size)
        val pending=options.filterNot { it.key in seen }
        val first=pick(pending,minOf(wanted,pending.size))
        if (first.size==wanted) return first
        // Every unasked question goes FIRST. Only then fill from a new cycle.
        val chosen=first.map { it.key }.toSet()
        val old=options.filter { it.key in seen && it.key !in chosen }
        return (first+pick(old,wanted-first.size)).distinctBy { it.key }
    }

    fun mark(seen: Set<String>, answered: String, eligible: Set<String>): Set<String> {
        if (answered !in eligible) return seen
        val next=(seen intersect eligible)+answered
        return if (next.size==eligible.size) emptySet() else next
    }
}
''',encoding="utf-8")

p=src/"LockStore.kt"
s=p.read_text(encoding="utf-8")
a='''    fun progress(question: StudyQuestion): QuestionProgress {'''
assert a in s,"missing progress"
s=s.replace(a,'''    private fun bankKey(items: List<StudyQuestion>) =
        "answered_cycle_" + QuestionCycle.id(items)

    private fun answeredBank(items: List<StudyQuestion>): Set<String> = try {
        val array=JSONArray(prefs.getString(bankKey(items),"[]"))
        val valid=items.map { it.key }.toSet()
        (0 until array.length()).map { array.optString(it) }.filter { it in valid }.toSet()
    } catch (_: Exception) { emptySet() }

    fun cycleStatus(rule: AppRule): Pair<Int,Int> {
        val all=QuestionCycle.eligible(questions(),rule)
        return answeredBank(all).size to all.size
    }

    fun selectQuestions(rule: AppRule): List<StudyQuestion> {
        val items=QuestionCycle.eligible(questions(),rule)
        val selected=QuestionCycle.choose(items,answeredBank(items),rule.questionCount) { list,n ->
            if (n==0 || list.isEmpty()) emptyList()
            else QuizEngine.select(list,rule.copy(questionCount=n),::progress)
        }
        return selected.map { question ->
            if (question.numericVariation==null) question
            else {
                val k="last_variant_"+question.key
                val old=prefs.getString(k,"")
                var current=question
                for (retry in 0..29) {
                    if (retry>0) current=NumericQuizVariants.instantiate(question)
                    if (current.prompt!=old && !current.prompt.contains('{')) break
                }
                prefs.edit().putString(k,current.prompt).apply()
                current
            }
        }
    }

    private fun markAnswered(question: StudyQuestion,rule: AppRule) {
        val items=QuestionCycle.eligible(questions(),rule)
        if (items.isEmpty()) return
        val ids=QuestionCycle.mark(answeredBank(items),question.key,items.map { it.key }.toSet())
        val array=JSONArray()
        ids.sorted().forEach { array.put(it) }
        // Committed immediately, even if Android stops the process after grading.
        prefs.edit().putString(bankKey(items),array.toString()).commit()
    }

'''+a,1)
a='''fun recordAnswer(question: StudyQuestion, right: Boolean) {'''
assert a in s,"missing recordAnswer"
s=s.replace(a,'''fun recordAnswer(question: StudyQuestion, right: Boolean, rule: AppRule? = null) {''',1)
a='''prefs.edit().putString("progress_'''+chr(36)+'''{question.key}", data.toString()).apply()'''
assert a in s,"missing progress write"
s=s.replace(a,a+'''
        markAnswered(question,rule ?: AppRule("all-questions"))''',1)
a='''        }
        } catch (_: Exception) { defaultQuestions() }
    }

    fun putQuestions'''
assert a in s,"missing questions end"
s=s.replace(a,'''        }.map(NumericQuizVariants::upgradeSimpleArithmetic)
        } catch (_: Exception) {
            defaultQuestions().map(NumericQuizVariants::upgradeSimpleArithmetic)
        }
    }

    fun putQuestions''',1)
a='''val raw = prefs.getString("questions", null) ?: return defaultQuestions()'''
assert a in s,"missing default"
s=s.replace(a,'''val raw = prefs.getString("questions", null)
            ?: return defaultQuestions().map(NumericQuizVariants::upgradeSimpleArithmetic)''',1)
p.write_text(s,encoding="utf-8")

p=src/"NumericQuizVariants.kt"
s=p.read_text(encoding="utf-8")
a='''    fun accepted(question: StudyQuestion, response: String): Boolean {'''
assert a in s,"missing accepted"
s=s.replace(a,'''    /** Only change legacy arithmetic if the original result can be verified. */
    fun upgradeSimpleArithmetic(q: StudyQuestion): StudyQuestion {
        if (q.numericVariation!=null || q.answer.contains('|')) return q
        val pattern=Regex(
            "^\\\\s*¿?Cu[aá]nto es\\\\s+([0-9]{1,4})\\\\s*([+×÷*/−-])\\\\s*" +
            "([0-9]{1,4})\\\\s*\\\\?\\\\s*$", RegexOption.IGNORE_CASE)
        val match=pattern.matchEntire(q.prompt) ?: return q
        val a=match.groupValues[1].toIntOrNull() ?: return q
        val b=match.groupValues[3].toIntOrNull() ?: return q
        val sign=match.groupValues[2]
        if (b==0 && sign in listOf("÷","/")) return q
        val expected=runCatching {
            CalculatorEngine.evaluate(a.toString()+sign+b).toDouble()
        }.getOrNull() ?: return q
        val existing=q.answer.trim().replace(',','.').toDoubleOrNull() ?: return q
        if (kotlin.math.abs(expected-existing)>1e-8) return q
        fun range(name: String,value: Int): NumericVariable {
            val low=(value*0.65).toInt().coerceAtLeast(1)
            val high=(value*1.55).toInt().coerceAtLeast(low+4).coerceAtMost(10000)
            return NumericVariable(name,low.toDouble(),high.toDouble(),1.0)
        }
        val spec=NumericVariation(
            listOf(range("a",a),range("b",b)),
            "{a}"+sign+"{b}",if (sign in listOf("÷","/")) 2 else 0)
        return q.copy(
            prompt="¿Cuánto es {a} "+sign+" {b}?",
            explanation="Aplica la operación indicada a los nuevos valores.",
            numericVariation=spec,
            questionId=q.questionId.ifBlank {
                "legacy_"+q.prompt.hashCode().toUInt().toString(16)
            })
    }

'''+a,1)
a='''instantiate(StudyQuestion(prompt,"0",type, listOf("a","b","c","d"),
                    numericVariation=spec), Random(seed)).answer.isNotBlank()'''
b='''instantiate(StudyQuestion(prompt,"0",type,listOf("a","b","c","d"),
                    numericVariation=spec),Random(seed)).let {
                    it.numericVariation!=null && !it.prompt.contains('{') &&
                        it.answer.isNotBlank()
                }'''
assert a in s,"missing import validation"
s=s.replace(a,b,1)
p.write_text(s,encoding="utf-8")

p=src/"BlockAccessibilityService.kt"
s=p.read_text(encoding="utf-8")
a="QuizEngine.select(store.questions(), rule, store::progress)"
assert a in s,"missing block select"
s=s.replace(a,"store.selectQuestions(rule)",1)
a="store.recordAnswer(question, right)"
assert a in s,"missing block record"
s=s.replace(a,"store.recordAnswer(question, right, rule)",1)
p.write_text(s,encoding="utf-8")

p=src/"StudyGateActivity.kt"
s=p.read_text(encoding="utf-8")
a="QuizEngine.select(store.questions(), rule, store::progress)"
assert a in s,"missing gate select"
s=s.replace(a,"store.selectQuestions(rule)",1)
a="store.recordAnswer(q, right)"
assert a in s,"missing gate record"
s=s.replace(a,'''store.recordAnswer(q, right, AppRule("scheduled:"+occ.task.id,
                packIds=occ.task.packIds,difficulty=occ.task.difficulty,
                questionCount=occ.task.questionCount,passPercent=occ.task.passPercent))''',1)
p.write_text(s,encoding="utf-8")

p=r/"app/build.gradle.kts"
s=p.read_text(encoding="utf-8")
if 'versionName = "0.6.15"' not in s or 'versionCode = 21' not in s:
    raise RuntimeError("Expected v0.6.15")
p.write_text(s.replace('versionName = "0.6.15"','versionName = "0.6.16"')
              .replace('versionCode = 21','versionCode = 22'),encoding="utf-8")
print("v0.6.16 bank, no-repeat behavior and legacy math migration applied")
