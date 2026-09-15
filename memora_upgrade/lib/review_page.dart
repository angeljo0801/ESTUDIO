import 'dart:math';

import 'package:flutter/material.dart';

import 'models.dart';
import 'study_engine.dart';

class ReviewPage extends StatefulWidget {
  const ReviewPage({super.key, required this.guide, required this.onSave});

  final StudyGuide guide;
  final Future<void> Function() onSave;

  @override
  State<ReviewPage> createState() => _ReviewPageState();
}

class _ReviewPageState extends State<ReviewPage> {
  late List<StudyCard> _queue;
  int _index = 0;
  bool _revealed = false;
  int _good = 0;
  int _again = 0;

  @override
  void initState() {
    super.initState();
    final usable = widget.guide.cards.where(StudyEngine.isCardUsable).toList();
    final due = usable.where((card) => card.isDue).toList();
    _queue = due.isNotEmpty ? due : usable;
    _queue.shuffle(Random());
  }

  StudyCard get _card => _queue[_index];

  Future<void> _rate(int quality) async {
    _card.rate(quality);
    if (quality == 0) {
      _again += 1;
    } else {
      _good += 1;
    }
    widget.guide.lastStudiedAt = DateTime.now();
    if (_index >= _queue.length - 1) {
      await widget.onSave();
      if (!mounted) return;
      setState(() => _index += 1);
      return;
    }
    setState(() {
      _index += 1;
      _revealed = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_index >= _queue.length) {
      return Scaffold(
        appBar: AppBar(title: const Text('Repaso terminado')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.celebration_rounded, size: 80),
                const SizedBox(height: 18),
                Text(
                  _queue.isEmpty ? 'No hay tarjetas válidas para repasar' : 'Sesión completada',
                  style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w900),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 10),
                Text(
                  _queue.isEmpty
                      ? 'Memora descartó tarjetas incompletas o fragmentadas de esta guía.'
                      : '$_good bien • $_again para reforzar',
                  textAlign: TextAlign.center,
                ),
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

    final progress = (_index + 1) / _queue.length;
    return Scaffold(
      appBar: AppBar(
        title: Text('${_index + 1} / ${_queue.length}'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(4),
          child: LinearProgressIndicator(value: progress, minHeight: 4),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            children: [
              if (_card.source.isNotEmpty)
                Align(
                  alignment: Alignment.centerLeft,
                  child: Chip(label: Text(_card.source, maxLines: 1, overflow: TextOverflow.ellipsis)),
                ),
              Expanded(
                child: Center(
                  child: SingleChildScrollView(
                    child: Card(
                      child: InkWell(
                        borderRadius: BorderRadius.circular(22),
                        onTap: () => setState(() => _revealed = true),
                        child: Container(
                          width: double.infinity,
                          constraints: const BoxConstraints(minHeight: 320),
                          padding: const EdgeInsets.all(24),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Text('PREGUNTA', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 1.4)),
                              const SizedBox(height: 16),
                              Text(
                                _card.question,
                                textAlign: TextAlign.center,
                                style: const TextStyle(fontSize: 23, fontWeight: FontWeight.w800, height: 1.25),
                              ),
                              if (_revealed) ...[
                                const Padding(
                                  padding: EdgeInsets.symmetric(vertical: 24),
                                  child: Divider(),
                                ),
                                const Text('RESPUESTA', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 1.4)),
                                const SizedBox(height: 12),
                                Text(
                                  _card.answer,
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(fontSize: 19, height: 1.4),
                                ),
                              ] else ...[
                                const SizedBox(height: 28),
                                const Text('Toca la tarjeta para ver la respuesta'),
                              ],
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              if (!_revealed)
                FilledButton(
                  onPressed: () => setState(() => _revealed = true),
                  style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
                  child: const Text('Mostrar respuesta'),
                )
              else
                Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(
                            onPressed: () => _rate(0),
                            style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(50)),
                            child: const Text('No lo sé'),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: OutlinedButton(
                            onPressed: () => _rate(1),
                            style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(50)),
                            child: const Text('Difícil'),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: FilledButton.tonal(
                            onPressed: () => _rate(2),
                            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50)),
                            child: const Text('Bien'),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: FilledButton(
                            onPressed: () => _rate(3),
                            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50)),
                            child: const Text('Fácil'),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
            ],
          ),
        ),
      ),
    );
  }
}