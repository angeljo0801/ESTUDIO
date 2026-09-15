from pathlib import Path

# -----------------------------------------------------------------------------
# Faster hybrid exam generation: use AI for only a small verified subset and
# fill the rest from the tutor's validated indexed content.
# -----------------------------------------------------------------------------
p = Path('lib/daily_exam_page.dart')
s = p.read_text()

replacements = [
    (
        "      final aiCount = min(count, localish ? 10 : 20);",
        "      final aiCount = min(count, localish ? 2 : 6);",
    ),
    (
        "        maxChars: localish ? 12000 : 24000,",
        "        maxChars: localish ? 6000 : 12000,",
    ),
    (
        "          responseMode: localish ? 'normal' : 'deep',",
        "          responseMode: localish ? 'fast' : 'normal',",
    ),
    (
        "${recentQuestions.take(30).map((q) => '- $q').join('\\n')}",
        "${recentQuestions.take(12).map((q) => '- $q').join('\\n')}",
    ),
]
for old, new in replacements:
    if old not in s:
        raise RuntimeError(f'Exam speed anchor not found: {old[:80]}')
    s = s.replace(old, new, 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# Study plan: export current plan as PDF and copy it to the clipboard.
# -----------------------------------------------------------------------------
p = Path('lib/study_plan_page.dart')
s = p.read_text()

old_import = "import 'package:flutter/material.dart';\n"
new_import = """import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_file_dialog/flutter_file_dialog.dart';
"""
if old_import not in s:
    raise RuntimeError('Study plan Flutter import anchor not found')
s = s.replace(old_import, new_import, 1)

old_local_import = "import 'guide_store.dart';\n"
new_local_import = """import 'guide_store.dart';
import 'guide_file_service.dart';
"""
if old_local_import not in s:
    raise RuntimeError('Study plan local import anchor not found')
s = s.replace(old_local_import, new_local_import, 1)

build_anchor = "  @override\n  Widget build(BuildContext context) => Scaffold(\n"
helper = r'''  Future<void> _copyPlan() async {
    if (plan.trim().isEmpty) return;
    await Clipboard.setData(ClipboardData(text: plan));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Plan copiado al portapapeles.')),
    );
  }

  Future<void> _exportPlanPdf() async {
    if (plan.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Primero crea un plan para poder exportarlo.')),
      );
      return;
    }
    try {
      final objective = goal.text.trim().isEmpty
          ? 'Plan de aprendizaje'
          : goal.text.trim();
      final metadata = """Objetivo: $objective
Minutos diarios: ${minutes.text.trim()}
Intensidad: $intensity
Modalidad: ${dated ? 'Fecha objetivo' : 'Aprendizaje continuo'}
Creado por: ${createdBy.isEmpty ? 'Memora' : createdBy}
Fuente de IA: ${usedSource.isEmpty ? 'No indicada' : usedSource}

$plan""";
      final path = await GuideFileService.createPdf(
        title: 'Plan de aprendizaje - $objective',
        content: metadata,
      );
      final stamp = DateTime.now().millisecondsSinceEpoch;
      final result = await FlutterFileDialog.saveFile(
        params: SaveFileDialogParams(
          sourceFilePath: path,
          fileName: 'Plan_Memora_$stamp.pdf',
          mimeTypesFilter: const ['application/pdf'],
          localOnly: true,
        ),
      );
      if (!mounted || result == null) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Plan exportado como PDF.')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No pude exportar el plan: $e')),
      );
    }
  }

'''
if build_anchor not in s:
    raise RuntimeError('Study plan build anchor not found')
s = s.replace(build_anchor, helper + build_anchor, 1)

old_plan_block = """                  if (plan.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(18),
                        child: SelectableText(plan),
                      ),
                    ),
                  ],
"""
new_plan_block = """                  if (plan.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(18),
                        child: SelectableText(plan),
                      ),
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: [
                        FilledButton.icon(
                          onPressed: _exportPlanPdf,
                          icon: const Icon(Icons.picture_as_pdf_outlined),
                          label: const Text('Exportar plan a PDF'),
                        ),
                        OutlinedButton.icon(
                          onPressed: _copyPlan,
                          icon: const Icon(Icons.copy_outlined),
                          label: const Text('Copiar plan'),
                        ),
                      ],
                    ),
                  ],
"""
if old_plan_block not in s:
    raise RuntimeError('Study plan result block anchor not found')
s = s.replace(old_plan_block, new_plan_block, 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# AI settings: keep the final save button clearly above Android navigation.
# -----------------------------------------------------------------------------
p = Path('lib/llm_settings_page.dart')
s = p.read_text()

old_padding = "                padding: const EdgeInsets.all(16),"
new_padding = "                padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.of(context).padding.bottom + 140),"
if old_padding not in s:
    raise RuntimeError('AI settings ListView padding anchor not found')
s = s.replace(old_padding, new_padding, 1)

old_button = """                  const SizedBox(height: 22),
                  FilledButton.icon(
                    onPressed: _save,
                    icon: const Icon(Icons.save),
                    label: const Text('Guardar y usar esta opción'),
                  ),
"""
new_button = """                  const SizedBox(height: 22),
                  SafeArea(
                    top: false,
                    minimum: const EdgeInsets.only(bottom: 18),
                    child: SizedBox(
                      width: double.infinity,
                      height: 56,
                      child: FilledButton.icon(
                        onPressed: _save,
                        icon: const Icon(Icons.save),
                        label: const Text('Guardar y usar esta opción'),
                      ),
                    ),
                  ),
"""
if old_button not in s:
    raise RuntimeError('AI settings save button anchor not found')
s = s.replace(old_button, new_button, 1)
p.write_text(s)

print('Memora v1.12 speed, plan export and AI settings UI patch applied successfully')
