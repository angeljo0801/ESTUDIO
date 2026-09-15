from pathlib import Path

# Memora v1.16
# Quality-first study cards: remove generic fill-in-the-blank cards, reject
# narrative/prompt fragments, and regenerate affected legacy guides.

# -----------------------------------------------------------------------------
# StudyEngine
# -----------------------------------------------------------------------------
p = Path('lib/study_engine.dart')
s = p.read_text()

old = """    'although', 'though', 'unless', 'once',
  };
"""
new = """    'although', 'though', 'unless', 'once',
    'imagine', 'suppose', 'consider', 'picture', 'remember', 'note', 'assume',
    'let', 'lets', 'let\'s', 'think', 'say', 'look', 'try',
  };
"""
if old not in s:
    raise RuntimeError('bad definition starts anchor not found')
s = s.replace(old, new, 1)

anchor = """  static final Set<String> _badDefinitionEndWords = {
    'quickly', 'slowly', 'often', 'usually', 'generally', 'typically', 'annually',
    'monthly', 'weekly', 'daily', 'yearly', 'today', 'tomorrow', 'yesterday',
  };

"""
insert = anchor + """  static final Set<String> _badSentenceStarts = {
    'this', 'that', 'these', 'those', 'it', 'they', 'we', 'you', 'your', 'i',
    'he', 'she', 'here', 'there', 'imagine', 'suppose', 'consider', 'picture',
    'remember', 'note', 'assume', 'let', 'lets', 'think', 'say', 'look', 'try',
    'why', 'how', 'what', 'when', 'where', 'who', 'which',
    'because', 'and', 'or', 'but', 'so', 'then',
    'esto', 'eso', 'estos', 'estas', 'ellos', 'ellas', 'nosotros', 'usted',
    'ustedes', 'imagina', 'imagine', 'suponga', 'supongamos', 'considera',
    'considere', 'recuerda', 'recuerde', 'nota', 'mira', 'piense', 'piensa',
    'porqué', 'por', 'cómo', 'como', 'qué', 'que', 'cuándo', 'cuando',
  };

  static final Set<String> _genericActionWords = {
    'distinguish', 'understand', 'remember', 'consider', 'imagine', 'explain',
    'identify', 'determine', 'recognize', 'compare', 'describe', 'discuss',
    'distinguishes', 'understands', 'remembers', 'considers', 'explains',
    'identifies', 'determines', 'recognizes', 'compares', 'describes',
    'distinguir', 'entender', 'recordar', 'considerar', 'imaginar', 'explicar',
    'identificar', 'determinar', 'reconocer', 'comparar', 'describir',
  };

"""
if anchor not in s:
    raise RuntimeError('quality set insertion anchor not found')
s = s.replace(anchor, insert, 1)

# Build content frequencies once; concept questions will prefer recurring terms.
loop_anchor = "    for (final raw in lines) {"
if loop_anchor not in s:
    raise RuntimeError('StudyEngine line loop anchor not found')
s = s.replace(loop_anchor, """    final contentWordFrequencies = _contentWordFrequencies(text);

    for (final raw in lines) {""", 1)

# v1.11 already wraps this condition with _isCompleteClozeSentence, so replace
# that post-v1.11 form rather than the older base-source form.
old = """      for (final sentence in _sentences(line)) {
        if (sentence.length >= 40 &&
            sentence.length <= 320 &&
            _isCompleteClozeSentence(sentence)) {
          sentenceCandidates.add((text: sentence, topic: currentTopic));
        }
      }
"""
new = """      for (final sentence in _sentences(line)) {
        if (_isUsefulDeclarativeSentence(sentence)) {
          sentenceCandidates.add((text: sentence, topic: currentTopic));
        }
      }
"""
if old not in s:
    raise RuntimeError('sentence candidate anchor not found')
s = s.replace(old, new, 1)

old = """    for (final candidate in sentenceCandidates) {
      if (cards.length >= maxCards) break;
      final sentence = candidate.text;
      final keyword = _bestKeyword(sentence);
      if (keyword == null) continue;
      final blanked = sentence.replaceFirst(
        RegExp(RegExp.escape(keyword), caseSensitive: false),
        '______',
      );
      if (blanked == sentence) continue;
      addCard('Completa la idea:\\n$blanked', keyword, candidate.topic);
    }
"""
new = """    for (final candidate in sentenceCandidates) {
      if (cards.length >= maxCards) break;
      final sentence = candidate.text;
      final keyword = _bestConceptKeyword(sentence, contentWordFrequencies);
      if (keyword == null) continue;
      addCard(
        '¿Qué explica el contenido sobre “$keyword”?',
        sentence,
        candidate.topic,
      );
    }
"""
if old not in s:
    raise RuntimeError('legacy cloze generation anchor not found')
s = s.replace(old, new, 1)

old = """    if (cards.length < 12) {
      for (final raw in lines) {
        if (cards.length >= 40) break;
        final line = raw.replaceFirst(RegExp(r'^[\\-•*\\d\\s\\.\\)\\(]+'), '').trim();
        if (_looksLikeHeading(line) || line.length < 30 || line.length > 280) continue;
        if (line.endsWith('?')) continue;
        final words = _words(line);
        if (words.length < 6) continue;
        final cue = words.take(min(7, words.length)).join(' ');
        addCard('Explica esta idea: $cue…', line, currentTopic);
      }
    }
"""
new = """    if (cards.length < 12) {
      for (final raw in lines) {
        if (cards.length >= 40) break;
        final line = raw.replaceFirst(RegExp(r'^[\\-•*\\d\\s\\.\\)\\(]+'), '').trim();
        if (_looksLikeHeading(line) || !_isUsefulDeclarativeSentence(line)) continue;
        final keyword = _bestConceptKeyword(line, contentWordFrequencies);
        if (keyword == null) continue;
        addCard(
          '¿Qué explica el contenido sobre “$keyword”?',
          line,
          currentTopic,
        );
      }
    }
"""
if old not in s:
    raise RuntimeError('legacy fallback card anchor not found')
s = s.replace(old, new, 1)

old = """    if (q.startsWith('Completa la idea:')) {
      if (!q.contains('______') || a.length < 3) return false;
    }

    return true;
"""
new = """    // v1.16 no longer uses generic cloze / cue cards because they often test
    // grammar or sentence fragments instead of knowledge. Remove legacy ones.
    if (q.startsWith('Completa la idea:') || q.startsWith('Explica esta idea:')) {
      return false;
    }

    if (q.startsWith('¿Qué explica el contenido sobre')) {
      if (!_isUsefulDeclarativeSentence(a)) return false;
    }

    return true;
"""
if old not in s:
    raise RuntimeError('legacy card usability anchor not found')
s = s.replace(old, new, 1)

helper_anchor = "  static bool _isStructuralLabel(String value) {"
helpers = r'''  static Map<String, int> _contentWordFrequencies(String text) {
    final frequencies = <String, int>{};
    for (final word in _words(text)) {
      if (word.length < 5 || _stopWords.contains(word)) continue;
      if (_badSentenceStarts.contains(word) || _genericActionWords.contains(word)) continue;
      frequencies[word] = (frequencies[word] ?? 0) + 1;
    }
    return frequencies;
  }

  static bool _isUsefulDeclarativeSentence(String value) {
    final sentence = value.replaceAll(RegExp(r'\s+'), ' ').trim();
    if (sentence.length < 45 || sentence.length > 320) return false;
    if (sentence.contains('?') || sentence.startsWith('¿')) return false;
    final words = _words(sentence);
    if (words.length < 8 || words.length > 48) return false;
    if (_badSentenceStarts.contains(words.first)) return false;
    if (RegExp(r'^(?:for example|for instance|e\.g\.|por ejemplo)\b', caseSensitive: false)
        .hasMatch(sentence)) return false;
    return true;
  }

  static String? _bestConceptKeyword(
    String sentence,
    Map<String, int> frequencies,
  ) {
    final originals = RegExp(
      r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9'-]{4,}",
    ).allMatches(sentence).map((m) => m.group(0)!).toList();

    final candidates = originals.where((word) {
      final w = word.toLowerCase();
      if (_stopWords.contains(w) || _badSentenceStarts.contains(w)) return false;
      if (_genericActionWords.contains(w) || _looksLikeVerbFragment(w)) return false;
      return true;
    }).toList();
    if (candidates.isEmpty) return null;

    candidates.sort((a, b) {
      final af = frequencies[a.toLowerCase()] ?? 0;
      final bf = frequencies[b.toLowerCase()] ?? 0;
      final frequencyCompare = bf.compareTo(af);
      if (frequencyCompare != 0) return frequencyCompare;
      return b.length.compareTo(a.length);
    });

    final best = candidates.first;
    final bestFrequency = frequencies[best.toLowerCase()] ?? 0;
    // For short/common words, require recurrence in the source. A long specific
    // term can still be useful even if it appears only once.
    if (bestFrequency < 2 && best.length < 9) return null;
    return best;
  }

'''
if helper_anchor not in s:
    raise RuntimeError('StudyEngine helper insertion anchor not found')
s = s.replace(helper_anchor, helpers + helper_anchor, 1)

p.write_text(s)

# -----------------------------------------------------------------------------
# GuideStore: if a legacy guide contains any newly rejected card, rebuild its
# generated cards from the original source and preserve progress where the new
# question/answer pair still matches an old one.
# -----------------------------------------------------------------------------
p = Path('lib/guide_store.dart')
s = p.read_text()
old = """      var repaired = false;
      for (final guide in guides) {
        final cleaned = guide.cards.where(StudyEngine.isCardUsable).toList();
        if (cleaned.length != guide.cards.length) {
          guide.cards = cleaned;
          repaired = true;
        }
        if (guide.cards.isEmpty && guide.text.trim().isNotEmpty) {
          guide.cards = StudyEngine.buildCards(guide.text);
          repaired = true;
        }
      }
"""
new = """      var repaired = false;
      for (final guide in guides) {
        final hasRejectedCard = guide.cards.any((card) => !StudyEngine.isCardUsable(card));
        if ((hasRejectedCard || guide.cards.isEmpty) && guide.text.trim().isNotEmpty) {
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
      }
"""
if old not in s:
    raise RuntimeError('GuideStore migration anchor not found')
s = s.replace(old, new, 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# Daily exams: invalidate v1.15 sessions so already-generated cloze cards do not
# survive after upgrading.
# -----------------------------------------------------------------------------
p = Path('lib/daily_exam_page.dart')
s = p.read_text()
old = "  static const _storageKey = 'memora_tutor_exams_v3';"
new = "  static const _storageKey = 'memora_tutor_exams_v4';"
if old not in s:
    raise RuntimeError('Daily exam v3 storage key anchor not found')
s = s.replace(old, new, 1)
p.write_text(s)

print('Memora v1.16 semantic card quality patch applied successfully')
