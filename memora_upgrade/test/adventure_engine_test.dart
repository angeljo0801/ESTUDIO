import 'package:flutter_test/flutter_test.dart';
import 'package:memora/adventure_engine.dart';
import 'package:memora/models.dart';

StudyCard card(int i, String question, String answer) => StudyCard(
  id: 'card_$i',
  question: question,
  answer: answer,
  source: 'Chapter 1',
  dueAt: DateTime(2020),
);

StudyGuide guideWithCards(List<StudyCard> cards) => StudyGuide(
  id: 'test-guide',
  title: 'Electricity',
  sourceType: 'quiz',
  sourceName: 'electricity.json',
  text: '',
  summary: '',
  cards: cards,
  createdAt: DateTime(2026),
);

void main() {
  test('turns all study cards into chapters of at most three', () {
    final guide = guideWithCards([
      card(1, 'What is voltage?', 'Electrical potential difference.'),
      card(2, 'What is resistance?', 'Opposition to current.'),
      card(3, 'What is current?', 'Electric charge per second.'),
      card(4, 'What is a circuit?', 'A complete conductive path.'),
    ]);
    final episodes = AdventureEngine.episodesFor(guide);
    expect(episodes.length, 2);
    expect(episodes[0].cards.length, 3);
    expect(episodes[1].cards.length, 1);
    expect(episodes.expand((e) => e.cards).length, 4);
  });

  test('choices contain exactly one correct answer', () {
    final cards = [
      card(1, 'What is voltage?', 'Electrical potential difference.'),
      card(2, 'What is resistance?', 'Opposition to current.'),
      card(3, 'What is current?', 'Electric charge per second.'),
      card(4, 'What is a circuit?', 'A complete conductive path.'),
    ];
    final choices = AdventureEngine.choicesFor(cards.first, cards);
    expect(choices.length, 4);
    expect(choices.where((c) => c == cards.first.answer).length, 1);
    expect(choices.toSet().length, choices.length);
  });

  test('falls back to memory recall when there are not enough options', () {
    final cards = [
      card(1, 'What is voltage?', 'Electrical potential difference.'),
      card(2, 'What is an alternative term?', 'Electrical potential difference.'),
    ];
    expect(AdventureEngine.choicesFor(cards.first, cards), isEmpty);
  });

  test('handles a completely empty guide without crashing', () {
    expect(AdventureEngine.episodesFor(guideWithCards([])), isEmpty);
  });
}
