import 'dart:io';

import 'package:flutter/material.dart';

import 'ai_service.dart';
import 'guide_file_service.dart';
import 'guide_store.dart';
import 'study_engine.dart';

class GuideCreatorPage extends StatefulWidget {
  const GuideCreatorPage({super.key, required this.store});
  final GuideStore store;

  @override
  State<GuideCreatorPage> createState() => _GuideCreatorPageState();
}

class _GuideCreatorPageState extends State<GuideCreatorPage> {
  final titleController = TextEditingController();
  final promptController = TextEditingController();
  final selectedGuideIds = <String>{};
  String format = 'pdf';
  String aiSource = 'global';
  bool busy = false;
  String status = '';

  @override
  void dispose() {
    titleController.dispose();
    promptController.dispose();
    super.dispose();
  }

  String _sourceLabel(String value) {
    switch (value) {
      case 'private':
        return 'GGUF privado de Memora';
      case 'shared':
        return 'GGUF compartido';
      case 'gemini':
        return 'Gemini configurado';
      case 'openai':
        return 'OpenAI / compatible configurado';
      case 'local':
        return 'Ollama / servidor local configurado';
      default:
        return 'Configuración general de Memora';
    }
  }

  Future<void> _pickSources() async {
    final working = Set<String>.from(selectedGuideIds);
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => StatefulBuilder(
        builder: (context, setSheetState) => SafeArea(
          child: SizedBox(
            height: MediaQuery.of(context).size.height * .78,
            child: Column(
              children: [
                const Padding(
                  padding: EdgeInsets.all(16),
                  child: Text(
                    'Fuentes para crear la nueva guía',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                ),
                Expanded(
                  child: widget.store.guides.isEmpty
                      ? const Center(
                          child: Text(
                            'No hay guías todavía. Puedes crear desde un prompt.',
                          ),
                        )
                      : ListView(
                          children: [
                            for (final guide in widget.store.guides)
                              CheckboxListTile(
                                value: working.contains(guide.id),
                                title: Text(guide.title),
                                subtitle: Text(guide.sourceType.toUpperCase()),
                                onChanged: (value) {
                                  setSheetState(() {
                                    if (value == true) {
                                      working.add(guide.id);
                                    } else {
                                      working.remove(guide.id);
                                    }
                                  });
                                },
                              ),
                          ],
                        ),
                ),
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: FilledButton(
                    onPressed: () {
                      setState(() {
                        selectedGuideIds
                          ..clear()
                          ..addAll(working);
                      });
                      Navigator.pop(sheetContext);
                    },
                    child: const Text('Usar estas fuentes'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _buildKnowledge() {
    final selected = widget.store.guides
        .where((guide) => selectedGuideIds.contains(guide.id))
        .toList();
    if (selected.isEmpty) return '';
    final perGuide = (26000 ~/ selected.length).clamp(2500, 12000);
    final buffer = StringBuffer();
    for (final guide in selected) {
      final text = guide.text.length > perGuide
          ? guide.text.substring(0, perGuide)
          : guide.text;
      buffer.writeln('\n=== ${guide.title} (${guide.sourceType}) ===');
      buffer.writeln(text);
    }
    return buffer.toString();
  }

  Future<void> _generate() async {
    final title = titleController.text.trim();
    final request = promptController.text.trim();
    if (title.isEmpty || request.isEmpty || busy) return;
    setState(() {
      busy = true;
      status = 'Generando contenido con ${_sourceLabel(aiSource)}…';
    });
    try {
      final knowledge = _buildKnowledge();
      final prompt = format == 'pdf'
          ? '''Crea una guía profesional lista para guardar como PDF.
TÍTULO: $title
PETICIÓN DEL USUARIO: $request
${knowledge.isEmpty ? '' : 'BASES DE CONOCIMIENTO:\n$knowledge'}

REQUISITOS:
- Escribe contenido claro, completo y bien organizado.
- Usa títulos y subtítulos en texto plano.
- Incluye explicaciones, ejemplos, conceptos clave y una sección final de repaso cuando aplique.
- Si se proporcionaron bases de conocimiento, no inventes datos que las contradigan y priorízalas.
- Devuelve solamente el contenido de la guía, sin comentarios sobre el proceso.'''
          : '''Crea una guía estructurada para convertirla directamente en un archivo Excel.
TÍTULO: $title
PETICIÓN DEL USUARIO: $request
${knowledge.isEmpty ? '' : 'BASES DE CONOCIMIENTO:\n$knowledge'}

DEVUELVE EXCLUSIVAMENTE una tabla TSV (valores separados por TABULADORES), sin bloque de código ni explicaciones externas.
La primera fila debe ser: Tema<TAB>Concepto<TAB>Explicación<TAB>Ejemplo/Nota
Luego crea filas útiles y completas. No uses tabuladores dentro de una celda. Si se proporcionaron bases de conocimiento, prioriza esa información.''';

      final result = await AiService.askConfigured(
        prompt: prompt,
        providerOverride: aiSource,
      );
      final path = format == 'pdf'
          ? await GuideFileService.createPdf(title: title, content: result)
          : await GuideFileService.createExcel(
              title: title,
              tableContent: result,
            );
      final filename = path.split(Platform.pathSeparator).last;
      final guide = StudyEngine.buildGuide(
        title: title,
        sourceType: format == 'pdf' ? 'pdf' : 'xlsx',
        sourceName: filename,
        text: result,
        filePath: path,
      );
      await widget.store.add(guide);
      if (!mounted) return;
      setState(() => status = 'Creado: $filename. Ya está en tu biblioteca.');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '${format.toUpperCase()} creado y añadido a Biblioteca.',
          ),
        ),
      );
    } catch (e) {
      if (mounted) setState(() => status = 'No pude crear el archivo: $e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Crear guía con IA')),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextField(
              controller: titleController,
              decoration: const InputDecoration(
                labelText: 'Nombre de la guía',
                hintText: 'Ej. Finanzas corporativas - Capítulo 4',
              ),
            ),
            const SizedBox(height: 12),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(
                  value: 'pdf',
                  icon: Icon(Icons.picture_as_pdf),
                  label: Text('PDF'),
                ),
                ButtonSegment(
                  value: 'xlsx',
                  icon: Icon(Icons.table_chart),
                  label: Text('Excel'),
                ),
              ],
              selected: {format},
              onSelectionChanged: (values) =>
                  setState(() => format = values.first),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: aiSource,
              decoration: const InputDecoration(
                labelText: 'IA / modelo que creará el archivo',
                prefixIcon: Icon(Icons.memory),
              ),
              items: const [
                DropdownMenuItem(
                  value: 'global',
                  child: Text('Configuración general de Memora'),
                ),
                DropdownMenuItem(
                  value: 'private',
                  child: Text('GGUF privado de Memora'),
                ),
                DropdownMenuItem(
                  value: 'shared',
                  child: Text('GGUF compartido'),
                ),
                DropdownMenuItem(
                  value: 'gemini',
                  child: Text('Gemini configurado'),
                ),
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
                  setState(() => aiSource = value ?? 'global'),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _pickSources,
              icon: const Icon(Icons.library_books_outlined),
              label: Text(
                selectedGuideIds.isEmpty
                    ? 'Usar guías existentes como fuentes (opcional)'
                    : '${selectedGuideIds.length} fuente(s) seleccionada(s)',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: promptController,
              minLines: 6,
              maxLines: 12,
              decoration: const InputDecoration(
                labelText: 'Qué quieres que contenga',
                alignLabelWithHint: true,
                hintText:
                    'Describe la guía, tabla o base de datos que quieres crear…',
              ),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: busy ? null : _generate,
              icon: busy
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.auto_awesome),
              label: Text(
                busy
                    ? 'Creando archivo…'
                    : 'Crear y guardar en Biblioteca',
              ),
              style: FilledButton.styleFrom(
                minimumSize: const Size.fromHeight(52),
              ),
            ),
            if (status.isNotEmpty) ...[
              const SizedBox(height: 14),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(status),
                ),
              ),
            ],
          ],
        ),
      );
}
