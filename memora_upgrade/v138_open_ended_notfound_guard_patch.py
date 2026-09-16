from pathlib import Path

p = Path('lib/tutor_page.dart')
s = p.read_text()

# v1.38: for an open-ended tutor request, a non-empty grounded context means
# there is material available to answer from. Some models are overly cautious
# and still return Memora's exact not-found sentence. Do not accept that false
# negative; fall back to a grounded answer extracted from the supplied evidence.
old = """      var finalResult = result.trim();
      if (finalResult.isEmpty || _looksLikeEcho(shownQuestion, finalResult)) {
        finalResult = broad
            ? _groundedFallback(context)
            : 'I could not find that in the assigned guides.';
      }
"""

new = """      var finalResult = result.trim();
      final normalizedResult = finalResult.toLowerCase().trim();
      final modelReturnedNotFound = normalizedResult ==
              'i could not find that in the assigned guides.' ||
          normalizedResult.contains('could not find that in the assigned guides') ||
          normalizedResult.contains('couldn\\'t find that in the assigned guides');

      if (finalResult.isEmpty ||
          _looksLikeEcho(shownQuestion, finalResult) ||
          (broad && context.trim().isNotEmpty && modelReturnedNotFound)) {
        finalResult = broad
            ? _groundedFallback(context)
            : 'I could not find that in the assigned guides.';
      }
"""

if old not in s:
    raise RuntimeError('v1.38 tutor final-result guard anchor not found')
s = s.replace(old, new, 1)

# Make the model instruction unambiguous too: an open-ended request with source
# evidence is always answerable by selecting a supported point from that evidence.
old_rule = """      final sourceRule = broad
          ? 'The user asked for an open-ended point from the assigned material. Choose ONE meaningful fact or concept explicitly present in SOURCE EVIDENCE and explain it. Do not repeat the user request.'
"""
new_rule = """      final sourceRule = broad
          ? 'The user asked for an open-ended point from the assigned material. SOURCE EVIDENCE contains material you can use. Choose ONE meaningful supported fact, concept, relationship, formula, cause/effect, comparison, or application and explain it naturally. For this open-ended request, do NOT reply with the not-found sentence when SOURCE EVIDENCE is non-empty. Do not repeat the user request.'
"""
if old_rule not in s:
    raise RuntimeError('v1.38 broad source-rule anchor not found')
s = s.replace(old_rule, new_rule, 1)

p.write_text(s)
print('Memora v1.38 open-ended not-found guard patch applied successfully')
