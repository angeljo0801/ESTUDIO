#!/usr/bin/env python3
"""FocoQuiz v0.6.12: searchable guide reader that opens original SAF URI directly."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
src=root/"app/src/main/java/com/focoquiz/app"
(src/"GuideViewerActivity.kt").write_text('''package com.focoquiz.app

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.Bundle
import android.os.ParcelFileDescriptor
import android.text.SpannableString
import android.text.Spanned
import android.text.style.BackgroundColorSpan
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.text.PDFTextStripper
import java.util.Locale
import java.util.concurrent.Executors
import kotlin.math.min

/** Opens SAF content:// URI in place. No imported file copies or downloads. */
class GuideViewerActivity : Activity() {
    private val executor = Executors.newSingleThreadExecutor()
    private var currentDoc: GuideLink? = null
    private var fileDescriptor: ParcelFileDescriptor? = null
    private var pdfRenderer: PdfRenderer? = null
    private var pageNumber = 0
    private var pageCount = 0
    private var textBody = ""
    private var searchMatches = emptyList<Pair<Int, String>>()
    private var currentMatch = 0
    private var workSerial = 0

    private lateinit var title: TextView
    private lateinit var status: TextView
    private lateinit var pageStatus: TextView
    private lateinit var image: ImageView
    private lateinit var text: TextView
    private lateinit var scroller: ScrollView
    private lateinit var pageNav: LinearLayout
    private lateinit var matchesBar: LinearLayout
    private lateinit var matchesLabel: TextView
    private var shownBitmap: Bitmap? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Style.bg
        val guide = GuideLinks(this).find(intent.getStringExtra("guide_id").orEmpty())
        if (guide == null) {
            Toast.makeText(this, "Esta guía ya no está en la biblioteca", Toast.LENGTH_LONG).show()
            finish()
            return
        }
        currentDoc = guide
        val rootScroll = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Style.bg)
            setPadding(Style.dp(this@GuideViewerActivity, 14),
                Style.dp(this@GuideViewerActivity, 16),
                Style.dp(this@GuideViewerActivity, 14),
                Style.dp(this@GuideViewerActivity, 14))
        }
        setContentView(rootScroll)
        val toolbar = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        toolbar.addView(Style.action(this, "← Atrás").apply {
            textSize = 15f
            setOnClickListener { finish() }
        }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        toolbar.addView(Style.action(this, "⌕ Buscar").apply {
            textSize = 15f
            setOnClickListener { askSearch() }
        }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        rootScroll.addView(toolbar)
        title = Style.label(this, guide.title, 19f, Style.text, true)
        rootScroll.addView(title)
        status = Style.label(this, "Abriendo archivo original...", 14f, Style.subtle)
        rootScroll.addView(status)

        matchesBar = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            visibility = View.GONE
        }
        matchesBar.addView(Style.action(this, "‹ Anterior").apply {
            setOnClickListener { openMatch(-1) }
        }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        matchesLabel = Style.label(this, "", 13f, Style.accent, true)
        matchesLabel.gravity = Gravity.CENTER
        matchesBar.addView(matchesLabel, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        matchesBar.addView(Style.action(this, "Siguiente ›").apply {
            setOnClickListener { openMatch(1) }
        }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        rootScroll.addView(matchesBar)

        pageNav = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            visibility = View.GONE
        }
        pageNav.addView(Style.action(this, "◀ Página").apply {
            setOnClickListener { showPage(pageNumber - 1) }
        }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        pageStatus = Style.label(this, "", 14f, Style.text, true)
        pageStatus.gravity = Gravity.CENTER
        pageNav.addView(pageStatus, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        pageNav.addView(Style.action(this, "Página ▶").apply {
            setOnClickListener { showPage(pageNumber + 1) }
        }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        rootScroll.addView(pageNav)

        scroller = ScrollView(this).apply { isFillViewport = true }
        val body = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        scroller.addView(body)
        image = ImageView(this).apply {
            adjustViewBounds = true
            scaleType = ImageView.ScaleType.FIT_CENTER
            visibility = View.GONE
            contentDescription = "Página de la guía"
        }
        body.addView(image, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        text = Style.label(this, "", 17f, Style.text)
        text.setTextIsSelectable(true)
        body.addView(text)
        rootScroll.addView(scroller, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))

        openDocument(guide)
    }

    private fun onFailure(problem: String) {
        if (isFinishing || isDestroyed) return
        status.text = problem + " Si moviste o borraste el archivo, vuelve a vincularlo desde el dashboard."
    }
    private fun isPdf(doc: GuideLink): Boolean =
        doc.mime.contains("pdf", ignoreCase = true) ||
            doc.title.endsWith(".pdf", ignoreCase = true)
    private fun isText(doc: GuideLink): Boolean =
        doc.mime.startsWith("text/") || doc.title.endsWith(".txt", true) ||
            doc.title.endsWith(".md", true) || doc.title.endsWith(".markdown", true)

    private fun openDocument(doc: GuideLink) {
        executor.execute {
            try {
                when {
                    isPdf(doc) -> {
                        val fd = contentResolver.openFileDescriptor(doc.uri, "r")
                            ?: throw IllegalArgumentException("El archivo ya no está disponible")
                        val renderer = PdfRenderer(fd)
                        fileDescriptor = fd
                        pdfRenderer = renderer
                        pageCount = renderer.pageCount
                        runOnUiThread {
                            if (!isFinishing && !isDestroyed) {
                                pageNav.visibility = View.VISIBLE
                                status.text = "PDF original · " + pageCount + " páginas · lectura sin copias"
                                showPage(0)
                            }
                        }
                    }
                    isText(doc) -> {
                        // Cap large guides for UI safety; never copy to internal storage.
                        val bytes = contentResolver.openInputStream(doc.uri)?.use {
                            it.readNBytes(4 * 1024 * 1024 + 1)
                        } ?: throw IllegalArgumentException("No se puede abrir este archivo")
                        if (bytes.size > 4 * 1024 * 1024)
                            throw IllegalArgumentException("Este texto supera 4 MB; usa un PDF")
                        val loaded = bytes.toString(Charsets.UTF_8)
                        runOnUiThread {
                            if (!isFinishing && !isDestroyed) {
                                textBody = loaded
                                text.text = loaded
                                text.visibility = View.VISIBLE
                                image.visibility = View.GONE
                                status.text = "Texto original · búsqueda disponible · sin copias"
                            }
                        }
                    }
                    doc.mime.startsWith("image/") ||
                        doc.title.matches(Regex(".*\\\\.(png|jpe?g|webp)$",
                            RegexOption.IGNORE_CASE)) -> {
                        val opts = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                        contentResolver.openInputStream(doc.uri)?.use {
                            BitmapFactory.decodeStream(it, null, opts)
                        }
                        val maxSize = maxOf(opts.outHeight, opts.outWidth)
                        var scale = 1
                        while (maxSize / scale > 1700) scale *= 2
                        val decodeOpts = BitmapFactory.Options().apply { inSampleSize = scale }
                        val bitmap = contentResolver.openInputStream(doc.uri)?.use {
                            BitmapFactory.decodeStream(it, null, decodeOpts)
                        } ?: throw IllegalArgumentException("No se pudo abrir la imagen")
                        runOnUiThread {
                            if (!isFinishing && !isDestroyed) {
                                shownBitmap = bitmap
                                image.setImageBitmap(bitmap)
                                image.visibility = View.VISIBLE
                                text.visibility = View.GONE
                                status.text = "Imagen original · sin texto buscable (necesita OCR)"
                            } else bitmap.recycle()
                        }
                    }
                    else -> {
                        runOnUiThread {
                            if (!isFinishing && !isDestroyed) {
                                status.text = "Para este formato, utiliza el visor de documentos del móvil."
                                val open = Style.action(this, "Abrir en otra aplicación")
                                (scroller.getChildAt(0) as LinearLayout).addView(open)
                                open.setOnClickListener {
                                    try {
                                        startActivity(Intent(Intent.ACTION_VIEW).apply {
                                            setDataAndType(doc.uri, doc.mime)
                                            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                                        })
                                    } catch (_: Exception) {
                                        Toast.makeText(this, "No hay aplicación para abrir este formato", Toast.LENGTH_LONG).show()
                                    }
                                }
                            }
                        }
                    }
                }
            } catch (e: Exception) {
                runOnUiThread { onFailure("Error al leer la guía: " + (e.message ?: "permiso expirado")) }
            }
        }
    }

    private fun showPage(index: Int) {
        if (index !in 0 until pageCount) return
        pageNumber = index
        pageStatus.text = "" + (index + 1) + " / " + pageCount
        status.text = "Cargando página " + (index + 1) + "..."
        val serial = ++workSerial
        executor.execute {
            try {
                val renderer = pdfRenderer ?: return@execute
                val page = renderer.openPage(index)
                val bitmap = try {
                    val targetWidth = min(1200, maxOf(650, resources.displayMetrics.widthPixels * 2))
                    val width = targetWidth
                    val height = min(2700, maxOf(1, (width.toLong() * page.height / page.width).toInt()))
                    Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888).apply {
                        eraseColor(Color.WHITE)
                        page.render(this, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    }
                } finally { page.close() }
                runOnUiThread {
                    if (serial != workSerial || isFinishing || isDestroyed) {
                        bitmap.recycle()
                    } else {
                        val old = shownBitmap
                        shownBitmap = bitmap
                        image.setImageBitmap(bitmap)
                        image.visibility = View.VISIBLE
                        text.visibility = View.GONE
                        scroller.scrollTo(0, 0)
                        status.text = "PDF original · página " + (index + 1) + " de " + pageCount
                        // Release previous bitmap after ImageView no longer displays it.
                        if (old !== bitmap) old?.recycle()
                    }
                }
            } catch (e: Exception) {
                runOnUiThread { onFailure("No se pudo mostrar la página: " + e.message) }
            }
        }
    }

    private fun askSearch() {
        val doc = currentDoc ?: return
        if (!isPdf(doc) && !isText(doc)) {
            Toast.makeText(this, "La búsqueda está disponible en PDF con texto y TXT/MD", Toast.LENGTH_LONG).show()
            return
        }
        val field = EditText(this).apply {
            hint = "Palabra o frase"
            textSize = 18f
            setSingleLine(true)
        }
        AlertDialog.Builder(this).setTitle("⌕ Buscar en la guía")
            .setView(field)
            .setNegativeButton("Cancelar", null)
            .setPositiveButton("Buscar") { _, _ ->
                val query = field.text.toString().trim()
                if (query.isNotEmpty()) search(doc, query)
            }.show()
    }

    private fun search(doc: GuideLink, term: String) {
        searchMatches = emptyList()
        currentMatch = 0
        matchesBar.visibility = View.GONE
        if (isText(doc)) {
            val match = textBody.indexOf(term, ignoreCase = true)
            if (match < 0) {
                status.text = "No se encontró: " + term
            } else {
                val highlighted = SpannableString(textBody)
                highlighted.setSpan(BackgroundColorSpan(Color.rgb(180, 135, 40)),
                    match, match + term.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                text.text = highlighted
                status.text = "Encontrado: " + term
                text.post {
                    val layout = text.layout ?: return@post
                    val y = layout.getLineTop(layout.getLineForOffset(match))
                    scroller.scrollTo(0, y)
                }
            }
            return
        }
        status.text = "Buscando texto en el PDF... (sin OCR para páginas escaneadas)"
        val serial = ++workSerial
        executor.execute {
            try {
                PDFBoxResourceLoader.init(applicationContext)
                val found = mutableListOf<Pair<Int, String>>()
                contentResolver.openInputStream(doc.uri)?.use { stream ->
                    PDDocument.load(stream).use { pdf ->
                        val stripper = PDFTextStripper()
                        val count = pdf.numberOfPages
                        for (page in 1..count) {
                            stripper.startPage = page
                            stripper.endPage = page
                            val pageText = stripper.getText(pdf)
                            val at = pageText.indexOf(term, ignoreCase = true)
                            if (at >= 0) {
                                val start = (at - 42).coerceAtLeast(0)
                                val end = (at + term.length + 65).coerceAtMost(pageText.length)
                                found.add((page-1) to pageText.substring(start, end)
                                    .replace(Regex("\\\\s+"), " ").trim())
                                if (found.size == 150) break
                            }
                        }
                    }
                } ?: throw IllegalArgumentException("No se puede leer el PDF original")
                runOnUiThread {
                    if (isFinishing || isDestroyed || serial != workSerial) return@runOnUiThread
                    searchMatches = found
                    if (found.isEmpty()) {
                        status.text = "Sin resultados. Un PDF escaneado necesita OCR para buscar texto."
                    } else {
                        matchesBar.visibility = View.VISIBLE
                        currentMatch = 0
                        jumpToMatch()
                    }
                }
            } catch (error: Exception) {
                runOnUiThread {
                    onFailure("No se pudo buscar: " + (error.message ?: "PDF incompatible"))
                }
            }
        }
    }

    private fun openMatch(delta: Int) {
        if (searchMatches.isEmpty()) return
        currentMatch = (currentMatch + delta + searchMatches.size) % searchMatches.size
        jumpToMatch()
    }
    private fun jumpToMatch() {
        val found = searchMatches.getOrNull(currentMatch) ?: return
        matchesLabel.text = (currentMatch + 1).toString() + " / " + searchMatches.size
        showPage(found.first)
        status.text = "Coincidencia: " + found.second
    }

    override fun onDestroy() {
        ++workSerial
        executor.execute {
            try { pdfRenderer?.close() } catch (_: Exception) { }
            try { fileDescriptor?.close() } catch (_: Exception) { }
        }
        executor.shutdown()
        shownBitmap?.let {
            if (::image.isInitialized) image.setImageDrawable(null)
            if (!it.isRecycled) it.recycle()
        }
        super.onDestroy()
    }
}
''',encoding="utf-8")
gradle=root/"app/build.gradle.kts"
s=gradle.read_text(encoding="utf-8")
needle='''dependencies {
'''
if needle not in s:raise RuntimeError("No dependencies declaration")
s=s.replace(needle,'''dependencies {
    // Text extraction/search from PDFs; original document stays in its provider.
    implementation("com.tom-roush:pdfbox-android:2.0.27.0")
''',1)
if 'versionName = "0.6.11"' not in s or 'versionCode = 17' not in s:
    raise RuntimeError("Expected FocoQuiz v0.6.11 base")
s=s.replace('versionName = "0.6.11"','versionName = "0.6.12"')
s=s.replace('versionCode = 17','versionCode = 18')
gradle.write_text(s,encoding="utf-8")
print("0.6.12: PDF and text readers, in-document search, backward navigation, no guide copies")
