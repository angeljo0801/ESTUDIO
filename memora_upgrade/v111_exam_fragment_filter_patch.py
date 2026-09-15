from pathlib import Path

# -----------------------------------------------------------------------------
# StudyEngine: only create cloze cards from complete sentences.
# -----------------------------------------------------------------------------
p = Path('lib/study_engine.dart')
s = p.read_text()

old = """      for (final sentence in _sentences(line)) {
        if (sentence.length >= 40 && sentence.length <= 320) {
          sentenceCandidates.add((text: sentence, topic: currentTopic));
        }
      }
"""
new = """      for (final sentence in _sentences(line)) {
        if (sentence.length >= 40 &&
            sentence.length <= 320 &&
            _isCompleteClozeSentence(sentence)) {
          sentenceCandidates.add((text: sentence, topic: currentTopic));
        }
      }
"""
if old not in s:
    raise RuntimeError('StudyEngine sentence candidate anchor not found')
s = s.replace(old, new, 1)

anchor = "  static bool _isStructuralLabel(String value) {"
helper = r'''  static bool _isCompleteClozeSentence(String sentence) {
    final text = sentence.trim();
    if (text.isEmpty) return false;
    // A colon/semicolon/comma/dash at the end usually introduces content that
    // was split onto the next PDF line. It is not a complete exam statement.
    if (RegExp(r'[:;,\-–—]\s*$').hasMatch(text)) return false;
    // Cloze questions should be based on a complete sentence, not a heading or
    // a PDF fragment. This intentionally requires terminal punctuation.
    if (!RegExp(r'[.!?]\s*$').hasMatch(text)) return false;
    final words = _words(text);
    if (words.length < 7) return false;
    return true;
  }

'''
if anchor not in s:
    raise RuntimeError('StudyEngine helper insertion anchor not found')
s = s.replace(anchor, helper + anchor, 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# Exam engine: reject malformed/incomplete cloze questions, including cards
# imported by older Memora versions, and purge affected saved exam sessions.
# -----------------------------------------------------------------------------
p = Path('lib/daily_exam_page.dart')
s = p.read_text()

old = r'''  bool _lowQualityQuestion(String question) {
    final q = question.trim();
    if (q.length < 10 || _matchWords(q).length < 2) return true;
    if (RegExp(
      r'^¿?cuál es la fórmula o relación de [a-z][a-z0-9]{0,4}\??$',
      caseSensitive: false,
    ).hasMatch(q)) return true;
    return false;
  }
'''
new = r'''  bool _lowQualityQuestion(String question) {
    final q = question.trim();
    if (q.length < 10 || _matchWords(q).length < 2) return true;
    if (RegExp(
      r'^¿?cuál es la fórmula o relación de [a-z][a-z0-9]{0,4}\??$',
      caseSensitive: false,
    ).hasMatch(q)) return true;

    // Never test an unfinished introductory fragment such as
    // "______ programs may emphasize:". These typically come from a PDF line
    // whose continuation was placed on the next line.
    if (q.endsWith(':') || q.endsWith(';') || q.endsWith(',')) return true;
    if (q.contains('______')) {
      final body = q
          .replaceFirst(RegExp(r'^Completa la idea:\s*', caseSensitive: false), '')
          .trim();
      if (body.endsWith(':') ||
          body.endsWith(';') ||
          body.endsWith(',') ||
          RegExp(r'[-–—]\s*$').hasMatch(body)) {
        return true;
      }
      if (!RegExp(r'[.!?]\s*$').hasMatch(body)) return true;
      final remainingWords = _matchWords(body.replaceAll('______', ''));
      if (remainingWords.length < 6) return true;
    }
    return false;
  }
'''
if old not in s:
    raise RuntimeError('DailyExam low-quality helper anchor not found')
s = s.replace(old, new, 1)

old = """    if (!mounted) return;
    setState(() {
      tutors = loadedTutors;
      sessions = loadedSessions;
"""
new = """    // Drop only saved exams that contain malformed questions from older
    // generators. Good exam history remains intact.
    final beforeCleanup = loadedSessions.length;
    loadedSessions.removeWhere(
      (exam) => exam.questions.any(
        (q) => _lowQualityQuestion(q.question) || _looksIncomplete(q.answer),
      ),
    );
    if (loadedSessions.length != beforeCleanup) {
      await prefs.setString(
        _storageKey,
        jsonEncode(loadedSessions.map((e) => e.toJson()).toList()),
      );
    }

    if (!mounted) return;
    setState(() {
      tutors = loadedTutors;
      sessions = loadedSessions;
"""
if old not in s:
    raise RuntimeError('DailyExam load cleanup anchor not found')
s = s.replace(old, new, 1)
p.write_text(s)

print('Memora v1.11 incomplete exam fragment filter applied successfully')
