from pathlib import Path

# v178: catch glossary/formula collisions like:
# "PMT = Payment FV = Future value ..." being misread as a formula card.
# Formula cards are always sent to the optional AI final debugger, and the
# deterministic fallback rejects obviously merged glossary rows even if AI is
# unavailable.

# ---------------------------------------------------------------------------
# Local hard filter.
# ---------------------------------------------------------------------------
p = Path('lib/study_card_quality_service.dart')
s = p.read_text()

anchor = """    if (RegExp(r'[×÷=]').hasMatch(q) &&
        RegExp(r'\\b\\d+\\.\\d+\\b').hasMatch(q) &&
        RegExp(r'\\b[A-Z][a-z]+\\s+[A-Z][a-z]+').hasMatch(q)) {
      return true;
    }
"""
extra = anchor + r'''    final formulaQuestion = RegExp(
      r'^what is the formula or relationship for\b',
      caseSensitive: false,
    ).hasMatch(q);
    final repeatedGlossaryDefinitions = RegExp(
      r'\b[A-Z]{2,8}\s*=\s*[A-Za-z][A-Za-z ]{1,45}\s+[A-Z]{2,8}\s*=',
    ).hasMatch(a);
    if (repeatedGlossaryDefinitions) return true;

    if (formulaQuestion) {
      // A real relationship should contain an actual mathematical relationship,
      // not a glossary expansion such as "PMT = Payment".
      final rhs = a.contains('=') ? a.substring(a.indexOf('=') + 1).trim() : a;
      final hasMathRelationship =
          RegExp(r'[+\-×÷/*^()]').hasMatch(rhs) ||
          RegExp(r'\b(?:plus|minus|times|divided by|multiplied by|ratio|rate)\b',
                  caseSensitive: false)
              .hasMatch(rhs);
      final equalsCount = '='.allMatches(a).length;
      if (!a.contains('=') || repeatedGlossaryDefinitions) return true;
      if (equalsCount >= 2 && !hasMathRelationship) return true;
      if (!hasMathRelationship &&
          RegExp(r'^[A-Za-z][A-Za-z ]{1,35}$').hasMatch(rhs)) {
        return true;
      }
    }
'''
if anchor not in s:
    raise SystemExit('v178 local malformed anchor missing')
s = s.replace(anchor, extra, 1)
p.write_text(s)

# ---------------------------------------------------------------------------
# AI debugger: every formula/relationship card is suspicious by definition,
# because this is where PDF glossary collisions are especially costly.
# ---------------------------------------------------------------------------
p = Path('lib/ai_card_review_service.dart')
s = p.read_text()

suspicious_anchor = """    if (q.length > 175 || a.length < 20) return true;
    if (_delimiterBalance(q) != 0 || _delimiterBalance(a) != 0) return true;
"""
suspicious_new = """    if (q.length > 175 || a.length < 20) return true;
    if (_delimiterBalance(q) != 0 || _delimiterBalance(a) != 0) return true;
    if (RegExp(
      r'^what is the formula or relationship for\\b',
      caseSensitive: false,
    ).hasMatch(q)) {
      return true;
    }
    if (RegExp(
      r'\\b[A-Z]{2,8}\\s*=\\s*[A-Za-z][A-Za-z ]{1,45}\\s+[A-Z]{2,8}\\s*=',
    ).hasMatch(a)) {
      return true;
    }
"""
if suspicious_anchor not in s:
    raise SystemExit('v178 AI suspicious anchor missing')
s = s.replace(suspicious_anchor, suspicious_new, 1)

prompt_anchor = """- Broken equations, section numbers, headings, and unrelated fragments should be FIXED only when the intended card is unambiguous.
- A FIX must remain about the same source concept.
"""
prompt_new = """- Broken equations, section numbers, headings, and unrelated fragments should be FIXED only when the intended card is unambiguous.
- A glossary list such as "PMT = Payment, FV = Future value" is NOT a mathematical formula. If a card asks for a formula but the evidence only expands abbreviations, REJECT it.
- If multiple glossary definitions were accidentally merged into one answer, REJECT unless the exact intended formula is explicitly present in SOURCE EVIDENCE.
- A FIX must remain about the same source concept.
"""
if prompt_anchor not in s:
    raise SystemExit('v178 AI prompt anchor missing')
s = s.replace(prompt_anchor, prompt_new, 1)
p.write_text(s)

print('v178 applied: formula cards now catch glossary/PDF collisions')
