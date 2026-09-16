import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fast_model_setup_page.dart';
import 'local_model_manager.dart';

class ModelManagerPage extends StatefulWidget {
  const ModelManagerPage({super.key});

  @override
  State<ModelManagerPage> createState() => _ModelManagerPageState();
}

class _ModelManagerPageState extends State<ModelManagerPage> {
  bool loading = true;
  bool ollamaLoading = false;
  String ollamaMessage = '';
  List<PrivateGgufModel> privateModels = const [];
  List<OllamaModelInfo> ollamaModels = const [];
  String currentPrivatePath = '';
  String currentOllamaModel = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  String _bytes(int value) {
    if (value <= 0) return '';
    const mb = 1024 * 1024;
    const gb = 1024 * mb;
    if (value >= gb) return '${(value / gb).toStringAsFixed(2)} GB';
    return '${(value / mb).toStringAsFixed(value < 100 * mb ? 1 : 0)} MB';
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final private = await LocalModelManager.privateModels();
    if (!mounted) return;
    setState(() {
      privateModels = private;
      currentPrivatePath = prefs.getString('device_model_path') ?? '';
      currentOllamaModel = prefs.getString('local_model') ?? '';
      loading = false;
    });
    await _refreshOllama(silent: true);
  }

  Future<void> _refreshOllama({bool silent = false}) async {
    if (ollamaLoading) return;
    setState(() {
      ollamaLoading = true;
      if (!silent) ollamaMessage = 'Checking the configured Ollama server…';
    });
    try {
      final models = await LocalModelManager.ollamaModels();
      if (!mounted) return;
      setState(() {
        ollamaModels = models;
        ollamaMessage = models.isEmpty
            ? 'The configured Ollama server is reachable, but it has no downloaded models.'
            : '';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        ollamaModels = const [];
        ollamaMessage =
            'Ollama model management is unavailable at the local server configured in AI Settings. $e';
      });
    } finally {
      if (mounted) setState(() => ollamaLoading = false);
    }
  }

  Future<bool> _confirmDelete(String title, String body) async {
    return await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: Text(title),
            content: Text(body),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Cancel'),
              ),
              FilledButton.icon(
                onPressed: () => Navigator.pop(context, true),
                icon: const Icon(Icons.delete_outline),
                label: const Text('Delete'),
              ),
            ],
          ),
        ) ??
        false;
  }

  Future<void> _deletePrivate(PrivateGgufModel model) async {
    final yes = await _confirmDelete(
      'Delete private GGUF?',
      'Delete ${model.name} from Memora storage? This cannot be undone.',
    );
    if (!yes) return;
    try {
      await LocalModelManager.deletePrivateModel(model.path);
      await _load();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${model.name} deleted from Memora.')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not delete the model: $e')),
      );
    }
  }

  Future<void> _useOllama(OllamaModelInfo model) async {
    await LocalModelManager.useOllamaModel(model.name);
    if (!mounted) return;
    setState(() => currentOllamaModel = model.name);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('${model.name} is now the general Memora AI.')),
    );
  }

  Future<void> _deleteOllama(OllamaModelInfo model) async {
    final yes = await _confirmDelete(
      'Delete Ollama model?',
      'Ask the configured Ollama server to permanently delete ${model.name}?',
    );
    if (!yes) return;
    try {
      await LocalModelManager.deleteOllamaModel(model.name);
      await _refreshOllama();
      final prefs = await SharedPreferences.getInstance();
      if (!mounted) return;
      setState(() => currentOllamaModel = prefs.getString('local_model') ?? '');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${model.name} deleted from Ollama.')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not delete the Ollama model: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Downloaded models')),
        body: loading
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: _load,
                child: ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 48),
                  children: [
                    Card(
                      child: ListTile(
                        leading: const Icon(Icons.bolt_rounded),
                        title: const Text('Fast on-device model'),
                        subtitle: const Text(
                          'Download, use, or export the recommended Qwen2.5 1.5B GGUF.',
                        ),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () async {
                          await Navigator.push(
                            context,
                            MaterialPageRoute(builder: (_) => const FastModelSetupPage()),
                          );
                          if (mounted) await _load();
                        },
                      ),
                    ),
                    const SizedBox(height: 18),
                    const Text(
                      'Private GGUF models in Memora',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    if (privateModels.isEmpty)
                      const Card(
                        child: Padding(
                          padding: EdgeInsets.all(16),
                          child: Text('Memora has no private GGUF files stored.'),
                        ),
                      )
                    else
                      for (final model in privateModels)
                        Card(
                          child: ListTile(
                            leading: Icon(
                              model.path == currentPrivatePath
                                  ? Icons.memory_rounded
                                  : Icons.memory_outlined,
                            ),
                            title: Text(model.name),
                            subtitle: Text(
                              [
                                if (_bytes(model.bytes).isNotEmpty) _bytes(model.bytes),
                                if (model.path == currentPrivatePath) 'Selected private model',
                              ].join(' • '),
                            ),
                            trailing: IconButton(
                              tooltip: 'Delete model',
                              onPressed: () => _deletePrivate(model),
                              icon: const Icon(Icons.delete_outline),
                            ),
                          ),
                        ),
                    const SizedBox(height: 22),
                    Row(
                      children: [
                        const Expanded(
                          child: Text(
                            'Ollama models',
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                        ),
                        IconButton(
                          tooltip: 'Refresh Ollama models',
                          onPressed: ollamaLoading ? null : _refreshOllama,
                          icon: ollamaLoading
                              ? const SizedBox(
                                  width: 20,
                                  height: 20,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.refresh),
                        ),
                      ],
                    ),
                    const Text(
                      'These are managed by the Ollama server configured under Local LLM in AI Settings.',
                    ),
                    const SizedBox(height: 8),
                    if (ollamaMessage.isNotEmpty)
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Text(ollamaMessage),
                        ),
                      ),
                    for (final model in ollamaModels)
                      Card(
                        child: ListTile(
                          leading: Icon(
                            model.name == currentOllamaModel
                                ? Icons.check_circle_outline
                                : Icons.cloud_download_outlined,
                          ),
                          title: Text(model.name),
                          subtitle: Text(
                            [
                              if (_bytes(model.size).isNotEmpty) _bytes(model.size),
                              if (model.name == currentOllamaModel) 'Selected Ollama model',
                            ].join(' • '),
                          ),
                          onTap: () => _useOllama(model),
                          trailing: IconButton(
                            tooltip: 'Delete from Ollama',
                            onPressed: () => _deleteOllama(model),
                            icon: const Icon(Icons.delete_outline),
                          ),
                        ),
                      ),
                    const SizedBox(height: 20),
                    const Text(
                      'Shared GGUF files are external files that may also be used by other apps. Memora will never delete a shared file from here; change or remove that file with your phone file manager if you want to delete the external copy.',
                    ),
                  ],
                ),
              ),
      );
}
