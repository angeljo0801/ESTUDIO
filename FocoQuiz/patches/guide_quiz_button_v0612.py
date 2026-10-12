#!/usr/bin/env python3
"""FocoQuiz 0.6.12: guide button at top left of quiz and progress restore from accessibility overlay."""
from pathlib import Path
src=Path(__file__).resolve().parents[1]/"app/src/main/java/com/focoquiz/app"

block=src/"BlockAccessibilityService.kt"
s=block.read_text(encoding="utf-8")
def put(a,b):
    global s
    if a not in s:raise RuntimeError("Quiz service insertion failed: "+a[:120])
    s=s.replace(a,b,1)

put('''    private var expectedState: AccessState? = null''',
'''    private var expectedState: AccessState? = null
    // If user opens a linked study guide, retain their quiz position and draft answer.
    private var guideReturnPackage: String? = null
    private var guideReturnDeadline = 0L
    private var guideReturnQuestion: String? = null
    private var guideReturnAnswer: String? = null
    private var guideReturnChoice: String? = null
    private var guideReturnFeedback: String? = null''')

put('''        session = QuizEngine.select(store.questions(), rule, store::progress)
        index = 0
        correctCount = 0
        submitted = false
        if (session.isEmpty())''',
'''        val resume = guideReturnPackage == pkg &&
            android.os.SystemClock.elapsedRealtime() <= guideReturnDeadline &&
            session.isNotEmpty() && index in session.indices &&
            store.rules()[pkg] != null
        if (!resume) {
            session = QuizEngine.select(store.questions(), rule, store::progress)
            index = 0
            correctCount = 0
            submitted = false
            guideReturnPackage = null
            guideReturnQuestion = null
        }
        if (session.isEmpty())''')

put('''        val question = session[index]
        val necessary''',
'''        val question = session[index]
        // The button is located at the upper LEFT of the question panel.
        val restoring = guideReturnPackage == pkg &&
            guideReturnQuestion == question.key
        var saveDraft: (() -> Unit)? = null
        QuizGuideButton.attach(this, box, question.packId) {
            guideReturnPackage = pkg
            guideReturnDeadline = android.os.SystemClock.elapsedRealtime() + 20 * 60_000L
            guideReturnQuestion = question.key
            saveDraft?.invoke()
            // Hide only FocoQuiz's own overlay; system Home/Back remain available.
            foregroundApp = null
            hideOverlay()
        }
        val necessary''')
put('''        var selected = ""
        val answerInput: EditText?''',
'''        var selected = if (restoring) guideReturnChoice.orEmpty() else ""
        val answerInput: EditText?''')
put('''            box.addView(Style.label(this, "Selecciona una opción", 14f, Style.accent).apply { tag = "chosen" })''',
'''            box.addView(Style.label(this,
                if (selected.isBlank()) "Selecciona una opción" else "Elegiste: " + selected,
                14f, Style.accent).apply { tag = "chosen" })''')
put('''            box.addView(answerInput)
        }
        QuizCalculator.attach''',
'''            box.addView(answerInput)
            if (restoring && guideReturnAnswer != null) answerInput.setText(guideReturnAnswer)
        }
        saveDraft = {
            guideReturnAnswer = answerInput?.text?.toString()
            guideReturnChoice = selected
            guideReturnFeedback = if (::statusView.isInitialized) null else null
        }
        QuizCalculator.attach''')
# statusView is nullable not lateinit; removing incorrect check.
s=s.replace('''            guideReturnFeedback = if (::statusView.isInitialized) null else null
''','',1)
put('''        val feedback = Style.label(this, "", 15f, Style.subtle)
        box.addView(feedback)''',
'''        val feedback = Style.label(this,
            if (restoring) guideReturnFeedback.orEmpty() else "", 15f, Style.subtle)
        box.addView(feedback)
        saveDraft = {
            guideReturnAnswer = answerInput?.text?.toString()
            guideReturnChoice = selected
            guideReturnFeedback = feedback.text?.toString()
        }''')
put('''        box.addView(check, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
    }

    private fun normalize''',
'''        if (restoring && submitted) {
            answerInput?.isEnabled = false
            check.text = if (index == session.lastIndex) "Ver resultado" else "Siguiente pregunta"
        }
        box.addView(check, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
        if (restoring) {
            guideReturnPackage = null
            guideReturnQuestion = null
            guideReturnAnswer = null
            guideReturnChoice = null
            guideReturnFeedback = null
        }
    }

    private fun normalize''')

block.write_text(s,encoding="utf-8")

gate=src/"StudyGateActivity.kt"
s=gate.read_text(encoding="utf-8")
anchor='''        val q = questions[questionIndex]
        addInfo("Pregunta'''
if anchor not in s:raise RuntimeError("Study gate question anchor missing")
s=s.replace(anchor,'''        val q = questions[questionIndex]
        QuizGuideButton.attach(this, content, q.packId)
        addInfo("Pregunta''',1)
gate.write_text(s,encoding="utf-8")
print("0.6.12: quiz guide button on upper left, draft/score preserved on overlay return.")
