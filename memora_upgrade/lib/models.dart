class StudyCard {
  StudyCard({
    required this.id,
    required this.question,
    required this.answer,
    required this.source,
    required this.dueAt,
    this.intervalDays = 0,
    this.ease = 2.5,
    this.correct = 0,
    this.wrong = 0,
    this.streak = 0,
  });

  final String id;
  final String question;
  final String answer;
  final String source;
  DateTime dueAt;
  int intervalDays;
  double ease;
  int correct;
  int wrong;
  int streak;

  bool get isDue => !dueAt.isAfter(DateTime.now());

  void rate(int quality) {
    final now = DateTime.now();
    if (quality <= 0) {
      wrong += 1;
      streak = 0;
      intervalDays = 0;
      ease = (ease - 0.20).clamp(1.3, 3.0);
      dueAt = now.add(const Duration(minutes: 10));
      return;
    }

    correct += 1;
    streak += 1;
    if (quality == 1) {
      ease = (ease - 0.10).clamp(1.3, 3.0);
      intervalDays = intervalDays <= 1 ? 1 : (intervalDays * 1.25).round();
    } else if (quality == 2) {
      intervalDays = switch (streak) {
        1 => 1,
        2 => 3,
        _ => (intervalDays * ease).round().clamp(2, 365),
      };
    } else {
      ease = (ease + 0.10).clamp(1.3, 3.0);
      intervalDays = switch (streak) {
        1 => 3,
        2 => 7,
        _ => (intervalDays * (ease + 0.35)).round().clamp(4, 365),
      };
    }
    dueAt = now.add(Duration(days: intervalDays));
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'question': question,
        'answer': answer,
        'source': source,
        'dueAt': dueAt.toIso8601String(),
        'intervalDays': intervalDays,
        'ease': ease,
        'correct': correct,
        'wrong': wrong,
        'streak': streak,
      };

  factory StudyCard.fromJson(Map<String, dynamic> json) => StudyCard(
        id: json['id'] as String,
        question: json['question'] as String,
        answer: json['answer'] as String,
        source: (json['source'] as String?) ?? '',
        dueAt: DateTime.tryParse((json['dueAt'] as String?) ?? '') ?? DateTime.now(),
        intervalDays: (json['intervalDays'] as num?)?.toInt() ?? 0,
        ease: (json['ease'] as num?)?.toDouble() ?? 2.5,
        correct: (json['correct'] as num?)?.toInt() ?? 0,
        wrong: (json['wrong'] as num?)?.toInt() ?? 0,
        streak: (json['streak'] as num?)?.toInt() ?? 0,
      );
}

class StudyGuide {
  StudyGuide({
    required this.id,
    required this.title,
    required this.sourceType,
    required this.sourceName,
    required this.text,
    required this.summary,
    required this.cards,
    required this.createdAt,
    this.filePath,
    this.lastStudiedAt,
  });

  final String id;
  String title;
  final String sourceType;
  final String sourceName;
  final String text;
  String summary;
  List<StudyCard> cards;
  final DateTime createdAt;
  final String? filePath;
  DateTime? lastStudiedAt;

  bool get hasFile => filePath != null && filePath!.trim().isNotEmpty;
  int get dueCount => cards.where((card) => card.isDue).length;
  int get totalCorrect => cards.fold(0, (sum, card) => sum + card.correct);
  int get totalWrong => cards.fold(0, (sum, card) => sum + card.wrong);
  int get attempts => totalCorrect + totalWrong;
  double get accuracy => attempts == 0 ? 0 : totalCorrect / attempts;
  int get masteredCount => cards.where((card) => card.streak >= 3 && card.intervalDays >= 7).length;

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'sourceType': sourceType,
        'sourceName': sourceName,
        'text': text,
        'summary': summary,
        'cards': cards.map((card) => card.toJson()).toList(),
        'createdAt': createdAt.toIso8601String(),
        'filePath': filePath,
        'lastStudiedAt': lastStudiedAt?.toIso8601String(),
      };

  factory StudyGuide.fromJson(Map<String, dynamic> json) => StudyGuide(
        id: json['id'] as String,
        title: json['title'] as String,
        sourceType: (json['sourceType'] as String?) ?? 'texto',
        sourceName: (json['sourceName'] as String?) ?? '',
        text: (json['text'] as String?) ?? '',
        summary: (json['summary'] as String?) ?? '',
        cards: ((json['cards'] as List<dynamic>?) ?? const [])
            .map((item) => StudyCard.fromJson(Map<String, dynamic>.from(item as Map)))
            .toList(),
        createdAt: DateTime.tryParse((json['createdAt'] as String?) ?? '') ?? DateTime.now(),
        filePath: json['filePath']?.toString(),
        lastStudiedAt: json['lastStudiedAt'] == null
            ? null
            : DateTime.tryParse(json['lastStudiedAt'] as String),
      );
}
