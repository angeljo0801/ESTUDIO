from pathlib import Path

# v186: make shared GGUF selection durable across restarts/background work.
# Android file pickers can sometimes return a temporary file:// cache path even
# when SAF lifetime access was requested. A cache path disappears later and
# produces "The shared model no longer exists at that location."

p = Path('lib/llm_settings_page.dart')
s = p.read_text()

start = s.find("  Future<void> _selectSharedGguf() async {")
end = s.find("  Future<void> _exportPrivateGguf()", start)
if start < 0 or end < 0:
    raise SystemExit('v186 shared picker method anchors missing')

method = r'''  Future<void> _selectSharedGguf() async {
    setState(() => selectingShared = true);
    try {
      final picked = await FilePicker.pickFile(
        type: FileType.custom,
        allowedExtensions: ['gguf'],
        androidOptions: const FilePickerAndroidOptions(
          safOptions: AndroidSAFOptions(
            grant: AndroidSAFGrant.lifetime,
            accessMode: AndroidSAFAccessMode.readOnly,
            persistGrant: true,
          ),
        ),
      );
      if (picked == null) return;

      var uriText = picked.uri.toString().trim();
      final pickedPath = picked.path?.trim() ?? '';
      if (uriText.isEmpty && pickedPath.isNotEmpty) {
        uriText = Uri.file(pickedPath).toString();
      }
      if (uriText.isEmpty) {
        throw Exception(
          'Android no devolvió una ubicación utilizable para el archivo.',
        );
      }

      var pinnedFallback = false;
      final parsed = Uri.tryParse(uriText);

      if (parsed == null ||
          parsed.scheme.isEmpty ||
          parsed.scheme.toLowerCase() == 'file') {
        final sourcePath = parsed != null &&
                parsed.scheme.toLowerCase() == 'file'
            ? parsed.toFilePath()
            : pickedPath;
        if (sourcePath.isEmpty || !await File(sourcePath).exists()) {
          throw Exception(
            'El archivo seleccionado ya no está disponible. Vuelve a elegirlo.',
          );
        }

        final support = await getApplicationSupportDirectory();
        final scopeName = widget.scope == 'global' ? 'global' : widget.scope;
        final dir = Directory('${support.path}/shared_models/$scopeName');
        await dir.create(recursive: true);
        final safeName =
            picked.name.replaceAll(RegExp(r'[^a-zA-Z0-9._-]'), '_');
        final destination = '${dir.path}/$safeName';

        if (sourcePath != destination) {
          await File(sourcePath).copy(destination);
        }
        uriText = Uri.file(destination).toString();
        pinnedFallback = true;
      }

      final p = await SharedPreferences.getInstance();
      await _writePref(p, 'shared_model_uri', uriText);
      await _writePref(p, 'shared_model_name', picked.name);
      await _writePref(p, 'device_model_mode', 'shared');

      if (mounted) {
        setState(() {
          sharedModelUri = uriText;
          sharedModelName = picked.name;
          deviceModelMode = 'shared';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              pinnedFallback
                  ? 'Modelo seleccionado. Android dio una ruta temporal, así que Memora guardó una copia estable para poder usarla en segundo plano.'
                  : 'Modelo compartido seleccionado con acceso persistente.',
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No pude seleccionar el modelo compartido: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => selectingShared = false);
    }
  }

'''
s = s[:start] + method + s[end:]
p.write_text(s)

print('v186 applied: shared GGUF paths are durable across restarts/background work')
