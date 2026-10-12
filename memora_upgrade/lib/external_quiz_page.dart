import 'dart:convert';
import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:flutter_file_dialog/flutter_file_dialog.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import 'guide_store.dart';
import 'models.dart';
import 'study_engine.dart';

/// Same offline versioned contract as FocoQuiz.
class ExternalQuizFormat {
  static Map<String, dynamic> parse(String raw) {
    if (raw.length > 2000000) throw const FormatException('Archivo demasiado grande (máximo 2 MB).');
    final data = jsonDecode(raw.replaceFirst('\uFEFF', '').trim());
    if (data is! Map) throw const FormatException('Se esperaba un objeto JSON.');
    final pack = Map<String, dynamic>.from(data);
    if (pack['format'] != 'focoquiz.quiz' || pack['version'] != 1) {
      throw const FormatException('Formato no compatible: se exige focoquiz.quiz versión 1.');
    }
    if (pack['title'] is! String || (pack['title'] as String).trim().isEmpty) {
      throw const FormatException('Falta el título del examen.');
    }
    final questions = pack['questions'];
    if (questions is! List || questions.isEmpty || questions.length > 500) {
      throw const FormatException('Se necesitan entre 1 y 500 preguntas.');
    }
    final ids = <String>{};
    for (var i = 0; i < questions.length; i++) {
      if (questions[i] is! Map) throw FormatException('Pregunta inválida: ' + (i + 1).toString());
      final q = Map<String, dynamic>.from(questions[i] as Map);
      final id = q['id'];
      final question = q['question'];
      final answer = q['answer'];
      final type = q['type'];
      if (id is! String || id.trim().isEmpty || !ids.add(id) ||
          question is! String || question.trim().length < 4 ||
          question.length > 1500 || answer is! String || answer.trim().isEmpty ||
          answer.length > 300 || answer.contains('|')) {
        throw FormatException('ID, enunciado o respuesta incorrecta en pregunta ' + (i + 1).toString());
      }
      if (type == 'multiple_choice') {
        final options = q['options'];
        if (options is! List || options.length != 4 ||
            options.any((e) => e is! String || e.trim().isEmpty) ||
            options.toSet().length != 4 || !options.contains(answer)) {
          throw FormatException('Cuatro opciones únicas y respuesta coincidente necesarias en pregunta ' + (i + 1).toString());
        }
      } else if (type == 'short_answer') {
        final alternatives = q['accepted_answers'];
        if (alternatives != null &&
            (alternatives is! List || alternatives.any((e) => e is! String || (e as String).contains('|')))) {
          throw FormatException('Respuestas alternativas inválidas en pregunta ' + (i + 1).toString());
        }
      } else {
        throw FormatException('Tipo de pregunta desconocido: ' + (i + 1).toString());
      }
    }
    return pack;
  }

  static Map<String, dynamic> fromGuide(StudyGuide guide) {
    if (guide.cards.isEmpty) throw const FormatException('La guía no tiene preguntas.');
    return {
      'format': 'focoquiz.quiz',
      'version': 1,
      'title': guide.title,
      'source': guide.sourceName,
      'language': 'es',
      'questions': guide.cards.where(StudyEngine.isCardUsable).toList().asMap().entries.map((entry) => {
        'id': 'q' + (entry.key + 1).toString(),
        'type': 'short_answer',
        'question': entry.value.question,
        'answer': entry.value.answer,
        'accepted_answers': <String>[],
        'explanation': '',
        'topic': guide.title,
        'difficulty': 'medium',
      }).toList(),
    };
  }

  static const prompt = '''
PROMPT PARA UNA IA EXTERNA A MEMORA

Lee exclusivamente la guía de estudio que adjunto o el texto final.
Crea entre 10 y 30 preguntas diversas (o la cantidad que solicite).
Devuelve SOLO un objeto JSON UTF-8 sin Markdown ni explicaciones fuera del JSON.
Usa este formato exacto y sustituye las preguntas por datos verificados en la guía:
{
 "format": "focoquiz.quiz",
 "version": 1,
 "title": "Nombre del examen",
 "source": "Nombre de la guía",
 "language": "es",
 "questions": [
  {"id":"q1","type":"multiple_choice","question":"Pregunta",
   "options":["Opción 1","Opción 2","Opción 3","Opción 4"],
   "answer":"Opción 1","explanation":"Explicación según la guía",
   "topic":"Tema","difficulty":"medium"},
  {"id":"q2","type":"short_answer","question":"Pregunta",
   "answer":"Respuesta","accepted_answers":[],
   "explanation":"Explicación según la guía",
   "topic":"Tema","difficulty":"easy"}
 ]
}
REGLAS: IDs únicos, preguntas completas, opciones únicas y exactamente
4 por pregunta de opción múltiple. answer debe coincidir literalmente
con una opción de multiple_choice. No inventes información, evita
preguntas repetidas, no agregues datos externos y mezcla dificultades.
Guarda la respuesta como examen.json en codificación UTF-8.
FIN DEL PROMPT
''';
}

class ExternalQuizPage extends StatefulWidget {
  const ExternalQuizPage({super.key, required this.store});
  final GuideStore store;
  @override State<ExternalQuizPage> createState() => _ExternalQuizPageState();
}

class _ExternalQuizPageState extends State<ExternalQuizPage> {
  String? selection;
  String status = '';
  bool busy = false;

  StudyGuide? get selectedGuide {
    final guides = widget.store.guides;
    if (guides.isEmpty) return null;
    for (final g in guides) { if (g.id == selection) return g; }
    return guides.first;
  }

  Future<String> _writeFile(String filename, String body) async {
    final root = await getApplicationDocumentsDirectory();
    final dir = Directory(root.path + '/external_quizzes');
    await dir.create(recursive: true);
    final file = File(dir.path + '/' + DateTime.now().microsecondsSinceEpoch.toString() + '_' + filename);
    await file.writeAsString(body, flush: true);
    return file.path;
  }

  Future<void> _execute(Future<String> Function() operation) async {
    if (busy) return;
    setState(() { busy = true; status = ''; });
    try {
      final message = await operation();
      if (mounted) setState(() => status = message);
    } catch (e) {
      if (mounted) setState(() => status = 'Error: ' + e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<String> _import() async {
    final item = await FilePicker.pickFile(
      type: FileType.custom, allowedExtensions: ['json']);
    if (item == null) return 'Importación cancelada.';
    final bytes = await item.readAsBytes();
    if (bytes.isEmpty) throw const FormatException('Archivo no disponible.');
    final pack = ExternalQuizFormat.parse(utf8.decode(bytes));
    final path = await _writeFile('examen.json', const JsonEncoder.withIndent('  ').convert(pack));
    final now = DateTime.now();
    final title = pack['title'] as String;
    final questions = (pack['questions'] as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    final cards = questions.asMap().entries.map((entry) => StudyCard(
      id: now.microsecondsSinceEpoch.toString() + '_' + entry.key.toString(),
      question: entry.value['question'] as String,
      answer: entry.value['answer'] as String,
      source: title,
      dueAt: now,
    )).toList();
    await widget.store.add(StudyGuide(
      id: now.microsecondsSinceEpoch.toString(),
      title: 'Examen externo: ' + title,
      sourceType: 'quiz',
      sourceName: item.name,
      text: questions.map((q) => (q['question'] as String) + '\nRespuesta: ' + (q['answer'] as String)).join('\n\n'),
      summary: 'Examen importado desde IA externa con ' + cards.length.toString() + ' preguntas. JSON original conservado.',
      cards: cards,
      createdAt: now,
      filePath: path,
    ));
    return 'Importado en Biblioteca: ' + cards.length.toString() + ' preguntas.';
  }

  Future<String> _save(String path, String filename) async {
    final result = await FlutterFileDialog.saveFile(
      params: SaveFileDialogParams(
        sourceFilePath: path, fileName: filename,
        mimeTypesFilter: const ['application/octet-stream'], localOnly: true));
    return result == null ? 'Guardado cancelado.' : 'Archivo guardado.';
  }

  Future<String> _prompt() async {
    const asset = 'assets/quiz-format/PLANTILLA_Y_PROMPT_PARA_CUALQUIER_IA.md';
    final template = await rootBundle.loadString(asset);
    // Only append the guide if the user explicitly chose it.
    final guide = selection == null ? null : selectedGuide;
    final fullPrompt = template +
      (guide == null ? '' : '\n\n=== GUÍA PARA LA IA EXTERNA: ' + guide.title + ' ===\n' + guide.text);
    final path = await _writeFile('PLANTILLA_Y_PROMPT_PARA_CUALQUIER_IA.md', fullPrompt);
    return _save(path, 'PLANTILLA_Y_PROMPT_PARA_CUALQUIER_IA.md');
  }

  Future<String> _example() async {
    const asset = 'assets/quiz-format/EJEMPLO_EXAMEN.json';
    final example = await rootBundle.loadString(asset);
    ExternalQuizFormat.parse(example);
    final path = await _writeFile('EJEMPLO_EXAMEN.json', example);
    return _save(path, 'EJEMPLO_EXAMEN.json');
  }

  Future<String> _quizPath() async {
    final guide = selectedGuide;
    if (guide == null) throw const FormatException('Selecciona una guía.');
    if (guide.sourceType == 'quiz' && guide.filePath != null &&
        await File(guide.filePath!).exists()) {
      ExternalQuizFormat.parse(await File(guide.filePath!).readAsString());
      return guide.filePath!;
    }
    final pack = ExternalQuizFormat.fromGuide(guide);
    ExternalQuizFormat.parse(jsonEncode(pack));
    return _writeFile('examen.json', const JsonEncoder.withIndent('  ').convert(pack));
  }

  Future<String> _export() async => _save(await _quizPath(), 'Memora_examen.json');

  Future<String> _share() async {
    final path = await _quizPath();
    await SharePlus.instance.share(ShareParams(
      files: [XFile(path, mimeType: 'application/json')],
      title: 'Enviar examen de Memora a FocoQuiz',
    ));
    return 'Selecciona FocoQuiz en las opciones de Compartir de Android.';
  }

  @override Widget build(BuildContext context) {
    final guides = widget.store.guides;
    return Scaffold(
      appBar: AppBar(title: const Text('Exámenes externos y FocoQuiz')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        const Text('Importa exámenes hechos por ChatGPT, Gemini, Claude o cualquier otra IA externa a Memora. No necesitas claves API.',
          style: TextStyle(fontSize: 17)),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: busy ? null : () => _execute(_import),
          icon: const Icon(Icons.upload_file),
          label: const Text('Importar examen externo (.json)')),
        const SizedBox(height: 18),
        const Text('Plantillas descargables (incluidas en la app)',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        const Text('Guarda el prompt para dárselo a cualquier IA externa junto con tu guía. Descarga también un examen JSON de ejemplo para comprobar el formato.'),
        const SizedBox(height: 10),
        OutlinedButton.icon(
          onPressed: busy ? null : () => _execute(_prompt),
          icon: const Icon(Icons.download),
          label: const Text('Descargar plantilla + prompt para IA (.md)')),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: busy ? null : () => _execute(_example),
          icon: const Icon(Icons.file_download_outlined),
          label: const Text('Descargar ejemplo de examen (.json)')),
        const SizedBox(height: 24),
        const Text('Intercambiar con FocoQuiz', style: TextStyle(
          fontWeight: FontWeight.bold, fontSize: 19)),
        const SizedBox(height: 10),
        if (guides.isNotEmpty) DropdownButtonFormField<String>(
          initialValue: guides.any((g) => g.id == selection) ? selection : guides.first.id,
          decoration: const InputDecoration(labelText: 'Guía o examen (para exportar o añadir al prompt)'),
          items: guides.map((g) => DropdownMenuItem(
            value: g.id, child: Text(g.title, overflow: TextOverflow.ellipsis))).toList(),
          onChanged: (id) => setState(() => selection = id),
        ),
        if (guides.isEmpty) const Text('Añade primero una guía a Biblioteca.'),
        const SizedBox(height: 10),
        OutlinedButton.icon(
          onPressed: busy || guides.isEmpty ? null : () => _execute(_export),
          icon: const Icon(Icons.file_download),
          label: const Text('Exportar examen compatible (.json)')),
        FilledButton.icon(
          onPressed: busy || guides.isEmpty ? null : () => _execute(_share),
          icon: const Icon(Icons.share),
          label: const Text('Compartir examen con FocoQuiz')),
        if (busy) const LinearProgressIndicator(),
        if (status.isNotEmpty) Padding(
          padding: const EdgeInsets.only(top: 14), child: SelectableText(status)),
      ]),
    );
  }
}
