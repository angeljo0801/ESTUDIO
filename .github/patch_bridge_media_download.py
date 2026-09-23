from pathlib import Path
import re
import sys

if len(sys.argv) != 4:
    raise SystemExit('usage: patch_bridge_media_download.py <file_bridge.dart> <ManagerFileBridge.kt> <FileBridgeService.kt>')

dart_path = Path(sys.argv[1])
manager_path = Path(sys.argv[2])
service_path = Path(sys.argv[3])

def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f'{label} anchor not found')
    return text.replace(old, new, 1)

s = dart_path.read_text()
s = s.replace("import 'package:path_provider/path_provider.dart';\n", "")
s = replace_once(
    s,
    "  bool _busy = false;\n  List<Map<String, dynamic>> _items = const [];",
    "  bool _busy = false;\n  bool _gridView = false;\n  List<Map<String, dynamic>> _items = const [];",
    'dart browser fields',
)

download_pattern = re.compile(
    r"  Future<void> _download\(Map<String, dynamic> item\) async \{.*?\n  \}\n\n  Future<void> _createFolder",
    re.S,
)
new_download = """  Future<void> _download(Map<String, dynamic> item) async {
    final name = (item['name'] ?? 'archivo').toString();
    setState(() => _busy = true);
    try {
      final remotePath = _joinRemotePath(_path, name);
      final uri = Uri.parse('${widget.baseUrl}/file').replace(queryParameters: {'path': remotePath});
      final raw = await _bridgeChannel.invokeMapMethod<String, dynamic>(
        'downloadRemote',
        {
          'url': uri.toString(),
          'token': widget.token,
          'fileName': name,
        },
      );
      if (raw != null) {
        _snack('Archivo guardado.');
      }
    } on PlatformException catch (e) {
      _snack('No pude descargar: ${e.message ?? e.code}');
    } catch (e) {
      _snack('No pude descargar: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _createFolder"""
s, count = download_pattern.subn(new_download, s, count=1)
if count != 1:
    raise RuntimeError('dart download anchor not found')

insert_after_size = """  String _sizeText(dynamic value) {
    final bytes = value is num ? value.toInt() : 0;
    if (bytes <= 0) return '';
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) return '${(bytes / 1024 / 1024).toStringAsFixed(1)} MB';
    return '${(bytes / 1024 / 1024 / 1024).toStringAsFixed(1)} GB';
  }
"""
helpers = insert_after_size + r"""

  String _extension(String name) {
    final dot = name.lastIndexOf('.');
    if (dot < 0 || dot == name.length - 1) return '';
    return name.substring(dot + 1).toLowerCase();
  }

  bool _hasRemoteThumbnail(String name) {
    const exts = {
      'jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'heic', 'heif',
      'mp4', 'mkv', 'mov', 'avi', 'webm', 'm4v', '3gp',
      'apk',
    };
    return exts.contains(_extension(name));
  }

  IconData _fileIcon(String name) {
    final ext = _extension(name);
    if (const {'jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'heic', 'heif'}.contains(ext)) {
      return Icons.image_outlined;
    }
    if (const {'mp4', 'mkv', 'mov', 'avi', 'webm', 'm4v', '3gp'}.contains(ext)) {
      return Icons.video_file_outlined;
    }
    if (const {'mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg', 'opus'}.contains(ext)) {
      return Icons.audio_file_outlined;
    }
    if (ext == 'pdf') return Icons.picture_as_pdf_outlined;
    if (const {'zip', 'rar', '7z', 'tar', 'gz'}.contains(ext)) return Icons.archive_outlined;
    if (const {'doc', 'docx', 'odt', 'rtf'}.contains(ext)) return Icons.description_outlined;
    if (const {'xls', 'xlsx', 'csv', 'ods'}.contains(ext)) return Icons.table_chart_outlined;
    if (const {'ppt', 'pptx', 'odp'}.contains(ext)) return Icons.slideshow_outlined;
    if (const {'txt', 'md', 'json', 'xml', 'yaml', 'yml', 'log'}.contains(ext)) return Icons.text_snippet_outlined;
    if (ext == 'apk') return Icons.android;
    return Icons.insert_drive_file_outlined;
  }

  Widget _fileVisual(Map<String, dynamic> item, {double size = 48}) {
    final isDir = item['isDir'] == true;
    final name = (item['name'] ?? '').toString();
    if (isDir) {
      return SizedBox.square(
        dimension: size,
        child: Icon(Icons.folder, size: size * 0.78),
      );
    }

    Widget fallback() => SizedBox.square(
          dimension: size,
          child: Icon(_fileIcon(name), size: size * 0.72),
        );

    if (!_hasRemoteThumbnail(name)) return fallback();

    final remotePath = _joinRemotePath(_path, name);
    final uri = Uri.parse('${widget.baseUrl}/thumbnail').replace(
      queryParameters: {
        'path': remotePath,
        'size': (size * 3).round().clamp(96, 512).toString(),
      },
    );
    final isVideo = const {'mp4', 'mkv', 'mov', 'avi', 'webm', 'm4v', '3gp'}.contains(_extension(name));

    final image = Image.network(
      uri.toString(),
      width: size,
      height: size,
      fit: BoxFit.cover,
      headers: {
        HttpHeaders.authorizationHeader: 'Bearer ${widget.token}',
        'X-Local-Manager-Token': widget.token,
      },
      errorBuilder: (_, __, ___) => fallback(),
    );

    return ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: SizedBox.square(
        dimension: size,
        child: Stack(
          fit: StackFit.expand,
          children: [
            image,
            if (isVideo)
              const Center(
                child: Icon(Icons.play_circle_fill, size: 26),
              ),
          ],
        ),
      ),
    );
  }

  Widget _listItem(Map<String, dynamic> item) {
    final isDir = item['isDir'] == true;
    final name = (item['name'] ?? '').toString();
    return ListTile(
      leading: _fileVisual(item),
      title: Text(name),
      subtitle: isDir ? null : Text(_sizeText(item['size'])),
      onTap: isDir ? () => _openDir(name) : () => _download(item),
      trailing: PopupMenuButton<String>(
        onSelected: (value) {
          if (value == 'download' && !isDir) _download(item);
          if (value == 'delete') _deleteItem(item);
        },
        itemBuilder: (_) => [
          if (!isDir) const PopupMenuItem(value: 'download', child: Text('Descargar')),
          const PopupMenuItem(value: 'delete', child: Text('Eliminar')),
        ],
      ),
    );
  }

  Widget _gridItem(Map<String, dynamic> item) {
    final isDir = item['isDir'] == true;
    final name = (item['name'] ?? '').toString();
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: isDir ? () => _openDir(name) : () => _download(item),
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: Center(child: _fileVisual(item, size: 96)),
              ),
              const SizedBox(height: 8),
              Text(
                name,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
              ),
              if (!isDir)
                Text(
                  _sizeText(item['size']),
                  maxLines: 1,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              Align(
                alignment: Alignment.centerRight,
                child: PopupMenuButton<String>(
                  padding: EdgeInsets.zero,
                  onSelected: (value) {
                    if (value == 'download' && !isDir) _download(item);
                    if (value == 'delete') _deleteItem(item);
                  },
                  itemBuilder: (_) => [
                    if (!isDir) const PopupMenuItem(value: 'download', child: Text('Descargar')),
                    const PopupMenuItem(value: 'delete', child: Text('Eliminar')),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
"""
s = replace_once(s, insert_after_size, helpers, 'dart helpers')

old_actions = """          actions: [
            IconButton(onPressed: _busy ? null : _createFolder, icon: const Icon(Icons.create_new_folder_outlined)),
            IconButton(onPressed: _busy ? null : _upload, icon: const Icon(Icons.upload_file)),
            IconButton(onPressed: _busy ? null : _reload, icon: const Icon(Icons.refresh)),
          ],"""
new_actions = """          actions: [
            IconButton(
              tooltip: _gridView ? 'Vista de lista' : 'Vista de cuadrícula',
              onPressed: () => setState(() => _gridView = !_gridView),
              icon: Icon(_gridView ? Icons.view_list_outlined : Icons.grid_view_outlined),
            ),
            IconButton(onPressed: _busy ? null : _createFolder, icon: const Icon(Icons.create_new_folder_outlined)),
            IconButton(onPressed: _busy ? null : _upload, icon: const Icon(Icons.upload_file)),
            IconButton(onPressed: _busy ? null : _reload, icon: const Icon(Icons.refresh)),
          ],"""
s = replace_once(s, old_actions, new_actions, 'dart appbar actions')

old_list = """                : _items.isEmpty
                    ? const Center(child: Text('Carpeta vacía'))
                    : ListView.builder(
                        itemCount: _items.length,
                        itemBuilder: (context, index) {
                          final item = _items[index];
                          final isDir = item['isDir'] == true;
                          final name = (item['name'] ?? '').toString();
                          return ListTile(
                            leading: Icon(isDir ? Icons.folder : Icons.insert_drive_file_outlined),
                            title: Text(name),
                            subtitle: isDir ? null : Text(_sizeText(item['size'])),
                            onTap: isDir ? () => _openDir(name) : () => _download(item),
                            trailing: PopupMenuButton<String>(
                              onSelected: (value) {
                                if (value == 'download' && !isDir) _download(item);
                                if (value == 'delete') _deleteItem(item);
                              },
                              itemBuilder: (_) => [
                                if (!isDir) const PopupMenuItem(value: 'download', child: Text('Descargar')),
                                const PopupMenuItem(value: 'delete', child: Text('Eliminar')),
                              ],
                            ),
                          );
                        },
                      ),"""
new_list = """                : _items.isEmpty
                    ? const Center(child: Text('Carpeta vacía'))
                    : _gridView
                        ? GridView.builder(
                            padding: const EdgeInsets.all(8),
                            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                              crossAxisCount: 3,
                              mainAxisSpacing: 8,
                              crossAxisSpacing: 8,
                              childAspectRatio: 0.72,
                            ),
                            itemCount: _items.length,
                            itemBuilder: (context, index) => _gridItem(_items[index]),
                          )
                        : ListView.builder(
                            itemCount: _items.length,
                            itemBuilder: (context, index) => _listItem(_items[index]),
                          ),"""
s = replace_once(s, old_list, new_list, 'dart list/grid body')
dart_path.write_text(s)

s = manager_path.read_text()
anchor = 'import io.flutter.plugin.common.MethodChannel\n'
if 'import java.net.HttpURLConnection' not in s:
    s = replace_once(
        s,
        anchor,
        anchor + 'import java.io.IOException\nimport java.net.HttpURLConnection\nimport java.net.URL\n',
        'manager imports',
    )

s = replace_once(
    s,
    '    private const val REQUEST_STORAGE = 6414\n',
    '    private const val REQUEST_STORAGE = 6414\n    private const val REQUEST_SAVE_REMOTE = 6415\n',
    'manager request code',
)

s = replace_once(
    s,
    '    private var activity: Activity? = null\n    private var pendingPick: MethodChannel.Result? = null\n',
    '''    private var activity: Activity? = null
    private var pendingPick: MethodChannel.Result? = null
    private var pendingDownload: PendingDownload? = null

    private data class PendingDownload(
        val url: String,
        val token: String,
        val fileName: String,
        val result: MethodChannel.Result
    )
''',
    'manager pending fields',
)

s = replace_once(
    s,
    '''                    "requestAllFilesAccess" -> {
                        requestAllFilesAccess()
                        result.success(true)
                    }
                    "startHost" -> {''',
    '''                    "requestAllFilesAccess" -> {
                        requestAllFilesAccess()
                        result.success(true)
                    }
                    "downloadRemote" -> downloadRemote(
                        call.argument<String>("url").orEmpty(),
                        call.argument<String>("token").orEmpty(),
                        call.argument<String>("fileName").orEmpty(),
                        result
                    )
                    "startHost" -> {''',
    'manager method switch',
)

manager_helpers = r'''    private fun downloadRemote(
        url: String,
        token: String,
        fileName: String,
        result: MethodChannel.Result
    ) {
        val current = activity ?: run {
            result.error("FILE_BRIDGE", "No hay una actividad disponible.", null)
            return
        }
        if (pendingDownload != null) {
            result.error("FILE_BRIDGE", "Ya hay una descarga esperando destino.", null)
            return
        }
        require(url.startsWith("http://") || url.startsWith("https://")) {
            "Dirección remota inválida."
        }
        require(token.length >= 16) { "Token inválido." }
        require(fileName.isNotBlank()) { "Nombre de archivo inválido." }

        pendingDownload = PendingDownload(url, token, fileName, result)
        val intent = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = mimeTypeFor(fileName)
            putExtra(Intent.EXTRA_TITLE, fileName)
        }
        try {
            current.startActivityForResult(intent, REQUEST_SAVE_REMOTE)
        } catch (e: Exception) {
            pendingDownload = null
            result.error("FILE_BRIDGE", e.message ?: "No pude abrir el selector para guardar.", null)
        }
    }

    private fun mimeTypeFor(name: String): String {
        return when (name.substringAfterLast('.', "").lowercase()) {
            "jpg", "jpeg" -> "image/jpeg"
            "png" -> "image/png"
            "webp" -> "image/webp"
            "gif" -> "image/gif"
            "heic", "heif" -> "image/heic"
            "mp4", "m4v" -> "video/mp4"
            "webm" -> "video/webm"
            "mp3" -> "audio/mpeg"
            "wav" -> "audio/wav"
            "pdf" -> "application/pdf"
            "apk" -> "application/vnd.android.package-archive"
            "zip" -> "application/zip"
            "txt", "log" -> "text/plain"
            "json" -> "application/json"
            else -> "application/octet-stream"
        }
    }

    private fun performRemoteDownload(pending: PendingDownload, destination: Uri) {
        val current = activity ?: run {
            pending.result.error("FILE_BRIDGE", "La actividad dejó de estar disponible.", null)
            return
        }
        Thread {
            var connection: HttpURLConnection? = null
            try {
                connection = URL(pending.url).openConnection() as HttpURLConnection
                connection.requestMethod = "GET"
                connection.connectTimeout = 15_000
                connection.readTimeout = 30_000
                connection.setRequestProperty("Authorization", "Bearer ${pending.token}")
                connection.setRequestProperty("X-Local-Manager-Token", pending.token)
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

                val resolver = current.contentResolver
                val output = resolver.openOutputStream(destination, "w")
                    ?: throw IOException("No pude abrir el archivo de destino.")
                connection.inputStream.buffered(64 * 1024).use { input ->
                    output.buffered(64 * 1024).use { out ->
                        input.copyTo(out, 64 * 1024)
                    }
                }

                current.runOnUiThread {
                    pending.result.success(mapOf("saved" to true, "uri" to destination.toString()))
                }
            } catch (e: Exception) {
                current.runOnUiThread {
                    pending.result.error("FILE_BRIDGE_DOWNLOAD", e.message ?: e.javaClass.simpleName, null)
                }
            } finally {
                connection?.disconnect()
            }
        }.start()
    }

'''
s = replace_once(
    s,
    '    private fun pickRoot(result: MethodChannel.Result) {\n',
    manager_helpers + '    private fun pickRoot(result: MethodChannel.Result) {\n',
    'manager helpers',
)

old_activity_result = '''    fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?): Boolean {
        if (requestCode != REQUEST_TREE) return false
        val result = pendingPick
        pendingPick = null
        if (result == null) return true
        if (resultCode != Activity.RESULT_OK || data?.data == null) {
            result.success(null)
            return true
        }

        try {
            val uri = data.data!!
            val flags = data.flags and
                (Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
            activity?.contentResolver?.takePersistableUriPermission(uri, flags)
            val context = activity?.applicationContext
                ?: error("La actividad dejó de estar disponible.")
            val name = displayName(context, uri)
            context.getSharedPreferences(FileBridgeService.PREFS, Context.MODE_PRIVATE)
                .edit()
                .putString(FileBridgeService.KEY_ROOT_URI, uri.toString())
                .putString(FileBridgeService.KEY_ROOT_NAME, name)
                .putString(FileBridgeService.KEY_MODE, FileBridgeService.MODE_FOLDER)
                .apply()
            result.success(mapOf("rootUri" to uri.toString(), "rootName" to name))
        } catch (e: Exception) {
            result.error("FILE_BRIDGE", e.message ?: "No pude guardar el permiso de la carpeta.", null)
        }
        return true
    }
'''
new_activity_result = '''    fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?): Boolean {
        if (requestCode == REQUEST_SAVE_REMOTE) {
            val pending = pendingDownload
            pendingDownload = null
            if (pending == null) return true
            if (resultCode != Activity.RESULT_OK || data?.data == null) {
                pending.result.success(null)
                return true
            }
            performRemoteDownload(pending, data.data!!)
            return true
        }

        if (requestCode != REQUEST_TREE) return false
        val result = pendingPick
        pendingPick = null
        if (result == null) return true
        if (resultCode != Activity.RESULT_OK || data?.data == null) {
            result.success(null)
            return true
        }

        try {
            val uri = data.data!!
            val flags = data.flags and
                (Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
            activity?.contentResolver?.takePersistableUriPermission(uri, flags)
            val context = activity?.applicationContext
                ?: error("La actividad dejó de estar disponible.")
            val name = displayName(context, uri)
            context.getSharedPreferences(FileBridgeService.PREFS, Context.MODE_PRIVATE)
                .edit()
                .putString(FileBridgeService.KEY_ROOT_URI, uri.toString())
                .putString(FileBridgeService.KEY_ROOT_NAME, name)
                .putString(FileBridgeService.KEY_MODE, FileBridgeService.MODE_FOLDER)
                .apply()
            result.success(mapOf("rootUri" to uri.toString(), "rootName" to name))
        } catch (e: Exception) {
            result.error("FILE_BRIDGE", e.message ?: "No pude guardar el permiso de la carpeta.", null)
        }
        return true
    }
'''
s = replace_once(s, old_activity_result, new_activity_result, 'manager activity result')
manager_path.write_text(s)

s = service_path.read_text()
if 'import android.graphics.Bitmap' not in s:
    s = replace_once(
        s,
        'import android.app.Service\n',
        'import android.app.Service\nimport android.graphics.Bitmap\nimport android.graphics.BitmapFactory\nimport android.graphics.Canvas\nimport android.graphics.drawable.Drawable\nimport android.media.MediaMetadataRetriever\n',
        'service android imports',
    )
if 'import java.io.ByteArrayOutputStream' not in s:
    s = replace_once(
        s,
        'import java.io.BufferedOutputStream\n',
        'import java.io.BufferedOutputStream\nimport java.io.ByteArrayOutputStream\n',
        'service io import',
    )

old_route = '''                method == "GET" && uri.path == "/file" -> {
                    if (path.isEmpty()) {
                        sendText(output, 400, "A file path is required")
                        return
                    }
                    if (activeMode == MODE_ALL) {
                        streamAllStorageFile(path, output)
                    } else {
                        streamSelectedTreeFile(path, output)
                    }
                }
'''
new_route = old_route + '''
                method == "GET" && uri.path == "/thumbnail" -> {
                    if (path.isEmpty()) {
                        sendText(output, 400, "A file path is required")
                        return
                    }
                    val size = query["size"]?.toIntOrNull()?.coerceIn(64, 512) ?: 192
                    val thumb = if (activeMode == MODE_ALL) {
                        thumbnailAllStorage(path, size)
                    } else {
                        thumbnailSelectedTree(path, size)
                    }
                    if (thumb == null) {
                        sendText(output, 404, "Thumbnail unavailable")
                    } else {
                        writeHeaders(output, 200, thumb.first, thumb.second.size.toLong())
                        output.write(thumb.second)
                    }
                }
'''
s = replace_once(s, old_route, new_route, 'service thumbnail route')

thumb_helpers = r'''    private fun extension(name: String): String =
        name.substringAfterLast('.', "").lowercase()

    private fun isImageExtension(ext: String): Boolean =
        ext in setOf("jpg", "jpeg", "png", "webp", "gif", "bmp", "heic", "heif")

    private fun isVideoExtension(ext: String): Boolean =
        ext in setOf("mp4", "mkv", "mov", "avi", "webm", "m4v", "3gp")

    private fun sampledSize(width: Int, height: Int, maxSize: Int): Int {
        var sample = 1
        while (width / sample > maxSize * 2 || height / sample > maxSize * 2) {
            sample *= 2
        }
        return sample.coerceAtLeast(1)
    }

    private fun scaleBitmap(source: Bitmap, maxSize: Int): Bitmap {
        if (source.width <= maxSize && source.height <= maxSize) return source
        val ratio = minOf(maxSize.toFloat() / source.width, maxSize.toFloat() / source.height)
        val width = (source.width * ratio).toInt().coerceAtLeast(1)
        val height = (source.height * ratio).toInt().coerceAtLeast(1)
        val scaled = Bitmap.createScaledBitmap(source, width, height, true)
        if (scaled !== source) source.recycle()
        return scaled
    }

    private fun bitmapBytes(bitmap: Bitmap, png: Boolean = false): Pair<String, ByteArray> {
        val stream = ByteArrayOutputStream()
        if (png) {
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)
        } else {
            bitmap.compress(Bitmap.CompressFormat.JPEG, 82, stream)
        }
        val bytes = stream.toByteArray()
        stream.close()
        bitmap.recycle()
        return (if (png) "image/png" else "image/jpeg") to bytes
    }

    private fun drawableBitmap(drawable: Drawable, maxSize: Int): Bitmap {
        val naturalWidth = drawable.intrinsicWidth.takeIf { it > 0 } ?: maxSize
        val naturalHeight = drawable.intrinsicHeight.takeIf { it > 0 } ?: maxSize
        val ratio = minOf(maxSize.toFloat() / naturalWidth, maxSize.toFloat() / naturalHeight)
        val width = (naturalWidth * ratio).toInt().coerceAtLeast(1)
        val height = (naturalHeight * ratio).toInt().coerceAtLeast(1)
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        drawable.setBounds(0, 0, width, height)
        drawable.draw(canvas)
        return bitmap
    }

    private fun thumbnailAllStorage(path: String, maxSize: Int): Pair<String, ByteArray>? {
        val file = safeAllFile(path)
        if (!file.exists() || !file.isFile) return null
        val ext = extension(file.name)

        if (isImageExtension(ext)) {
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeFile(file.absolutePath, bounds)
            if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null
            val options = BitmapFactory.Options().apply {
                inSampleSize = sampledSize(bounds.outWidth, bounds.outHeight, maxSize)
            }
            val bitmap = BitmapFactory.decodeFile(file.absolutePath, options) ?: return null
            return bitmapBytes(scaleBitmap(bitmap, maxSize))
        }

        if (isVideoExtension(ext)) {
            val retriever = MediaMetadataRetriever()
            return try {
                retriever.setDataSource(file.absolutePath)
                val bitmap = retriever.getFrameAtTime(-1, MediaMetadataRetriever.OPTION_CLOSEST_SYNC)
                    ?: return null
                bitmapBytes(scaleBitmap(bitmap, maxSize))
            } catch (_: Exception) {
                null
            } finally {
                try { retriever.release() } catch (_: Exception) {}
            }
        }

        if (ext == "apk") {
            return try {
                val info = packageManager.getPackageArchiveInfo(file.absolutePath, 0) ?: return null
                val appInfo = info.applicationInfo ?: return null
                appInfo.sourceDir = file.absolutePath
                appInfo.publicSourceDir = file.absolutePath
                val drawable = appInfo.loadIcon(packageManager)
                bitmapBytes(drawableBitmap(drawable, maxSize), png = true)
            } catch (_: Exception) {
                null
            }
        }
        return null
    }

    private fun thumbnailSelectedTree(path: String, maxSize: Int): Pair<String, ByteArray>? {
        val doc = resolveDoc(path)
        if (doc.isDir) return null
        val ext = extension(doc.name)

        if (isImageExtension(ext)) {
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            contentResolver.openInputStream(doc.uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
            if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null
            val options = BitmapFactory.Options().apply {
                inSampleSize = sampledSize(bounds.outWidth, bounds.outHeight, maxSize)
            }
            val bitmap = contentResolver.openInputStream(doc.uri)?.use {
                BitmapFactory.decodeStream(it, null, options)
            } ?: return null
            return bitmapBytes(scaleBitmap(bitmap, maxSize))
        }

        if (isVideoExtension(ext)) {
            val retriever = MediaMetadataRetriever()
            return try {
                retriever.setDataSource(this, doc.uri)
                val bitmap = retriever.getFrameAtTime(-1, MediaMetadataRetriever.OPTION_CLOSEST_SYNC)
                    ?: return null
                bitmapBytes(scaleBitmap(bitmap, maxSize))
            } catch (_: Exception) {
                null
            } finally {
                try { retriever.release() } catch (_: Exception) {}
            }
        }
        return null
    }

'''
s = replace_once(
    s,
    '    // ---------- User-selected folder mode (Storage Access Framework) ----------\n',
    thumb_helpers + '    // ---------- User-selected folder mode (Storage Access Framework) ----------\n',
    'service thumbnail helpers',
)
service_path.write_text(s)

print('Local Manager media thumbnails + streamed save patch applied')
