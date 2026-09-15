from pathlib import Path

# Memora v1.14
# Tutors now always use Memora's global AI configuration. Agents keep their
# own per-agent AI assignment, and PDF/Excel creation keeps its own selector.
# A quick global AI selector is added to the Tutors screen.

p = Path('lib/tutor_page.dart')
s = p.read_text()

old = "  String globalLocalModel = '';\n  String accelerationLabel = 'Se detectará al usar un GGUF';"
new = "  String globalLocalModel = '';\n  String globalProvider = 'gemini';\n  String accelerationLabel = 'Se detectará al usar un GGUF';"
if old not in s:
    raise RuntimeError('Tutor state anchor not found')
s = s.replace(old, new, 1)

old = "    globalLocalModel = prefs.getString('local_model') ?? '';\n    responseMode = prefs.getString(_responseModeKey) ?? 'fast';"
new = "    globalLocalModel = prefs.getString('local_model') ?? '';\n    globalProvider = prefs.getString('llm_provider') ?? 'gemini';\n    responseMode = prefs.getString(_responseModeKey) ?? 'fast';"
if old not in s:
    raise RuntimeError('Tutor global provider load anchor not found')
s = s.replace(old, new, 1)

old = "        tutor.copyWith(\n          recommendedModels:"
new = "        tutor.copyWith(\n          modelSource: 'global',\n          recommendedModels:"
if old not in s:
    raise RuntimeError('Tutor profile migration anchor not found')
s = s.replace(old, new, 1)

old = "      case 'local':\n        return 'Ollama / servidor local configurado';\n      default:"
new = "      case 'local':\n        return 'Ollama / servidor local configurado';\n      case 'device':\n        return 'GGUF del teléfono';\n      default:"
if old not in s:
    raise RuntimeError('Tutor source label anchor not found')
s = s.replace(old, new, 1)

old = """    if (mounted) {
      setState(() => globalLocalModel = model);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$model seleccionado como modelo general de Ollama.')),
      );
    }
  }

  Future<void> _selectTutor(String? id) async {
"""
new = """    if (mounted) {
      setState(() {
        globalLocalModel = model;
        globalProvider = 'local';
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$model seleccionado como modelo general de Ollama.')),
      );
    }
  }

  Future<void> _setGlobalProvider(String provider) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('llm_provider', provider);
    if (!mounted) return;
    setState(() => globalProvider = provider);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('IA general: ${_sourceLabel(provider)}')),
    );
  }

  Future<void> _openQuickAiSelector() async {
    final selected = await showModalBottomSheet<String>(
      context: context,
      builder: (sheetContext) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(8, 12, 8, 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const ListTile(
                title: Text(
                  'Selector rápido de IA',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 19),
                ),
                subtitle: Text('Cambia la IA general de todos los tutores.'),
              ),
              for (final option in const [
                ('gemini', Icons.cloud_outlined, 'Gemini online'),
                ('openai', Icons.public, 'OpenAI / compatible'),
                ('local', Icons.smartphone, 'Ollama / servidor local'),
                ('device', Icons.memory, 'GGUF del teléfono'),
              ])
                ListTile(
                  leading: Icon(option.$2),
                  title: Text(option.$3),
                  trailing: globalProvider == option.$1
                      ? const Icon(Icons.check_circle)
                      : null,
                  onTap: () => Navigator.pop(sheetContext, option.$1),
                ),
              const SizedBox(height: 4),
              OutlinedButton.icon(
                onPressed: () {
                  Navigator.pop(sheetContext);
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const LlmSettingsPage()),
                  ).then((_) async {
                    final prefs = await SharedPreferences.getInstance();
                    final provider = prefs.getString('llm_provider') ?? 'gemini';
                    final model = prefs.getString('local_model') ?? '';
                    if (mounted) {
                      setState(() {
                        globalProvider = provider;
                        globalLocalModel = model;
                      });
                    }
                  });
                },
                icon: const Icon(Icons.tune),
                label: const Text('Ajustes completos de IA'),
              ),
            ],
          ),
        ),
      ),
    );
    if (selected != null) await _setGlobalProvider(selected);
  }

  Future<void> _selectTutor(String? id) async {
"""
if old not in s:
    raise RuntimeError('Tutor quick selector insertion anchor not found')
s = s.replace(old, new, 1)

# Tutor requests always follow the global AI selected in Memora.
s = s.replace("providerOverride: tutor.modelSource,", "providerOverride: 'global',")
s = s.replace("_sourceLabel(activeTutor.modelSource)", "_sourceLabel(globalProvider)")

# Old saved tutor-specific sources are ignored and removed from the tutor editor.
old = "    var source = existing?.modelSource ?? 'global';\n\n"
if old not in s:
    raise RuntimeError('Tutor editor source variable anchor not found')
s = s.replace(old, '', 1)

old = """                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: source,
                  decoration:
                      const InputDecoration(labelText: 'Fuente de IA de este tutor'),
                  items: const [
                    DropdownMenuItem(value: 'global', child: Text('Configuración general')),
                    DropdownMenuItem(value: 'private', child: Text('GGUF privado')),
                    DropdownMenuItem(value: 'shared', child: Text('GGUF compartido')),
                    DropdownMenuItem(value: 'gemini', child: Text('Gemini configurado')),
                    DropdownMenuItem(
                      value: 'openai',
                      child: Text('OpenAI / compatible configurado'),
                    ),
                    DropdownMenuItem(
                      value: 'local',
                      child: Text('Ollama / servidor local configurado'),
                    ),
                  ],
                  onChanged: (value) =>
                      setDialogState(() => source = value ?? 'global'),
                ),
"""
if old not in s:
    raise RuntimeError('Tutor editor source dropdown anchor not found')
s = s.replace(old, """                const SizedBox(height: 12),
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'Este tutor usa la IA general de Memora. Puedes cambiarla al instante desde el selector rápido.',
                  ),
                ),
""", 1)

if "                    modelSource: source," not in s:
    raise RuntimeError('Tutor saved source anchor not found')
s = s.replace("                    modelSource: source,", "                    modelSource: 'global',", 1)

# Manager cards no longer imply that each tutor owns a different provider.
s = s.replace("'${_sourceLabel(tutor.modelSource)} • ${tutor.guideIds.length} guía(s)'", "'IA general de Memora • ${tutor.guideIds.length} guía(s)'")

# Put the quick selector directly under the active tutor selector.
old = """                    onChanged: _selectTutor,
                  ),
                  const SizedBox(height: 10),
                  Card(
                    child: ExpansionTile(
                      leading: const Icon(Icons.memory_outlined),
"""
new = """                    onChanged: _selectTutor,
                  ),
                  const SizedBox(height: 10),
                  Card(
                    child: ListTile(
                      leading: const Icon(Icons.bolt_outlined),
                      title: const Text('IA general de los tutores'),
                      subtitle: Text(_sourceLabel(globalProvider)),
                      trailing: const Icon(Icons.swap_horiz),
                      onTap: busy ? null : _openQuickAiSelector,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Card(
                    child: ExpansionTile(
                      leading: const Icon(Icons.memory_outlined),
"""
if old not in s:
    raise RuntimeError('Tutor quick selector UI anchor not found')
s = s.replace(old, new, 1)

p.write_text(s)

# Every other tutor-driven feature (daily exams, study plans, etc.) also treats
# tutor profiles as global. This keeps old persisted profiles compatible.
p = Path('lib/tutor_context_service.dart')
s = p.read_text()
old = "      modelSource: json['modelSource']?.toString() ?? 'global',"
new = "      modelSource: 'global',"
if old not in s:
    raise RuntimeError('TutorContext model source anchor not found')
p.write_text(s.replace(old, new, 1))

print('Memora v1.14 global tutor AI and quick selector patch applied successfully')
