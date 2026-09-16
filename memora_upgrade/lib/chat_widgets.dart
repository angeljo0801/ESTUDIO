import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'chat_store.dart';
import 'on_device_translation_service.dart';

class ChatTranscript extends StatefulWidget {
  const ChatTranscript({
    super.key,
    required this.messages,
    required this.participantName,
    this.emptyText = 'Start a conversation.',
  });

  final List<ChatMessage> messages;
  final String participantName;
  final String emptyText;

  @override
  State<ChatTranscript> createState() => _ChatTranscriptState();
}

class _ChatTranscriptState extends State<ChatTranscript> {
  static const _autoSpanishKey = 'memora_auto_translate_spanish';
  bool _autoSpanish = false;

  @override
  void initState() {
    super.initState();
    _loadTranslationPreference();
    OnDeviceTranslationService.warmUpSpanish();
  }

  Future<void> _loadTranslationPreference() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() => _autoSpanish = prefs.getBool(_autoSpanishKey) ?? false);
  }

  Future<void> _setAutoSpanish(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_autoSpanishKey, value);
    if (!mounted) return;
    setState(() => _autoSpanish = value);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          value
              ? 'Auto ES enabled. New assistant replies will be translated to Spanish.'
              : 'Auto ES disabled.',
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (widget.messages.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            widget.emptyText,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ),
      );
    }

    return ListView.builder(
      reverse: true,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
      itemCount: widget.messages.length,
      itemBuilder: (context, index) {
        final message = widget.messages[widget.messages.length - 1 - index];
        return _ChatBubble(
          key: ValueKey(
            '${message.createdAt.microsecondsSinceEpoch}:${message.role}:${message.text.hashCode}',
          ),
          message: message,
          participantName: widget.participantName,
          autoSpanish: _autoSpanish,
          onAutoSpanishChanged: _setAutoSpanish,
        );
      },
    );
  }
}

class _ChatBubble extends StatefulWidget {
  const _ChatBubble({
    super.key,
    required this.message,
    required this.participantName,
    required this.autoSpanish,
    required this.onAutoSpanishChanged,
  });

  final ChatMessage message;
  final String participantName;
  final bool autoSpanish;
  final Future<void> Function(bool value) onAutoSpanishChanged;

  @override
  State<_ChatBubble> createState() => _ChatBubbleState();
}

class _ChatBubbleState extends State<_ChatBubble> {
  String? _spanish;
  bool _showSpanish = false;
  bool _translating = false;

  bool get _mine => widget.message.role == 'user';

  bool get _isTemporaryStatus {
    final text = widget.message.text.trim().toLowerCase();
    return text == 'thinking...' ||
        text == 'thinking…' ||
        text == 'reading the guide...' ||
        text == 'reading the guide…';
  }

  bool get _canTranslate =>
      !_mine && widget.message.text.trim().isNotEmpty && !_isTemporaryStatus;

  @override
  void initState() {
    super.initState();
    if (widget.autoSpanish && _canTranslate) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _translate(show: true));
    }
  }

  @override
  void didUpdateWidget(covariant _ChatBubble oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.message.text != widget.message.text) {
      _spanish = null;
      _showSpanish = false;
      _translating = false;
      if (widget.autoSpanish && _canTranslate) {
        WidgetsBinding.instance.addPostFrameCallback((_) => _translate(show: true));
      }
    } else if (!oldWidget.autoSpanish && widget.autoSpanish && _canTranslate) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _translate(show: true));
    }
  }

  Future<void> _translate({required bool show}) async {
    if (!_canTranslate || _translating) return;
    if (_spanish != null) {
      if (mounted) setState(() => _showSpanish = show);
      return;
    }
    if (mounted) {
      setState(() {
        _translating = true;
        if (show) _showSpanish = true;
      });
    }
    try {
      final translated = await OnDeviceTranslationService.toSpanish(widget.message.text);
      if (!mounted) return;
      setState(() {
        _spanish = translated;
        _showSpanish = show;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _translating = false;
        _showSpanish = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Spanish translation is not ready yet. Check your connection once so Android can download the offline translator. ($e)',
          ),
        ),
      );
      return;
    }
    if (mounted) setState(() => _translating = false);
  }

  Future<void> _toggleSpanish() async {
    if (_showSpanish) {
      setState(() => _showSpanish = false);
      return;
    }
    await _translate(show: true);
  }

  @override
  Widget build(BuildContext context) {
    final displayedText = _showSpanish && _spanish != null
        ? _spanish!
        : widget.message.text;

    return Align(
      alignment: _mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * .82),
        margin: const EdgeInsets.symmetric(vertical: 5),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: _mine
              ? Theme.of(context).colorScheme.primaryContainer
              : Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(_mine ? 16 : 4),
            bottomRight: Radius.circular(_mine ? 4 : 16),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _mine ? 'You' : widget.participantName,
              style: Theme.of(context)
                  .textTheme
                  .labelSmall
                  ?.copyWith(fontWeight: FontWeight.bold),
            ),
            if (widget.message.attachments.isNotEmpty) ...[
              const SizedBox(height: 4),
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children: [
                  for (final name in widget.message.attachments)
                    Chip(
                      visualDensity: VisualDensity.compact,
                      avatar: const Icon(Icons.attach_file, size: 15),
                      label: Text(name, overflow: TextOverflow.ellipsis),
                    ),
                ],
              ),
            ],
            if (widget.message.text.isNotEmpty) ...[
              const SizedBox(height: 5),
              SelectableText(
                _translating && _showSpanish && _spanish == null
                    ? 'Translating to Spanish…'
                    : displayedText,
              ),
            ],
            if (_canTranslate) ...[
              const SizedBox(height: 4),
              Wrap(
                spacing: 2,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  TextButton.icon(
                    onPressed: _translating ? null : _toggleSpanish,
                    style: TextButton.styleFrom(
                      visualDensity: VisualDensity.compact,
                      padding: const EdgeInsets.symmetric(horizontal: 6),
                    ),
                    icon: const Icon(Icons.translate, size: 17),
                    label: Text(_showSpanish ? 'Original' : 'ES'),
                  ),
                  TextButton.icon(
                    onPressed: () => widget.onAutoSpanishChanged(!widget.autoSpanish),
                    style: TextButton.styleFrom(
                      visualDensity: VisualDensity.compact,
                      padding: const EdgeInsets.symmetric(horizontal: 6),
                    ),
                    icon: Icon(
                      widget.autoSpanish
                          ? Icons.check_circle_outline
                          : Icons.autorenew_rounded,
                      size: 17,
                    ),
                    label: Text(widget.autoSpanish ? 'Auto ES on' : 'Auto ES'),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
