from pathlib import Path
import re

# -----------------------------------------------------------------------------
# StudyEngine: do not confuse symbol definitions with formulas and repair
# formulas wrapped across PDF lines.
# -----------------------------------------------------------------------------
p = Path('lib/study_engine.dart')
s = p.read_text()

old_lines = """    final lines = text
        .replaceAll('\\r', '')
        .split('\\n')
        .map((line) => line.replaceAll(RegExp(r'[\\t ]+'), ' ').trim())
        .where((line) => line.isNotEmpty)
        .toList();
"""
new_lines = """    final rawLines = text
        .replaceAll('\\r', '')
        .split('\\n')
        .map((line) => line.replaceAll(RegExp(r'[\\t ]+'), ' ').trim())
        .where((line) => line.isNotEmpty)
        .toList();
    final lines = _mergeWrappedFormulaLines(rawLines);
"""
if old_lines not in s:
    raise RuntimeError('StudyEngine lines anchor not found')
s = s.replace(old_lines, new_lines, 1)

old_formula = """      final formula = formulaRegex.firstMatch(line);
      if (formula != null) {
        final left = formula.group(1)!.trim();
        final right = formula.group(2)!.trim();
        if (_words(left).length <= 6 && right.length <= 180) {
          addCard('¿Cuál es la fórmula o relación de $left?', '$left = $right', currentTopic);
        }
      }
"""
new_formula = """      final formula = formulaRegex.firstMatch(line);
      if (formula != null) {
        final left = formula.group(1)!.trim();
        final right = formula.group(2)!.trim();
        if (_words(left).length <= 6 && right.length <= 180) {
          final shortSymbol = RegExp(r'^[A-Za-z][A-Za-z0-9]{0,4}$').hasMatch(left);
          final rhsLooksMathematical = RegExp(r'[0-9+\\-*/^%×÷()]').hasMatch(right);
          if (shortSymbol && !rhsLooksMathematical) {
            addCard('¿Qué representa $left en este contenido?', right, currentTopic);
          } else {
            addCard('¿Cuál es la fórmula o relación de $left?', '$left = $right', currentTopic);
          }
        }
      }
"""
if old_formula not in s:
    raise RuntimeError('StudyEngine formula anchor not found')
s = s.replace(old_formula, new_formula, 1)

helper_anchor = "  static bool _isStructuralLabel(String value) {"
helper = r'''  static bool _formulaNeedsContinuation(String value) {
    final text = value.trim();
    if (!text.contains('=')) return false;
    var parens = 0;
    var brackets = 0;
    for (final rune in text.runes) {
      final ch = String.fromCharCode(rune);
      if (ch == '(') parens++;
      if (ch == ')') parens--;
      if (ch == '[') brackets++;
      if (ch == ']') brackets--;
    }
    if (parens > 0 || brackets > 0) return true;
    return RegExp(r'(?:[+\-–−×*/÷=]|\()\s*$').hasMatch(text);
  }

  static List<String> _mergeWrappedFormulaLines(List<String> input) {
    final out = <String>[];
    var i = 0;
    while (i < input.length) {
      var current = input[i].trim();
      if (current.contains('=')) {
        var j = i + 1;
        while (_formulaNeedsContinuation(current) && j < input.length && j <= i + 3) {
          final next = input[j].trim();
          if (next.isEmpty || _looksLikeHeading(next)) break;
          current = '$current $next'.replaceAll(RegExp(r'\s+'), ' ').trim();
          j++;
        }
        if (j > i + 1) i = j - 1;
      }
      out.add(current);
      i++;
    }
    return out;
  }

'''
if helper_anchor not in s:
    raise RuntimeError('StudyEngine helper anchor not found')
s = s.replace(helper_anchor, helper + helper_anchor, 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# Exam engine: novelty, card repair, evidence grounding, robust AI validation.
# -----------------------------------------------------------------------------
p = Path('lib/daily_exam_page.dart')
s = p.read_text()

import_anchor = "import 'models.dart';\n"
if import_anchor not in s:
    raise RuntimeError('daily exam import anchor not found')
s = s.replace(import_anchor, import_anchor + "import 'study_engine.dart';\n", 1)

start = s.find("  List<ExamQuestionData> _cardQuestions(")
end = s.find("  Future<TutorExamSession> _buildExam(", start)
if start < 0 or end < 0:
    raise RuntimeError('daily exam helper block not found')

new_helpers = r'''  String _questionKey(String text) => text
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-záéíóúüñ0-9]+'), ' ')
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim();

  Set<String> _matchWords(String text) => RegExp(r"[a-záéíóúüñ0-9]{3,}", caseSensitive: false)
      .allMatches(text.toLowerCase())
      .map((m) => m.group(0)!)
      .toSet();

  bool _nearDuplicate(String a, String b) {
    final ka = _questionKey(a);
    final kb = _questionKey(b);
    if (ka.isEmpty || kb.isEmpty) return false;
    if (ka == kb || ka.contains(kb) || kb.contains(ka)) return true;
    final wa = _matchWords(ka);
    final wb = _matchWords(kb);
    if (wa.isEmpty || wb.isEmpty) return false;
    final common = wa.intersection(wb).length;
    final union = wa.union(wb).length;
    return union > 0 && common / union >= .72;
  }

  bool _looksIncomplete(String answer) {
    final text = answer.trim();
    if (text.isEmpty) return true;
    var parens = 0;
    var brackets = 0;
    for (final rune in text.runes) {
      final ch = String.fromCharCode(rune);
      if (ch == '(') parens++;
      if (ch == ')') parens--;
      if (ch == '[') brackets++;
      if (ch == ']') brackets--;
    }
    if (parens > 0 || brackets > 0) return true;
    return RegExp(r'(?:[+\-–−×*/÷=]|\()\s*$').hasMatch(text);
  }

  String? _recoverWrappedAnswer(StudyGuide guide, String answer) {
    final eq = answer.indexOf('=');
    if (eq <= 0) return null;
    final left = answer.substring(0, eq).trim().toLowerCase();
    if (left.isEmpty) return null;
    final lines = guide.text.replaceAll('\r', '').split('\n');
    for (var i = 0; i < lines.length; i++) {
      final line = lines[i].replaceAll(RegExp(r'[\t ]+'), ' ').trim();
      if (!line.toLowerCase().startsWith(left) || !line.contains('=')) continue;
      var merged = line;
      var j = i + 1;
      while (_looksIncomplete(merged) && j < lines.length && j <= i + 3) {
        final next = lines[j].replaceAll(RegExp(r'[\t ]+'), ' ').trim();
        if (next.isEmpty) break;
        merged = '$merged $next'.replaceAll(RegExp(r'\s+'), ' ').trim();
        j++;
      }
      if (!_looksIncomplete(merged)) return merged;
    }
    return null;
  }

  bool _lowQualityQuestion(String question) {
    final q = question.trim();
    if (q.length < 10 || _matchWords(q).length < 2) return true;
    if (RegExp(
      r'^¿?cuál es la fórmula o relación de [a-z][a-z0-9]{0,4}\??$',
      caseSensitive: false,
    ).hasMatch(q)) return true;
    return false;
  }

  ExamQuestionData? _cleanCard(StudyGuide guide, StudyCard card) {
    var q = card.question.trim();
    var a = card.answer.trim();
    if (q.isEmpty || a.isEmpty) return null;

    final symbolic = RegExp(
      r'^¿Cuál es la fórmula o relación de ([A-Za-z][A-Za-z0-9]{0,4})\?$',
      caseSensitive: false,
    ).firstMatch(q);
    if (symbolic != null) {
      final symbol = symbolic.group(1)!;
      final assignment = RegExp(
        '^${RegExp.escape(symbol)}\\s*=\\s*(.+)\\$',
        caseSensitive: false,
      ).firstMatch(a);
      if (assignment != null) {
        final rhs = assignment.group(1)!.trim();
        final mathematical = RegExp(r'[0-9+\-*/^%×÷()]').hasMatch(rhs);
        if (!mathematical) {
          q = '¿Qué representa $symbol en este contenido?';
          a = rhs;
        }
      }
    }

    if (_looksIncomplete(a)) {
      final recovered = _recoverWrappedAnswer(guide, a);
      if (recovered == null) return null;
      a = recovered;
    }
    if (_lowQualityQuestion(q) || a.length < 3) return null;
    return ExamQuestionData(question: q, answer: a, sourceTitle: guide.title);
  }

  List<String> _recentQuestions(String tutorId, {int maxQuestions = 90}) {
    final own = sessions.where((e) => e.tutorId == tutorId).toList()
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
    final out = <String>[];
    for (final exam in own.take(8)) {
      for (final q in exam.questions) {
        if (out.length >= maxQuestions) return out;
        out.add(q.question);
      }
    }
    return out;
  }

  List<ExamQuestionData> _cardQuestions(
    List<StudyGuide> guides,
    int count, {
    List<String> avoidQuestions = const [],
  }) {
    final rng = Random(DateTime.now().microsecondsSinceEpoch);
    final candidates = <({ExamQuestionData item, double priority})>[];
    final seen = <String>[];

    void addCandidate(StudyGuide guide, StudyCard card, {double score = 0}) {
      final item = _cleanCard(guide, card);
      if (item == null) return;
      if (seen.any((q) => _nearDuplicate(q, item.question))) return;
      seen.add(item.question);
      candidates.add((item: item, priority: score + rng.nextDouble() * 5));
    }

    for (final guide in guides) {
      // Regenerate cards from the original text so old imports also benefit
      // from current parser fixes without forcing the user to re-import PDFs.
      for (final card in StudyEngine.buildCards(guide.text)) {
        addCandidate(guide, card);
      }
      for (final card in guide.cards) {
        final score = card.wrong * 2.0 + (card.isDue ? 1.5 : 0) - card.correct * .15;
        addCandidate(guide, card, score: score);
      }
    }

    final fresh = candidates
        .where((c) => !avoidQuestions.any((q) => _nearDuplicate(q, c.item.question)))
        .toList()
      ..sort((a, b) => b.priority.compareTo(a.priority));
    final reused = candidates
        .where((c) => avoidQuestions.any((q) => _nearDuplicate(q, c.item.question)))
        .toList()
      ..sort((a, b) => b.priority.compareTo(a.priority));

    final selected = <ExamQuestionData>[];
    for (final c in [...fresh, ...reused]) {
      if (selected.length >= count) break;
      if (selected.any((x) => _nearDuplicate(x.question, c.item.question))) continue;
      selected.add(c.item);
    }
    return selected;
  }

  String _normalizeEvidence(String text) => text
      .toLowerCase()
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim();

  bool _evidenceInContent(String evidence, String content) {
    final e = _normalizeEvidence(evidence);
    final c = _normalizeEvidence(content);
    return e.length >= 12 && c.contains(e);
  }

  bool _answerSupportedByEvidence(String answer, String evidence) {
    final a = _normalizeEvidence(answer);
    final e = _normalizeEvidence(evidence);
    if (a.isEmpty || e.isEmpty) return false;
    if (e.contains(a)) return true;
    final aw = _matchWords(a);
    final ew = _matchWords(e);
    if (aw.isEmpty) return false;
    return aw.intersection(ew).length / aw.length >= .65;
  }

  String _sourceForEvidence(List<StudyGuide> guides, String evidence, String fallback) {
    final e = _normalizeEvidence(evidence);
    for (final guide in guides) {
      if (_normalizeEvidence(guide.text).contains(e)) return guide.title;
    }
    return fallback.isEmpty ? 'Contenido del tutor' : fallback;
  }

  List<ExamQuestionData> _parseAiQuestions(
    String raw, {
    required String content,
    required List<StudyGuide> guides,
    required List<String> avoidQuestions,
  }) {
    try {
      final start = raw.indexOf('[');
      final end = raw.lastIndexOf(']');
      if (start < 0 || end <= start) return const [];
      final decoded = jsonDecode(raw.substring(start, end + 1));
      if (decoded is! List) return const [];
      final out = <ExamQuestionData>[];
      for (final item in decoded.whereType<Map>()) {
        final map = Map<String, dynamic>.from(item);
        final q = (map['question'] ?? map['pregunta'])?.toString().trim() ?? '';
        final proposed = (map['answer'] ?? map['respuesta'])?.toString().trim() ?? '';
        final evidence = (map['evidence'] ?? map['evidencia'])?.toString().trim() ?? '';
        final source = (map['source'] ?? map['fuente'])?.toString().trim() ?? '';
        if (_lowQualityQuestion(q) || evidence.isEmpty) continue;
        if (!_evidenceInContent(evidence, content)) continue;
        if (avoidQuestions.any((old) => _nearDuplicate(old, q))) continue;
        if (out.any((old) => _nearDuplicate(old.question, q))) continue;
        final answer = _answerSupportedByEvidence(proposed, evidence) ? proposed : evidence;
        if (_looksIncomplete(answer)) continue;
        out.add(ExamQuestionData(
          question: q,
          answer: answer,
          sourceTitle: _sourceForEvidence(guides, evidence, source),
        ));
      }
      return out;
    } catch (_) {
      return const [];
    }
  }

'''
s = s[:start] + new_helpers + s[end:]

# Add recent-question avoidance to _buildExam.
old = """    final fallback = _cardQuestions(guides, count);
    var questions = <ExamQuestionData>[];
    var generatorLabel = 'Instantáneo • contenido indexado';
"""
new = """    final recentQuestions = _recentQuestions(tutor.id);
    final fallback = _cardQuestions(
      guides,
      count,
      avoidQuestions: recentQuestions,
    );
    var questions = <ExamQuestionData>[];
    var generatorLabel = 'Instantáneo • contenido indexado';
    var aiAccepted = 0;
"""
if old not in s:
    raise RuntimeError('buildExam fallback anchor not found')
s = s.replace(old, new, 1)

# Replace AI prompt and parsing block with grounded evidence requirements.
old_prompt = """          prompt: '''Crea un examen de $aiCount preguntas basado EXCLUSIVAMENTE en el contenido del tutor ${tutor.name}.
Dificultad: $difficulty.

REGLAS:
- Evalúa comprensión real, no solo memorización literal.
- No uses información de otros tutores ni conocimiento externo.
- Distribuye las preguntas entre los temas disponibles.
- La respuesta debe ser breve pero suficiente para corregir.
- Devuelve SOLO un arreglo JSON válido, sin Markdown y sin explicaciones adicionales.
- Formato exacto de cada elemento: {\"question\":\"...\",\"answer\":\"...\",\"source\":\"nombre o tema de la fuente\"}.

CONTENIDO DEL TUTOR:
$content''',
        );
        questions = _parseAiQuestions(raw);
"""
new_prompt = """          prompt: '''Crea un examen NUEVO de $aiCount preguntas basado EXCLUSIVAMENTE en el contenido del tutor ${tutor.name}.
Dificultad: $difficulty.

REGLAS OBLIGATORIAS:
- Evalúa comprensión real, no solo memorización literal.
- No uses información externa ni contenido de otros tutores.
- No repitas ni reformules de manera casi idéntica preguntas recientes.
- No preguntes \"¿cuál es la fórmula de P/X/r...?\" cuando esa letra solo representa una variable. En ese caso pregunta qué representa la variable y da contexto.
- Toda fórmula debe estar COMPLETA. No cortes expresiones a mitad.
- Cada respuesta debe estar respaldada directamente por un fragmento de las fuentes.
- \"evidence\" DEBE ser una cita textual exacta y completa copiada del CONTENIDO DEL TUTOR; Memora verificará que exista antes de aceptar la pregunta.
- Devuelve SOLO un arreglo JSON válido, sin Markdown ni explicaciones.
- Formato exacto: {\"question\":\"...\",\"answer\":\"...\",\"evidence\":\"fragmento textual exacto\",\"source\":\"nombre/tema\"}.

PREGUNTAS RECIENTES QUE DEBES EVITAR:
${recentQuestions.take(30).map((q) => '- $q').join('\\n')}

CONTENIDO DEL TUTOR:
$content''',
        );
        questions = _parseAiQuestions(
          raw,
          content: content,
          guides: guides,
          avoidQuestions: recentQuestions,
        );
        aiAccepted = questions.length;
"""
if old_prompt not in s:
    raise RuntimeError('AI exam prompt anchor not found')
s = s.replace(old_prompt, new_prompt, 1)

old_dedupe = """    final seen = questions.map((e) => e.question.toLowerCase()).toSet();
    for (final item in fallback) {
      if (questions.length >= count) break;
      if (seen.add(item.question.toLowerCase())) questions.add(item);
    }
    if (questions.length > count) questions = questions.take(count).toList();
"""
new_dedupe = """    for (final item in fallback) {
      if (questions.length >= count) break;
      if (questions.any((q) => _nearDuplicate(q.question, item.question))) continue;
      questions.add(item);
    }
    if (questions.length > count) questions = questions.take(count).toList();
    if (generatorMode != 'instant') {
      if (aiAccepted == 0) {
        generatorLabel = '$generatorLabel • respaldo verificado de tarjetas';
      } else if (aiAccepted < questions.length) {
        generatorLabel = '$generatorLabel • $aiAccepted IA + ${questions.length - aiAccepted} verificadas';
      } else {
        generatorLabel = '$generatorLabel • respuestas verificadas contra fuente';
      }
    }
"""
if old_dedupe not in s:
    raise RuntimeError('exam dedupe anchor not found')
s = s.replace(old_dedupe, new_dedupe, 1)

p.write_text(s)
print('Memora v1.8 exam quality patch applied successfully')
