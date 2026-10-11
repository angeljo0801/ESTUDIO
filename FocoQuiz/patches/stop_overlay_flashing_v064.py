#!/usr/bin/env python3
"""FocoQuiz 0.6.4: stop the accessibility overlay from dismissing itself."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
pkgdir = root / 'app/src/main/java/com/focoquiz/app'
service = pkgdir / 'BlockAccessibilityService.kt'
gradle = root / 'app/build.gradle.kts'

s = service.read_text(encoding='utf-8')
old = '''        if (pkg == packageName) {
            foregroundApp = null
            hideOverlay()
            return
        }'''
new = '''        if (pkg == packageName) {
            // TYPE_ACCESSIBILITY_OVERLAY can emit our own window-state event.
            // That window is NOT the FocoQuiz Activity. Dismissing here would
            // remove the quiz; the next app event would show it again (flashing).
            if (ForegroundWindowEvents.isOverlayWindow(
                    packageName, pkg, event.className?.toString(),
                    overlay != null)) return
            foregroundApp = null
            hideOverlay()
            return
        }'''
if old not in s:
    raise SystemExit('FocoQuiz v0.6.4: expected own-package event handler missing')
s = s.replace(old, new, 1)
service.write_text(s, encoding='utf-8')

# Keep this helper Android-free so the important regression can be tested on JVM.
helper = pkgdir / 'ForegroundWindowEvents.kt'
helper.write_text('''package com.focoquiz.app

/** Distinguishes the actual app Activity from an accessibility overlay window. */
internal object ForegroundWindowEvents {
    private val ownScreens = setOf(
        "MainActivity", "QuizSettingsActivity", "StudyPlanEditorActivity",
        "StudyGateActivity", "ExerciseChallengeActivity", "RoutineEditorActivity"
    )
    fun isOverlayWindow(
        ownPackage: String, eventPackage: String?,
        eventClass: String?, overlayVisible: Boolean
    ): Boolean {
        if (!overlayVisible || eventPackage != ownPackage) return false
        // Only actual Activity transitions should dismiss an existing overlay.
        // Android widget classes are frequently reported for window changes.
        return eventClass !in ownScreens.map { "$ownPackage.$it" }
    }
}
''', encoding='utf-8')

build = gradle.read_text(encoding='utf-8')
if 'versionName = "0.6.3"' not in build or 'versionCode = 9' not in build:
    raise SystemExit('FocoQuiz v0.6.4: expected version 0.6.3')
build = build.replace('versionName = "0.6.3"', 'versionName = "0.6.4"')
build = build.replace('versionCode = 9', 'versionCode = 10')
gradle.write_text(build, encoding='utf-8')

tests = root / 'tests/ForegroundWindowEventsSmoke.kt'
tests.write_text('''package com.focoquiz.app

fun main() {
    val app = "com.focoquiz.app"
    // A window from the blocker itself must not hide an active questionnaire.
    check(ForegroundWindowEvents.isOverlayWindow(app, app, "android.widget.FrameLayout", true))
    check(ForegroundWindowEvents.isOverlayWindow(app, app, null, true))
    check(ForegroundWindowEvents.isOverlayWindow(app, app, "com.focoquiz.app.BlockAccessibilityService", true))
    // Opening an actual FocoQuiz screen should dismiss the overlay normally.
    check(!ForegroundWindowEvents.isOverlayWindow(app, app, "$app.MainActivity", true))
    check(!ForegroundWindowEvents.isOverlayWindow(app, app, "$app.StudyGateActivity", true))
    check(!ForegroundWindowEvents.isOverlayWindow(app, app, "$app.ExerciseChallengeActivity", true))
    // Other packages / no active overlay are not self-overlay events.
    check(!ForegroundWindowEvents.isOverlayWindow(app, "com.example.social", "android.widget.FrameLayout", true))
    check(!ForegroundWindowEvents.isOverlayWindow(app, app, "android.widget.FrameLayout", false))
    println("ForegroundWindowEvents regression tests passed")
}
''', encoding='utf-8')
print('FocoQuiz 0.6.4: fixed self-overlay dismissal, added regression checks')
