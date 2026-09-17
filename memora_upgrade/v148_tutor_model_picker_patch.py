from pathlib import Path
import re

p=Path('lib/tutor_page.dart'); s=p.read_text()

# Later patches may have reformatted or removed the old source declaration.
# Restore it relative to the stable edit-dialog signature instead of relying
# on an exact multiline TextEditingController layout.
if "var source = existing?.modelSource ?? 'global';" not in s:
    marker="  Future<TutorProfile?> _editTutorDialog({TutorProfile? existing}) async {"
    start=s.find(marker)
    if start < 0: raise RuntimeError('tutor edit dialog not found')
    result_pos=s.find("    final result = await showDialog<TutorProfile>(", start)
    if result_pos < 0: raise RuntimeError('tutor dialog result anchor not found')
    s=s[:result_pos]+"    var source = existing?.modelSource ?? 'global';\n\n"+s[result_pos:]

# If the old per-tutor dropdown survived, upgrade it in place. Otherwise add
# one immediately before the recommended-models field. This preserves that
# existing field exactly as a separate optional recommendation list.
selector="""                DropdownButtonFormField<String>(
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
"""
if 'Seleccionar IA / modelo' not in s:
    # Remove an older source dropdown if present so there is only one selector.
    edit_start=s.find("  Future<TutorProfile?> _editTutorDialog")
    models_label=s.find("labelText: 'Modelos recomendados (uno por línea)'", edit_start)
    if models_label < 0: raise RuntimeError('recommended models field not found')
    old_start=s.rfind("                DropdownButtonFormField<String>(", edit_start, models_label)
    if old_start >= 0:
        old_end=s.find("                const SizedBox(height: 12),", old_start)
        if old_end >= 0 and old_end < models_label:
            s=s[:old_start]+selector+s[old_end:]
        else:
            old_start=-1
    if old_start < 0:
        field_start=s.rfind("                TextField(", edit_start, models_label)
        if field_start < 0: raise RuntimeError('recommended models TextField anchor not found')
        s=s[:field_start]+selector+"                const SizedBox(height: 12),\n"+s[field_start:]

# Ensure the selected source is persisted and used. Replacement is tolerant:
# if a prior patch already restored these expressions, it is a no-op.
s=s.replace("modelSource: 'global',", "modelSource: source,", 1)
s=s.replace("providerOverride: 'global',", "providerOverride: tutor.modelSource,", 1)
p.write_text(s)

# Restore persisted modelSource if v1.14 forced deserialization to global.
p=Path('lib/tutor_context_service.dart'); c=p.read_text()
c=c.replace("modelSource: 'global',", "modelSource: json['modelSource']?.toString() ?? 'global',", 1)
p.write_text(c)
print('Tutor AI/model picker restored with resilient anchors')
