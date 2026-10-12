import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'adventure_engine.dart';
import 'guide_store.dart';
import 'models.dart';

/// A free, offline, animated interactive lesson - not an MP4 generator.
class AdventurePage extends StatefulWidget {
  const AdventurePage({super.key, required this.store, required this.guide});

  final GuideStore store;
  final StudyGuide guide;

  @override
  State<AdventurePage> createState() => _AdventurePageState();
}

class _AdventurePageState extends State<AdventurePage> {
  int _unlocked = 1;
  int _xp = 0;
  bool _loading = true;
  late final List<AdventureEpisode> _episodes;

  String get _key => 'memora_adventure_${widget.guide.id}';

  @override
  void initState() {
    super.initState();
    _episodes = AdventureEngine.episodesFor(widget.guide);
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() {
      _unlocked = max(1, prefs.getInt('${_key}_unlocked') ?? 1);
      _xp = prefs.getInt('${_key}_xp') ?? 0;
      _loading = false;
    });
  }

  Future<void> _open(AdventureEpisode episode) async {
    await Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => _EpisodePlayer(
        store: widget.store,
        guide: widget.guide,
        episode: episode,
        allCards: widget.guide.cards,
        progressKey: _key,
      ),
    ));
    if (mounted) await _load();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Memora Aventuras')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
              children: [
                Container(
                  padding: const EdgeInsets.all(22),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(colors: [cs.primaryContainer, cs.tertiaryContainer]),
                    borderRadius: BorderRadius.circular(25),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('🎬  TEMPORADA DE ESTUDIO', style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 1)),
                      const SizedBox(height: 10),
                      Text(widget.guide.title, style: const TextStyle(fontSize: 23, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 9),
                      const Text('Historias animadas, voz, preguntas y puntos. Todo basado en las tarjetas de tu guía.'),
                      const SizedBox(height: 15),
                      Wrap(spacing: 9, runSpacing: 8, children: [
                        Chip(avatar: const Icon(Icons.stars_rounded, size: 18), label: Text('$_xp XP')),
                        Chip(avatar: const Icon(Icons.movie_filter_rounded, size: 18), label: Text('${_episodes.length} episodios')),
                        Chip(avatar: const Icon(Icons.offline_bolt_rounded, size: 18), label: const Text('Sin API de pago')),
                      ]),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                const Text('Elige tu próximo episodio', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 19)),
                const SizedBox(height: 10),
                if (_episodes.isEmpty)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(18),
                      child: Text('Esta guía todavía no tiene preguntas utilizables. Crea o corrige sus tarjetas para comenzar la aventura.'),
                    ),
                  ),
                for (final episode in _episodes)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 9),
                    child: Card(
                      child: ListTile(
                        contentPadding: const EdgeInsets.fromLTRB(16, 10, 12, 10),
                        leading: CircleAvatar(
                          radius: 27,
                          backgroundColor: cs.primaryContainer,
                          child: Text(episode.number > _unlocked ? '🔒' : episode.icon,
                              style: const TextStyle(fontSize: 24)),
                        ),
                        title: Text('Episodio ${episode.number}',
                            style: const TextStyle(fontWeight: FontWeight.w800)),
                        subtitle: Text(episode.title,
                            maxLines: 2, overflow: TextOverflow.ellipsis),
                        trailing: Icon(episode.number > _unlocked
                            ? Icons.lock_outline_rounded
                            : episode.number < _unlocked
                                ? Icons.check_circle_outline_rounded
                                : Icons.play_circle_fill_rounded),
                        enabled: episode.number <= _unlocked,
                        onTap: episode.number <= _unlocked ? () => _open(episode) : null,
                      ),
                    ),
                  ),
                const SizedBox(height: 8),
                const Text(
                  'Cada episodio contiene hasta tres desafíos. Las respuestas se guardan en el repaso de Memora; lo que falles aparecerá antes para volver a practicar.',
                  style: TextStyle(height: 1.4),
                ),
              ],
            ),
    );
  }
}

class _EpisodePlayer extends StatefulWidget {
  const _EpisodePlayer({
    required this.store,
    required this.guide,
    required this.episode,
    required this.allCards,
    required this.progressKey,
  });

  final GuideStore store;
  final StudyGuide guide;
  final AdventureEpisode episode;
  final List<StudyCard> allCards;
  final String progressKey;

  @override
  State<_EpisodePlayer> createState() => _EpisodePlayerState();
}

class _EpisodePlayerState extends State<_EpisodePlayer> {
  final FlutterTts _tts = FlutterTts();
  int _step = 0;
  int _earned = 0;
  bool _voiceOn = true;
  bool _finished = false;
  bool _rated = false;
  bool _needsSelfGrade = false;
  bool _saving = false;
  bool? _wasCorrect;
  String? _selected;
  String _stage = 'story';

  StudyCard get _card => widget.episode.cards[_step];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _say(_narrative());
    });
  }

  @override
  void dispose() {
    _tts.stop();
    super.dispose();
  }

  String _narrative() {
    return '${AdventureEngine.storyHook(_step)} '
        'La respuesta de la guía es: ${_card.answer}.';
  }

  Future<void> _say(String text) async {
    if (!_voiceOn || !mounted) return;
    try {
      await _tts.stop();
      final english = RegExp(r'\b(the|what|which|with|from|this|that|how)\b', caseSensitive: false)
              .allMatches(text).length >= 2;
      await _tts.setLanguage(english ? 'en-US' : 'es-ES');
      await _tts.setSpeechRate(0.47);
      await _tts.setPitch(1.05);
      if (_voiceOn && mounted) await _tts.speak(text);
    } catch (_) {
      // Device TTS voice packs can be missing; the lesson remains usable.
    }
  }

  void _changeStage(String next, {String? voiceText}) {
    setState(() => _stage = next);
    if (voiceText != null) _say(voiceText);
  }

  Future<void> _answer(bool correct, {String? selected}) async {
    if (_saving || _rated) return;
    setState(() {
      _saving = true;
      _rated = true;
      _needsSelfGrade = false;
      _wasCorrect = correct;
      _selected = selected;
      _stage = 'feedback';
      _earned += correct ? 100 : 20;
    });
    _tts.stop();
    _card.rate(correct ? 2 : 0);
    widget.guide.lastStudiedAt = DateTime.now();
    try {
      await widget.store.update(widget.guide);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No pude guardar el repaso; revisa el almacenamiento.')),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
    if (mounted) _say(correct ? '¡Excelente! ${_card.answer}' : 'Seguimos aprendiendo. ${_card.answer}');
  }

  Future<void> _complete() async {
    _tts.stop();
    final prefs = await SharedPreferences.getInstance();
    final bestKey = '${widget.progressKey}_best_${widget.episode.number}';
    final previousBest = prefs.getInt(bestKey) ?? 0;
    final extra = max(0, _earned - previousBest);
    await prefs.setInt(bestKey, max(previousBest, _earned));
    await prefs.setInt(widget.progressKey + '_xp',
        (prefs.getInt(widget.progressKey + '_xp') ?? 0) + extra);
    final next = widget.episode.number + 1;
    final unlocked = prefs.getInt(widget.progressKey + '_unlocked') ?? 1;
    if (next > unlocked) {
      await prefs.setInt(widget.progressKey + '_unlocked', next);
    }
    if (mounted) setState(() => _finished = true);
  }

  void _next() {
    if (_step + 1 >= widget.episode.cards.length) {
      _complete();
      return;
    }
    setState(() {
      _step++;
      _stage = 'story';
      _rated = false;
      _wasCorrect = null;
      _needsSelfGrade = false;
      _selected = null;
    });
    _say(_narrative());
  }

  Widget _robot(ColorScheme cs) {
    return TweenAnimationBuilder<double>(
      key: ValueKey<String>('${_stage}_$_step'),
      tween: Tween(begin: 0.88, end: 1),
      duration: const Duration(milliseconds: 650),
      curve: Curves.elasticOut,
      builder: (context, scale, child) => Transform.scale(scale: scale, child: child),
      child: Container(
        width: 126,
        height: 126,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: LinearGradient(colors: [cs.primaryContainer, cs.tertiaryContainer]),
          boxShadow: [BoxShadow(color: cs.primary.withValues(alpha: 0.25), blurRadius: 35)],
        ),
        child: Text(widget.episode.icon == '🚀' ? '🤖' : widget.episode.icon,
            style: const TextStyle(fontSize: 69)),
      ),
    );
  }

  Widget _story(ColorScheme cs) => Column(
        key: const ValueKey('story'),
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('🎭 ESCENA ANIMADA', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1)),
          const SizedBox(height: 12),
          Text(AdventureEngine.storyHook(_step),
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
          const SizedBox(height: 20),
          Card(
            color: cs.surfaceContainerHigh,
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('📖 Del material de tu guía', style: TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 12),
                SelectableText(_card.answer, style: const TextStyle(fontSize: 19, height: 1.5)),
                if (_card.source.trim().isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text('Fuente: ${_card.source}', style: Theme.of(context).textTheme.bodySmall,
                      maxLines: 3, overflow: TextOverflow.ellipsis),
                ],
              ]),
            ),
          ),
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: () => _changeStage('challenge', voiceText: _card.question),
            icon: const Icon(Icons.sports_esports_rounded),
            label: const Text('¡Acepto el desafío!'),
          ),
        ],
      );

  Widget _challenge(ColorScheme cs) {
    final choices = AdventureEngine.choicesFor(_card, widget.allCards);
    return Column(
      key: const ValueKey('challenge'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text('⚡ DESAFÍO DE MEMORIA', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1)),
        const SizedBox(height: 14),
        Text(_card.question, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
        const SizedBox(height: 18),
        if (choices.isNotEmpty)
          for (final choice in choices)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: OutlinedButton(
                onPressed: _saving ? null : () => _answer(choice == _card.answer.trim(), selected: choice),
                style: OutlinedButton.styleFrom(padding: const EdgeInsets.all(16),
                    alignment: Alignment.centerLeft),
                child: Text(choice, style: const TextStyle(fontSize: 16)),
              ),
            )
        else ...[
          const Text('Trata de responder en voz alta o mentalmente antes de revelar la respuesta.'),
          const SizedBox(height: 15),
          FilledButton.icon(
            onPressed: () {
              _tts.stop();
              setState(() {
                _stage = 'feedback';
                _needsSelfGrade = true;
              });
            },
            icon: const Icon(Icons.visibility_rounded),
            label: const Text('Ver la respuesta'),
          ),
        ],
      ],
    );
  }

  Widget _feedback(ColorScheme cs) => Column(
        key: const ValueKey('feedback'),
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(_needsSelfGrade
              ? '🎯 Comprueba tu respuesta'
              : _wasCorrect == true ? '🎉 ¡Correcto! +100 XP' : '🧠 ¡A seguir practicando! +20 XP',
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
          const SizedBox(height: 14),
          if (_selected != null && _wasCorrect == false)
            Text('Elegiste: $_selected', style: TextStyle(color: cs.error)),
          Card(
            color: cs.surfaceContainerHigh,
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('Respuesta de la guía', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 12),
                SelectableText(_card.answer, style: const TextStyle(fontSize: 19, height: 1.4)),
              ]),
            ),
          ),
          const SizedBox(height: 15),
          if (_needsSelfGrade) ...[
            FilledButton.icon(
              onPressed: _saving ? null : () => _answer(true),
              icon: const Icon(Icons.check_rounded),
              label: const Text('La recordé bien'),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _saving ? null : () => _answer(false),
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Necesito repasarla'),
            ),
          ] else
            FilledButton.icon(
              onPressed: _saving ? null : _next,
              icon: const Icon(Icons.arrow_forward_rounded),
              label: Text(_step + 1 == widget.episode.cards.length
                  ? 'Terminar episodio' : 'Siguiente escena'),
            ),
        ],
      );

  Widget _ending() => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('🏆', style: TextStyle(fontSize: 90)),
            const SizedBox(height: 12),
            const Text('¡Episodio completado!', textAlign: TextAlign.center,
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 24)),
            const SizedBox(height: 12),
            Text('Conseguiste $_earned XP en esta partida',
                textAlign: TextAlign.center, style: const TextStyle(fontSize: 18)),
            const SizedBox(height: 15),
            const Text('Tus resultados se añadieron al repaso espaciado de Memora.',
                textAlign: TextAlign.center),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: () => Navigator.pop(context),
              icon: const Icon(Icons.list_rounded),
              label: const Text('Volver a episodios'),
            ),
          ],
        ),
      );

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: Text('Episodio ${widget.episode.number}'),
        actions: [
          IconButton(
            tooltip: _voiceOn ? 'Silenciar narración' : 'Activar narración',
            icon: Icon(_voiceOn ? Icons.volume_up_rounded : Icons.volume_off_rounded),
            onPressed: () {
              setState(() => _voiceOn = !_voiceOn);
              if (!_voiceOn) {
                _tts.stop();
              } else if (!_finished) {
                _say(_stage == 'story' ? _narrative()
                    : _stage == 'challenge' ? _card.question : _card.answer);
              }
            },
          ),
        ],
      ),
      body: SafeArea(
        child: _finished ? Padding(padding: const EdgeInsets.all(25), child: _ending()) :
          ListView(
            padding: const EdgeInsets.fromLTRB(18, 8, 18, 28),
            children: [
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                Text('Escena ${_step + 1} de ${widget.episode.cards.length}'),
                Text('⭐ $_earned XP', style: const TextStyle(fontWeight: FontWeight.bold)),
              ]),
              const SizedBox(height: 9),
              LinearProgressIndicator(
                value: (_step + (_stage == 'story' ? 0 : _stage == 'challenge' ? .5 : 1)) /
                    widget.episode.cards.length,
                minHeight: 8,
                borderRadius: BorderRadius.circular(8),
              ),
              const SizedBox(height: 23),
              Center(child: _robot(cs)),
              const SizedBox(height: 24),
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 250),
                child: _stage == 'story' ? _story(cs)
                    : _stage == 'challenge' ? _challenge(cs) : _feedback(cs),
              ),
            ],
          ),
      ),
    );
  }
}
