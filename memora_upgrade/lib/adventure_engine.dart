import 'dart:math';

import 'models.dart';
import 'study_engine.dart';

/// Offline story episodes grounded in a guide's existing study cards.
/// This engine does not invent facts or pretend to generate AI video.
class AdventureEpisode {
  const AdventureEpisode({
    required this.number,
    required this.title,
    required this.cards,
    required this.icon,
  });
  final int number;
  final String title;
  final List<StudyCard> cards;
  final String icon;
}

class AdventureEngine {
  static List<AdventureEpisode> episodesFor(StudyGuide guide) {
    final cards = guide.cards.where((c) =>
        StudyEngine.isCardUsable(c) ||
        (guide.sourceType == 'quiz' &&
            c.question.trim().isNotEmpty &&
            c.answer.trim().isNotEmpty)).toList();
    final episodes = <AdventureEpisode>[];
    for (var start = 0; start < cards.length; start += 3) {
      final end = min(start + 3, cards.length);
      final chunk = cards.sublist(start, end);
      final first = chunk.first.question.trim();
      final short = first.length > 42 ? '${first.substring(0, 42)}…' : first;
      episodes.add(AdventureEpisode(
        number: episodes.length + 1,
        title: short,
        cards: chunk,
        icon: iconFor(guide.title + ' ' + first),
      ));
    }
    return episodes;
  }

  static String iconFor(String text) {
    final t = text.toLowerCase();
    if (RegExp(r'circuit|volt|electric|resist|electr|ohm|transistor').hasMatch(t)) return '⚡';
    if (RegExp(r'math|algebra|ecuaci|polynomial|formula|calculus').hasMatch(t)) return '🧩';
    if (RegExp(r'network|internet|ubuntu|linux|comput|virtualiz').hasMatch(t)) return '💻';
    if (RegExp(r'histor|war|guerra|century').hasMatch(t)) return '🗺️';
    if (RegExp(r'finance|finanza|interest|interés|money|dinero').hasMatch(t)) return '💰';
    return '🚀';
  }

  static String storyHook(int index) {
    const hooks = [
      '¡Alerta en la estación de aprendizaje! Byte necesita tu ayuda para resolver este misterio.',
      'Nuestro robot perdió una pieza de conocimiento. ¡Vamos a recuperarla!',
      'El laboratorio está listo. Antes de activar la siguiente máquina, descubre esta idea.',
      '¡Nuevo desafío desbloqueado! Byte apuesta que puedes explicarlo mejor que él.',
      'El capitán de la misión pregunta: ¿puedes dominar este concepto?',
    ];
    return hooks[index % hooks.length];
  }

  /// Only use answer choices from other cards. If there are too few
  /// distinct, reliable alternatives, the UI uses self-assessed recall.
  static List<String> choicesFor(StudyCard target, List<StudyCard> all) {
    final correct = target.answer.trim();
    if (correct.isEmpty || correct.length > 150) return [];
    String norm(String s) => s
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-z0-9áéíóúüñ]+'), ' ')
        .trim();
    final correctNorm = norm(correct);
    final used = <String>{correctNorm};
    final wrong = <String>[];
    for (final other in all) {
      if (other.id == target.id) continue;
      final answer = other.answer.trim();
      final normalized = norm(answer);
      if (answer.isEmpty || answer.length > 150 || normalized.length < 3) continue;
      if (used.contains(normalized)) continue;
      // Discard overlapping answers that could also be correct.
      if (normalized.contains(correctNorm) || correctNorm.contains(normalized)) continue;
      used.add(normalized);
      wrong.add(answer);
      if (wrong.length == 3) break;
    }
    if (wrong.length < 2) return [];
    final result = <String>[correct, ...wrong];
    // Stable shuffle so the right answer isn't always the first option.
    result.shuffle(Random(target.id.hashCode));
    return result;
  }
}
