#!/usr/bin/env python3
"""FocoQuiz 0.6.9: enforce configuration hours in every editor and datastore."""
from pathlib import Path
src=Path(__file__).resolve().parents[1]/"app/src/main/java/com/focoquiz/app"
def mod(file, replacements):
    p=src/file
    s=p.read_text(encoding="utf-8")
    for before, after in replacements:
        if before not in s:
            raise RuntimeError("v0.6.9 editor patch mismatch in "+file+": "+before[:110])
        s=s.replace(before,after,1)
    p.write_text(s,encoding="utf-8")

guardfield='''    private val configurationGuard by lazy { ConfigurationHoursGuard(this) }
'''
methods='''    override fun onResume() {
        super.onResume()
        configurationGuard.resume()
    }

    override fun onPause() {
        configurationGuard.pause()
        super.onPause()
    }

'''

mod("QuizSettingsActivity.kt",[
('''class QuizSettingsActivity : Activity() {
''','''class QuizSettingsActivity : Activity() {
'''+guardfield),
('''        super.onCreate(savedInstanceState)
        store = LockStore(this)''',
'''        super.onCreate(savedInstanceState)
        if (!configurationGuard.check()) return
        store = LockStore(this)'''),
('''    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {''',
methods+'''    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {'''),
('''        if (resultCode != RESULT_OK) return''',
'''        if (!configurationGuard.check() || resultCode != RESULT_OK) return'''),
('''    private fun importFromUri(uri: Uri) {
        try {''',
'''    private fun importFromUri(uri: Uri) {
        if (!configurationGuard.check()) return
        try {'''),
('''    private fun editQuestion(index: Int?) {
        val old''',
'''    private fun editQuestion(index: Int?) {
        if (!configurationGuard.check()) return
        val old''')
])

mod("RoutineEditorActivity.kt",[
('''class RoutineEditorActivity : Activity() {
''','''class RoutineEditorActivity : Activity() {
'''+guardfield),
('''        super.onCreate(savedInstanceState)
        title = "Mis rutinas''',
'''        super.onCreate(savedInstanceState)
        if (!configurationGuard.check()) return
        title = "Mis rutinas'''),
('''    private fun refresh() {''',methods+'''    private fun refresh() {''')
])

mod("StudyPlanEditorActivity.kt",[
('''class StudyPlanEditorActivity : Activity() {
''','''class StudyPlanEditorActivity : Activity() {
'''+guardfield),
('''        super.onCreate(savedInstanceState)
        val scroll''',
'''        super.onCreate(savedInstanceState)
        if (!configurationGuard.check()) return
        val scroll'''),
('''    override fun onResume() { super.onResume(); if (::root.isInitialized) render() }''',
'''    override fun onResume() {
        super.onResume()
        if (!configurationGuard.resume()) return
        if (::root.isInitialized) render()
    }

    override fun onPause() {
        configurationGuard.pause()
        super.onPause()
    }''')
])

# Stop writes even if a dialog's SAVE action races the two-second lock timer.
mod("StudyPlanStore.kt",[
('''    fun save(plan: StudyPlan) {
        require''',
'''    fun save(plan: StudyPlan) {
        if (!ConfigurationHours(prefsContext).canEdit()) return
        require'''),
('''    fun delete(planId: String) { persist''',
'''    fun delete(planId: String) {
        if (!ConfigurationHours(prefsContext).canEdit()) return
        persist'''),
('''    private val prefs = context.applicationContext.getSharedPreferences''',
'''    private val prefsContext = context.applicationContext
    private val prefs = context.applicationContext.getSharedPreferences''')
])

# Only authoring mutations are blocked. Automatic quiz progress, unlock expiry,
# scheduled checks and default social protections must keep functioning 24/7.
mod("LockStore.kt",[
('''class LockStore(context: Context) {
    private val prefs''',
'''class LockStore(context: Context) {
    private val configHours = ConfigurationHours(context)
    private val prefs'''),
('''    fun putRoutine(routine: ExerciseRoutine) {
        val updated''',
'''    fun putRoutine(routine: ExerciseRoutine) {
        if (!configHours.canEdit()) return
        val updated'''),
('''    fun deleteRoutine(id: String): Boolean {
        if (rules()''',
'''    fun deleteRoutine(id: String): Boolean {
        if (!configHours.canEdit()) return false
        if (rules()'''),
('''    fun putQuestions(questions: List<StudyQuestion>) {
        val array''',
'''    fun putQuestions(questions: List<StudyQuestion>) {
        if (!configHours.canEdit()) return
        val array'''),
('''    fun importQuiz(quiz: ImportedQuiz): Int {
        val existing''',
'''    fun importQuiz(quiz: ImportedQuiz): Int {
        if (!configHours.canEdit()) return 0
        val existing'''),
('''    fun setQuestionTarget(n: Int) { prefs.edit()''',
'''    fun setQuestionTarget(n: Int) { if (!configHours.canEdit()) return; prefs.edit()'''),
('''    fun setUnlockMinutes(n: Int) { prefs.edit()''',
'''    fun setUnlockMinutes(n: Int) { if (!configHours.canEdit()) return; prefs.edit()''')
])
print("v0.6.9: question, routine and study-plan editors close outside the window; writes protected.")
