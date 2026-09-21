package com.angelapps.local_ai_manager

import android.content.ContentUris
import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import java.io.File
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.MethodChannel

object ManagerBackupStorageBridge {
    private const val CHANNEL = "com.angelapps.local_ai_manager/backups"
    private const val FOLDER = "LocalAIManager"

    fun register(context: Context, messenger: BinaryMessenger) {
        MethodChannel(messenger, CHANNEL).setMethodCallHandler { call, result ->
            try {
                when (call.method) {
                    "writeBackup" -> {
                        val name = call.argument<String>("fileName")
                            ?: "Local-AI-Manager-Backup.json"
                        val content = call.argument<String>("content") ?: ""
                        val overwrite = call.argument<Boolean>("overwrite") ?: false
                        result.success(write(context, name, content, overwrite))
                    }
                    "listBackups" -> result.success(list(context))
                    "readBackup" -> {
                        val uri = call.argument<String>("uri") ?: ""
                        result.success(read(context, uri))
                    }
                    else -> result.notImplemented()
                }
            } catch (e: Exception) {
                result.error("BACKUP_ERROR", e.message, null)
            }
        }
    }

    private fun relativePath() =
        Environment.DIRECTORY_DOWNLOADS + "/" + FOLDER + "/"

    private fun write(
        context: Context,
        fileName: String,
        content: String,
        overwrite: Boolean
    ): Map<String, Any?> {
        require(fileName.endsWith(".json"))
        if (Build.VERSION.SDK_INT >= 29) {
            val resolver = context.contentResolver
            val collection = MediaStore.Downloads.EXTERNAL_CONTENT_URI
            var uri: Uri? = null
            if (overwrite) {
                resolver.query(
                    collection,
                    arrayOf(MediaStore.Downloads._ID),
                    MediaStore.Downloads.DISPLAY_NAME + "=? AND " +
                        MediaStore.Downloads.RELATIVE_PATH + "=?",
                    arrayOf(fileName, relativePath()),
                    null
                )?.use { cursor ->
                    if (cursor.moveToFirst()) {
                        uri = ContentUris.withAppendedId(
                            collection,
                            cursor.getLong(0)
                        )
                    }
                }
            }
            if (uri == null) {
                val values = ContentValues().apply {
                    put(MediaStore.Downloads.DISPLAY_NAME, fileName)
                    put(MediaStore.Downloads.MIME_TYPE, "application/json")
                    put(MediaStore.Downloads.RELATIVE_PATH, relativePath())
                    put(MediaStore.Downloads.IS_PENDING, 1)
                }
                uri = resolver.insert(collection, values)
                    ?: error("No pude crear la copia.")
            }
            resolver.openOutputStream(uri!!, "wt")?.use {
                it.write(content.toByteArray(Charsets.UTF_8))
            } ?: error("No pude escribir la copia.")
            resolver.update(
                uri!!,
                ContentValues().apply {
                    put(MediaStore.Downloads.IS_PENDING, 0)
                },
                null,
                null
            )
            return mapOf("name" to fileName, "uri" to uri.toString())
        }

        val dir = File(
            Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_DOWNLOADS
            ),
            FOLDER
        )
        dir.mkdirs()
        val file = File(dir, fileName)
        if (file.exists() && !overwrite) error("La copia ya existe.")
        file.writeText(content, Charsets.UTF_8)
        return mapOf("name" to file.name, "uri" to Uri.fromFile(file).toString())
    }

    private fun list(context: Context): List<Map<String, Any?>> {
        if (Build.VERSION.SDK_INT >= 29) {
            val result = mutableListOf<Map<String, Any?>>()
            val resolver = context.contentResolver
            val collection = MediaStore.Downloads.EXTERNAL_CONTENT_URI
            resolver.query(
                collection,
                arrayOf(
                    MediaStore.Downloads._ID,
                    MediaStore.Downloads.DISPLAY_NAME,
                    MediaStore.Downloads.DATE_MODIFIED
                ),
                MediaStore.Downloads.RELATIVE_PATH + "=?",
                arrayOf(relativePath()),
                MediaStore.Downloads.DATE_MODIFIED + " DESC"
            )?.use { cursor ->
                val idCol =
                    cursor.getColumnIndexOrThrow(MediaStore.Downloads._ID)
                val nameCol =
                    cursor.getColumnIndexOrThrow(MediaStore.Downloads.DISPLAY_NAME)
                val dateCol =
                    cursor.getColumnIndexOrThrow(MediaStore.Downloads.DATE_MODIFIED)
                while (cursor.moveToNext()) {
                    val name = cursor.getString(nameCol) ?: continue
                    if (!name.endsWith(".json")) continue
                    val uri = ContentUris.withAppendedId(
                        collection,
                        cursor.getLong(idCol)
                    )
                    result.add(
                        mapOf(
                            "name" to name,
                            "uri" to uri.toString(),
                            "modifiedMs" to cursor.getLong(dateCol) * 1000L
                        )
                    )
                }
            }
            return result
        }

        val dir = File(
            Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_DOWNLOADS
            ),
            FOLDER
        )
        return (dir.listFiles() ?: emptyArray())
            .filter { it.isFile && it.name.endsWith(".json") }
            .sortedByDescending { it.lastModified() }
            .map {
                mapOf(
                    "name" to it.name,
                    "uri" to Uri.fromFile(it).toString(),
                    "modifiedMs" to it.lastModified()
                )
            }
    }

    private fun read(context: Context, raw: String): String {
        val uri = Uri.parse(raw)
        return if (uri.scheme == "content") {
            context.contentResolver.openInputStream(uri)?.use {
                it.bufferedReader(Charsets.UTF_8).readText()
            } ?: error("No pude abrir la copia.")
        } else {
            File(uri.path ?: error("Ruta inválida.")).readText(Charsets.UTF_8)
        }
    }
}
