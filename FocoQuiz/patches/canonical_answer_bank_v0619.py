#!/usr/bin/env python3
"""FocoQuiz v0.6.19: globally deduplicate answered question identities across imports."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
src=root/"app/src/main/java/com/focoquiz/app"
cycle=src/"QuestionCycle.kt"
store=src/"LockStore.kt"
build=root/"app/build.gradle.kts"
c=cycle.read_text(encoding="utf-8")
anchor='''internal object QuestionCycle {
'''
if anchor not in c:raise RuntimeError("Missing cycle object")
c=c.replace(anchor,'''internal object QuestionCycle {
    /**
     * Equivalent questions imported from different guides may have different IDs.
     * The "answered" bank uses a content fingerprint, never the imported ID.
     * Numeric questions are fingerprinted BEFORE changing {variables}, so every
     * numerical variant of the same problem shares one completed-question record.
     */
    fun canonicalId(question: StudyQuestion): String {
        val normalized=question.prompt.trim()
            .lowercase(java.util.Locale.ROOT).replace(Regex("\\\\s+"), " ")
        val bytes=normalized.toByteArray(Charsets.UTF_8)
        val hash=MessageDigest.getInstance("SHA-256").digest(bytes)
        return "q_" + hash.take(16).joinToString("") { "%02x".format(it) }
    }

''',1)
cycle.write_text(c,encoding="utf-8")
s=store.read_text(encoding="utf-8")
def replace(a,b):
 global s
 if a not in s: raise RuntimeError("0.6.19 LockStore anchor missing: "+a[:130])
 s=s.replace(a,b,1)

replace('''    private val globalBankPref = "answered_cycle_global_v2"''',
'''    private val globalBankPref = "answered_cycle_global_v3"''')

old='''    private fun globalAnswered(): Set<String> {
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
        globalAnswered().intersect(items.map { it.key }.toSet())'''
new='''    private fun globalAnswered(): Set<String> {
        val existing=prefs.getString(globalBankPref,null)
        if (existing != null) return readKeyArray(existing)
        // Migrate both v2 global and older per-pool banks. Those stored IDs were
        // per-import; map them back to the original question templates.
        val previous=prefs.all.keys.filter {
            it.startsWith("answered_cycle_") && it != globalBankPref
        }
        val ids=previous.flatMap { readKeyArray(prefs.getString(it,null)) }.toSet()
        val byOldId=questions().associate { item ->
            // stabilize numeric legacy IDs before forming the lookup
            val stable=QuestionCycle.eligible(listOf(item),AppRule("migration"))
                .firstOrNull() ?: item
            stable.key to QuestionCycle.canonicalId(stable)
        }
        val migrated=ids.mapNotNull { byOldId[it] }.toSet()
        val editor=prefs.edit().putString(globalBankPref,
            JSONArray(migrated.sorted()).toString())
        previous.forEach(editor::remove)
        editor.commit()
        return migrated
    }

    private fun answeredBank(items: List<StudyQuestion>): Set<String> {
        val global=globalAnswered()
        return items.filter { QuestionCycle.canonicalId(it) in global }
            .map { it.key }.toSet()
    }'''
replace(old,new)

old='''    private fun markAnswered(question: StudyQuestion,rule: AppRule) {
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
new='''    private fun markAnswered(question: StudyQuestion,rule: AppRule) {
        val source=questions()
        // Look up by stable ID from the *unmodified* template, since a math
        // question's visible prompt already has randomized numbers by grading.
        val inThisQuiz=QuestionCycle.eligible(source,rule)
        val template=inThisQuiz.firstOrNull { it.key==question.key } ?: return
        val answeredId=QuestionCycle.canonicalId(template)
        val all=QuestionCycle.eligible(source,AppRule("global-question-bank"))
        if (all.isEmpty()) return
        val available=all.map(QuestionCycle::canonicalId).toSet()
        if (answeredId !in available) return
        val already=globalAnswered().intersect(available)
        val next=already+answeredId
        // Reset only when every unique visible question has actually been graded.
        val toSave=if (next.size>=available.size) emptySet() else next
        val arr=JSONArray()
        toSave.sorted().forEach { arr.put(it) }
        // Synchronous commit survives forceful process termination after answer.
        prefs.edit().putString(globalBankPref,arr.toString()).commit()
    }'''
replace(old,new)
store.write_text(s,encoding="utf-8")

test=root/"app/src/test/java/com/focoquiz/app/CanonicalQuestionBankTest.kt"
test.parent.mkdir(parents=True,exist_ok=True)
test.write_text('''package com.focoquiz.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CanonicalQuestionBankTest {
    @Test fun sameQuestionFromDifferentGuidesSharesOneAnsweredIdentity() {
        val first=StudyQuestion("¿Qué significa LAN?","Local Area Network",
            questionId="q1",packId="guideA")
        val second=StudyQuestion("  ¿QUÉ significa lan?  ","Local Area Network",
            questionId="q999",packId="guideB")
        assertFalse(first.key==second.key)
        assertEquals(QuestionCycle.canonicalId(first),QuestionCycle.canonicalId(second))
    }

    @Test fun changingMathValuesDoesNotChangeTheIdentityOfTheTemplate() {
        val template=StudyQuestion("Calcular {V}/{R}","1",
            questionId="ohm",packId="guideA")
        val otherSource=template.copy(packId="guideB",questionId="q288")
        assertEquals(QuestionCycle.canonicalId(template),
            QuestionCycle.canonicalId(otherSource))
        assertTrue(QuestionCycle.canonicalId(template)!=QuestionCycle.canonicalId(
            template.copy(prompt="Calcular potencia {V}*{I}")))
    }

    @Test fun restrictedPackAndGlobalPoolWillNotReplayAnAlreadyAnsweredDuplicate() {
        val a=StudyQuestion("¿Qué es un router?","Router",packId="A",questionId="a1")
        val b=StudyQuestion("¿QUÉ ES UN ROUTER?","Router",packId="B",questionId="b1")
        val c=StudyQuestion("¿Qué es una LAN?","LAN",packId="B",questionId="b2")
        val chosen=QuestionCycle.eligible(listOf(a,b,c),AppRule("B",packIds=setOf("B")))
        val seen=setOf(QuestionCycle.canonicalId(a))
        val answeredKeys=chosen.filter { QuestionCycle.canonicalId(it) in seen }
            .map { it.key }.toSet()
        val next=QuestionCycle.choose(chosen,answeredKeys,1) { all,count ->
            all.take(count)
        }
        assertEquals(1,next.size)
        assertEquals(c.key,next.single().key)
    }
}
''',encoding="utf-8")
b=build.read_text(encoding="utf-8")
if 'versionName = "0.6.18"' not in b or 'versionCode = 24' not in b:
    raise RuntimeError("Expected v0.6.18")
build.write_text(b.replace('versionName = "0.6.18"','versionName = "0.6.19"')
    .replace('versionCode = 24','versionCode = 25'),encoding="utf-8")
print("v0.6.19: canonical fingerprints shared across imports and numeric instances.")
