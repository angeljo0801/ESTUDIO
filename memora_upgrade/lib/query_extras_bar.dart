import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_to_text.dart';

import 'query_attachment_service.dart';

class QueryExtrasBar extends StatefulWidget {
  const QueryExtrasBar({
    super.key,
    required this.controller,
    this.enabled = true,
  });

  final TextEditingController controller;
  final bool enabled;

  @override
  QueryExtrasBarState createState() => QueryExtrasBarState();
}

class QueryExtrasBarState extends State<QueryExtrasBar> {
  final SpeechToText _speech = SpeechToText();
  final List<QueryAttachment> _attachments = [];
  bool _processing = false;
  bool _listening = false;
  String _voicePrefix = '';

  List<QueryAttachment> get attachments => List.unmodifiable(_attachments);

  void clearAttachments() {
    if (!mounted) return;
    setState(() => _attachments.clear());
  }

  Future<void> _add(String type) async {
    if (_processing || !widget.enabled) return;
    setState(() => _processing = true);
    try {
      QueryAttachment? attachment;
      if (type == 'pdf') attachment = await QueryAttachmentService.pickPdf();
      if (type == 'gallery') attachment = await QueryAttachmentService.pickImageFromGallery();
      if (type == 'camera') attachment = await QueryAttachmentService.takePhoto();
      if (attachment != null && mounted) {
        setState(() => _attachments.add(attachment!));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No pude adjuntar el archivo: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _processing = false);
    }
  }

  Future<void> _toggleVoice() async {
    if (!widget.enabled) return;
    if (_listening) {
      await _speech.stop();
      if (mounted) setState(() => _listening = false);
      return;
    }

    final available = await _speech.initialize(
      onStatus: (status) {
        if (!mounted) return;
        if (status == SpeechToText.doneStatus || status == SpeechToText.notListeningStatus) {
          setState(() => _listening = false);
        }
      },
      onError: (error) {
        if (!mounted) return;
        setState(() => _listening = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No pude escuchar el audio: ${error.errorMsg}')),
        );
      },
    );
    if (!available) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('El reconocimiento de voz no está disponible en este dispositivo.')),
        );
      }
      return;
    }

    _voicePrefix = widget.controller.text.trim();
    if (_voicePrefix.isNotEmpty) _voicePrefix = '$_voicePrefix ';
    setState(() => _listening = true);
    await _speech.listen(
      onResult: _onSpeechResult,
      listenOptions: SpeechListenOptions(
        partialResults: true,
        cancelOnError: true,
        listenMode: ListenMode.dictation,
        autoPunctuation: true,
      ),
    );
  }

  void _onSpeechResult(SpeechRecognitionResult result) {
    final text = '$_voicePrefix${result.recognizedWords}'.trimRight();
    widget.controller.value = TextEditingValue(
      text: text,
      selection: TextSelection.collapsed(offset: text.length),
    );
  }

  @override
  void dispose() {
    _speech.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            PopupMenuButton<String>(
              enabled: widget.enabled && !_processing,
              tooltip: 'Adjuntar',
              icon: _processing
                  ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.attach_file_rounded),
              onSelected: _add,
              itemBuilder: (context) => const [
                PopupMenuItem(value: 'pdf', child: ListTile(leading: Icon(Icons.picture_as_pdf_rounded), title: Text('PDF'))),
                PopupMenuItem(value: 'camera', child: ListTile(leading: Icon(Icons.photo_camera_rounded), title: Text('Tomar foto'))),
                PopupMenuItem(value: 'gallery', child: ListTile(leading: Icon(Icons.image_rounded), title: Text('Galería / screenshot'))),
              ],
            ),
            IconButton(
              onPressed: widget.enabled ? _toggleVoice : null,
              tooltip: _listening ? 'Detener dictado' : 'Preguntar por voz',
              icon: Icon(_listening ? Icons.mic_rounded : Icons.mic_none_rounded),
            ),
            if (_listening)
              const Expanded(
                child: Text('Escuchando… habla tu pregunta', style: TextStyle(fontWeight: FontWeight.w600)),
              )
            else
              const Expanded(
                child: Text('Adjunta PDF, foto o screenshot • o dicta la pregunta', style: TextStyle(fontSize: 12)),
              ),
          ],
        ),
        if (_attachments.isNotEmpty)
          Wrap(
            spacing: 7,
            runSpacing: 7,
            children: [
              for (var i = 0; i < _attachments.length; i++)
                InputChip(
                  avatar: Icon(_attachments[i].isImage ? Icons.image_outlined : Icons.picture_as_pdf_outlined, size: 18),
                  label: Text(_attachments[i].name, overflow: TextOverflow.ellipsis),
                  onDeleted: widget.enabled
                      ? () => setState(() => _attachments.removeAt(i))
                      : null,
                ),
            ],
          ),
      ],
    );
  }
}
