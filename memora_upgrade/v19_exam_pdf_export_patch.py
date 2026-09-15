from pathlib import Path

p = Path('lib/daily_exam_page.dart')
s = p.read_text()

# Imports for PDF generation and Android save dialog.
old_imports = "import 'dart:convert';\nimport 'dart:math';\n\nimport 'package:flutter/material.dart';\n"
new_imports = "import 'dart:convert';\nimport 'dart:io';\nimport 'dart:math';\n\nimport 'package:flutter/material.dart';\nimport 'package:flutter_file_dialog/flutter_file_dialog.dart';\nimport 'package:path_provider/path_provider.dart';\nimport 'package:pdf/pdf.dart';\nimport 'package:pdf/widgets.dart' as pw;\n"
if old_imports not in s:
    raise RuntimeError('Exam PDF import anchor not found')
s = s.replace(old_imports, new_imports, 1)

# Add export helper before generator dropdown.
anchor = "  Widget _generatorDropdown({\n"
helper = r'''  Future<void> _exportExamPdf(TutorExamSession exam) async {
    try {
      String clean(String value) {
        final out = StringBuffer();
        for (final rune in value.runes) {
          if (rune == 10 || rune == 13 || rune == 9 || (rune >= 32 && rune <= 255)) {
            out.writeCharCode(rune);
          } else {
            out.write('?');
          }
        }
        return out.toString();
      }

      final doc = pw.Document();
      final created = exam.createdAt;
      final date = '${created.year}-${created.month.toString().padLeft(2, '0')}-${created.day.toString().padLeft(2, '0')}';
      final title = exam.isDaily ? 'Examen diario - ${exam.tutorName}' : 'Examen - ${exam.tutorName}';

      doc.addPage(
        pw.MultiPage(
          pageFormat: PdfPageFormat.a4,
          margin: const pw.EdgeInsets.all(36),
          build: (_) => [
            pw.Text(
              clean(title),
              style: pw.TextStyle(fontSize: 22, fontWeight: pw.FontWeight.bold),
            ),
            pw.SizedBox(height: 7),
            pw.Text(clean('Tutor: ${exam.tutorName}'), style: const pw.TextStyle(fontSize: 11)),
            pw.Text(clean('Dificultad: ${exam.difficulty}'), style: const pw.TextStyle(fontSize: 11)),
            pw.Text(clean('Fecha: $date'), style: const pw.TextStyle(fontSize: 11)),
            pw.Text(clean('Preguntas: ${exam.questions.length}'), style: const pw.TextStyle(fontSize: 11)),
            if (exam.generatorLabel.trim().isNotEmpty)
              pw.Text(clean('Generador: ${exam.generatorLabel}'), style: const pw.TextStyle(fontSize: 10)),
            pw.SizedBox(height: 20),
            pw.Text('PREGUNTAS', style: pw.TextStyle(fontSize: 16, fontWeight: pw.FontWeight.bold)),
            pw.SizedBox(height: 10),
            for (var i = 0; i < exam.questions.length; i++) ...[
              pw.Text(
                clean('${i + 1}. ${exam.questions[i].question}'),
                style: pw.TextStyle(fontSize: 11.5, fontWeight: pw.FontWeight.bold),
              ),
              if (exam.questions[i].sourceTitle.trim().isNotEmpty)
                pw.Text(
                  clean('Fuente: ${exam.questions[i].sourceTitle}'),
                  style: const pw.TextStyle(fontSize: 8.5, color: PdfColors.grey700),
                ),
              pw.SizedBox(height: 13),
            ],
            pw.SizedBox(height: 12),
            pw.Divider(),
            pw.SizedBox(height: 8),
            pw.Text('RESPUESTAS', style: pw.TextStyle(fontSize: 16, fontWeight: pw.FontWeight.bold)),
            pw.SizedBox(height: 10),
            for (var i = 0; i < exam.questions.length; i++) ...[
              pw.Text(
                clean('${i + 1}. ${exam.questions[i].answer}'),
                style: const pw.TextStyle(fontSize: 10.5),
              ),
              if (exam.questions[i].sourceTitle.trim().isNotEmpty)
                pw.Text(
                  clean('Fuente: ${exam.questions[i].sourceTitle}'),
                  style: const pw.TextStyle(fontSize: 8.5, color: PdfColors.grey700),
                ),
              pw.SizedBox(height: 11),
            ],
          ],
        ),
      );

      final root = await getTemporaryDirectory();
      final safeTutor = exam.tutorName
          .replaceAll(RegExp(r'[^A-Za-z0-9_-]+'), '_')
          .replaceAll(RegExp(r'_+'), '_')
          .replaceAll(RegExp(r'^_|_$'), '');
      final fileName = 'Memora_Examen_${safeTutor.isEmpty ? 'Tutor' : safeTutor}_$date.pdf';
      final file = File('${root.path}/$fileName');
      await file.writeAsBytes(await doc.save(), flush: true);

      final saved = await FlutterFileDialog.saveFile(
        params: SaveFileDialogParams(
          sourceFilePath: file.path,
          fileName: fileName,
        ),
      );
      if (!mounted || saved == null) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Examen exportado como PDF.')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No pude exportar el PDF: $e')),
      );
    }
  }

'''
if anchor not in s:
    raise RuntimeError('Exam PDF helper anchor not found')
s = s.replace(anchor, helper + anchor, 1)

# Add PDF button beside each custom-created exam.
old_trailing = """                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () => _openExam(exam),
"""
new_trailing = """                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      tooltip: 'Exportar examen a PDF',
                      onPressed: () => _exportExamPdf(exam),
                      icon: const Icon(Icons.picture_as_pdf_outlined),
                    ),
                    const Icon(Icons.chevron_right_rounded),
                  ],
                ),
                onTap: () => _openExam(exam),
"""
if old_trailing not in s:
    raise RuntimeError('Created exam trailing anchor not found')
s = s.replace(old_trailing, new_trailing, 1)

p.write_text(s)
print('Memora v1.9 exam PDF export patch applied successfully')
