import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

class MemoraBackupBridge {
  static const _channel = MethodChannel('com.memora/backups');

  static Future<Map<String, dynamic>> write({
    required String fileName,
    required Uint8List bytes,
    bool overwrite = false,
  }) async {
    final raw = await _channel.invokeMethod<Map<dynamic, dynamic>>(
      'writeBackup',
      {'fileName': fileName, 'bytes': bytes, 'overwrite': overwrite},
    );
    return Map<String, dynamic>.from(raw ?? const {});
  }

  static Future<List<Map<String, dynamic>>> list() async {
    final raw = await _channel.invokeMethod<List<dynamic>>('listBackups');
    return (raw ?? const [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  static Future<Uint8List> read(String uri) async {
    final raw = await _channel.invokeMethod<Uint8List>(
      'readBackup',
      {'uri': uri},
    );
    return raw ?? Uint8List(0);
  }
}

class MemoraBackupService {
  static const _autoEnabledKey = 'memora_auto_backup_enabled';
  static const _lastAutoKey = 'memora_last_auto_backup_at';

  static bool _sensitivePref(String key) {
    final k = key.toLowerCase();
    return k.contains('api_key') ||
        k.contains('apikey') ||
        k.endsWith('_key') ||
        k.contains('password') ||
        k.contains('secret') ||
        k.contains('access_token') ||
        k.contains('refresh_token');
  }

  static bool _skipFile(File file) {
    final p = file.path.toLowerCase().replaceAll('\\', '/');
    final name = p.split('/').last;
    return p.contains('/models/') ||
        p.contains('/model_cache/') ||
        name.endsWith('.gguf') ||
        name.endsWith('.safetensors');
  }

  static Future<Map<String, dynamic>> _preferences() async {
    final prefs = await SharedPreferences.getInstance();
    final values = <String, dynamic>{};
    final excluded = <String>[];
    for (final key in prefs.getKeys()) {
      if (_sensitivePref(key)) {
        excluded.add(key);
        continue;
      }
      final value = prefs.get(key);
      if (value is String ||
          value is bool ||
          value is int ||
          value is double ||
          value is List<String>) {
        values[key] = value;
      }
    }
    return {'values': values, 'excluded': excluded};
  }

  static Future<void> _addDirectory(
    Archive archive,
    Directory root,
    String prefix,
  ) async {
    if (!await root.exists()) return;
    await for (final entity in root.list(recursive: true, followLinks: false)) {
      if (entity is! File || _skipFile(entity)) continue;
      final rootPath =
          root.path.endsWith(Platform.pathSeparator)
              ? root.path
              : root.path + Platform.pathSeparator;
      if (!entity.path.startsWith(rootPath)) continue;
      final relative = entity.path.substring(rootPath.length).replaceAll('\\', '/');
      if (relative.isEmpty) continue;
      final bytes = await entity.readAsBytes();
      archive.addFile(ArchiveFile('$prefix/$relative', bytes.length, bytes));
    }
  }

  static Future<Uint8List> buildBackup() async {
    final archive = Archive();
    final prefs = await _preferences();
    final meta = {
      'format': 'MemoraBackup',
      'formatVersion': 1,
      'createdAt': DateTime.now().toIso8601String(),
      'modelsIncluded': false,
      'apiCredentialsIncluded': false,
      'excludedPreferences': prefs['excluded'],
    };
    final metaBytes = utf8.encode(jsonEncode(meta));
    archive.addFile(
      ArchiveFile('meta/backup.json', metaBytes.length, metaBytes),
    );
    final prefBytes = utf8.encode(jsonEncode(prefs['values']));
    archive.addFile(
      ArchiveFile('meta/preferences.json', prefBytes.length, prefBytes),
    );

    final docs = await getApplicationDocumentsDirectory();
    final support = await getApplicationSupportDirectory();
    await _addDirectory(archive, docs, 'documents');
    if (support.path != docs.path) {
      await _addDirectory(archive, support, 'support');
    }

    final encoded = ZipEncoder().encode(archive);
    if (encoded == null) throw Exception('No pude crear el ZIP de Memora.');
    return Uint8List.fromList(encoded);
  }

  static Future<Map<String, dynamic>> createManualBackup() async {
    final bytes = await buildBackup();
    final now = DateTime.now();
    String p(int n) => n.toString().padLeft(2, '0');
    final name =
        'Memora-Backup-${now.year}${p(now.month)}${p(now.day)}-'
        '${p(now.hour)}${p(now.minute)}${p(now.second)}.zip';
    return MemoraBackupBridge.write(
      fileName: name,
      bytes: bytes,
      overwrite: false,
    );
  }

  static Future<void> autoBackupIfDue() async {
    final prefs = await SharedPreferences.getInstance();
    final enabled = prefs.getBool(_autoEnabledKey) ?? true;
    if (!enabled) return;
    final last = DateTime.tryParse(prefs.getString(_lastAutoKey) ?? '');
    final now = DateTime.now();
    if (last != null && now.difference(last) < const Duration(hours: 24)) {
      return;
    }
    final bytes = await buildBackup();
    await MemoraBackupBridge.write(
      fileName: 'Memora-AutoBackup.zip',
      bytes: bytes,
      overwrite: true,
    );
    await prefs.setString(_lastAutoKey, now.toIso8601String());
  }

  static Future<bool> autoEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_autoEnabledKey) ?? true;
  }

  static Future<void> setAutoEnabled(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_autoEnabledKey, value);
  }

  static Future<void> _clearNonModelFiles(Directory root) async {
    if (!await root.exists()) return;
    final entities = await root.list(followLinks: false).toList();
    for (final entity in entities) {
      final lower = entity.path.toLowerCase().replaceAll('\\', '/');
      if (lower.endsWith('/models') || lower.endsWith('/model_cache')) continue;
      if (entity is File) {
        if (_skipFile(entity)) continue;
        await entity.delete();
      } else if (entity is Directory) {
        await entity.delete(recursive: true);
      }
    }
  }

  static Future<void> restore(String uri) async {
    final bytes = await MemoraBackupBridge.read(uri);
    if (bytes.isEmpty) throw Exception('La copia está vacía.');
    final archive = ZipDecoder().decodeBytes(bytes);

    ArchiveFile? metaFile;
    ArchiveFile? prefsFile;
    for (final file in archive.files) {
      if (file.name == 'meta/backup.json') metaFile = file;
      if (file.name == 'meta/preferences.json') prefsFile = file;
    }
    if (metaFile == null || prefsFile == null) {
      throw Exception('El archivo no es una copia válida de Memora.');
    }
    final meta = jsonDecode(utf8.decode(metaFile.content as List<int>));
    if (meta is! Map || meta['format'] != 'MemoraBackup') {
      throw Exception('Formato de copia no compatible.');
    }

    final docs = await getApplicationDocumentsDirectory();
    final support = await getApplicationSupportDirectory();
    await _clearNonModelFiles(docs);
    if (support.path != docs.path) await _clearNonModelFiles(support);

    for (final file in archive.files) {
      if (!file.isFile) continue;
      final name = file.name;
      Directory? root;
      String? relative;
      if (name.startsWith('documents/')) {
        root = docs;
        relative = name.substring('documents/'.length);
      } else if (name.startsWith('support/')) {
        root = support;
        relative = name.substring('support/'.length);
      }
      if (root == null || relative == null || relative.isEmpty) continue;
      if (relative.contains('..')) continue;
      final out = File(
        root.path + Platform.pathSeparator + relative.replaceAll('/', Platform.pathSeparator),
      );
      if (_skipFile(out)) continue;
      await out.parent.create(recursive: true);
      await out.writeAsBytes(List<int>.from(file.content as List), flush: true);
    }

    final prefsDecoded =
        jsonDecode(utf8.decode(prefsFile.content as List<int>));
    if (prefsDecoded is Map) {
      final prefs = await SharedPreferences.getInstance();
      final keepAuto = prefs.getBool(_autoEnabledKey) ?? true;
      await prefs.clear();
      for (final entry in prefsDecoded.entries) {
        final key = entry.key.toString();
        if (_sensitivePref(key)) continue;
        final value = entry.value;
        if (value is String) {
          await prefs.setString(key, value);
        } else if (value is bool) {
          await prefs.setBool(key, value);
        } else if (value is int) {
          await prefs.setInt(key, value);
        } else if (value is double) {
          await prefs.setDouble(key, value);
        } else if (value is List) {
          await prefs.setStringList(
            key,
            value.map((e) => e.toString()).toList(),
          );
        }
      }
      if (!prefs.containsKey(_autoEnabledKey)) {
        await prefs.setBool(_autoEnabledKey, keepAuto);
      }
    }
  }
}

class MemoraBackupPage extends StatefulWidget {
  const MemoraBackupPage({super.key});

  @override
  State<MemoraBackupPage> createState() => _MemoraBackupPageState();
}

class _MemoraBackupPageState extends State<MemoraBackupPage> {
  bool loading = true;
  bool working = false;
  bool autoEnabled = true;
  List<Map<String, dynamic>> backups = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final enabled = await MemoraBackupService.autoEnabled();
    final list = await MemoraBackupBridge.list();
    if (!mounted) return;
    setState(() {
      autoEnabled = enabled;
      backups = list;
      loading = false;
    });
  }

  Future<void> _create() async {
    setState(() => working = true);
    try {
      final result = await MemoraBackupService.createManualBackup();
      await _load();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Copia creada en Descargas/Memora: ' +
                (result['name']?.toString() ?? 'backup'),
          ),
        ),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No pude crear la copia: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => working = false);
    }
  }

  Future<void> _restore(Map<String, dynamic> item) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Restaurar Memora'),
        content: Text(
          'Se reemplazarán los datos actuales por "' +
              (item['name']?.toString() ?? 'backup') +
              '". Los modelos GGUF actuales no se borrarán.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Restaurar'),
          ),
        ],
      ),
    );
    if (ok != true) return;

    setState(() => working = true);
    try {
      await MemoraBackupService.restore(item['uri']?.toString() ?? '');
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (dialogContext) => AlertDialog(
          title: const Text('Copia restaurada'),
          content: const Text(
            'Cierra y vuelve a abrir Memora para cargar completamente los datos restaurados.',
          ),
          actions: [
            FilledButton(
              onPressed: () {
                Navigator.pop(dialogContext);
                SystemNavigator.pop();
              },
              child: const Text('Cerrar Memora'),
            ),
          ],
        ),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No pude restaurar la copia: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => working = false);
    }
  }

  String _date(Map<String, dynamic> item) {
    final ms = (item['modifiedMs'] as num?)?.toInt();
    if (ms == null || ms <= 0) return '';
    final d = DateTime.fromMillisecondsSinceEpoch(ms);
    String p(int n) => n.toString().padLeft(2, '0');
    return '${d.year}-${p(d.month)}-${p(d.day)} '
        '${p(d.hour)}:${p(d.minute)}';
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Copias de seguridad')),
        body: loading
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Copia automática diaria'),
                    subtitle: const Text(
                      'Se guarda en Descargas/Memora y sobrevive a una desinstalación.',
                    ),
                    value: autoEnabled,
                    onChanged: working
                        ? null
                        : (value) async {
                            await MemoraBackupService.setAutoEnabled(value);
                            if (mounted) {
                              setState(() => autoEnabled = value);
                            }
                          },
                  ),
                  FilledButton.icon(
                    onPressed: working ? null : _create,
                    icon: const Icon(Icons.backup_outlined),
                    label: Text(
                      working ? 'Procesando…' : 'Crear copia ahora',
                    ),
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    'Incluye biblioteca, archivos importados, chats, tarjetas, '
                    'planes, agentes y preferencias. No incluye modelos GGUF '
                    'ni claves API.',
                  ),
                  const Divider(height: 28),
                  const Text(
                    'Copias disponibles',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  if (backups.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 20),
                      child: Text('Todavía no hay copias guardadas.'),
                    ),
                  for (final item in backups)
                    Card(
                      child: ListTile(
                        leading: const Icon(Icons.restore_outlined),
                        title: Text(item['name']?.toString() ?? 'Backup'),
                        subtitle: Text(_date(item)),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: working ? null : () => _restore(item),
                      ),
                    ),
                ],
              ),
      );
}
