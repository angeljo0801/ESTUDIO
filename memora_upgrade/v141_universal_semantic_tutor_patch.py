from pathlib import Path

p = Path('lib/tutor_page.dart')
s = p.read_text()

# -----------------------------------------------------------------------------
# Memora v1.41: universal natural-language tutor routing.
# The selected LLM, not a phrase list, is the final authority on what a user's
# message means. Fast regex paths remain only optimizations for obvious cases.
# -----------------------------------------------------------------------------
helper_anchor = "  bool _isOpenEndedContinuation(String value) {\n"
helpers = r'''  String _tutorIntentFromResult(String value) {
    final match = RegExp(
      r'^\s*\[\[(OPEN|SPECIFIC|FOLLOWUP|CHAT)\]\]',
      caseSensitive: false,
    ).firstMatch(value);
    return match?.group(1)?.toUpperCase() ?? '';
  }

  String _stripTutorIntentMarker(String value) {
    return value.replaceFirst(
      RegExp(
        r'^\s*\[\[(?:OPEN|SPECIFIC|FOLLOWUP|CHAT)\]\]\s*',
        caseSensitive: false,
      ),
      '',
    );
  }

  String _visibleTutorPartial(String value) {
    final trimmed = value.trimLeft();
    if (!trimmed.startsWith('[[')) return value;
    final end = trimmed.indexOf(']]');
    if (end < 0) return '';
    return trimmed.substring(end + 2).trimLeft();
  }

'''
if '_tutorIntentFromResult(' not in s:
    if helper_anchor not in s:
        raise RuntimeError('v1.41 tutor helper anchor not found')
    s = s.replace(helper_anchor, helpers + helper_anchor, 1)

old_history = """    final history = broadRequest
        ? ''
        : simpleRequest
            ? current.conversationContext(maxChars: 700, maxMessages: 4)
            : _conversationHistory();
"""
new_history = """    final history = current.conversationContext(
      maxChars: simpleRequest ? 1800 : 3200,
      maxMessages: simpleRequest ? 6 : 10,
    );
"""
if new_history not in s:
    if old_history not in s:
        raise RuntimeError('v1.41 conversation history anchor not found')
    s = s.replace(old_history, new_history, 1)

if 'START your response with exactly one machine marker:' not in s:
    source_start = s.find('      final sourceRule = broad\n')
    source_end = s.find('\n\n      final result = await AiService.askConfigured(', source_start)
    if source_start < 0 or source_end < 0:
        raise RuntimeError('v1.41 source rule block not found')
    # This replacement spans the old sourceRule block through the call site.
    # Preserve answerStyle here because the prompt below still interpolates it.
    new_source = r"""      final answerStyle = broad
          ? 'Answer in 1-2 concise sentences. Pick one concrete point from the supplied guide excerpt and explain it directly.'
          : responseMode == 'fast'
              ? 'Answer directly in 1-3 concise sentences. No preamble and no unnecessary repetition.'
              : responseMode == 'deep'
                  ? 'Give a thorough but focused explanation, connecting the relevant ideas in the guide.'
                  : 'Give a clear, concise explanation with enough context to understand the answer.';
      final sourceRule = '''Interpret the CURRENT USER MESSAGE by meaning, not by literal keywords or command phrases.
Use CONVERSATION HISTORY to resolve pronouns, omitted subjects, shorthand, typos, colloquial language, and follow-ups.
Silently determine the intent, then START your response with exactly one machine marker:
[[OPEN]] = the user wants any/new/another/more material from the assigned guides, including an open-ended continuation.
[[SPECIFIC]] = the user is asking a specific factual question about the material.
[[FOLLOWUP]] = the user wants the previous answer explained, simplified, expanded, compared, reformulated, or otherwise transformed.
[[CHAT]] = greeting, acknowledgement, conversational/meta message, or something that does not ask for new factual guide content.

Interpret semantically across languages. Do not require any particular phrase to trigger an intent.
If OPEN, choose ONE useful supported fact, concept, relationship, formula, cause/effect, comparison, example, or application from SOURCE EVIDENCE and answer naturally. Prefer a different point from recent turns.
If SPECIFIC, answer only if SOURCE EVIDENCE or CURRENT ATTACHMENTS support the requested fact; otherwise use the exact not-found sentence required below.
If FOLLOWUP, use CONVERSATION HISTORY to understand what the user refers to and respond to that conversational request while keeping factual claims consistent with the assigned material.
If CHAT, respond naturally; do not force an unrelated guide fact into the conversation.
The marker is for Memora only. After the marker, write only the normal user-facing answer.''';"""
    s = s[:source_start] + new_source + s[source_end:]

old_prompt_line = "- Keep the conversation natural and use the history only for conversational continuity, never as evidence that overrides the guides.\n"
new_prompt_line = """- Keep the conversation natural. Use CONVERSATION HISTORY to resolve references and understand what the user means.
- Greetings, acknowledgements, and conversational/meta requests that do not ask for new factual guide content may be answered naturally without source evidence.
- When the user asks to explain, simplify, expand, compare, or reformulate your previous grounded answer, use that previous answer as conversational context while keeping all factual claims consistent with the assigned material.
- Conversation history must never override contradictory SOURCE EVIDENCE.
"""
if new_prompt_line not in s:
    if old_prompt_line not in s:
        raise RuntimeError('v1.41 permanent conversation rule anchor not found')
    s = s.replace(old_prompt_line, new_prompt_line, 1)

old_partial = """        onPartial: (partial) {
          if (partial.isNotEmpty) _updateAssistantBubble(pending.id, partial, token);
        },
"""
new_partial = """        onPartial: (partial) {
          final visible = _visibleTutorPartial(partial);
          if (visible.isNotEmpty) {
            _updateAssistantBubble(pending.id, visible, token);
          }
        },
"""
if new_partial not in s:
    if old_partial not in s:
        raise RuntimeError('v1.41 streaming partial anchor not found')
    s = s.replace(old_partial, new_partial, 1)

old_final = """      var finalResult = result.trim();
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
new_final = """      final semanticIntent = _tutorIntentFromResult(result);
      var finalResult = _stripTutorIntentMarker(result).trim();
      final normalizedResult = finalResult.toLowerCase().trim();
      final modelReturnedNotFound = normalizedResult ==
              'i could not find that in the assigned guides.' ||
          normalizedResult.contains('could not find that in the assigned guides') ||
          normalizedResult.contains('couldn\\'t find that in the assigned guides');
      final semanticallyOpen = broad || semanticIntent == 'OPEN';

      if (finalResult.isEmpty ||
          _looksLikeEcho(shownQuestion, finalResult) ||
          (semanticallyOpen && context.trim().isNotEmpty && modelReturnedNotFound)) {
        finalResult = semanticallyOpen
            ? _groundedFallback(context)
            : 'I could not find that in the assigned guides.';
      }
"""
if new_final not in s:
    if old_final not in s:
        raise RuntimeError('v1.41 final semantic result anchor not found')
    s = s.replace(old_final, new_final, 1)

p.write_text(s)
print('Memora v1.41 universal semantic tutor patch applied successfully')

import os
_v142 = Path(os.environ['GITHUB_WORKSPACE']) / 'memora_upgrade' / 'v142_clean_exam_answers_patch.py'
exec(compile(_v142.read_text(), str(_v142), 'exec'))
