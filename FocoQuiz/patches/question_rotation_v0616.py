#!/usr/bin/env python3
"""FocoQuiz 0.6.16: persisted answered-question cycles across quiz attempts."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"app/src/main/java/com/focoquiz/app"
engine=p/"QuizEngine.kt"
s=engine.read_text(encoding="utf-8")
marker='''    fun required(count: Int, passPercent: Int): Int ='''
if marker not in s:raise SystemExit("Missing QuizEngine required()")
s=s.replace(marker,'''    /**
     * All unseen questions come FIRST. If a quiz needs more questions than remain,
     * draw the remaining slots from the last cycle, without duplicating a question
     * within this same attempt. Never mark a question as seen merely for showing it.
     */
    fun selectForAttempt(
        all: List<StudyQuestion>, rule: AppRule,
        progress: (StudyQuestion) -> QuestionProgress,
        answeredKeys: Set<String>,
        random: Random = Random.Default
    ): List<StudyQuestion> {
        val eligible = all.filter {
            (rule.packIds.isEmpty() || it.packId in rule.packIds) &&
                (rule.difficulty == QuizDifficulty.MIXED || it.difficulty == rule.difficulty)
        }.distinctBy { it.key }
        val target = minOf(rule.questionCount, eligible.size)
        if (target == 0) return emptyList()
        val unseen = eligible.filterNot { it.key in answeredKeys }
        val freshCount = minOf(target, unseen.size)
        val fresh = if (freshCount > 0) select(unseen,
            rule.copy(questionCount = freshCount), progress, random) else emptyList()
        val leftover = target - fresh.size
        val recycled = if (leftover > 0) select(
            eligible.filter { it.key in answeredKeys && it.key !in fresh.map { f -> f.key } },
            rule.copy(questionCount = leftover), progress, random) else emptyList()
        return fresh + recycled
    }

'''+marker,1)
engine.write_text(s,encoding="utf-8")

lock=p/"LockStore.kt"
s=lock.read_text(encoding="utf-8")
marker='''    fun progress(question: StudyQuestion): QuestionProgress {'''
if marker not in s:raise SystemExit("LockStore progress anchor missing")
s=s.replace(marker,'''    /**
     * Answered-question bank, persisted between attempts and shared by any apps
     * that use exactly the same eligible guides/difficulty pool.
     * The key is a digest of STABLE question IDs; changing guide selections
     * creates an independent cycle. No duplication of the question data.
     */
    private fun rotationScope(rule: AppRule, eligible: List<StudyQuestion>): String {
        val keys = eligible.map { it.key }.distinct().sorted().joinToString("\\n")
        val digest = java.security.MessageDigest.getInstance("SHA-256")
            .digest(keys.toByteArray(Charsets.UTF_8)).take(12)
            .joinToString("") { "%02x".format(it) }
        return "cycle_used_" + digest
    }

    private fun eligibleForRule(rule: AppRule): List<StudyQuestion> =
        questions().filter {
            (rule.packIds.isEmpty() || it.packId in rule.packIds) &&
                (rule.difficulty == QuizDifficulty.MIXED ||
                    it.difficulty == rule.difficulty)
        }.distinctBy { it.key }

    /** Returns only questions already ANSWERED in the current rotation. */
    fun answeredKeys(rule: AppRule): Set<String> {
        val eligible = eligibleForRule(rule)
        if (eligible.isEmpty()) return emptySet()
        val scope = rotationScope(rule, eligible)
        val valid = eligible.map { it.key }.toSet()
        val stored = runCatching {
            val a = JSONArray(prefs.getString(scope, "[]"))
            (0 until a.length()).map { a.optString(it) }.toSet()
        }.getOrDefault(emptySet())
        val used = stored.intersect(valid)
        if (used.size >= valid.size) {
            prefs.edit().remove(scope).apply()
            return emptySet()
        }
        return used
    }

    /**
     * Mark on actual submission (right OR wrong), never on selection,
     * and reset only after every eligible question has been answered.
     */
    fun markAnswered(question: StudyQuestion, rule: AppRule) {
        val eligible = eligibleForRule(rule)
        val keys = eligible.map { it.key }.toSet()
        if (question.key !in keys || keys.isEmpty()) return
        val scope = rotationScope(rule, eligible)
        val used = answeredKeys(rule).toMutableSet()
        used.add(question.key)
        val editor = prefs.edit()
        if (used.containsAll(keys)) editor.remove(scope)
        else editor.putString(scope, JSONArray(used.toList()).toString())
        editor.apply()
    }

'''+marker,1)
lock.write_text(s,encoding="utf-8")

for file,selection,newselect,mark,marknew in [
 ("BlockAccessibilityService.kt",
  "QuizEngine.select(store.questions(), rule, store::progress)",
  "QuizEngine.selectForAttempt(store.questions(), rule, store::progress, store.answeredKeys(rule))",
  "store.recordAnswer(question, right)",
  "store.recordAnswer(question, right)\\n            store.markAnswered(question, rule)"),
 ("StudyGateActivity.kt",
  "QuizEngine.select(store.questions(), rule, store::progress)",
  "QuizEngine.selectForAttempt(store.questions(), rule, store::progress, store.answeredKeys(rule))",
  "store.recordAnswer(q, right)",
  """store.recordAnswer(q, right)
            // Same exact guide/difficulty scope as beginQuiz() so all apps/plans
            // share the rotation when they use an identical question pool.
            val cycleRule = AppRule("scheduled:" + occ.task.id,
                packIds = occ.task.packIds, difficulty = occ.task.difficulty,
                questionCount = occ.task.questionCount, passPercent = occ.task.passPercent)
            store.markAnswered(q, cycleRule)""")
]:
    q=p/file
    text=q.read_text(encoding="utf-8")
    if selection not in text or mark not in text:raise SystemExit(file+" selection/mark anchors absent")
    text=text.replace(selection,newselect,1)
    text=text.replace(mark,marknew.replace("\\n","\n"),1)
    q.write_text(text,encoding="utf-8")

build=p.parents[5]/"build.gradle.kts"
# p = .../FocoQuiz/app/src/main/java/com/focoquiz/app, parents[5] = .../FocoQuiz/app
assert build.name=="build.gradle.kts",build
b=build.read_text(encoding="utf-8")
if 'versionName = "0.6.15"' not in b or 'versionCode = 21' not in b:
    raise SystemExit("Need signed FocoQuiz v0.6.15")
build.write_text(b.replace('versionName = "0.6.15"','versionName = "0.6.16"')
             .replace('versionCode = 21','versionCode = 22'),encoding="utf-8")
print("FocoQuiz 0.6.16: persistent rotation marks only answered questions, then resets after full pool.")
