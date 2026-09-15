import 'dart:io';

import 'package:flutter/material.dart';

import 'ai_service.dart';
import 'completion_notification_service.dart';
import 'guide_file_service.dart';
import 'guide_store.dart';
import 'models.dart';
import 'study_engine.dart';

class GuideTranslationPage extends StatefulWidget {
  const GuideTranslationPage({
    super.key,
    required this.store,
    required this.guide,
  });

  final GuideStore store;
  final StudyGuide guide;

  @override
  State<GuideTranslationPage> createState() => _GuideTranslationPageState();
}

class _GuideTranslationPageState extends State<GuideTranslationPage> {
  String targetLanguage = 'English';
  String aiSource = 'global';
  bool busy = false;
  int completedChunks = 0;
  int totalChunks = 0;
  String status = '';

  String _sourceLabel(String value) {
    switch (value) {
      case 'private':
        return 'Memora private GGUF';
      case 'shared':
        return 'Shared GGUF';
      case 'gemini':
        return 'Configured Gemini';
      case 'openai':
        return 'Configured OpenAI / compatible';
      case 'local':
        return 'Configured Ollama / local server';
      default:
        return 'Memora general AI';
    }
  }

  List<String> _splitIntoChunks(String text, int maxChars) {
    final normalized = text.replaceAll('\r\n', '\n').replaceAll('\r', '\n').trim();
    if (normalized.isEmpty) return const [];

    final chunks = <String>[];
    final current = StringBuffer();

    void flush() {
      final value = current.toString().trim();
      if (value.isNotEmpty) chunks.add(value);
      current.clear();
    }

    for (final paragraph in normalized.split(RegExp(r'\n{2,}'))) {
      final p = paragraph.trim();
      if (p.isEmpty) continue;

      if (p.length > maxChars) {
        flush();
        var start = 0;
        while (start < p.length) {
          var end = (start + maxChars).clamp(0, p.length);
          if (end < p.length) {
            final searchStart = (end - 500).clamp(start, end);
            final sentenceBreak = p.lastIndexOf(RegExp(r'[.!?]\s'), end);
            final lineBreak = p.lastIndexOf('\n', end);
            final candidate = sentenceBreak > searchStart ? sentenceBreak + 1 : lineBreak;
            if (candidate > start + 500) end = candidate;
          }
          final piece = p.substring(start, end).trim();
          if (piece.isNotEmpty) chunks.add(piece);
          start = end;
        }
        continue;
      }

      final extra = current.isEmpty ? p.length : p.length + 2;
      if (current.length + extra > maxChars) flush();
      if (current.isNotEmpty) current.write('\n\n');
      current.write(p);
    }
    flush();
    return chunks;
  }

  Future<void> _translate() async {
    if (busy) return;
    final sourceText = widget.guide.text.trim();
    if (sourceText.isEmpty) {
      setState(() => status = 'This guide has no text to translate.');
      return;
    }

    final localish = aiSource == 'private' || aiSource == 'shared' || aiSource == 'local';
    final chunks = _splitIntoChunks(sourceText, localish ? 4200 : 8000);
    if (chunks.isEmpty) return;

    setState(() {
      busy = true;
      completedChunks = 0;
      totalChunks = chunks.length;
      status = 'Preparing translation…';
    });

    try {
      final translated = <String>[];
      for (var i = 0; i < chunks.length; i++) {
        if (!mounted) return;
        setState(() {
          status = 'Translating part ${i + 1} of ${chunks.length} with ${_sourceLabel(aiSource)}…';
        });
        final result = await AiService.askConfigured(
          providerOverride: aiSource,
          responseMode: 'fast',
          prompt: '''Translate the following study-guide content into $targetLanguage.

RULES:
- Preserve meaning, formulas, numbers, units, names, headings, lists, examples, and technical terminology.
- Do not summarize, shorten, expand, explain, or add facts.
- Keep the original structure and paragraph order as closely as possible.
- Translate every natural-language sentence, including questions and labels.
- Return ONLY the translated content. Do not add Markdown fences or commentary about the translation.
- If a technical term is normally kept in English, keep it when appropriate.

PART ${i + 1} OF ${chunks.length}:
${chunks[i]}''',
        );
        final clean = result.trim();
        if (clean.isEmpty) {
          throw Exception('The AI returned an empty translation for part ${i + 1}.');
        }
        translated.add(clean);
        if (mounted) {
          setState(() => completedChunks = i + 1);
        }
      }

      final translatedText = translated.join('\n\n').trim();
      final languageSuffix = targetLanguage == 'English' ? 'English' : 'Spanish';
      final title = '${widget.guide.title} — $languageSuffix';
      final pdfPath = await GuideFileService.createPdf(
        title: title,
        content: translatedText,
      );
      final fileName = pdfPath.split(Platform.pathSeparator).last;
      final translatedGuide = StudyEngine.buildGuide(
        title: title,
        sourceType: 'pdf',
        sourceName: fileName,
        text: translatedText,
        filePath: pdfPath,
      );
      await widget.store.add(translatedGuide);
      await CompletionNotificationService.show(
        title: 'Guide translation ready',
        body: '$title was added to your Library.',
      );

      if (!mounted) return;
      setState(() {
        status = 'Done. The translated guide was added to your Library and a PDF copy was created.';
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Translated guide added to Library.'),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => status = 'Translation failed: ${AiService.userFacingError(e)}');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _cancel() async {
    await AiService.cancelCurrent();
    if (!mounted) return;
    setState(() {
      busy = false;
      status = 'Translation cancelled.';
    });
  }

  @override
  Widget build(BuildContext context) {
    final progress = totalChunks == 0 ? 0.0 : completedChunks / totalChunks;
    return Scaffold(
      appBar: AppBar(title: const Text('Translate guide')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    widget.guide.title,
                    style: const TextStyle(fontSize: 19, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Memora creates a translated copy, regenerates its study cards in the target language, and keeps the original guide unchanged.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          DropdownButtonFormField<String>(
            initialValue: targetLanguage,
            decoration: const InputDecoration(
              labelText: 'Target language',
              prefixIcon: Icon(Icons.translate_rounded),
            ),
            items: const [
              DropdownMenuItem(value: 'English', child: Text('English')),
              DropdownMenuItem(value: 'Spanish', child: Text('Spanish')),
            ],
            onChanged: busy ? null : (value) => setState(() => targetLanguage = value ?? 'English'),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: aiSource,
            decoration: const InputDecoration(
              labelText: 'AI / model for translation',
              prefixIcon: Icon(Icons.memory_rounded),
            ),
            items: const [
              DropdownMenuItem(value: 'global', child: Text('Memora general AI')),
              DropdownMenuItem(value: 'private', child: Text('Memora private GGUF')),
              DropdownMenuItem(value: 'shared', child: Text('Shared GGUF')),
              DropdownMenuItem(value: 'gemini', child: Text('Configured Gemini')),
              DropdownMenuItem(value: 'openai', child: Text('Configured OpenAI / compatible')),
              DropdownMenuItem(value: 'local', child: Text('Configured Ollama / local server')),
            ],
            onChanged: busy ? null : (value) => setState(() => aiSource = value ?? 'global'),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: busy ? null : _translate,
            icon: const Icon(Icons.translate_rounded),
            label: Text(busy ? 'Translating…' : 'Translate and add to Library'),
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(54)),
          ),
          if (busy) ...[
            const SizedBox(height: 12),
            LinearProgressIndicator(value: progress == 0 ? null : progress),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: _cancel,
              icon: const Icon(Icons.stop_circle_outlined),
              label: const Text('Cancel translation'),
            ),
          ],
          if (status.isNotEmpty) ...[
            const SizedBox(height: 14),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(status),
              ),
            ),
          ],
          const SizedBox(height: 16),
          const Text(
            'For long guides, Memora translates the content in smaller parts so on-device models can handle it without exceeding their context window.',
          ),
        ],
      ),
    );
  }
}
