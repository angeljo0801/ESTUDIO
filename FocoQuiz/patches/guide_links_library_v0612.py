#!/usr/bin/env python3
"""FocoQuiz 0.6.12: reference-only guide library using Android SAF persisted URIs."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
src=root/"app/src/main/java/com/focoquiz/app"
(src/"GuideLinks.kt").write_text('''package com.focoquiz.app

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.OpenableColumns
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

/** These are ONLY persisted content:// references; guide bytes are never copied. */
internal data class GuideLink(val id: String, val title: String, val mime: String, val uri: Uri)

internal class GuideLinks(context: Context) {
    private val app = context.applicationContext
    private val prefs = app.getSharedPreferences("focoquiz_guide_references", Context.MODE_PRIVATE)

    fun list(): List<GuideLink> = try {
        val items = JSONArray(prefs.getString("items", "[]"))
        (0 until items.length()).mapNotNull { i ->
            val o = items.optJSONObject(i) ?: return@mapNotNull null
            val id = o.optString("id")
            val address = o.optString("uri")
            if (id.isBlank() || !address.startsWith("content://")) null
            else GuideLink(id, o.optString("title").take(180), o.optString("mime"),
                Uri.parse(address))
        }
    } catch (_: Exception) { emptyList() }

    private fun store(items: List<GuideLink>) {
        val arr = JSONArray()
        items.forEach {
            arr.put(JSONObject().put("id", it.id).put("title", it.title)
                .put("mime", it.mime).put("uri", it.uri.toString()))
        }
        prefs.edit().putString("items", arr.toString()).apply()
    }

    fun add(uri: Uri, name: String, mime: String): Boolean {
        if (!ConfigurationHours(app).canEdit()) return false
        if (uri.scheme != "content") return false
        val current = list()
        if (current.any { it.uri == uri }) return true
        if (current.size >= 120) return false
        // ACTION_OPEN_DOCUMENT grants a read URI permission, persist it across restarts.
        app.contentResolver.takePersistableUriPermission(
            uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
        store(current + GuideLink(UUID.randomUUID().toString(),
            name.take(180).ifBlank { "Guía sin nombre" }, mime.take(120), uri))
        return true
    }

    fun remove(id: String): Boolean {
        if (!ConfigurationHours(app).canEdit()) return false
        val guides = list()
        val guide = guides.firstOrNull { it.id == id } ?: return false
        store(guides.filterNot { it.id == id })
        try {
            app.contentResolver.releasePersistableUriPermission(
                guide.uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
        } catch (_: SecurityException) { }
        // Remove stale pack selections referencing this library entry.
        prefs.all.keys.filter { it.startsWith("pack_") && prefs.getString(it, "") == id }
            .forEach { prefs.edit().remove(it).apply() }
        return true
    }

    fun find(id: String) = list().firstOrNull { it.id == id }
    fun selectForExam(packId: String, guideId: String) {
        if (packId.length in 1..120 && guideId.length <= 120 &&
            list().any { it.id == guideId })
            prefs.edit().putString("pack_" + packId, guideId).apply()
    }
    fun selectedForExam(packId: String) =
        prefs.getString("pack_" + packId, "")?.takeIf { it.isNotBlank() }

    fun name(uri: Uri): String {
        val cursor = app.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME),
            null, null, null)
        return cursor?.use {
            if (it.moveToFirst()) it.getString(0) else null
        }?.take(180) ?: uri.lastPathSegment.orEmpty().takeLast(100).ifBlank { "Guía" }
    }
}
''',encoding="utf-8")

(src/"GuideLibraryActivity.kt").write_text('''package com.focoquiz.app

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Toast

/** Manage original document LINKS from the main dashboard. No file copies. */
class GuideLibraryActivity : Activity() {
    private val library by lazy { GuideLinks(this) }
    private lateinit var items: LinearLayout
    private val pickRequest = 6112

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Style.bg
        val scroll = ScrollView(this).apply { setBackgroundColor(Style.bg) }
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(Style.dp(this@GuideLibraryActivity, 18),
                Style.dp(this@GuideLibraryActivity, 22),
                Style.dp(this@GuideLibraryActivity, 18),
                Style.dp(this@GuideLibraryActivity, 28))
        }
        scroll.addView(column)
        setContentView(scroll)
        column.addView(Style.action(this, "← Volver al dashboard").apply {
            setOnClickListener { finish() }
        })
        Style.addSpace(column, 12)
        column.addView(Style.label(this, "Biblioteca de guías", 25f, Style.text, true))
        column.addView(Style.label(this,
            "Esta biblioteca guarda enlaces a los archivos de tu teléfono. " +
                "No se hace ninguna copia y no consume espacio por los documentos.", 16f, Style.subtle))
        Style.addSpace(column, 15)
        column.addView(Style.action(this, "＋ Seleccionar guía del teléfono").apply {
            setOnClickListener {
                if (!ConfigurationHours(this@GuideLibraryActivity).canEdit()) {
                    Toast.makeText(this@GuideLibraryActivity, "Solo puedes añadir guías durante el horario de configuración", Toast.LENGTH_LONG).show()
                } else {
                    val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                        addCategory(Intent.CATEGORY_OPENABLE)
                        type = "*/*"
                        putExtra(Intent.EXTRA_MIME_TYPES, arrayOf(
                            "application/pdf", "text/plain", "text/markdown",
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "application/msword", "image/jpeg", "image/png", "image/webp"))
                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or
                            Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
                    }
                    startActivityForResult(intent, pickRequest)
                }
            }
        })
        Style.addSpace(column, 15)
        items = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        column.addView(items)
        render()
    }

    override fun onResume() { super.onResume(); if (::items.isInitialized) render() }

    private fun render() {
        items.removeAllViews()
        val docs = library.list()
        if (docs.isEmpty()) {
            items.addView(Style.label(this, "No hay guías vinculadas todavía.", 17f, Style.subtle))
        }
        docs.forEach { doc ->
            val card = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                background = Style.shape(Style.panel, 14, this@GuideLibraryActivity)
                setPadding(Style.dp(this@GuideLibraryActivity, 12),
                    Style.dp(this@GuideLibraryActivity, 12),
                    Style.dp(this@GuideLibraryActivity, 12),
                    Style.dp(this@GuideLibraryActivity, 12))
            }
            card.addView(Style.label(this, "📄 " + doc.title, 18f, Style.text, true))
            card.addView(Style.label(this, "Archivo original · enlace guardado", 13f, Style.subtle))
            card.addView(Style.action(this, "Abrir guía").apply {
                setOnClickListener {
                    startActivity(Intent(this@GuideLibraryActivity,
                        GuideViewerActivity::class.java).putExtra("guide_id", doc.id))
                }
            })
            card.addView(Style.action(this, "Quitar de biblioteca").apply {
                isEnabled = ConfigurationHours(this@GuideLibraryActivity).canEdit()
                setOnClickListener {
                    if (!ConfigurationHours(this@GuideLibraryActivity).canEdit()) {
                        Toast.makeText(this@GuideLibraryActivity, "Fuera del horario permitido", Toast.LENGTH_SHORT).show()
                        return@setOnClickListener
                    }
                    AlertDialog.Builder(this@GuideLibraryActivity)
                        .setTitle("Quitar enlace")
                        .setMessage("Se quitará de FocoQuiz, pero NO se borrará el documento del teléfono.")
                        .setNegativeButton("Cancelar", null)
                        .setPositiveButton("Quitar") { _, _ ->
                            library.remove(doc.id)
                            render()
                        }.show()
                }
            })
            items.addView(card, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
            Style.addSpace(items, 10)
        }
    }

    @Deprecated("Legacy Activity result API for minSdk 26")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != pickRequest || resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        try {
            val ok = library.add(uri, library.name(uri),
                contentResolver.getType(uri) ?: "application/octet-stream")
            if (!ok) throw IllegalStateException("Horario cerrado o biblioteca llena")
            Toast.makeText(this, "Enlace a la guía guardado", Toast.LENGTH_SHORT).show()
        } catch (error: Exception) {
            AlertDialog.Builder(this).setTitle("No se pudo añadir la guía")
                .setMessage("El proveedor del archivo debe permitir el acceso permanente. " +
                    "Selecciona el documento desde Archivos. Detalle: " + error.message)
                .setPositiveButton("Entendido", null).show()
        }
        render()
    }
}
''',encoding="utf-8")

(src/"GuidePickerActivity.kt").write_text('''package com.focoquiz.app

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.ScrollView

/** Read-only guide selection inside a quiz; cannot modify the library. */
class GuidePickerActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Style.bg
        val packId = intent.getStringExtra("exam_pack").orEmpty()
        val store = GuideLinks(this)
        val scroll = ScrollView(this).apply { setBackgroundColor(Style.bg) }
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(Style.dp(this@GuidePickerActivity, 18),
                Style.dp(this@GuidePickerActivity, 20),
                Style.dp(this@GuidePickerActivity, 18),
                Style.dp(this@GuidePickerActivity, 28))
        }
        scroll.addView(root)
        setContentView(scroll)
        root.addView(Style.action(this, "← Volver a la pregunta").apply {
            setOnClickListener { finish() }
        })
        Style.addSpace(root, 10)
        root.addView(Style.label(this, "📖 Elegir guía del examen", 24f, Style.text, true))
        root.addView(Style.label(this,
            "Selecciona un documento vinculado desde el dashboard. " +
                "No es necesario salir del quiz para volver a consultarlo.", 15f, Style.subtle))
        Style.addSpace(root, 12)
        val selected = store.selectedForExam(packId)
        val docs = store.list().sortedWith(
            compareByDescending<GuideLink> { it.id == selected }.thenBy { it.title })
        if (docs.isEmpty()) {
            root.addView(Style.label(this,
                "La biblioteca está vacía. Vuelve al dashboard durante tu horario " +
                    "de configuración y selecciona una guía del teléfono.", 17f, Style.text))
        }
        docs.forEach { doc ->
            root.addView(Style.action(this,
                (if (doc.id == selected) "✓ " else "📄 ") + doc.title).apply {
                setOnClickListener {
                    if (packId.isNotBlank()) store.selectForExam(packId, doc.id)
                    startActivity(Intent(this@GuidePickerActivity,
                        GuideViewerActivity::class.java).putExtra("guide_id", doc.id))
                    // Back from the viewer returns directly to the paused quiz.
                    finish()
                }
            })
            Style.addSpace(root, 8)
        }
    }
}

internal object QuizGuideButton {
    fun attach(context: android.content.Context, parent: LinearLayout, packId: String,
               beforeOpen: (() -> Unit)? = null) {
        val bar = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = android.view.Gravity.START
        }
        val button = Style.action(context, "📖 Guía").apply {
            textSize = 15f
            minHeight = Style.dp(context, 44)
            setOnClickListener {
                beforeOpen?.invoke()
                val intent = Intent(context, GuidePickerActivity::class.java)
                    .putExtra("exam_pack", packId)
                if (context !is Activity) intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
            }
        }
        bar.addView(button, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        parent.addView(bar)
        Style.addSpace(parent, 5)
    }
}
''',encoding="utf-8")

manifest=root/"app/src/main/AndroidManifest.xml"
s=manifest.read_text(encoding="utf-8")
anchor='''        <activity android:name=".StudyPlanEditorActivity" android:exported="false" />'''
if anchor not in s:raise RuntimeError("Missing manifest activity anchor")
s=s.replace(anchor,'''        <activity android:name=".GuideLibraryActivity" android:exported="false" />
        <activity android:name=".GuidePickerActivity" android:exported="false" />
        <activity android:name=".GuideViewerActivity" android:exported="false" />
'''+anchor,1)
manifest.write_text(s,encoding="utf-8")

main=src/"MainActivity.kt"
s=main.read_text(encoding="utf-8")
anchor='''        root.addView(configScheduleCard())'''
if anchor not in s:raise RuntimeError("Missing configuration schedule card")
s=s.replace(anchor,'''        val guidesCard = card()
        guidesCard.addView(Style.label(this, "📖 Biblioteca de guías", 21f, Style.text, true))
        guidesCard.addView(Style.label(this,
            "Selecciona documentos originales del teléfono. Se guardan únicamente " +
                "enlaces, no copias. Abre las guías desde la esquina izquierda del quiz.",
            15f, Style.subtle))
        val guideCount = GuideLinks(this).list().size
        guidesCard.addView(Style.action(this,
            "Seleccionar y administrar guías (" + guideCount + ")").apply {
            setOnClickListener {
                startActivity(Intent(this@MainActivity, GuideLibraryActivity::class.java))
            }
        })
        root.addView(guidesCard)
        Style.addSpace(root, 14)
'''+anchor,1)
main.write_text(s,encoding="utf-8")
print("0.6.12: SAF reference-only guide library, main dashboard entry and in-quiz selector")
