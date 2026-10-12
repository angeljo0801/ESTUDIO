#!/usr/bin/env python3
"""FocoQuiz v0.6.13: single-tap Home, fresh randomized attempts, durable AccessibilityService."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
src=root/"app/src/main/java/com/focoquiz/app"
sfile=src/"BlockAccessibilityService.kt"
s=sfile.read_text(encoding="utf-8")
def edit(old,new):
    global s
    if old not in s: raise SystemExit("v0.6.13 service patch mismatch: "+old[:150])
    s=s.replace(old,new,1)

edit('import android.os.Looper\n','import android.os.Looper\nimport android.os.SystemClock\n')

edit('''    private var guideReturnFeedback: String? = null''',
'''    private var guideReturnFeedback: String? = null
    private var homeTransitionPending = false
    private var homeRequestSerial = 0
    private var homeTransitionUntil = 0L

    /** Discard ALL attempt-only state. Guide viewer is the only deliberate exception. */
    private fun abandonAttempt() {
        session = emptyList()
        index = 0
        correctCount = 0
        submitted = false
        guideReturnPackage = null
        guideReturnDeadline = 0L
        guideReturnQuestion = null
        guideReturnAnswer = null
        guideReturnChoice = null
        guideReturnFeedback = null
    }

    private fun launchSystemHomeFallback() {
        runCatching {
            startActivity(Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED))
        }
    }

    /** Ask Android to navigate while the overlay still exists, then dismiss it.
     * A bounded retry covers Samsung launchers which occasionally ignore the first dispatch.
     * This never restricts system navigation, Settings or emergency calls. */
    private fun leaveForHome() {
        ++homeRequestSerial
        val serial = homeRequestSerial
        val source = overlayTarget
        homeTransitionPending = true
        homeTransitionUntil = SystemClock.elapsedRealtime() + 1300L
        abandonAttempt()
        closeKeyboard()
        val dispatched = performGlobalAction(GLOBAL_ACTION_HOME)
        foregroundApp = null
        hideOverlay()
        if (!dispatched) launchSystemHomeFallback()
        handler.postDelayed({
            if (homeRequestSerial == serial && homeTransitionPending &&
                SystemClock.elapsedRealtime() <= homeTransitionUntil) {
                // Retry at most once, without requiring a second tap.
                val retry = performGlobalAction(GLOBAL_ACTION_HOME)
                if (!retry) launchSystemHomeFallback()
            }
        }, 430L)
        handler.postDelayed({
            if (homeRequestSerial == serial) homeTransitionPending = false
        }, 1400L)
    }''')
edit('''        handler.removeCallbacks(recheck)
        handler.post(recheck)
    }

    override fun onAccessibilityEvent''',
'''        handler.removeCallbacks(recheck)
        homeTransitionPending = false
        abandonAttempt()
        handler.post(recheck)
    }

    override fun onAccessibilityEvent''')

edit('''        if (pkg == packageName) {
            // TYPE_ACCESSIBILITY_OVERLAY''',
'''        if (pkg == packageName) {
            // TYPE_ACCESSIBILITY_OVERLAY''')
edit('''            foregroundApp = null
            hideOverlay()
            return
        }
        if (isSystemSafe(pkg)) {
            foregroundApp = null
            hideOverlay()
            return
        }''',
'''            val cls = event.className?.toString().orEmpty()
            if (guideReturnPackage == null ||
                (!cls.endsWith(".GuidePickerActivity") && !cls.endsWith(".GuideViewerActivity"))) {
                abandonAttempt()
            }
            foregroundApp = null
            hideOverlay()
            return
        }
        if (isSystemSafe(pkg)) {
            homeTransitionPending = false
            ++homeRequestSerial
            abandonAttempt()
            foregroundApp = null
            hideOverlay()
            return
        }''')
edit('''        foregroundApp = pkg
        refreshProtection()
    }''',
'''        if (homeTransitionPending &&
            SystemClock.elapsedRealtime() < homeTransitionUntil) {
            // Do not re-open the quiz while Android is moving to Home.
            return
        }
        if (pkg != guideReturnPackage && session.isNotEmpty()) abandonAttempt()
        foregroundApp = pkg
        refreshProtection()
    }''')

edit('''        goHome.setOnClickListener {
            closeKeyboard()
            foregroundApp = null
            hideOverlay()
            performGlobalAction(GLOBAL_ACTION_HOME)
        }''',
'''        goHome.setOnClickListener { leaveForHome() }''')
edit('''        leave.setOnClickListener {
            foregroundApp = null
            hideOverlay()
            performGlobalAction(GLOBAL_ACTION_HOME)
        }''',
'''        leave.setOnClickListener { leaveForHome() }''')

edit('''        val view = overlay
        overlay = null''',
'''        val view = overlay
        // On Home/external-app exits, the quiz is discarded. Only the explicit
        // document-viewer handoff can preserve the current attempt.
        if (guideReturnPackage == null) {
            session = emptyList()
            index = 0
            correctCount = 0
            submitted = false
        }
        overlay = null''')

edit('''    override fun onInterrupt() { hideOverlay() }
    override fun onDestroy() {
        handler.removeCallbacks(recheck)
        hideOverlay()''',
'''    override fun onInterrupt() {
        // If temporarily interrupted but still enabled, try refreshing again.
        hideOverlay()
        handler.removeCallbacks(recheck)
        handler.postDelayed(recheck, 250L)
    }
    override fun onDestroy() {
        handler.removeCallbacks(recheck)
        ++homeRequestSerial
        homeTransitionPending = false
        abandonAttempt()
        hideOverlay()''')
sfile.write_text(s,encoding="utf-8")

# Make selection order uniformly mixed independently from weighted selection.
q=src/"QuizEngine.kt"
v=q.read_text(encoding="utf-8")
anchor='''        return chosen
    }

    fun required'''
if anchor not in v: raise SystemExit("v0.6.13 missing select return")
v=v.replace(anchor,'''        // Selection may favor weaker questions, but presentation order is new and
        // uniformly randomized on EVERY attempt, with no duplicates.
        return chosen.shuffled(random)
    }

    fun required''',1)
q.write_text(v,encoding="utf-8")

# A quiz from a scheduled study plan also restarts when the user actually exits
# the activity. Opening a linked guide intentionally preserves it.
g=src/"StudyGateActivity.kt"
v=g.read_text(encoding="utf-8")
anchor='''    private var submitted = false'''
if anchor not in v:raise SystemExit("missing scheduled quiz state")
v=v.replace(anchor,'''    private var submitted = false
    private var viewingLinkedGuide = false
    private var guideOpenAt = 0L
    private var needsFreshAttempt = false''',1)

anchor='''        } else if (active.task.type == StudyTaskType.STUDY_TIMER && !running && timerEnd > 0L) {'''
if anchor not in v:raise SystemExit("missing onResume gate")
v=v.replace(anchor,'''        } else if (active.task.type == StudyTaskType.QUIZ && needsFreshAttempt) {
            needsFreshAttempt = false
            renderTask(active) // beginQuiz selects a NEW, shuffled attempt from question 1
        } else if (active.task.type == StudyTaskType.STUDY_TIMER && !running && timerEnd > 0L) {''',1)
# mark return completed only after decision made
anchor='''    private fun addTitle(text: String)'''
if anchor not in v:raise SystemExit("missing addTitle")
v=v.replace(anchor,'''    override fun onStop() {
        if (occurrence?.task?.type == StudyTaskType.QUIZ && !isChangingConfigurations) {
            val guideHandoff = viewingLinkedGuide &&
                SystemClock.elapsedRealtime() - guideOpenAt < 20L * 60_000L
            if (!guideHandoff) {
                questions = emptyList()
                questionIndex = 0
                correct = 0
                submitted = false
                needsFreshAttempt = true
            }
        }
        super.onStop()
    }

'''+anchor,1)
anchor='''        QuizGuideButton.attach(this, content, q.packId)'''
if anchor not in v:raise SystemExit("missing guide button in study gate")
v=v.replace(anchor,'''        QuizGuideButton.attach(this, content, q.packId) {
            viewingLinkedGuide = true
            guideOpenAt = SystemClock.elapsedRealtime()
        }''',1)
# reset guide flag when returning to paused activity, not in onStop
anchor='''        super.onResume()
        val active = plans.pending()'''
if anchor not in v: raise SystemExit("missing gate onResume start")
v=v.replace(anchor,'''        super.onResume()
        // A return after a guide handoff continues this question; a normal exit restarts it.
        viewingLinkedGuide = false
        val active = plans.pending()''',1)
g.write_text(v,encoding="utf-8")

# Add an honest battery/Accessibility settings shortcut, requiring a user's explicit choice.
m=src/"MainActivity.kt"
v=m.read_text(encoding="utf-8")
anchor='''        serviceCard.addView(activate)
        root.addView(serviceCard)'''
if anchor not in v:raise SystemExit("missing service status card")
v=v.replace(anchor,'''        serviceCard.addView(activate)
        serviceCard.addView(Style.label(this,
            "Protección permanente: el servicio de Accesibilidad funciona sin mantener " +
                "el dashboard abierto. En Samsung, configura Batería → Sin restricciones " +
                "para reducir pausas; Android aún puede detenerlo tras forzar cierre " +
                "o desactivar Accesibilidad.", 14f, Style.subtle))
        serviceCard.addView(Style.action(this, "Ajustes de batería · mantener protección activa").apply {
            setOnClickListener {
                try {
                    startActivity(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))
                } catch (_: Exception) {
                    startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                        android.net.Uri.parse("package:" + packageName)))
                }
            }
        })
        root.addView(serviceCard)''',1)
m.write_text(v,encoding="utf-8")

build=root/"app/build.gradle.kts"
v=build.read_text(encoding="utf-8")
if 'versionName = "0.6.12"' not in v or 'versionCode = 18' not in v:
    raise SystemExit("Expected FocoQuiz 0.6.12")
build.write_text(v.replace('versionName = "0.6.12"','versionName = "0.6.13"')
                  .replace('versionCode = 18','versionCode = 19'),encoding="utf-8")
print("v0.6.13: one-tap Home dispatch and retry, fresh randomized attempts, battery info.")
