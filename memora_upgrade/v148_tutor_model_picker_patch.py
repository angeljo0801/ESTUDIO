from pathlib import Path

p=Path('lib/tutor_page.dart'); s=p.read_text()

edit_marker="  Future<TutorProfile?> _editTutorDialog({TutorProfile? existing}) async {"
edit_start=s.find(edit_marker)
if edit_start < 0: raise RuntimeError('tutor edit dialog not found')

# v1.14 forces existing profiles to global during the upgrade pass. Restore
# each tutor's own saved source there; this code is outside the dialog and must
# never reference the dialog-local `source` variable.
s=s.replace(
    "        tutor.copyWith(\n          modelSource: 'global',",
    "        tutor.copyWith(\n          modelSource: tutor.modelSource,",
    1,
)

# Restore the dialog-local source variable after v1.14 removes it.
if "var source = existing?.modelSource ?? 'global';" not in s[edit_start:]:
    result_pos=s.find("    final result = await showDialog<TutorProfile>(", edit_start)
    if result_pos < 0: raise RuntimeError('tutor dialog result anchor not found')
    s=s[:result_pos]+"    var source = existing?.modelSource ?? 'global';\n\n"+s[result_pos:]
    edit_start=s.find(edit_marker)

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
if 'Seleccionar IA / modelo' not in s[edit_start:]:
    models_label=s.find("labelText: 'Modelos recomendados (uno por línea)'", edit_start)
    if models_label < 0: raise RuntimeError('recommended models field not found')
    # v1.14 replaces the old dropdown with explanatory text, so insert the new
    # selector immediately before the recommended-models TextField.
    field_start=s.rfind("                TextField(", edit_start, models_label)
    if field_start < 0: raise RuntimeError('recommended models TextField anchor not found')
    s=s[:field_start]+selector+"                const SizedBox(height: 12),\n"+s[field_start:]

# Persist the selected source only inside the TutorProfile constructed by the
# edit dialog. Do not globally replace modelSource values elsewhere.
edit_start=s.find(edit_marker)
edit_end=s.find("  Future<void> _addTutor()", edit_start)
if edit_end < 0: raise RuntimeError('tutor edit dialog end not found')
segment=s[edit_start:edit_end]
segment=segment.replace("modelSource: 'global',", "modelSource: source,", 1)
s=s[:edit_start]+segment+s[edit_end:]

# Tutor chat requests should honor the tutor-specific selection.
s=s.replace("providerOverride: 'global',", "providerOverride: tutor.modelSource,", 1)
p.write_text(s)

# Restore persisted modelSource specifically in fromJson. Never touch the
# const fallback TutorContextProfile entries, where `json` is out of scope.
p=Path('lib/tutor_context_service.dart'); c=p.read_text()
factory_start=c.find('factory TutorContextProfile.fromJson')
factory_end=c.find('\n  }\n}', factory_start)
if factory_start < 0 or factory_end < 0: raise RuntimeError('TutorContext fromJson not found')
factory=c[factory_start:factory_end]
factory=factory.replace("modelSource: 'global',", "modelSource: json['modelSource']?.toString() ?? 'global',", 1)
c=c[:factory_start]+factory+c[factory_end:]
p.write_text(c)
print('Tutor AI/model picker restored with correctly scoped model source')
