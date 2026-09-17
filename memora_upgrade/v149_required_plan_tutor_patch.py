from pathlib import Path

p=Path('lib/study_plan_page.dart'); s=p.read_text()

# A learning plan must be grounded in exactly one tutor's assigned guides.
s=s.replace("  String contentOwner = 'library';", "  String? contentOwner;", 1)

old="""    final ownerTutor = contentOwner == 'library' ? null : _tutorById(contentOwner);
    final guides = ownerTutor == null
        ? widget.store.guides
        : TutorContextService.guidesFor(widget.store, ownerTutor);
"""
new="""    final ownerTutor = contentOwner == null ? null : _tutorById(contentOwner!);
    if (ownerTutor == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Selecciona un tutor para elegir la biblioteca del plan.')),
      );
      return;
    }
    final guides = TutorContextService.guidesFor(widget.store, ownerTutor);
"""
if old not in s: raise RuntimeError('plan content source logic not found')
s=s.replace(old,new,1)

old_empty="""          content: Text(
            ownerTutor == null
                ? 'Añade al menos una guía a Biblioteca.'
                : '${ownerTutor.name} todavía no tiene guías asignadas.',
          ),
"""
new_empty="""          content: Text('${ownerTutor.name} todavía no tiene guías asignadas.'),
"""
if old_empty in s: s=s.replace(old_empty,new_empty,1)

# Remove the whole-library choice. No tutor is preselected: the user must make
# an explicit tutor choice for each plan creation screen/session.
old_items="""                            items: [
                              const DropdownMenuItem(
                                value: 'library',
                                child: Text('Toda mi Biblioteca'),
                              ),
                              for (final tutor in tutors)
"""
new_items="""                            hint: const Text('Selecciona un tutor'),
                            items: [
                              for (final tutor in tutors)
"""
if old_items not in s: raise RuntimeError('whole-library dropdown option not found')
s=s.replace(old_items,new_items,1)
s=s.replace("onChanged: busy ? null : (v) => setState(() => contentOwner = v ?? 'library'),", "onChanged: busy ? null : (v) => setState(() => contentOwner = v),", 1)

# Make the content relationship explicit without changing Plan generator.
s=s.replace("labelText: 'Contenido del plan',", "labelText: 'Tutor / biblioteca del plan *',", 1)

# Do not allow generation until a tutor is explicitly selected. The generate()
# guard above remains as a second validation layer.
s=s.replace("onPressed: busy ? null : generate,", "onPressed: busy || contentOwner == null ? null : generate,", 1)

p.write_text(s)
print('Learning Plan now requires one tutor and uses only that tutor library')
