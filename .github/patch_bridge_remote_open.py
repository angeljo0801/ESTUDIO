from pathlib import Path
import sys

if len(sys.argv) != 5:
    raise SystemExit("usage: patch_bridge_remote_open.py <file_bridge.dart> <ManagerFileBridge.kt> <AndroidManifest.xml> <file_paths.xml>")

dart_path = Path(sys.argv[1])
manager_path = Path(sys.argv[2])
manifest_path = Path(sys.argv[3])
paths_xml = Path(sys.argv[4])

def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"{label} anchor not found")
    return text.replace(old, new, 1)

# ---------- Flutter UI ----------
s = dart_path.read_text()

download_anchor = """  Future<void> _download(Map<String, dynamic> item) async {
"""
if "Future<void> _openRemote(Map<String, dynamic> item)" not in s:
    open_method = """  Future<void> _openRemote(Map<String, dynamic> item) async {
    final name = (item['name'] ?? 'archivo').toString();
    setState(() => _busy = true);
    try {
      final remotePath = _joinRemotePath(_path, name);
      final uri = Uri.parse('${widget.baseUrl}/file').replace(queryParameters: {'path': remotePath});
      final raw = await _bridgeChannel.invokeMapMethod<String, dynamic>(
        'openRemote',
        {
          'url': uri.toString(),
          'token': widget.token,
          'fileName': name,
        },
      );
      if (raw == null) {
        _snack('Vista previa cancelada.');
      }
    } on PlatformException catch (e) {
      _snack('No pude abrir: ${e.message ?? e.code}');
    } catch (e) {
      _snack('No pude abrir: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

"""
    s = replace_once(s, download_anchor, open_method + download_anchor, "dart open method")

s = s.replace(
    "onTap: isDir ? () => _openDir(name) : () => _download(item),",
    "onTap: isDir ? () => _openDir(name) : () => _openRemote(item),",
)

old_list_select = """        onSelected: (value) {
          if (value == 'download' && !isDir) _download(item);
          if (value == 'delete') _deleteItem(item);
        },
        itemBuilder: (_) => [
          if (!isDir) const PopupMenuItem(value: 'download', child: Text('Descargar')),
          const PopupMenuItem(value: 'delete', child: Text('Eliminar')),
        ],"""
new_list_select = """        onSelected: (value) {
          if (value == 'open' && !isDir) _openRemote(item);
          if (value == 'download' && !isDir) _download(item);
          if (value == 'delete') _deleteItem(item);
        },
        itemBuilder: (_) => [
          if (!isDir) const PopupMenuItem(value: 'open', child: Text('Abrir')),
          if (!isDir) const PopupMenuItem(value: 'download', child: Text('Descargar')),
          const PopupMenuItem(value: 'delete', child: Text('Eliminar')),
        ],"""
if old_list_select in s:
    s = s.replace(old_list_select, new_list_select)

old_grid_select = """                  onSelected: (value) {
                    if (value == 'download' && !isDir) _download(item);
                    if (value == 'delete') _deleteItem(item);
                  },
                  itemBuilder: (_) => [
                    if (!isDir) const PopupMenuItem(value: 'download', child: Text('Descargar')),
                    const PopupMenuItem(value: 'delete', child: Text('Eliminar')),
                  ],"""
new_grid_select = """                  onSelected: (value) {
                    if (value == 'open' && !isDir) _openRemote(item);
                    if (value == 'download' && !isDir) _download(item);
                    if (value == 'delete') _deleteItem(item);
                  },
                  itemBuilder: (_) => [
                    if (!isDir) const PopupMenuItem(value: 'open', child: Text('Abrir')),
                    if (!isDir) const PopupMenuItem(value: 'download', child: Text('Descargar')),
                    const PopupMenuItem(value: 'delete', child: Text('Eliminar')),
                  ],"""
if old_grid_select in s:
    s = s.replace(old_grid_select, new_grid_select)

dart_path.write_text(s)

# ---------- Android bridge ----------
s = manager_path.read_text()
if "import androidx.core.content.FileProvider" not in s:
    s = replace_once(
        s,
        "import io.flutter.plugin.common.MethodChannel\n",
        "import io.flutter.plugin.common.MethodChannel\nimport androidx.core.content.FileProvider\nimport java.io.File\nimport java.io.FileOutputStream\n",
        "manager preview imports",
    )

switch_anchor = """"downloadRemote" -> downloadRemote(
                        call.argument<String>("url").orEmpty(),
                        call.argument<String>("token").orEmpty(),
                        call.argument<String>("fileName").orEmpty(),
                        result
                    )
"""
if '"openRemote" -> openRemote(' not in s:
    switch_new = switch_anchor + """                    "openRemote" -> openRemote(
                        call.argument<String>("url").orEmpty(),
                        call.argument<String>("token").orEmpty(),
                        call.argument<String>("fileName").orEmpty(),
                        result
                    )
"""
    s = replace_once(s, switch_anchor, switch_new, "manager openRemote switch")

pick_anchor = "    private fun pickRoot(result: MethodChannel.Result) {\n"
if "private fun openRemote(" not in s:
    open_native = r'''    private fun openRemote(
        url: String,
        token: String,
        fileName: String,
        result: MethodChannel.Result
    ) {
        val current = activity ?: run {
            result.error("FILE_BRIDGE", "No hay una actividad disponible.", null)
            return
        }
        require(url.startsWith("http://") || url.startsWith("https://")) {
            "Dirección remota inválida."
        }
        require(token.length >= 16) { "Token inválido." }
        require(fileName.isNotBlank()) { "Nombre de archivo inválido." }

        Thread {
            var connection: HttpURLConnection? = null
            var cachedFile: File? = null
            try {
                val previewDir = File(current.cacheDir, "remote_preview").apply { mkdirs() }
                val cutoff = System.currentTimeMillis() - (24L * 60L * 60L * 1000L)
                previewDir.listFiles()?.forEach { old ->
                    if (old.lastModified() < cutoff) {
                        try { old.delete() } catch (_: Exception) {}
                    }
                }

                val cleanName = fileName
                    .replace(Regex("[^A-Za-z0-9._() -]"), "_")
                    .take(160)
                    .ifBlank { "preview.bin" }
                cachedFile = File(previewDir, "${System.currentTimeMillis()}_$cleanName")

                connection = URL(url).openConnection() as HttpURLConnection
                connection.requestMethod = "GET"
                connection.connectTimeout = 15_000
                connection.readTimeout = 60_000
                connection.setRequestProperty("Authorization", "Bearer $token")
                connection.setRequestProperty("X-Local-Manager-Token", token)
                connection.setRequestProperty("Connection", "close")
                connection.connect()

                val code = connection.responseCode
                if (code !in 200..299) {
                    val body = try {
                        connection.errorStream?.bufferedReader()?.use { it.readText().take(512) }.orEmpty()
                    } catch (_: Exception) {
                        ""
                    }
                    throw IOException("HTTP $code${if (body.isBlank()) "" else ": $body"}")
                }

                connection.inputStream.buffered(64 * 1024).use { input ->
                    FileOutputStream(cachedFile).buffered(64 * 1024).use { out ->
                        input.copyTo(out, 64 * 1024)
                    }
                }

                val contentUri = FileProvider.getUriForFile(
                    current,
                    "${current.packageName}.fileprovider",
                    cachedFile
                )
                val mime = mimeTypeFor(fileName)
                val viewIntent = Intent(Intent.ACTION_VIEW).apply {
                    setDataAndType(contentUri, mime)
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                }

                current.runOnUiThread {
                    try {
                        val chooser = Intent.createChooser(viewIntent, "Abrir $fileName")
                        current.startActivity(chooser)
                        result.success(
                            mapOf(
                                "opened" to true,
                                "temporary" to true,
                                "mimeType" to mime
                            )
                        )
                    } catch (e: Exception) {
                        cachedFile?.delete()
                        result.error(
                            "FILE_BRIDGE_OPEN",
                            "No hay una aplicación compatible para abrir este archivo.",
                            null
                        )
                    }
                }
            } catch (e: Exception) {
                cachedFile?.delete()
                current.runOnUiThread {
                    result.error(
                        "FILE_BRIDGE_OPEN",
                        e.message ?: e.javaClass.simpleName,
                        null
                    )
                }
            } finally {
                connection?.disconnect()
            }
        }.start()
    }

'''
    s = replace_once(s, pick_anchor, open_native + pick_anchor, "manager openRemote function")

manager_path.write_text(s)

# ---------- FileProvider ----------
manifest = manifest_path.read_text()
if 'androidx.core.content.FileProvider' not in manifest:
    provider = '''        <provider
            android:name="androidx.core.content.FileProvider"
            android:authorities="${applicationId}.fileprovider"
            android:exported="false"
            android:grantUriPermissions="true">
            <meta-data
                android:name="android.support.FILE_PROVIDER_PATHS"
                android:resource="@xml/file_paths" />
        </provider>
'''
    marker = "    </application>"
    if marker not in manifest:
        raise RuntimeError("manifest application closing tag not found")
    manifest = manifest.replace(marker, provider + marker, 1)
manifest_path.write_text(manifest)

paths_xml.parent.mkdir(parents=True, exist_ok=True)
paths_xml.write_text('''<?xml version="1.0" encoding="utf-8"?>
<paths xmlns:android="http://schemas.android.com/apk/res/android">
    <cache-path name="remote_preview" path="remote_preview/" />
</paths>
''')

print("Remote open/preview patch applied")
