#!/usr/bin/env python3
"""FocoQuiz 0.6.16: quiz bank progress and regression tests."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
src=r/"app/src/main/java/com/focoquiz/app"
p=src/"BlockAccessibilityService.kt"
s=p.read_text(encoding="utf-8")
a='''        Style.addSpace(box, 8)
        box.addView(Style.label(this, question.prompt, 20f, Style.text, true))'''
if a not in s:raise RuntimeError("Missing quiz question label")
s=s.replace(a,'''        val (usedCount,poolSize)=store.cycleStatus(rule)
        box.addView(Style.label(this,
            "Banco de respondidas: " + usedCount + " / " + poolSize +
                " · No se repiten hasta agotar el banco",13f,Style.subtle))
        Style.addSpace(box, 8)
        box.addView(Style.label(this, question.prompt, 20f, Style.text, true))''',1)
p.write_text(s,encoding="utf-8")
p=src/"StudyGateActivity.kt"
s=p.read_text(encoding="utf-8")
a='''        Style.addSpace(content, 14)
        content.addView(Style.label(this, q.prompt, 19f, Style.text, true))'''
if a not in s:raise RuntimeError("Missing study gate question")
s=s.replace(a,'''        val cycleRule=AppRule("scheduled:" + occ.task.id,
            packIds=occ.task.packIds,difficulty=occ.task.difficulty,
            questionCount=occ.task.questionCount,passPercent=occ.task.passPercent)
        val (usedCount,poolSize)=store.cycleStatus(cycleRule)
        addInfo("Banco de respondidas: " + usedCount + " / " + poolSize)
        Style.addSpace(content, 14)
        content.addView(Style.label(this, q.prompt, 19f, Style.text, true))''',1)
p.write_text(s,encoding="utf-8")

p=r/"tests/QuestionCycleSmoke.kt"
p.parent.mkdir(parents=True,exist_ok=True)
p.write_text('''package com.focoquiz.app

fun main() {
    val catalog=(1..12).map {
        StudyQuestion("Q"+it,it.toString(),questionId="n"+it)
    }
    val eligible=QuestionCycle.eligible(catalog,AppRule("test",questionCount=5))
    check(eligible.size==12)
    var already=emptySet<String>()
    val universe=eligible.map { it.key }.toSet()
    fun choose(n: Int)=QuestionCycle.choose(
        eligible,already,n) { possible,count -> possible.take(count) }
    val first=choose(5)
    check(first.size==5 && first.map { it.key }.distinct().size==5)
    first.forEach { already=QuestionCycle.mark(already,it.key,universe) }
    check(already.size==5)
    val second=choose(5)
    check(second.none { it.key in first.map { q -> q.key } })
    second.forEach { already=QuestionCycle.mark(already,it.key,universe) }
    check(already.size==10)
    val third=choose(5)
    check(third.size==5 && third.map { it.key }.distinct().size==5)
    check(third.take(2).none { it.key in already })
    already=QuestionCycle.mark(already,third[0].key,universe)
    check(already.size==11)
    already=QuestionCycle.mark(already,third[1].key,universe)
    check(already.isEmpty())
    check(choose(5).size==5)
    println("QuestionCycle bank regression checks passed")
}
''',encoding="utf-8")
print("v0.6.16: answered-bank counters and smoke tests added.")
