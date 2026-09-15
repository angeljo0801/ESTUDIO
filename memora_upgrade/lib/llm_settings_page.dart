import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_file_dialog/flutter_file_dialog.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

class LlmSettingsPage extends StatefulWidget {
  const LlmSettingsPage({super.key});
  @override
  State<LlmSettingsPage> createState() => _LlmSettingsPageState();
}

class _LlmSettingsPageState extends State<LlmSettingsPage> {
  String provider = 'gemini';
  String deviceModelMode = 'private';
  bool loading = true;
  bool importingModel = false;
  bool exportingModel = false;
  bool selectingShared = false;

  String deviceModelPath = '';
  String sharedModelUri = '';
  String sharedModelName = '';

  final geminiKey = TextEditingController();
  final onlineUrl = TextEditingController();
  final onlineModel = TextEditingController();
  final onlineKey = TextEditingController();
  final localUrl = TextEditingController();
  final localModel = TextEditingController();
  final localKey = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final p = await SharedPreferences.getInstance();
    provider = p.getString('llm_provider') ?? 'gemini';
    deviceModelMode = p.getString('device_model_mode') ?? 'private';
    geminiKey.text = p.getString('gemini_key') ?? '';
    onlineUrl.text = p.getString('openai_base_url') ?? 'https://api.openai.com/v1';
    onlineModel.text = p.getString('openai_model') ?? 'gpt-4.1-mini';
    onlineKey.text = p.getString('openai_key') ?? '';
    localUrl.text = p.getString('local_base_url') ?? 'http://127.0.0.1:11434/v1';
    localModel.text = p.getString('local_model') ?? 'llama3.2:3b';
    localKey.text = p.getString('local_key') ?? '';
    deviceModelPath = p.getString('device_model_path') ?? '';
    sharedModelUri = p.getString('shared_model_uri') ?? '';
    sharedModelName = p.getString('shared_model_name') ?? '';
    if (mounted) setState(() => loading = false);
  }

  Future<void> _importPrivateGguf() async {
    final picked = await FilePicker.pickFile(
      type: FileType.custom,
      allowedExtensions: ['gguf'],
    );
    final sourcePath = picked?.path;
    if (picked == null || sourcePath == null) return;

    setState(() => importingModel = true);
    try {
      final dir = await getApplicationSupportDirectory();
      final modelDir = Directory('${dir.path}/models');
      await modelDir.create(recursive: true);
      final old = deviceModelPath;
      final safeName = picked.name.replaceAll(RegExp(r'[^a-zA-Z0-9._-]'), '_');
      final destination = '${modelDir.path}/$safeName';
      if (sourcePath != destination) await File(sourcePath).copy(destination);

      final p = await SharedPreferences.getInstance();
      await p.setString('device_model_path', destination);
      await p.setString('device_model_mode', 'private');
      if (old.isNotEmpty && old != destination && File(old).existsSync()) {
        await File(old).delete();
      }
      if (mounted) {
        setState(() {
          deviceModelPath = destination;
          deviceModelMode = 'private';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Modelo privado de Memora importado correctamente.')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No pude importar el modelo privado: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => importingModel = false);
    }
  }

  Future<void> _selectSharedGguf() async {
    setState(() => selectingShared = true);
    try {
      final picked = await FilePicker.pickFile(
        type: FileType.custom,
        allowedExtensions: ['gguf'],
        androidSafOptions: const AndroidSAFOptions(
          grant: AndroidSAFGrant.lifetime,
          accessMode: AndroidSAFAccessMode.readOnly,
          persistGrant: true,
        ),
      );
      if (picked == null) return;
      final uri = picked.uri.toString();
      if (uri.isEmpty) {
        throw Exception('Android no devolvió una ubicación persistente para el archivo.');
      }

      final p = await SharedPreferences.getInstance();
      await p.setString('shared_model_uri', uri);
      await p.setString('shared_model_name', picked.name);
      await p.setString('device_model_mode', 'shared');
      if (mounted) {
        setState(() {
          sharedModelUri = uri;
          sharedModelName = picked.name;
          deviceModelMode = 'shared';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Modelo compartido seleccionado. Memora no creó otra copia.')),
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

  Future<void> _exportPrivateGguf() async {
    if (deviceModelPath.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Primero importa un modelo privado para Memora.')),
        );
      }
      return;
    }
    final source = File(deviceModelPath);
    if (!await source.exists()) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('El modelo privado ya no existe en el almacenamiento de Memora.')),
        );
      }
      return;
    }

    setState(() => exportingModel = true);
    try {
      final modelName = source.uri.pathSegments.isEmpty
          ? 'memora-model.gguf'
          : source.uri.pathSegments.last;
      final result = await FlutterFileDialog.saveFile(
        params: SaveFileDialogParams(
          sourceFilePath: source.path,
          fileName: modelName,
          mimeTypesFilter: const ['application/octet-stream'],
          localOnly: true,
        ),
      );
      if (result != null && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Modelo privado exportado correctamente.')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No pude exportar el modelo: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => exportingModel = false);
    }
  }

  Future<void> _setDeviceMode(String? value) async {
    if (value == null) return;
    final p = await SharedPreferences.getInstance();
    await p.setString('device_model_mode', value);
    if (mounted) setState(() => deviceModelMode = value);
  }

  Future<void> _save() async {
    final p = await SharedPreferences.getInstance();
    await p.setString('llm_provider', provider);
    await p.setString('device_model_mode', deviceModelMode);
    await p.setString('gemini_key', geminiKey.text.trim());
    await p.setString('openai_base_url', onlineUrl.text.trim());
    await p.setString('openai_model', onlineModel.text.trim());
    await p.setString('openai_key', onlineKey.text.trim());
    await p.setString('local_base_url', localUrl.text.trim());
    await p.setString('local_model', localModel.text.trim());
    await p.setString('local_key', localKey.text.trim());
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Configuración de IA guardada')),
      );
    }
  }

  Widget _choice(String value, IconData icon, String title, String subtitle) =>
      Card(
        child: RadioListTile<String>(
          value: value,
          groupValue: provider,
          onChanged: (v) => setState(() => provider = v ?? 'gemini'),
          secondary: Icon(icon),
          title: Text(title),
          subtitle: Text(subtitle),
        ),
      );

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Ajustes de IA')),
        body: loading
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  const Text(
                    'Elige qué cerebro usará Memora',
                    style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 10),
                  _choice(
                    'gemini',
                    Icons.cloud_outlined,
                    'Gemini online',
                    'Rápido y sencillo con una clave de Google AI Studio.',
                  ),
                  _choice(
                    'openai',
                    Icons.public,
                    'LLM online compatible',
                    'OpenAI o cualquier API compatible con /chat/completions.',
                  ),
                  _choice(
                    'local',
                    Icons.smartphone,
                    'LLM local',
                    'Ollama, LM Studio u otro servidor compatible, sin nube.',
                  ),
                  const SizedBox(height: 14),
                  _choice(
                    'device',
                    Icons.memory,
                    'GGUF en este teléfono',
                    'Memora puede usar su modelo privado o un modelo compartido con otras APK.',
                  ),
                  const SizedBox(height: 14),
                  if (provider == 'gemini')
                    TextField(
                      controller: geminiKey,
                      obscureText: true,
                      decoration: const InputDecoration(
                        labelText: 'Clave de Gemini',
                        prefixIcon: Icon(Icons.key),
                      ),
                    ),
                  if (provider == 'openai') ...[
                    TextField(
                      controller: onlineUrl,
                      decoration: const InputDecoration(
                        labelText: 'URL base',
                        hintText: 'https://api.openai.com/v1',
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: onlineModel,
                      decoration: const InputDecoration(
                        labelText: 'Modelo',
                        hintText: 'gpt-4.1-mini',
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: onlineKey,
                      obscureText: true,
                      decoration: const InputDecoration(labelText: 'API key'),
                    ),
                  ],
                  if (provider == 'local') ...[
                    TextField(
                      controller: localUrl,
                      decoration: const InputDecoration(
                        labelText: 'URL del LLM local',
                        hintText: 'http://192.168.1.20:11434/v1',
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: localModel,
                      decoration: const InputDecoration(
                        labelText: 'Nombre del modelo',
                        hintText: 'llama3.2:3b',
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: localKey,
                      obscureText: true,
                      decoration: const InputDecoration(labelText: 'Clave opcional'),
                    ),
                    const SizedBox(height: 10),
                    const Text(
                      'El servidor debe exponer una API compatible con OpenAI. Si corre en otro equipo, usa su IP local; 127.0.0.1 solo sirve si el servidor corre en el propio teléfono.',
                    ),
                  ],
                  if (provider == 'device') ...[
                    const Text(
                      'Modelo de Memora',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 6),
                    Card(
                      child: RadioListTile<String>(
                        value: 'private',
                        groupValue: deviceModelMode,
                        onChanged: _setDeviceMode,
                        secondary: const Icon(Icons.lock_outline),
                        title: const Text('Modelo privado de Memora'),
                        subtitle: const Text(
                          'Memora guarda su propia copia. Es la opción principal y más estable.',
                        ),
                      ),
                    ),
                    Card(
                      child: RadioListTile<String>(
                        value: 'shared',
                        groupValue: deviceModelMode,
                        onChanged: _setDeviceMode,
                        secondary: const Icon(Icons.folder_shared_outlined),
                        title: const Text('Modelo compartido'),
                        subtitle: const Text(
                          'Usa un GGUF externo sin copiarlo dentro de Memora. Puede ser el mismo que usan otras APK.',
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    if (deviceModelMode == 'private') ...[
                      FilledButton.icon(
                        onPressed: importingModel || exportingModel || selectingShared
                            ? null
                            : _importPrivateGguf,
                        icon: const Icon(Icons.folder_open),
                        label: Text(
                          importingModel
                              ? 'Copiando modelo…'
                              : deviceModelPath.isEmpty
                                  ? 'Dar modelo privado a Memora'
                                  : 'Cambiar modelo privado de Memora',
                        ),
                      ),
                      const SizedBox(height: 10),
                      OutlinedButton.icon(
                        onPressed: deviceModelPath.isEmpty ||
                                importingModel ||
                                exportingModel ||
                                selectingShared
                            ? null
                            : _exportPrivateGguf,
                        icon: const Icon(Icons.file_download_outlined),
                        label: Text(
                          exportingModel ? 'Exportando modelo…' : 'Exportar modelo privado',
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        deviceModelPath.isEmpty
                            ? 'Memora todavía no tiene un modelo privado.'
                            : 'Privado: ${deviceModelPath.split('/').last}',
                      ),
                    ],
                    if (deviceModelMode == 'shared') ...[
                      FilledButton.icon(
                        onPressed: importingModel || exportingModel || selectingShared
                            ? null
                            : _selectSharedGguf,
                        icon: const Icon(Icons.folder_shared_outlined),
                        label: Text(
                          selectingShared
                              ? 'Seleccionando…'
                              : sharedModelUri.isEmpty
                                  ? 'Elegir modelo compartido .gguf'
                                  : 'Cambiar modelo compartido',
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        sharedModelUri.isEmpty
                            ? 'No hay un modelo compartido seleccionado.'
                            : 'Compartido: ${sharedModelName.isEmpty ? 'modelo.gguf' : sharedModelName}',
                      ),
                    ],
                    const SizedBox(height: 12),
                    const Text(
                      'Memora conserva ambos ajustes. Cambiar entre Privado y Compartido no borra el otro modelo. Así puedes dejar un modelo dedicado para Memora y otro único para el resto de tus aplicaciones.',
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Recomendado: modelo instruct de 1B a 4B, cuantización Q4. Los modelos grandes ocupan varios GB y consumen más RAM.',
                    ),
                  ],
                  const SizedBox(height: 22),
                  FilledButton.icon(
                    onPressed: _save,
                    icon: const Icon(Icons.save),
                    label: const Text('Guardar y usar esta opción'),
                  ),
                ],
              ),
      );
}
