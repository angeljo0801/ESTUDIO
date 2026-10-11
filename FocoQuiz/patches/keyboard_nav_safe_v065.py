#!/usr/bin/env python3
"""FocoQuiz v0.6.5: respect system navigation and keyboard while blocking an app."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
p=r/'app/src/main/java/com/focoquiz/app/BlockAccessibilityService.kt'
g=r/'app/build.gradle.kts'
s=p.read_text(encoding='utf-8')

def replace(old,new):
    global s
    if old not in s:
        if new in s:
            return
        raise SystemExit('FocoQuiz 0.6.5 patch mismatch: '+old[:100])
    s=s.replace(old,new,1)

replace('import android.os.Handler\n',
        'import android.os.Handler\nimport android.os.Build\n')
replace('import android.view.WindowManager\n',
        'import android.view.WindowManager\nimport android.view.WindowInsets\nimport android.view.inputmethod.EditorInfo\nimport android.view.inputmethod.InputMethodManager\n')

replace('    private var overlay: View? = null\n',
        '    private var overlay: View? = null\n    private var overlayScroll: ScrollView? = null\n')
replace('''        val root = FrameLayout(this).apply { setBackgroundColor(Color.argb(250, 15, 23, 42)) }
        val scroll = ScrollView(this).apply { isFillViewport = true }
        root.addView(scroll)''',
'''        val root = FrameLayout(this).apply {
            setBackgroundColor(Color.argb(250, 15, 23, 42))
            // Initially take focus instead of instantly opening the keyboard.
            isFocusableInTouchMode = true
            requestFocus()
        }
        val scroll = ScrollView(this).apply {
            isFillViewport = true
            clipToPadding = false
        }
        overlayScroll = scroll
        root.addView(scroll)''')
replace('''            gravity = Gravity.CENTER_VERTICAL
            setPadding(Style.dp(this@BlockAccessibilityService, 18),''',
'''            // Always start at the top so the keyboard cannot hide the question.
            gravity = Gravity.TOP
            setPadding(Style.dp(this@BlockAccessibilityService, 18),''')
replace('''        column.addView(panel)
        val name =''',
'''        column.addView(panel)
        val goHome = Style.action(this, "◀ Ir al inicio sin desbloquear")
        goHome.setOnClickListener {
            closeKeyboard()
            foregroundApp = null
            hideOverlay()
            performGlobalAction(GLOBAL_ACTION_HOME)
        }
        panel.addView(goHome)
        Style.addSpace(panel, 12)
        val name =''')
replace('''        val params = WindowManager.LayoutParams(-1, -1,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT).apply {
            gravity = Gravity.TOP or Gravity.START
            softInputMode = WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE
            setTitle("FocoQuiz · protección voluntaria")
        }''',
'''        val params = WindowManager.LayoutParams(-1, -1,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            // Never use FLAG_LAYOUT_IN_SCREEN: it can cover Home/Back navigation.
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
            PixelFormat.TRANSLUCENT).apply {
            gravity = Gravity.TOP or Gravity.START
            softInputMode = WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE or
                WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                // Keep the blocker inside both system bars and the IME viewport.
                setFitInsetsTypes(WindowInsets.Type.systemBars() or WindowInsets.Type.ime())
            }
            setTitle("FocoQuiz · protección voluntaria")
        }''')
replace('''            answerInput = EditText(this).apply {
                hint = "Escribe tu respuesta"''',
'''            // A reachable keyboard-dismiss control, BEFORE the text input.
            val dismissKeyboard = Style.action(this, "⌄ Ocultar teclado")
            dismissKeyboard.setOnClickListener { closeKeyboard() }
            box.addView(dismissKeyboard)
            Style.addSpace(box, 8)
            answerInput = EditText(this).apply {
                hint = "Escribe tu respuesta"
                imeOptions = EditorInfo.IME_ACTION_DONE
                setOnEditorActionListener { _, actionId, _ ->
                    if (actionId == EditorInfo.IME_ACTION_DONE) {
                        closeKeyboard()
                        true
                    } else false
                }''')
replace('''        check.setOnClickListener {
            if (overlayTarget != pkg) return@setOnClickListener''',
'''        check.setOnClickListener {
            if (overlayTarget != pkg) return@setOnClickListener
            closeKeyboard()''')
replace('''    private fun hideOverlay() {
        val view = overlay''',
'''    private fun closeKeyboard() {
        val input = overlay?.findFocus()
        val manager = getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager
        val token = input?.windowToken ?: overlay?.windowToken
        if (token != null) manager.hideSoftInputFromWindow(token, 0)
        input?.clearFocus()
        overlay?.requestFocus()
    }

    private fun hideOverlay() {
        closeKeyboard()
        val view = overlay''')
replace('''        overlay = null
        overlayTarget = null''',
'''        overlay = null
        overlayScroll = null
        overlayTarget = null''')
replace('''        box.removeAllViews()
        if (index >= session.size)''',
'''        box.removeAllViews()
        overlayScroll?.post { overlayScroll?.smoothScrollTo(0, 0) }
        if (index >= session.size)''')

p.write_text(s,encoding='utf-8')
v=g.read_text(encoding='utf-8')
if 'versionName = "0.6.4"' not in v or 'versionCode = 10' not in v:
    raise SystemExit('FocoQuiz 0.6.5 expected 0.6.4 Gradle source')
g.write_text(v.replace('versionName = "0.6.4"','versionName = "0.6.5"')
             .replace('versionCode = 10','versionCode = 11'), encoding='utf-8')
assert 'FLAG_LAYOUT_IN_SCREEN,' not in s
assert 'setFitInsetsTypes(WindowInsets.Type.systemBars() or WindowInsets.Type.ime())' in s
assert '⌄ Ocultar teclado' in s
assert '◀ Ir al inicio sin desbloquear' in s
print('FocoQuiz 0.6.5: protected system navigation and keyboard controls')
