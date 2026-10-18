#!/usr/bin/env python3
"""FocoQuiz v0.6.17 - eliminate identical prompts and protect stored question banks."""
from pathlib import Path

root=Path(__file__).resolve().parents[1]
src=root/"app/src/main/java/com/focoquiz/app"
lock=src/"LockStore.kt"
cycle=src/"QuestionCycle.kt"
gradle=root/"app/build.gradle.kts"

s=lock.read_text(encoding="utf-8")
def change(a,b):
    global s
    if a not in s:
        raise RuntimeError("v0.6.17 LockStore anchor missing: "+a[:120])
    s=s.replace(a,b,1)

change('''            val answer = item.optString("answer").trim()
            if (prompt.isBlank() || answer.isBlank()) null else StudyQuestion(''',
'''            val answer = item.optString("answer").trim()
            // One malformed numeric item must NOT discard every imported exam.
            // Drop only an unanswerable template with unresolved placeholders.
            val variant = runCatching {
                item.optJSONObject("numericVariation")?.let { obj ->
                    NumericQuizVariants.readConfig(obj, prompt,
                        item.optString("type","short_answer"), validateSamples = false)
                }
            }.getOrNull()
            val unresolved = Regex("\\\\{[A-Za-z][A-Za-z0-9_]*\\\\}").containsMatchIn(prompt)
            if (prompt.isBlank() || answer.isBlank() || (unresolved && variant == null)) null
            else StudyQuestion(''')
change('''                item.optJSONObject("numericVariation")?.let { obj ->
                    NumericQuizVariants.readConfig(obj, prompt,
                        item.optString("type","short_answer"), validateSamples = false)
                })
        }.map(NumericQuizVariants::upgradeSimpleArithmetic)
        } catch (_: Exception) {
            defaultQuestions().map(NumericQuizVariants::upgradeSimpleArithmetic)
        }''',
'''                variant)
        }.map(NumericQuizVariants::upgradeSimpleArithmetic)
        } catch (_: Exception) {
            // Showing ten unrelated demo questions instead of corrupted real exams
            // looked like infinite repetition and hid the real problem.
            emptyList()
        }''')
change('''                val old=prefs.getString(k,"")
                var current=question''',
'''                val old=prefs.getString(k,"")
                val oldAnswer=prefs.getString("last_variant_answer_"+question.key,"")
                var current=question''')
change('''                    if (current.prompt!=old && !current.prompt.contains('{')) break
                }
                prefs.edit().putString(k,current.prompt).apply()
                current''',
'''                    if (current.prompt!=old && current.answer!=oldAnswer &&
                        !current.prompt.contains('{')) break
                }
                // Persist both the operands and the result, to reduce memorization.
                prefs.edit().putString(k,current.prompt)
                    .putString("last_variant_answer_"+question.key,current.answer)
                    .apply()
                current''')

# The cycle logic used question IDs alone. Two different import IDs may contain
# the *same visible question*, giving apparent repeats in the quiz.
c=cycle.read_text(encoding="utf-8")
old='''    fun eligible(all: List<StudyQuestion>, rule: AppRule) =
        all.filter { q ->
            (rule.packIds.isEmpty() || q.packId in rule.packIds) &&
                (rule.difficulty == QuizDifficulty.MIXED || q.difficulty == rule.difficulty)
        }.distinctBy { it.key }'''
new='''    /** A quiz cannot present identical questions under different imported IDs. */
    fun eligible(all: List<StudyQuestion>, rule: AppRule): List<StudyQuestion> {
        val filtered = all.filter { q ->
            (rule.packIds.isEmpty() || q.packId in rule.packIds) &&
                (rule.difficulty == QuizDifficulty.MIXED || q.difficulty == rule.difficulty)
        }.distinctBy { it.key }
        // Treat cosmetic whitespace/case differences as duplicates. Keep different
        // concepts distinct; we do not remove every question that has numbers.
        return filtered.distinctBy {
            it.prompt.trim().lowercase(java.util.Locale.ROOT)
                .replace(Regex("\\\\s+"), " ")
        }
    }'''
if old not in c:raise RuntimeError("v0.6.17 QuestionCycle eligible anchor missing")
c=c.replace(old,new,1)
cycle.write_text(c,encoding="utf-8")
lock.write_text(s,encoding="utf-8")

v=gradle.read_text(encoding="utf-8")
if 'versionName = "0.6.16"' not in v or 'versionCode = 22' not in v:
    raise RuntimeError("Expected v0.6.16")
gradle.write_text(v.replace('versionName = "0.6.16"','versionName = "0.6.17"')
    .replace('versionCode = 22','versionCode = 23'),encoding="utf-8")
print("v0.6.17: bank preserves valid imports, duplicate prompt exclusion and new numeric results.")
