import 'package:flutter_test/flutter_test.dart';
import 'package:memora/pdf_text_heuristics.dart';
import 'package:memora/study_engine.dart';

void main() {
  group('Smart PDF extraction regressions', () {
    test('joins a wrapped financial formula', () {
      final lines = PdfTextHeuristics.mergeLines([
        'Real Return = (1 + Nominal Return)',
        '/ (1 + Inflation) - 1',
      ]);
      expect(lines.length, 1);
      expect(lines.single, contains('Real Return ='));
      expect(lines.single, contains('Inflation'));
    });

    test('repairs hyphenated words split across PDF lines', () {
      final lines = PdfTextHeuristics.mergeLines([
        'Diversifica-',
        'tion reduces unsystematic risk.',
      ]);
      expect(lines.single, contains('Diversification'));
    });

    test('removes repeated running headers and page numbers', () {
      final cleaned = PdfTextHeuristics.removeFurniture([
        ['Finance Handbook', 'Chapter text one', '1'],
        ['Finance Handbook', 'Chapter text two', '2'],
        ['Finance Handbook', 'Chapter text three', '3'],
      ]);
      expect(cleaned.every((page) => !page.contains('Finance Handbook')), isTrue);
      expect(cleaned.expand((page) => page).any((line) => line == '1'), isFalse);
    });

    test('keeps formula-based card generation meaningful', () {
      final cards = StudyEngine.buildCards(
        'Real Return\n'
        'Real Return = (1 + Nominal Return) / (1 + Inflation) - 1\n'
        'Real return measures purchasing-power growth after inflation.',
      );
      expect(cards, isNotEmpty);
      expect(
        cards.any((card) =>
            card.question.toLowerCase().contains('real return') &&
            card.answer.contains('Inflation')),
        isTrue,
      );
    });

    test('quality score penalizes broken extraction', () {
      final good = PdfTextHeuristics.quality(
        'Compound interest grows principal and accumulated interest over time. '
        'The effective annual rate reflects compounding frequency.',
      );
      final broken = PdfTextHeuristics.quality('� | _ | � | _ |');
      expect(good, greaterThan(broken));
    });
  });
}
