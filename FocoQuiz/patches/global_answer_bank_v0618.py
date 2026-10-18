#!/usr/bin/env python3
"""FocoQuiz v0.6.18: global answered bank shared by apps/study plans and stable template IDs."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
src=root/"app/src/main/java/com/focoquiz/app"

cycle=src/"QuestionCycle.kt"
c=cycle.read_text(encoding="utf-8")
old='''        }.distinctBy { it.key }
        // Treat cosmetic whitespace/case differences as duplicates. Keep different'''
new='''        }.map { q ->
            // Manual or legacy numeric templates may have no questionId. Numeric
            // instantiation changes prompt, so their old key changed at each attempt
            // and was impossible to record in the answered bank. Create a stable
            // identifier from the ORIGINAL template, before inserting numbers.
            if (q.numericVariation != null && q.questionId.isBlank()) {
                val bytes = (q.packId + "\\u0000" + q.prompt)
                    .toByteArray(Charsets.UTF_8)
                val hash = MessageDigest.getInstance("SHA-256").digest(bytes)
                    .take(12).joinToString("") { "%02x".format(it) }
                q.copy(questionId = "num_" + hash)
            } else q
        }.distinctBy { it.key }
        // Treat cosmetic whitespace/case differences as duplicates. Keep different'''
if old not in c:raise RuntimeError("v0.6.18: QuestionCycle.eligible anchor not found")
c=c.replace(old,new,1)
cycle.write_text(c,encoding="utf-8")

store=src/"LockStore.kt"
s=store.read_text(encoding="utf-8")
old='''    private fun bankKey(items: List<StudyQuestion>) =
        "answered_cycle_" + QuestionCycle.id(items)

    private fun answeredBank(items: List<StudyQuestion>): Set<String> = try {
        val array=JSONArray(prefs.getString(bankKey(items),"[]"))
        val valid=items.map { it.key }.toSet()
        (0 until array.length()).map { array.optString(it) }.filter { it in valid }.toSet()
    } catch (_: Exception) { emptySet() }

    fun cycleStatus(rule: AppRule): Pair<Int,Int> {
        val all=QuestionCycle.eligible(questions(),rule)
        return answeredBank(all).size to all.size
    }'''
new='''    // A single history across protected apps and study plans: switching from
    // "all guides" to a particular guide can no longer replay answered questions.
    private val globalBankPref = "answered_cycle_global_v2"

    private fun readKeyArray(raw: String?): Set<String> = try {
        val array=JSONArray(raw ?: "[]")
        (0 until minOf(array.length(), 3000)).map { array.optString(it) }
            .filter { it.isNotBlank() }.toSet()
    } catch (_: Exception) { emptySet() }

    private fun globalAnswered(): Set<String> {
        val existing=prefs.getString(globalBankPref,null)
        if (existing != null) return readKeyArray(existing)
        // Preserve the v0.6.16/17 banks when upgrading, even where their scopes
        // were different (e.g. an app and a scheduled exam with overlapping packs).
        val oldKeys=prefs.all.keys.filter {
            it.startsWith("answered_cycle_") && it != globalBankPref
        }
        val combined=oldKeys.flatMap { key ->
            readKeyArray(prefs.getString(key,null))
        }.toSet()
        val editor=prefs.edit().putString(globalBankPref,
            JSONArray(combined.sorted()).toString())
        oldKeys.forEach(editor::remove)
        editor.commit()
        return combined
    }

    private fun answeredBank(items: List<StudyQuestion>): Set<String> =
        globalAnswered().intersect(items.map { it.key }.toSet())

    fun cycleStatus(rule: AppRule): Pair<Int,Int> {
        val all=QuestionCycle.eligible(questions(),rule)
        return answeredBank(all).size to all.size
    }'''
if old not in s:raise RuntimeError("v0.6.18: LockStore bankKey/status anchor missing")
s=s.replace(old,new,1)
old='''    private fun markAnswered(question: StudyQuestion,rule: AppRule) {
        val items=QuestionCycle.eligible(questions(),rule)
        if (items.isEmpty()) return
        val ids=QuestionCycle.mark(answeredBank(items),question.key,items.map { it.key }.toSet())
        val array=JSONArray()
        ids.sorted().forEach { array.put(it) }
        // Committed immediately, even if Android stops the process after grading.
        prefs.edit().putString(bankKey(items),array.toString()).commit()
    }'''
new='''    private fun markAnswered(question: StudyQuestion,rule: AppRule) {
        val all=QuestionCycle.eligible(questions(),AppRule("global-question-bank"))
        if (all.isEmpty()) return
        val available=all.map { it.key }.toSet()
        // Rule is still used for selecting a quiz, but recording an answer is
        // GLOBAL: the same question stays excluded on any other app or plan.
        if (question.key !in available) return
        val already=globalAnswered().intersect(available)
        val next=already+question.key
        // Clear only when every eligible question in the library was answered.
        val toSave=if (next.size >= available.size) emptySet() else next
        val array=JSONArray()
        toSave.sorted().forEach { array.put(it) }
        // commit() survives immediate backgrounding, service restart or device kill.
        prefs.edit().putString(globalBankPref,array.toString()).commit()
    }'''
if old not in s:raise RuntimeError("v0.6.18: LockStore markAnswered anchor missing")
s=s.replace(old,new,1)
store.write_text(s,encoding="utf-8")

# Avoid accidentally displaying a generic answer as if a parametric arithmetic
# template had new numbers. The existing hint identifies fixed guides.
# Tests are Android-free and run against QuestionCycle's deterministic logic.
test=root/"tests/GlobalQuestionCycleSmoke.kt"
test.parent.mkdir(parents=True,exist_ok=True)
test.write_text('''package com.focoquiz.app

fun main() {
    val questions=(1..12).map { StudyQuestion("Pregunta $it","$it",
        packId=if (it<=6) "A" else "B",questionId="q$it") }
    val all=QuestionCycle.eligible(questions,AppRule("all",questionCount=5))
    val onlyA=QuestionCycle.eligible(questions,AppRule("one",packIds=setOf("A"),questionCount=5))
    check(all.size == 12 && onlyA.size == 6)
    var seen=emptySet<String>()
    val picks=mutableListOf<String>()
    fun next(eligible: List<StudyQuestion>,count: Int):List<StudyQuestion> =
        QuestionCycle.choose(eligible,seen,count) { items,n ->
            items.take(n)
        }
    // First exam used A; switching to all guides must NOT recycle those same A IDs.
    val first=next(onlyA,5)
    first.forEach { seen=seen+it.key; picks.add(it.key) }
    val second=next(all,5)
    check(second.none { it.key in picks })
    second.forEach { seen=seen+it.key; picks.add(it.key) }
    check(picks.distinct().size==10)
    val third=next(all,5)
    check(third.size==5 && third.map { it.key }.distinct().size==5)
    check(third.take(2).none { it.key in picks })
    check(third.take(2).map { it.key }.toSet()==all.map { it.key }.toSet()-picks.toSet())
    // Number substitutions must not change a question's bank ID.
    val template=StudyQuestion("¿Cuánto es {x} × {y}?","12",questionId="",
        numericVariation=NumericVariation(listOf(
            NumericVariable("x",2.0,9.0,1.0),
            NumericVariable("y",2.0,9.0,1.0)),"{x}*{y}",0))
    val fixed=QuestionCycle.eligible(listOf(template),AppRule("demo")).single()
    check(fixed.questionId.isNotBlank())
    val changed=fixed.copy(prompt="¿Cuánto es 3 × 7?", answer="21")
    check(changed.key==fixed.key)
    println("Global answer cycle / numeric identity smoke test passed")
}
''',encoding="utf-8")

b=root/"app/build.gradle.kts"
v=b.read_text(encoding="utf-8")
if 'versionName = "0.6.17"' not in v or 'versionCode = 23' not in v:
    raise RuntimeError("Expected stable FocoQuiz v0.6.17")
b.write_text(v.replace('versionName = "0.6.17"','versionName = "0.6.18"')
            .replace('versionCode = 23','versionCode = 24'),encoding="utf-8")
print("FocoQuiz v0.6.18: shared global answered bank and stable numeric question IDs.")
