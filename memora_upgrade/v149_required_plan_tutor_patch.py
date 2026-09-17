from pathlib import Path
import re

p=Path('lib/study_plan_page.dart'); s=p.read_text()

# A learning plan must be grounded in exactly one tutor's assigned guides.
s=s.replace("  String contentOwner = 'library';", "  String? contentOwner;", 1)

# Replace the final content-source resolution after all previous plan patches.
patterns = [
    r"    final ownerTutor = contentOwner == 'library' \? null : _tutorById\(contentOwner\);\n    final guides = ownerTutor == null\n        \? widget\.store\.guides\n        : TutorContextService\.guidesFor\(widget\.store, ownerTutor\);",
    r"    final ownerTutor = contentOwner == 'library' \? null : _tutorById\(contentOwner\);\n    final guides = ownerTutor == null \? widget\.store\.guides : TutorContextService\.guidesFor\(widget\.store, ownerTutor\);",
]
replacement="""    final ownerTutor = contentOwner == null ? null : _tutorById(contentOwner!);
    if (ownerTutor == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Selecciona un tutor para elegir la biblioteca del plan.')),
      );
      return;
    }
    final guides = TutorContextService.guidesFor(widget.store, ownerTutor);"""
if "Selecciona un tutor para elegir la biblioteca del plan." not in s:
    changed=False
    for pat in patterns:
        s2,n=re.subn(pat,replacement,s,count=1)
        if n:
            s=s2; changed=True; break
    if not changed: raise RuntimeError('plan content source logic not found')

# Simplify the no-guides message now that ownerTutor can never be null here.
s=re.sub(
    r"content: Text\(\s*ownerTutor == null\s*\? 'Añade al menos una guía a Biblioteca\.'\s*: '\$\{ownerTutor\.name\} todavía no tiene guías asignadas\.',\s*\),",
    "content: Text('${ownerTutor.name} todavía no tiene guías asignadas.'),",
    s,count=1,
)

# Remove any whole-library DropdownMenuItem regardless of whitespace/formatting.
s=re.sub(
    r"\s*const DropdownMenuItem(?:<String>)?\(\s*value: 'library',\s*child: Text\('Toda mi Biblioteca'\),\s*\),",
    "",
    s,count=1,
)

# Add a tutor-selection hint to the content dropdown if absent. Scope it to the
# first dropdown following the content label so Plan generator is untouched.
label_pos=s.find("labelText: 'Contenido del plan'")
if label_pos < 0: label_pos=s.find("labelText: 'Tutor / biblioteca del plan *'")
if label_pos < 0: raise RuntimeError('plan content dropdown label not found')
drop_start=s.rfind('DropdownButtonFormField<String>(',0,label_pos)
items_pos=s.find('items: [',label_pos)
if drop_start < 0 or items_pos < 0: raise RuntimeError('plan content dropdown not found')
segment=s[drop_start:items_pos]
if 'hint:' not in segment:
    s=s[:items_pos]+"hint: const Text('Selecciona un tutor'),\n                            "+s[items_pos:]

# Nullable selection and explicit label.
s=s.replace("onChanged: busy ? null : (v) => setState(() => contentOwner = v ?? 'library'),", "onChanged: busy ? null : (v) => setState(() => contentOwner = v),", 1)
s=s.replace("labelText: 'Contenido del plan',", "labelText: 'Tutor / biblioteca del plan *',", 1)

# Disable only the plan creation button until a tutor is selected.
button_text=s.find("'Crear mi plan'")
if button_text >= 0:
    button_start=s.rfind('FilledButton',0,button_text)
    if button_start >= 0:
        segment=s[button_start:button_text]
        if 'contentOwner == null' not in segment:
            segment=segment.replace('onPressed: busy ? null : generate,','onPressed: busy || contentOwner == null ? null : generate,',1)
            s=s[:button_start]+segment+s[button_text:]

p.write_text(s)
print('Learning Plan now requires one tutor and uses only that tutor library')
