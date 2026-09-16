from pathlib import Path

p = Path('lib/tutor_page.dart')
s = p.read_text()

# v1.40: short elliptical follow-ups such as "otro dato" should inherit the
# previous open-ended guide request instead of being treated as a brand-new
# literal search. Semantic routing remains the general fallback; this is a
# conversation-state fast path for common continuation turns.
helper_anchor = "  bool _isBroadGuideRequest(String value) {\n"
helper = r'''  bool _isOpenEndedContinuation(String value) {
    final text = value.toLowerCase().trim();
    if (text.isEmpty || text.length > 90) return false;

    // These are deliberately only continuation cues. They do not replace the
    // semantic router for arbitrary natural-language requests.
    return RegExp(
      r'^(?:otro|otra|otros|otras)(?:\s+(?:dato|concepto|punto|ejemplo|idea|tema|uno|una|más|mas))?[.!?¿¡\s]*$|'
      r'^(?:uno|una)\s+m[aá]s[.!?¿¡\s]*$|'
      r'^(?:dame|dime|mu[eé]strame|ponme)\s+(?:otro|otra|uno\s+m[aá]s|una\s+m[aá]s)(?:\s+(?:dato|concepto|punto|ejemplo|idea|tema))?[.!?¿¡\s]*$|'
      r'^(?:sigue|contin[uú]a|continua|m[aá]s|mas|again|another|more|next|continue|one\s+more|give\s+me\s+another|tell\s+me\s+another|something\s+else)[.!?¿¡\s]*$',
      caseSensitive: false,
    ).hasMatch(text);
  }

'''
if '_isOpenEndedContinuation(' not in s:
    if helper_anchor not in s:
        raise RuntimeError('v1.40 broad helper anchor not found')
    s = s.replace(helper_anchor, helper + helper_anchor, 1)

old_history = """    final shownQuestion = question.isEmpty ? 'Analyze the attached content.' : question;

    // Look at the immediately preceding user turn before adding the new one.
    // This makes short anaphoric turns inherit the established open-ended
    // intent without forcing a second LLM classifier call.
    var previousUserText = '';
    for (final message in current.messages.reversed) {
      if (message.role == 'user' && message.text.trim().isNotEmpty) {
        previousUserText = message.text.trim();
        break;
      }
    }
    final previousWasOpenEnded = previousUserText.isNotEmpty &&
        (_isBroadGuideRequest(previousUserText) ||
            _isOpenEndedContinuation(previousUserText));
    final continuationRequest = attachments.isEmpty &&
        previousWasOpenEnded &&
        _isOpenEndedContinuation(shownQuestion);

    final broadRequest = attachments.isEmpty &&
        (_isBroadGuideRequest(shownQuestion) || continuationRequest);
    final simpleRequest = attachments.isEmpty && _isSimpleTutorRequest(shownQuestion);
    final history = broadRequest
        ? ''
        : simpleRequest
            ? current.conversationContext(maxChars: 700, maxMessages: 4)
            : _conversationHistory();
"""

new_history = """    final shownQuestion = question.isEmpty ? 'Analyze the attached content.' : question;

    // Look at the immediately preceding user turn before adding the new one.
    // This makes short anaphoric turns inherit the established open-ended
    // intent without forcing a second LLM classifier call.
    var previousUserText = '';
    for (final message in current.messages.reversed) {
      if (message.role == 'user' && message.text.trim().isNotEmpty) {
        previousUserText = message.text.trim();
        break;
      }
    }
    final previousWasOpenEnded = previousUserText.isNotEmpty &&
        (_isBroadGuideRequest(previousUserText) ||
            _isOpenEndedContinuation(previousUserText));
    final continuationRequest = attachments.isEmpty &&
        previousWasOpenEnded &&
        _isOpenEndedContinuation(shownQuestion);

    final broadRequest = attachments.isEmpty &&
        (_isBroadGuideRequest(shownQuestion) || continuationRequest);
    final simpleRequest = attachments.isEmpty && _isSimpleTutorRequest(shownQuestion);
    final history = broadRequest
        ? ''
        : simpleRequest
            ? current.conversationContext(maxChars: 700, maxMessages: 4)
            : _conversationHistory();
"""

if old_history not in s:
    raise RuntimeError('v1.40 tutor conversation-history anchor not found')
s = s.replace(old_history, new_history, 1)

# Give semantic routing stronger conversational instructions too. This preserves
# semantic interpretation for wordings that are not covered by the fast path.
old_semantic = """First decide silently whether the user is making an open-ended request for material from the assigned guides or asking a specific factual question.
If it is open-ended, choose ONE useful fact, concept, relationship, formula, cause/effect, comparison, or application from SOURCE EVIDENCE and answer naturally.
"""
new_semantic = """First decide silently whether the user is making an open-ended request for material from the assigned guides or asking a specific factual question.
Use CONVERSATION HISTORY to resolve short, elliptical, or referential follow-ups. If the previous user intent was open-ended and the current message semantically means another/more/continue, preserve that open-ended intent rather than treating the words as a literal search query.
If it is open-ended, choose ONE useful fact, concept, relationship, formula, cause/effect, comparison, or application from SOURCE EVIDENCE and answer naturally.
"""
if old_semantic not in s:
    raise RuntimeError('v1.40 semantic continuation instruction anchor not found')
s = s.replace(old_semantic, new_semantic, 1)

p.write_text(s)
print('Memora v1.40 conversational open-ended follow-up patch applied successfully')

import os
_v141 = Path(os.environ['GITHUB_WORKSPACE']) / 'memora_upgrade' / 'v141_universal_semantic_tutor_patch.py'
exec(compile(_v141.read_text(), str(_v141), 'exec'))
