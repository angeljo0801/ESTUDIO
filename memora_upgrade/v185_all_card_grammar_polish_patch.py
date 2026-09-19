from pathlib import Path

# v185: grammar-polish EVERY accepted card.
#
# Validation and grammar cleanup are now the same mandatory AI pass:
# - KEEP means the concept/facts are already correct, but the model MUST still
#   return a polished question and answer using the guide/source evidence.
# - FIX means content/structure also needed repair.
# - REJECT still receives the v184 second-chance review.
#
# No accepted card may be published with blank AI-polished text.

p = Path('lib/ai_card_review_service.dart')
s = p.read_text()

# Strengthen action definitions.
old = """For EVERY ID choose exactly one:
- KEEP: already clear, useful, grammatical and supported by SOURCE EVIDENCE.
- FIX: improve the question/answer so it makes more sense, using ONLY the
  supplied SOURCE EVIDENCE.
- REJECT: mixed fragments, insufficient source evidence, ambiguous, ungradable,
  or impossible to repair without guessing.
"""
new = """For EVERY ID choose exactly one:
- KEEP: the underlying concept/facts are correct and supported by SOURCE EVIDENCE.
  EVEN FOR KEEP, rewrite and return a polished QUESTION and ANSWER with correct,
  natural grammar and clear study-card wording.
- FIX: the card also needs factual/structural repair. Rewrite and return a
  corrected QUESTION and ANSWER using ONLY SOURCE EVIDENCE.
- REJECT: mixed fragments, insufficient source evidence, ambiguous, ungradable,
  or impossible to repair without guessing.
"""
if old not in s:
    raise SystemExit('v185 action-definition anchor missing')
s = s.replace(old, new, 1)

# Add explicit grammar requirements.
old = """STRICT RULES:
1. Review EVERY ID.
2. Use only SOURCE EVIDENCE. Never add outside knowledge.
3. Never invent a formula, number, definition, example or relationship.
4. If wording is awkward but the source is clear, FIX it.
5. The corrected card must stay on the same concept.
6. Prefer one specific question with one clear answer.
7. Preserve meaningful numbers and formulas exactly.
8. If the PDF extraction mixed headings, glossary entries or unrelated lines,
   reconstruct only when the intended meaning is explicit in the evidence;
   otherwise REJECT.
9. Return ONLY a JSON array. No Markdown.
"""
new = """STRICT RULES:
1. Review EVERY ID.
2. Use only SOURCE EVIDENCE. Never add outside knowledge.
3. Never invent a formula, number, definition, example or relationship.
4. EVERY KEEP or FIX must return a complete rewritten question and answer.
5. Correct grammar, punctuation, agreement, OCR artifacts, awkward fragments,
   duplicated words, and unnatural phrasing even when the original card is
   factually correct.
6. Preserve the original meaning, technical terminology, formulas, units,
   names, and meaningful numbers exactly unless SOURCE EVIDENCE proves the
   draft was wrong.
7. The polished card must stay on the same concept.
8. Prefer one specific, natural question with one clear, complete answer.
9. Never shorten an answer so much that it loses information needed to study it.
10. If the PDF extraction mixed headings, glossary entries or unrelated lines,
    reconstruct only when the intended meaning is explicit in the evidence;
    otherwise REJECT.
11. Return ONLY a JSON array. No Markdown.
"""
if old not in s:
    # v183 may have the page/section rule inserted.
    old = """STRICT RULES:
1. Review EVERY ID.
2. Use only SOURCE EVIDENCE. Never add outside knowledge.
3. Never invent a formula, number, definition, example or relationship.
4. If wording is awkward but the source is clear, FIX it.
5. The corrected card must stay on the same concept.
6. Prefer one specific question with one clear answer.
7. Preserve meaningful numbers and formulas exactly.
8. Use PAGE/SECTION only to understand location; facts must come from evidence.
9. If PDF extraction mixed headings, glossary entries or unrelated lines,
   reconstruct only when the intended meaning is explicit; otherwise REJECT.
10. Return ONLY a JSON array. No Markdown.
"""
    new = """STRICT RULES:
1. Review EVERY ID.
2. Use only SOURCE EVIDENCE. Never add outside knowledge.
3. Never invent a formula, number, definition, example or relationship.
4. EVERY KEEP or FIX must return a complete rewritten question and answer.
5. Correct grammar, punctuation, agreement, OCR artifacts, awkward fragments,
   duplicated words, and unnatural phrasing even when the original card is
   factually correct.
6. Preserve the original meaning, technical terminology, formulas, units,
   names, and meaningful numbers exactly unless SOURCE EVIDENCE proves the
   draft was wrong.
7. The polished card must stay on the same concept.
8. Prefer one specific, natural question with one clear, complete answer.
9. Never shorten an answer so much that it loses information needed to study it.
10. Use PAGE/SECTION only to understand location; facts must come from evidence.
11. If PDF extraction mixed headings, glossary entries or unrelated lines,
    reconstruct only when the intended meaning is explicit; otherwise REJECT.
12. Return ONLY a JSON array. No Markdown.
"""
if old not in s:
    raise SystemExit('v185 strict-rules anchor missing')
s = s.replace(old, new, 1)

# JSON examples must teach even weaker/local models that KEEP returns text too.
old = """JSON FORMAT:
[
  {"id":0,"action":"KEEP","question":"","answer":""},
  {"id":1,"action":"FIX","question":"better question","answer":"better answer"},
  {"id":2,"action":"REJECT","question":"","answer":""}
]
"""
new = """JSON FORMAT:
[
  {"id":0,"action":"KEEP","question":"polished complete question?","answer":"Polished complete answer."},
  {"id":1,"action":"FIX","question":"corrected complete question?","answer":"Corrected complete answer."},
  {"id":2,"action":"REJECT","question":"","answer":""}
]
"""
if old not in s:
    raise SystemExit('v185 JSON-format anchor missing')
s = s.replace(old, new, 1)

# Before output, retry any accepted card for which the model failed to return
# usable polished text. The wider source context gives it one focused chance.
anchor = """    final output = <StudyCard>[];
"""
polish_retry = r'''    // Every accepted card must have AI-polished wording. If a model returned
    // KEEP/FIX but omitted the rewritten text, retry that card before publishing.
    final missingPolish = <int>[
      for (var i = 0; i < cards.length; i++)
        if (decisions[i] != null &&
            decisions[i]!.action != 'REJECT' &&
            (_clean(decisions[i]!.question).length < 10 ||
                _clean(decisions[i]!.answer).length < 6))
          i,
    ];

    for (final id in missingPolish) {
      try {
        final polished = await _request(
          guide: guide,
          cards: cards,
          indexes: <int>[id],
          focusedRetry: true,
          secondReview: true,
        );
        final decision = polished[id];
        if (decision != null) decisions[id] = decision;
      } catch (_) {
        // If grammar polish cannot be completed, this draft must not be exposed.
      }
    }

'''
if anchor not in s:
    raise SystemExit('v185 output anchor missing')
s = s.replace(anchor, polish_retry + anchor, 1)

# Replace KEEP's previous "publish original as-is" behavior. KEEP and FIX now
# both publish the AI-returned polished wording after source/numeric validation.
old = """      if (decision.action == 'KEEP') {
        if (StudyCardQualityService.isObviouslyMalformed(original)) {
          rejected++;
          continue;
        }
        output.add(original);
        continue;
      }

      final question = _clean(decision.question);
      final answer = _clean(decision.answer);
      final evidence = _evidenceFor(guide, original);

      if (question.length < 10 ||
          answer.length < 6 ||
          !_numbersSupported(question + ' ' + answer, evidence)) {
        rejected++;
        continue;
      }

      final repaired = StudyCard(
"""
new = """      final question = _clean(decision.question);
      final answer = _clean(decision.answer);
      final evidence = _evidenceFor(guide, original);

      // KEEP is no longer permission to pass the parser wording unchanged.
      // Every visible card must contain the model's polished wording.
      if (question.length < 10 ||
          answer.length < 6 ||
          !_numbersSupported(question + ' ' + answer, evidence)) {
        rejected++;
        continue;
      }

      final repaired = StudyCard(
"""
if old not in s:
    raise SystemExit('v185 KEEP-processing anchor missing')
s = s.replace(old, new, 1)

# Count a KEEP rewrite as fixed only when wording actually changed. This keeps
# diagnostics meaningful without affecting card publication.
old = """      output.add(repaired);
      fixed++;
"""
new = """      output.add(repaired);
      final wordingChanged =
          _clean(original.question) != question ||
          _clean(original.answer) != answer;
      if (decision.action == 'FIX' || wordingChanged) fixed++;
"""
if old not in s:
    raise SystemExit('v185 fixed-counter anchor missing')
s = s.replace(old, new, 1)

p.write_text(s)

print('v185 applied: every accepted card receives source-grounded AI grammar polish')
