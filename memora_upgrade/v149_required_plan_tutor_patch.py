from pathlib import Path
import re
import os

p=Path('lib/study_plan_page.dart'); s=p.read_text()

# Require an explicit tutor as the plan's content owner.
s=s.replace("  String contentOwner = 'library';", "  String? contentOwner;", 1)

# Replace whole-library resolution with the selected tutor's assigned guides only.
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
    for pat in patterns:
        s2,n=re.subn(pat,replacement,s,count=1)
        if n:
            s=s2
            break
    else:
        raise RuntimeError('plan content source logic not found')

# No global-library fallback remains.
s=re.sub(
    r"content: Text\(\s*ownerTutor == null\s*\? 'Añade al menos una guía a Biblioteca\.'\s*: '\$\{ownerTutor\.name\} todavía no tiene guías asignadas\.',\s*\),",
    "content: Text('${ownerTutor.name} todavía no tiene guías asignadas.'),",
    s,count=1,
)

# Locate the correct dropdown by its stable state variable, not translated labels.
owner_pos=s.find('initialValue: contentOwner')
if owner_pos < 0:
    owner_pos=s.find('value: contentOwner')
if owner_pos < 0: raise RuntimeError('contentOwner dropdown not found')
drop_start=s.rfind('DropdownButtonFormField<String>(',0,owner_pos)
# Bound this dropdown at its onChanged so generator dropdown cannot be touched.
onchanged_pos=s.find('onChanged:',owner_pos)
if drop_start < 0 or onchanged_pos < 0: raise RuntimeError('contentOwner dropdown bounds not found')
drop_end=s.find('\n                          ),',onchanged_pos)
if drop_end < 0: raise RuntimeError('contentOwner dropdown end not found')
segment=s[drop_start:drop_end]

# Remove the whole-library item from this dropdown only.
segment=re.sub(
    r"\s*const DropdownMenuItem(?:<String>)?\(\s*value: 'library',\s*child: Text\([^\n]*\),\s*\),",
    "",
    segment,count=1,
)

# Add an explicit tutor hint without relying on the label language.
if 'hint:' not in segment:
    items_pos=segment.find('items: [')
    if items_pos < 0: raise RuntimeError('contentOwner items not found')
    segment=segment[:items_pos]+"hint: const Text('Selecciona un tutor'),\n                            "+segment[items_pos:]

# Nullable selection; never silently return to whole library.
segment=re.sub(
    r"onChanged:\s*busy\s*\?\s*null\s*:\s*\(v\)\s*=>\s*setState\(\(\)\s*=>\s*contentOwner\s*=\s*v\s*\?\?\s*'library'\),",
    "onChanged: busy ? null : (v) => setState(() => contentOwner = v),",
    segment,count=1,
)

# Rename the content label if this version still has one. This is cosmetic only.
segment=segment.replace("labelText: 'Contenido del plan',", "labelText: 'Tutor / biblioteca del plan *',",1)
segment=segment.replace("labelText: 'Plan content',", "labelText: 'Tutor / plan library *',",1)
s=s[:drop_start]+segment+s[drop_end:]

# Disable the create-plan button until a tutor is explicitly selected.
button_text=s.find("'Crear mi plan'")
if button_text < 0: button_text=s.find("'Create my plan'")
if button_text >= 0:
    button_start=s.rfind('FilledButton',0,button_text)
    if button_start >= 0:
        b=s[button_start:button_text]
        if 'contentOwner == null' not in b:
            b=b.replace('onPressed: busy ? null : generate,','onPressed: busy || contentOwner == null ? null : generate,',1)
            s=s[:button_start]+b+s[button_text:]

p.write_text(s)
print('Learning Plan requires one tutor and only that tutor library')

_v150=Path(os.environ['GITHUB_WORKSPACE'])/'memora_upgrade'/'v150_active_profile_description_cards_patch.py'
exec(compile(_v150.read_text(),str(_v150),'exec'))
