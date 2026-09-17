from pathlib import Path
p=Path('lib/tutor_page.dart'); s=p.read_text()
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
p.write_text(s)
print('Tutor AI/model picker added')
