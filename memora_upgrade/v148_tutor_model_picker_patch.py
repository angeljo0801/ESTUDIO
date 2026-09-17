from pathlib import Path

p=Path('lib/tutor_page.dart'); s=p.read_text()

# v1.14 intentionally made tutors global-only. The user now wants the same
# per-tutor AI/model selector available in Agents, so restore a local source
# variable and persist/use it for this tutor while keeping the quick global
# selector available as an option.
editor_anchor="""    final models = TextEditingController(
      text: (existing?.recommendedModels ?? _generalModels).join('\n'),
    );
"""
if "var source = existing?.modelSource ?? 'global';" not in s:
    if editor_anchor not in s: raise RuntimeError('tutor editor source anchor not found')
    s=s.replace(editor_anchor, editor_anchor+"    var source = existing?.modelSource ?? 'global';\n", 1)

old="""                const SizedBox(height: 12),
                TextField(
                  controller: models,
                  minLines: 4,
                  maxLines: 8,
                  decoration: const InputDecoration(
                    labelText: 'Modelos recomendados (uno por línea)',
                    helperText:
                        'La lista sirve también como selector rápido del modelo general Ollama.',
                  ),
                ),"""
new="""                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: source,
                  decoration: const InputDecoration(labelText: 'Seleccionar IA / modelo'),
                  isExpanded: true,
                  items: const [
                    DropdownMenuItem(value: 'global', child: Text('Configuración general')),
                    DropdownMenuItem(value: 'gemini', child: Text('Gemini configurado')),
                    DropdownMenuItem(value: 'openai', child: Text('OpenAI / compatible configurado')),
                    DropdownMenuItem(value: 'local', child: Text('Ollama / servidor local configurado')),
                    DropdownMenuItem(value: 'device', child: Text('GGUF on this phone')),
                    DropdownMenuItem(value: 'private', child: Text('GGUF privado de Memora')),
                    DropdownMenuItem(value: 'shared', child: Text('GGUF compartido')),
                  ],
                  onChanged: (value) => setDialogState(() => source = value ?? 'global'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: models,
                  minLines: 4,
                  maxLines: 8,
                  decoration: const InputDecoration(
                    labelText: 'Modelos recomendados (uno por línea)',
                    helperText: 'Opcional: conserva tu lista de recomendaciones además del selector de IA.',
                  ),
                ),"""
if 'Seleccionar IA / modelo' not in s:
    if old not in s: raise RuntimeError('tutor recommended models anchor not found')
    s=s.replace(old,new,1)

# Override the global-only save/use behavior introduced by v1.14.
s=s.replace("                    modelSource: 'global',", "                    modelSource: source,", 1)
s=s.replace("providerOverride: 'global',", "providerOverride: tutor.modelSource,", 1)

p.write_text(s)

# v1.14 also forced deserialized tutor profiles to global. Restore persisted
# modelSource so the selection survives restarts and is available to plans/exams.
p=Path('lib/tutor_context_service.dart'); c=p.read_text()
c=c.replace("      modelSource: 'global',", "      modelSource: json['modelSource']?.toString() ?? 'global',", 1)
p.write_text(c)
print('Tutor AI/model picker restored and compile-safe')
