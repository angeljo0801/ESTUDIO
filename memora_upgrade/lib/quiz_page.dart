import 'dart:math';

import 'package:flutter/material.dart';

import 'models.dart';

class QuizPage extends StatefulWidget {
  const QuizPage({super.key, required this.guide, required this.onSave});

  final StudyGuide guide;
  final Future<void> Function() onSave;

  @override
  State<QuizPage> createState() => _QuizPageState();
}

class _QuizPageState extends State<QuizPage> {
  late final List<StudyCard> _questions;
  int _index = 0;
  int _score = 0;
  String? _selected;
  bool _answered = false;

  @override
  void initState() {
    super.initState();
    _questions = List<StudyCard>.from(widget.guide.cards)..shuffle(Random());
    if (_questions.length > 20) {
      _questions.removeRange(20, _questions.length);
    }
  }

  StudyCard get _card => _questions[_index];

  List<String> _optionsFor(StudyCard card) {
    final options = <String>{card.answer};
    final pool = widget.guide.cards.where((item) => item.id != card.id).toList()
      ..shuffle(Random());
    for (final other in pool) {
      if (other.answer.trim().isEmpty) continue;
      options.add(other.answer);
      if (options.length >= 4) break;
    }
    final list = options.toList()..shuffle(Random());
    return list;
  }

  void _choose(String option) {
    if (_answered) return;
    final correct = option == _card.answer;
    if (correct) {
      _score += 1;
      _card.rate(2);
    } else {
      _card.rate(0);
    }
    widget.guide.lastStudiedAt = DateTime.now();
    setState(() {
      _selected = option;
      _answered = true;
    });
  }

  Future<void> _next() async {
    if (_index >= _questions.length - 1) {
      await widget.onSave();
      if (!mounted) return;
      setState(() => _index += 1);
      return;
    }
    setState(() {
      _index += 1;
      _selected = null;
      _answered = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_index >= _questions.length) {
      final percent = _questions.isEmpty ? 0 : ((_score / _questions.length) * 100).round();
      return Scaffold(
        appBar: AppBar(title: const Text('Resultado')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(percent >= 70 ? Icons.emoji_events_rounded : Icons.replay_rounded, size: 84),
                const SizedBox(height: 18),
                Text('$percent%', style: const TextStyle(fontSize: 48, fontWeight: FontWeight.w900)),
                Text('$_score de ${_questions.length} correctas'),
                const SizedBox(height: 24),
                FilledButton.icon(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.done_rounded),
                  label: const Text('Terminar'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final options = _optionsFor(_card);
    return Scaffold(
      appBar: AppBar(
        title: Text('Examen ${_index + 1}/${_questions.length}'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(4),
          child: LinearProgressIndicator(value: (_index + 1) / _questions.length, minHeight: 4),
        ),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(22),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('PREGUNTA', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 1.3)),
                    const SizedBox(height: 14),
                    Text(_card.question, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, height: 1.3)),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),
            for (final option in options)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _OptionTile(
                  text: option,
                  answered: _answered,
                  selected: _selected == option,
                  correct: option == _card.answer,
                  onTap: () => _choose(option),
                ),
              ),
            if (_answered) ...[
              const SizedBox(height: 8),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(_selected == _card.answer ? Icons.check_circle_rounded : Icons.info_rounded),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          _selected == _card.answer
                              ? 'Correcto.'
                              : 'Respuesta correcta: ${_card.answer}',
                          style: const TextStyle(height: 1.4),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 10),
              FilledButton(
                onPressed: _next,
                style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
                child: Text(_index == _questions.length - 1 ? 'Ver resultado' : 'Siguiente'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _OptionTile extends StatelessWidget {
  const _OptionTile({
    required this.text,
    required this.answered,
    required this.selected,
    required this.correct,
    required this.onTap,
  });

  final String text;
  final bool answered;
  final bool selected;
  final bool correct;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    Color? background;
    IconData? icon;
    if (answered && correct) {
      background = Theme.of(context).colorScheme.primaryContainer;
      icon = Icons.check_circle_rounded;
    } else if (answered && selected && !correct) {
      background = Theme.of(context).colorScheme.errorContainer;
      icon = Icons.cancel_rounded;
    }

    return Material(
      color: background ?? Theme.of(context).colorScheme.surfaceContainer,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: answered ? null : onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
          child: Row(
            children: [
              Expanded(child: Text(text, style: const TextStyle(height: 1.35))),
              if (icon != null) ...[
                const SizedBox(width: 8),
                Icon(icon),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
