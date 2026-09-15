from pathlib import Path
import re

# Memora v1.20
# Rebuild study cards around meaningful facts/relationships instead of isolated
# words, and stop the exam engine from recycling weak legacy questions.

# -----------------------------------------------------------------------------
# StudyEngine: replace card generation + final card-quality gate.
# -----------------------------------------------------------------------------
p = Path('lib/study_engine.dart')
s = p.read_text()

start = s.find('  static List<StudyCard> buildCards(String text) {')
end = s.find('  /// Final safety check', start)
if start < 0 or end < 0:
    raise RuntimeError('StudyEngine buildCards block not found')

new_build = r'''  static int recommendedCardCount(String text) {
    final words = _words(text).length;
    if (words <= 0) return 0;
    if (words < 120) return (words / 18).ceil().clamp(4, 10).toInt();
    return (words / 58).ceil().clamp(16, 90).toInt();
  }

  static List<StudyCard> buildCards(String text) {
    final clean = _normalize(text);
    if (clean.isEmpty) return const [];

    final target = recommendedCardCount(clean);
    final maxCards = (target + 28).clamp(20, 120).toInt();
    final cards = <StudyCard>[];
    final seen = <String>{};
    final now = DateTime.now();
    var counter = 0;

    bool weakAnswer(String value) {
      final answer = value.replaceAll(RegExp(r'\s+'), ' ').trim();
      final words = _words(answer);
      if (answer.length < 10 || words.length < 3) return true;
      if (answer.endsWith('?')) return true;
      if (RegExp(r'^(?:not\b|part of\b|an?\s+(?:important|key|basic|general)\b)',
              caseSensitive: false)
          .hasMatch(answer)) return true;
      if (words.length <= 7 &&
          RegExp(r'\b(?:thing|part|career|success|important|good|bad|skill)\b',
                  caseSensitive: false)
              .hasMatch(answer)) return true;
      return false;
    }

    bool weakSubject(String value) {
      final subject = value.replaceAll(RegExp(r'\s+'), ' ').trim();
      final words = _words(subject);
      if (subject.length < 3 || subject.length > 80 || words.isEmpty || words.length > 10) {
        return true;
      }
      if ({
        'this', 'that', 'these', 'those', 'it', 'they', 'we', 'you', 'i',
        'he', 'she', 'there', 'here', 'each', 'every', 'when', 'while',
        'because', 'although', 'if', 'then', 'also', 'however', 'therefore',
        'imagine', 'suppose', 'consider', 'remember', 'note',
      }.contains(words.first)) return true;
      if (RegExp(r'[?!:;]').hasMatch(subject)) return true;
      return false;
    }

    String tidy(String value) => value
        .replaceAll(RegExp(r'\s+'), ' ')
        .replaceAll(RegExp(r'^[,;:\-–—\s]+|[,;:\-–—\s]+$'), '')
        .trim();

    void addCard(String question, String answer, String source) {
      final q = tidy(question);
      final a = answer.replaceAll(RegExp(r'\s+'), ' ').trim();
      if (q.length < 12 || a.length < 8) return;
      final candidate = StudyCard(
        id: '${now.microsecondsSinceEpoch}-${counter++}',
        question: q.endsWith('?') ? q : '$q?',
        answer: a,
        source: source,
        dueAt: now,
      );
      if (!isCardUsable(candidate)) return;
      final key = '${_normalizedKey(candidate.question)}|${_normalizedKey(candidate.answer)}';
      if (!seen.add(key)) return;
      cards.add(candidate);
    }

    final rawLines = clean
        .replaceAll('\r', '')
        .split('\n')
        .map((line) => line.replaceAll(RegExp(r'[\t ]+'), ' ').trim())
        .where((line) => line.isNotEmpty)
        .toList();
    final lines = _mergeWrappedFormulaLines(rawLines);
    final sentenceCandidates = <({String sentence, String topic})>[];
    var currentTopic = '';

    final formulaRegex = RegExp(
      r'^([A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 _/()\-]{0,45})\s*=\s*(.{2,190})$',
    );

    for (final raw in lines) {
      final line = raw.replaceFirst(RegExp(r'^[\-•*\d\s\.\)\(]+'), '').trim();
      if (line.isEmpty) continue;
      if (_looksLikeHeading(line)) {
        currentTopic = line.replaceAll(RegExp(r'[:\s]+$'), '').trim();
        continue;
      }

      final formula = formulaRegex.firstMatch(line);
      if (formula != null) {
        final left = tidy(formula.group(1)!);
        final right = tidy(formula.group(2)!);
        if (!weakSubject(left) && right.length >= 3) {
          addCard('What is the formula or relationship for $left', '$left = $right', currentTopic);
        }
      }

      final colon = line.indexOf(':');
      if (colon >= 2 && colon <= 70 && line.length - colon >= 14) {
        final term = tidy(line.substring(0, colon));
        final definition = tidy(line.substring(colon + 1));
        if (!weakSubject(term) && !_isStructuralLabel(term) && !weakAnswer(definition)) {
          addCard('What is $term', definition, currentTopic);
        }
      }

      for (final sentence in _sentences(line)) {
        final normalized = sentence.replaceAll(RegExp(r'\s+'), ' ').trim();
        final wc = _words(normalized).length;
        if (normalized.length >= 35 && normalized.length <= 330 && wc >= 7 && wc <= 55) {
          if (!normalized.endsWith('?') && !normalized.startsWith('¿')) {
            sentenceCandidates.add((sentence: normalized, topic: currentTopic));
          }
        }
      }
      if (cards.length >= maxCards) break;
    }

    for (final item in sentenceCandidates) {
      if (cards.length >= maxCards) break;
      final sentence = item.sentence;
      final topic = item.topic;
      var matched = false;

      // Explicit definitions are safe only when the definition has substance.
      final definition = RegExp(
        r'^(.{2,75}?)\s+(?:means|refers to|is defined as|are defined as)\s+(.{12,260}?)[.]?$',
        caseSensitive: false,
      ).firstMatch(sentence);
      if (definition != null) {
        final subject = tidy(definition.group(1)!);
        final answer = tidy(definition.group(2)!);
        if (!weakSubject(subject) && !weakAnswer(answer)) {
          addCard('What does $subject mean', answer, topic);
          matched = true;
        }
      }

      // Purpose / function.
      if (!matched) {
        final purpose = RegExp(
          r'^(.{2,75}?)\s+(?:is|are)\s+used\s+(?:to|for)\s+(.{12,240}?)[.]?$',
          caseSensitive: false,
        ).firstMatch(sentence);
        if (purpose != null) {
          final subject = tidy(purpose.group(1)!);
          final answer = tidy(purpose.group(2)!);
          if (!weakSubject(subject) && !weakAnswer(answer)) {
            addCard('What is $subject used for', answer, topic);
            matched = true;
          }
        }
      }

      // Cause / effect. Create both directions when the sentence supports them.
      final causeEffect = RegExp(
        r'^(.{2,85}?)\s+(causes?|leads? to|results? in|increases?|decreases?|reduces?|affects?)\s+(.{12,230}?)[.]?$',
        caseSensitive: false,
      ).firstMatch(sentence);
      if (causeEffect != null) {
        final subject = tidy(causeEffect.group(1)!);
        final verb = tidy(causeEffect.group(2)!);
        final effect = tidy(causeEffect.group(3)!);
        if (!weakSubject(subject) && !weakAnswer(effect)) {
          addCard('What effect does $subject have', '$subject $verb $effect.', topic);
          matched = true;
        }
      }

      final because = RegExp(r'^(.{10,170}?)\s+because\s+(.{12,170}?)[.]?$', caseSensitive: false)
          .firstMatch(sentence);
      if (because != null) {
        final claim = tidy(because.group(1)!);
        final reason = tidy(because.group(2)!);
        if (!weakAnswer(reason) && _words(claim).length <= 24) {
          addCard('Why is the following true: $claim', 'Because $reason.', topic);
          matched = true;
        }
      }

      // Comparison / distinction.
      if (!matched) {
        final comparison = RegExp(
          r'^(.{2,75}?)\s+(?:differs? from|is different from|are different from)\s+(.{12,230}?)[.]?$',
          caseSensitive: false,
        ).firstMatch(sentence);
        if (comparison != null) {
          final subject = tidy(comparison.group(1)!);
          final difference = tidy(comparison.group(2)!);
          if (!weakSubject(subject) && !weakAnswer(difference)) {
            addCard('How does $subject differ from the alternative described in the guide', difference, topic);
            matched = true;
          }
        }
      }

      // Referrals are common in professional-practice material and should test
      // the actual relationship rather than the generic word "client".
      if (!matched) {
        final referral = RegExp(
          r'^(.{2,70}?)\s+may\s+refer\s+(.{2,80}?)\s+to\s+(.{3,100}?)[.]?$',
          caseSensitive: false,
        ).firstMatch(sentence);
        if (referral != null) {
          final actor = tidy(referral.group(1)!);
          final object = tidy(referral.group(2)!);
          final destination = tidy(referral.group(3)!);
          if (!weakSubject(actor) && !weakAnswer('$destination professional')) {
            addCard('To whom may $actor refer $object', destination, topic);
            matched = true;
          }
        }
      }

      // Action / requirement / inclusion statements.
      if (!matched) {
        final action = RegExp(
          r'^(.{2,75}?)\s+(includes?|requires?|provides?|allows?|helps?|uses?|involves?|supports?)\s+(.{12,240}?)[.]?$',
          caseSensitive: false,
        ).firstMatch(sentence);
        if (action != null) {
          final subject = tidy(action.group(1)!);
          final verb = action.group(2)!.toLowerCase();
          final answer = tidy(action.group(3)!);
          if (!weakSubject(subject) && !weakAnswer(answer)) {
            final base = <String, String>{
                  'include': 'include', 'includes': 'include',
                  'require': 'require', 'requires': 'require',
                  'provide': 'provide', 'provides': 'provide',
                  'allow': 'allow', 'allows': 'allow',
                  'help': 'help with', 'helps': 'help with',
                  'use': 'use', 'uses': 'use',
                  'involve': 'involve', 'involves': 'involve',
                  'support': 'support', 'supports': 'support',
                }[verb] ?? verb;
            addCard('What does $subject $base', answer, topic);
            matched = true;
          }
        }
      }

      // Modal recommendations / capabilities.
      if (!matched) {
        final modal = RegExp(
          r'^(.{2,75}?)\s+(should|must|can|may)\s+(.{14,240}?)[.]?$',
          caseSensitive: false,
        ).firstMatch(sentence);
        if (modal != null) {
          final subject = tidy(modal.group(1)!);
          final modalWord = modal.group(2)!.toLowerCase();
          final action = tidy(modal.group(3)!);
          if (!weakSubject(subject) && !weakAnswer(action)) {
            addCard('What $modalWord $subject do', action, topic);
            matched = true;
          }
        }
      }

      // Substantive copula statements. Short generic claims such as
      // "Clear writing is an important professional skill" are intentionally
      // excluded; they do not make useful recall cards by themselves.
      if (!matched) {
        final copula = RegExp(
          r'^(.{2,75}?)\s+(?:is|are)\s+(.{18,260}?)[.]?$',
          caseSensitive: false,
        ).firstMatch(sentence);
        if (copula != null) {
          final subject = tidy(copula.group(1)!);
          final answer = tidy(copula.group(2)!);
          if (!weakSubject(subject) && !weakAnswer(answer) && _words(answer).length >= 7) {
            addCard('What should you know about $subject', answer, topic);
            matched = true;
          }
        }
      }

      // Last-resort factual sentence: use a real grammatical subject, never an
      // arbitrary keyword. This increases coverage without returning to the old
      // "What does the content explain about client?" behavior.
      if (!matched && cards.length < target) {
        final fact = RegExp(
          r'^(.{2,70}?)\s+(has|have|can|may|should|must|uses?|helps?|requires?|includes?|provides?|allows?|involves?|supports?|affects?)\s+(.{18,240}?)[.]?$',
          caseSensitive: false,
        ).firstMatch(sentence);
        if (fact != null) {
          final subject = tidy(fact.group(1)!);
          if (!weakSubject(subject) && !weakAnswer(sentence)) {
            addCard('What key fact does the guide give about $subject', sentence, topic);
          }
        }
      }
    }

    return cards.take(maxCards).toList();
  }

'''
s = s[:start] + new_build + s[end:]

start = s.find('  static bool isCardUsable(StudyCard card) {')
end = s.find('  static bool _looksLikeDefinitionPair(', start)
if start < 0 or end < 0:
    raise RuntimeError('StudyEngine isCardUsable block not found')

new_validator = r'''  static bool isCardUsable(StudyCard card) {
    final q = card.question.replaceAll(RegExp(r'\s+'), ' ').trim();
    final a = card.answer.replaceAll(RegExp(r'\s+'), ' ').trim();
    final qWords = _words(q);
    final aWords = _words(a);
    if (q.length < 12 || a.length < 8 || qWords.length < 3) return false;
    if (_normalizedKey(q) == _normalizedKey(a)) return false;
    if (a.endsWith('?') || a.startsWith('¿')) return false;

    // Legacy generators that produced the screenshots reported by the user.
    if (RegExp(r'^what does the content explain about\b', caseSensitive: false).hasMatch(q)) {
      return false;
    }
    if (RegExp(r'^(?:complete the idea|explain this idea)\b', caseSensitive: false).hasMatch(q)) {
      return false;
    }

    final weakAnswer = RegExp(
      r'^(?:not\b|part of\b|an?\s+(?:important|key|basic|general)\b)',
      caseSensitive: false,
    ).hasMatch(a) ||
        (aWords.length <= 7 &&
            RegExp(r'\b(?:thing|part|career|success|important|good|bad|skill)\b',
                    caseSensitive: false)
                .hasMatch(a));
    if (weakAnswer) return false;

    // The old "What is or what does X mean?" template was often created from
    // ordinary prose. Keep only substantial answers for backward compatibility.
    if (RegExp(r'^what is or what does\b', caseSensitive: false).hasMatch(q) &&
        aWords.length < 8) {
      return false;
    }

    // Isolated generic-word definitions are not useful study questions.
    final oneWordMeaning = RegExp(r'^what does\s+([a-z][a-z-]{2,})\s+mean\?$', caseSensitive: false)
        .firstMatch(q);
    if (oneWordMeaning != null && aWords.length < 7) return false;

    return true;
  }

'''
s = s[:start] + new_validator + s[end:]
p.write_text(s)

# -----------------------------------------------------------------------------
# GuideStore: if a guide still has too few cards for its amount of source text,
# rebuild it once with the new engine while retaining progress for exact pairs.
# -----------------------------------------------------------------------------
p = Path('lib/guide_store.dart')
s = p.read_text()
anchor = "      guides.sort((a, b) => b.createdAt.compareTo(a.createdAt));\n"
if anchor not in s:
    raise RuntimeError('GuideStore sort anchor not found')

density_pass = r'''      for (final guide in guides) {
        if (guide.text.trim().isEmpty) continue;
        final minimum = StudyEngine.recommendedCardCount(guide.text);
        final usable = guide.cards.where(StudyEngine.isCardUsable).toList();
        if (usable.length >= minimum) continue;

        final oldByPair = <String, StudyCard>{
          for (final card in guide.cards)
            '${card.question.trim().toLowerCase()}|${card.answer.trim().toLowerCase()}': card,
        };
        final rebuilt = StudyEngine.buildCards(guide.text);
        for (final card in rebuilt) {
          final old = oldByPair[
            '${card.question.trim().toLowerCase()}|${card.answer.trim().toLowerCase()}'
          ];
          if (old == null) continue;
          card.dueAt = old.dueAt;
          card.intervalDays = old.intervalDays;
          card.ease = old.ease;
          card.correct = old.correct;
          card.wrong = old.wrong;
          card.streak = old.streak;
        }
        guide.cards = rebuilt;
        repaired = true;
      }

'''
s = s.replace(anchor, density_pass + anchor, 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# Daily exam: stronger fallback/AI gates, better generation instructions, and
# invalidate already-saved weak sessions from previous versions.
# -----------------------------------------------------------------------------
p = Path('lib/daily_exam_page.dart')
s = p.read_text()

# Always give this quality release its own session storage namespace.
s, n = re.subn(
    r"static const _storageKey = 'memora_tutor_exams_[^']+';",
    "static const _storageKey = 'memora_tutor_exams_v120_quality';",
    s,
    count=1,
)
if n != 1:
    raise RuntimeError('Daily exam storage key not found')

start = s.find('  bool _lowQualityQuestion(String question) {')
end = s.find('  ExamQuestionData? _cleanCard(', start)
if start < 0 or end < 0:
    raise RuntimeError('Daily exam low-quality method not found')

quality_helpers = r'''  bool _weakExamAnswer(String answer) {
    final a = answer.replaceAll(RegExp(r'\s+'), ' ').trim();
    final words = _matchWords(a);
    if (a.length < 8 || words.length < 3 || a.endsWith('?')) return true;
    if (RegExp(r'^(?:not\b|part of\b|an?\s+(?:important|key|basic|general)\b)',
            caseSensitive: false)
        .hasMatch(a)) return true;
    if (words.length <= 7 &&
        RegExp(r'\b(?:thing|part|career|success|important|good|bad|skill)\b',
                caseSensitive: false)
            .hasMatch(a)) return true;
    return false;
  }

  bool _lowQualityQuestion(String question) {
    final q = question.replaceAll(RegExp(r'\s+'), ' ').trim();
    if (q.length < 14 || _matchWords(q).length < 3) return true;
    if (q.endsWith(':') || q.endsWith(';') || q.endsWith(',')) return true;
    if (q.contains('______')) return true;
    if (RegExp(r'^what does the content explain about\b', caseSensitive: false).hasMatch(q)) {
      return true;
    }
    if (RegExp(r'^what is or what does\b', caseSensitive: false).hasMatch(q)) {
      return true;
    }
    if (RegExp(r'^(?:complete the idea|explain this idea)\b', caseSensitive: false).hasMatch(q)) {
      return true;
    }
    // A one-word vocabulary prompt is too weak for an exam. Definitions should
    // ask for significance, mechanism, comparison, or application instead.
    if (RegExp(r'^what does\s+[a-z][a-z-]{2,}\s+mean\?$', caseSensitive: false).hasMatch(q)) {
      return true;
    }
    return false;
  }

'''
s = s[:start] + quality_helpers + s[end:]

# AI questions already require exact evidence. Add answer quality too.
old = "        if (_lowQualityQuestion(q) || evidence.isEmpty) continue;"
if old in s:
    s = s.replace(
        old,
        "        if (_lowQualityQuestion(q) || evidence.isEmpty || _weakExamAnswer(proposed)) continue;",
        1,
    )
else:
    raise RuntimeError('AI question validation anchor not found')

# Add strong pedagogical rules at the beginning of the existing exam prompt.
build_start = s.find('  Future<TutorExamSession> _buildExam(')
prompt_anchor = "          prompt: '''"
prompt_pos = s.find(prompt_anchor, build_start)
if build_start < 0 or prompt_pos < 0:
    raise RuntimeError('Daily exam AI prompt anchor not found')
insert_at = prompt_pos + len(prompt_anchor)
prompt_rules = r'''QUALITY REQUIREMENTS — these override any weaker instruction below:
- Write every question in natural English.
- Test knowledge, not isolated vocabulary or sentence fragments.
- NEVER write "What is or what does X mean?" or "What does the content explain about X?".
- Do not ask about generic isolated words such as client, advice, writing, system, career, success, or skill.
- Prefer WHY/HOW questions, cause-and-effect, comparison, consequences, formulas/calculations, decision making, or short realistic scenarios.
- If you ask for a definition, the term must be a genuine technical concept explicitly defined in the source, and the question must also test its significance or use.
- Each answer must be specific enough to teach/correct the learner, not a fragment such as "part of the career" or "an important skill".
- Each question must stand on its own and be answerable only from the supplied evidence.
- Spread questions across different ideas instead of paraphrasing the same fact.

'''
s = s[:insert_at] + prompt_rules + s[insert_at:]
p.write_text(s)

print('Memora v1.20 learning-quality patch applied successfully')
