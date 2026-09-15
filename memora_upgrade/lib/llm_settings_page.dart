import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class LlmSettingsPage extends StatefulWidget {
  const LlmSettingsPage({super.key});
  @override State<LlmSettingsPage> createState() => _LlmSettingsPageState();
}

class _LlmSettingsPageState extends State<LlmSettingsPage> {
  String provider = 'gemini'; bool loading = true;
  final geminiKey = TextEditingController(), onlineUrl = TextEditingController(), onlineModel = TextEditingController(), onlineKey = TextEditingController(), localUrl = TextEditingController(), localModel = TextEditingController(), localKey = TextEditingController();
  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    final p = await SharedPreferences.getInstance();
    provider = p.getString('llm_provider') ?? 'gemini'; geminiKey.text = p.getString('gemini_key') ?? '';
    onlineUrl.text = p.getString('openai_base_url') ?? 'https://api.openai.com/v1'; onlineModel.text = p.getString('openai_model') ?? 'gpt-4.1-mini'; onlineKey.text = p.getString('openai_key') ?? '';
    localUrl.text = p.getString('local_base_url') ?? 'http://127.0.0.1:11434/v1'; localModel.text = p.getString('local_model') ?? 'llama3.2:3b'; localKey.text = p.getString('local_key') ?? '';
    if (mounted) setState(() => loading = false);
  }
  Future<void> _save() async {
    final p = await SharedPreferences.getInstance();
    await p.setString('llm_provider', provider); await p.setString('gemini_key', geminiKey.text.trim()); await p.setString('openai_base_url', onlineUrl.text.trim()); await p.setString('openai_model', onlineModel.text.trim()); await p.setString('openai_key', onlineKey.text.trim()); await p.setString('local_base_url', localUrl.text.trim()); await p.setString('local_model', localModel.text.trim()); await p.setString('local_key', localKey.text.trim());
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Configuración de IA guardada')));
  }
  Widget _choice(String value, IconData icon, String title, String subtitle) => Card(child: RadioListTile<String>(value: value, groupValue: provider, onChanged: (v) => setState(() => provider = v ?? 'gemini'), secondary: Icon(icon), title: Text(title), subtitle: Text(subtitle)));
  @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('Ajustes de IA')), body: loading ? const Center(child: CircularProgressIndicator()) : ListView(padding: const EdgeInsets.all(16), children: [
    const Text('Elige qué cerebro usará Memora', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)), const SizedBox(height: 10),
    _choice('gemini', Icons.cloud_outlined, 'Gemini online', 'Rápido y sencillo con una clave de Google AI Studio.'),
    _choice('openai', Icons.public, 'LLM online compatible', 'OpenAI o cualquier API compatible con /chat/completions.'),
    _choice('local', Icons.smartphone, 'LLM local', 'Ollama, LM Studio u otro servidor compatible, sin nube.'), const SizedBox(height: 14),
    if (provider == 'gemini') TextField(controller: geminiKey, obscureText: true, decoration: const InputDecoration(labelText: 'Clave de Gemini', prefixIcon: Icon(Icons.key))),
    if (provider == 'openai') ...[TextField(controller: onlineUrl, decoration: const InputDecoration(labelText: 'URL base', hintText: 'https://api.openai.com/v1')), const SizedBox(height: 12), TextField(controller: onlineModel, decoration: const InputDecoration(labelText: 'Modelo', hintText: 'gpt-4.1-mini')), const SizedBox(height: 12), TextField(controller: onlineKey, obscureText: true, decoration: const InputDecoration(labelText: 'API key'))],
    if (provider == 'local') ...[TextField(controller: localUrl, decoration: const InputDecoration(labelText: 'URL del LLM local', hintText: 'http://192.168.1.20:11434/v1')), const SizedBox(height: 12), TextField(controller: localModel, decoration: const InputDecoration(labelText: 'Nombre del modelo', hintText: 'llama3.2:3b')), const SizedBox(height: 12), TextField(controller: localKey, obscureText: true, decoration: const InputDecoration(labelText: 'Clave opcional')), const SizedBox(height: 10), const Text('El servidor debe exponer una API compatible con OpenAI. Si corre en otro equipo, usa su IP local; 127.0.0.1 solo sirve si el servidor corre en el propio teléfono.')],
    const SizedBox(height: 22), FilledButton.icon(onPressed: _save, icon: const Icon(Icons.save), label: const Text('Guardar y usar esta opción')),
  ]));
}
