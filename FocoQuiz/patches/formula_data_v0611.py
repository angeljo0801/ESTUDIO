#!/usr/bin/env python3
"""FocoQuiz v0.6.11: formula bank import/storage with optional schema fields."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
src=root/"app/src/main/java/com/focoquiz/app"
def modify(file,replacements):
    p=src/file
    s=p.read_text(encoding="utf-8")
    for a,b in replacements:
        if a not in s:raise RuntimeError(file+" missing: "+a[:100])
        s=s.replace(a,b,1)
    p.write_text(s,encoding="utf-8")

modify("Policy.kt",[
('''data class QuestionProgress(''','''/** Generic formula from the user's imported study guide. */
data class StudyFormula(
    val id: String,
    val name: String,
    val expression: String,
    val variables: String = "",
    val whenToUse: String = "",
    val topic: String = ""
)

data class QuestionProgress('''),
('''    val difficulty: QuizDifficulty = QuizDifficulty.MEDIUM
) {
    val key''','''    val difficulty: QuizDifficulty = QuizDifficulty.MEDIUM,
    val formulaIds: List<String> = emptyList()
) {
    val key''')])

modify("QuizFormat.kt",[
('''data class ImportedQuiz(val title: String, val source: String, val packId: String, val questions: List<StudyQuestion>)''',
'''data class ImportedQuiz(
    val title: String, val source: String, val packId: String,
    val questions: List<StudyQuestion>, val formulas: List<StudyFormula> = emptyList()
)'''),
('''        val ids = mutableSetOf<String>()
        val questions''',
'''        // Optional formulas are backward compatible with focoquiz.quiz version 1.
        val formulaNodes = obj.optJSONArray("formulas")
        require(formulaNodes == null || formulaNodes.length() <= 120) {
            "Máximo 120 fórmulas por examen"
        }
        val formulaKeys = mutableSetOf<String>()
        val formulas = (0 until (formulaNodes?.length() ?: 0)).map { i ->
            val node = formulaNodes!!.optJSONObject(i)
                ?: error("Fórmula inválida, número " + (i + 1))
            val id = node.optString("id").trim()
            val name = node.optString("name").trim()
            val expression = node.optString("expression").trim()
            require(id.length in 1..60 && formulaKeys.add(id)) {
                "Cada fórmula debe tener un ID único"
            }
            require(name.length in 1..120 && expression.length in 1..400) {
                "Cada fórmula necesita nombre y expresión"
            }
            StudyFormula(id, name, expression,
                node.optString("variables").trim().take(700),
                node.optString("when_to_use").trim().take(400),
                node.optString("topic").trim().take(150))
        }
        val ids = mutableSetOf<String>()
        val questions'''),
('''            StudyQuestion(
                prompt = prompt,''',
'''            val rawRefs = node.optJSONArray("formula_ids")
            val formulaRefs = (0 until (rawRefs?.length() ?: 0)).map {
                rawRefs!!.optString(it).trim()
            }.filter { it.isNotEmpty() }.distinct()
            require(formulaRefs.size <= 20 && formulaRefs.all { it in formulaKeys }) {
                "Referencias a fórmulas inválidas en la pregunta " + (index + 1)
            }
            StudyQuestion(
                prompt = prompt,'''),
('''                questionId = id,
                topic =''',
'''                questionId = id,
                formulaIds = formulaRefs,
                topic ='''),
('''return ImportedQuiz(title, source, packId, questions.map { it.copy(packId = packId) })''',
'''return ImportedQuiz(title, source, packId,
            questions.map { it.copy(packId = packId) }, formulas)''')])

modify("LockStore.kt",[
('''                    .getOrDefault(QuizDifficulty.MEDIUM))
        }
        } catch''',
'''                    .getOrDefault(QuizDifficulty.MEDIUM),
                item.optJSONArray("formulaIds")?.let { refs ->
                    (0 until refs.length()).map { refs.optString(it) }
                        .filter { it.isNotBlank() }.distinct().take(20)
                } ?: emptyList())
        }
        } catch'''),
('''                .put("options", JSONArray(q.options)))''',
'''                .put("options", JSONArray(q.options))
                .put("formulaIds", JSONArray(q.formulaIds)))'''),
('''        prefs.edit().putString("packs", array.toString()).apply()
        return quiz.questions.size''',
'''        prefs.edit().putString("packs", array.toString())
            .putString("formulas_" + quiz.packId, JSONArray().apply {
                quiz.formulas.forEach { f ->
                    put(JSONObject().put("id", f.id).put("name", f.name)
                        .put("expression", f.expression).put("variables", f.variables)
                        .put("when_to_use", f.whenToUse).put("topic", f.topic))
                }
            }.toString()).apply()
        return quiz.questions.size''')])
p=src/"LockStore.kt"
s=p.read_text(encoding="utf-8")
anchor='''    private fun examMetadata(): Map<String, ExamPack> = try {'''
if anchor not in s:raise RuntimeError("missing examMetadata anchor")
s=s.replace(anchor,'''    /** Formula bank is stored once for each imported exam, never duplicated per question. */
    fun formulasForPack(packId: String): List<StudyFormula> = try {
        if (packId.length > 120 || !packId.matches(Regex("[A-Za-z0-9_-]+"))) emptyList()
        else {
            val arr = JSONArray(prefs.getString("formulas_" + packId, "[]"))
            (0 until arr.length().coerceAtMost(120)).mapNotNull { i ->
                val node = arr.optJSONObject(i) ?: return@mapNotNull null
                val name = node.optString("name")
                val expr = node.optString("expression")
                if (name.isBlank() || expr.isBlank()) null
                else StudyFormula(node.optString("id"), name, expr,
                    node.optString("variables"), node.optString("when_to_use"),
                    node.optString("topic"))
            }
        }
    } catch (_: Exception) { emptyList() }

'''+anchor,1)
p.write_text(s,encoding="utf-8")
print("v0.6.11: optional formulas parsed and stored by exam, question formula references retained.")
