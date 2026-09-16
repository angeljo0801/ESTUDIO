from pathlib import Path

p = Path('lib/tutor_page.dart')
s = p.read_text()

# Memora v1.32
# Let the selected LLM interpret open-ended tutor requests semantically when the
# literal retriever cannot map the user's wording to a specific guide excerpt.
# Explicit phrase matching remains only a zero-latency fast path; correctness no
# longer depends on adding every possible Spanish/English wording to a regex.

old_context = """      final attachmentText = QueryAttachmentService.buildTextContext(attachments);
      final broad = broadRequest;
      final simple = simpleRequest;
      final contextChars = broad
          ? 1200
          : (simple && responseMode == 'fast' ? 2400 : baseLimits.$1);
      final contextChunks = broad
          ? 2
          : (simple && responseMode == 'fast' ? 2 : baseLimits.$2);
      var context = broad
          ? await _randomGuideContext(guides, maxChars: contextChars)
          : KnowledgeRetriever.buildContext(
              guides: guides,
              query: '$question\\n$attachmentText',
              maxChars: contextChars,
              maxChunks: contextChunks,
              allowUnmatchedFallback: false,
            );
      if (!broad && context.startsWith('(No matching evidence found')) {
        context = KnowledgeRetriever.buildCoverageContext(
          guides: guides,
          maxChars: simple && responseMode == 'fast' ? 3600 : baseLimits.$1,
          maxChunks: simple && responseMode == 'fast' ? 4 : baseLimits.$2,
        );
      }
"""
new_context = """      final attachmentText = QueryAttachmentService.buildTextContext(attachments);
      final broad = broadRequest;
      final simple = simpleRequest;
      final contextChars = broad
          ? 1200
          : (simple && responseMode == 'fast' ? 2400 : baseLimits.$1);
      final contextChunks = broad
          ? 2
          : (simple && responseMode == 'fast' ? 2 : baseLimits.$2);
      var semanticIntentRouting = false;
      var context = broad
          ? await _randomGuideContext(guides, maxChars: contextChars)
          : KnowledgeRetriever.buildContext(
              guides: guides,
              query: '$question\\n$attachmentText',
              maxChars: contextChars,
              maxChunks: contextChunks,
              allowUnmatchedFallback: false,
            );

      // If literal/fuzzy retrieval cannot map the wording to a specific excerpt,
      // do NOT reject the request before the LLM sees it. Give the model a real,
      // non-repeating sample of the assigned material and let it infer whether
      // the user's meaning is open-ended or a specific unsupported question.
      if (!broad &&
          attachments.isEmpty &&
          context.startsWith('(No matching evidence found')) {
        semanticIntentRouting = true;
        context = await _randomGuideContext(
          guides,
          maxChars: simple && responseMode == 'fast' ? 1800 : 3200,
        );
        if (context.trim().isEmpty) {
          context = KnowledgeRetriever.buildCoverageContext(
            guides: guides,
            maxChars: simple && responseMode == 'fast' ? 3600 : baseLimits.$1,
            maxChunks: simple && responseMode == 'fast' ? 4 : baseLimits.$2,
          );
        }
      } else if (!broad && context.startsWith('(No matching evidence found')) {
        context = KnowledgeRetriever.buildCoverageContext(
          guides: guides,
          maxChars: simple && responseMode == 'fast' ? 3600 : baseLimits.$1,
          maxChunks: simple && responseMode == 'fast' ? 4 : baseLimits.$2,
        );
      }
"""
if old_context not in s:
    raise RuntimeError('v1.32 semantic context anchor not found')
s = s.replace(old_context, new_context, 1)

old_rule = """      final sourceRule = broad
          ? 'The user asked for a random point. Choose ONE meaningful fact or concept explicitly present in SOURCE EVIDENCE and explain it. Do not repeat the user request.'
          : 'Answer only when SOURCE EVIDENCE or CURRENT ATTACHMENTS support the answer. The wording may be paraphrased; it does not need to be a literal sentence match.';
"""
new_rule = """      final sourceRule = broad
          ? 'The user asked for an open-ended point from the assigned material. Choose ONE meaningful fact or concept explicitly present in SOURCE EVIDENCE and explain it. Do not repeat the user request.'
          : semanticIntentRouting
              ? '''Interpret the CURRENT USER MESSAGE by meaning, not by literal keyword matching.
First decide silently whether the user is making an open-ended request for material from the assigned guides or asking a specific factual question.
If it is open-ended, choose ONE useful fact, concept, relationship, formula, cause/effect, comparison, or application from SOURCE EVIDENCE and answer naturally.
If it is a specific question, answer only when SOURCE EVIDENCE directly supports that answer; otherwise use the exact not-found reply required below.
Do not require the user's wording to appear verbatim in the guide and do not mention this routing decision.'''
              : 'Answer only when SOURCE EVIDENCE or CURRENT ATTACHMENTS support the answer. The wording may be paraphrased; it does not need to be a literal sentence match.';
"""
if old_rule not in s:
    raise RuntimeError('v1.32 semantic source-rule anchor not found')
s = s.replace(old_rule, new_rule, 1)

# The semantic route is intentionally handled by the same answer-generation call
# rather than a second classifier call, preserving responsiveness on Ollama/GGUF.
old_mode = """        responseMode: broad || (simple && responseMode == 'fast') ? 'fast' : responseMode,
"""
new_mode = """        responseMode: broad || semanticIntentRouting || (simple && responseMode == 'fast')
            ? 'fast'
            : responseMode,
"""
if old_mode not in s:
    raise RuntimeError('v1.32 response mode anchor not found')
s = s.replace(old_mode, new_mode, 1)

# Clarify the permanent system prompt so the LLM knows that Memora itself may
# have supplied coverage evidence because the user's phrasing was semantic.
old_prompt_rule = """- Never invent a fact that is not supported by SOURCE EVIDENCE or CURRENT ATTACHMENTS.
- If the answer is not explicitly supported, reply exactly: I could not find that in the assigned guides.
"""
new_prompt_rule = """- Never invent a fact that is not supported by SOURCE EVIDENCE or CURRENT ATTACHMENTS.
- Understand the user's request semantically across natural wording and languages; do not treat the message as a literal search string.
- If the message is open-ended, it is valid to select a supported point from the supplied evidence even when the user's words do not occur in that evidence.
- If a specific requested answer is not supported, reply exactly: I could not find that in the assigned guides.
"""
if old_prompt_rule not in s:
    raise RuntimeError('v1.32 semantic prompt anchor not found')
s = s.replace(old_prompt_rule, new_prompt_rule, 1)

p.write_text(s)
print('Memora v1.32 semantic tutor intent router patch applied successfully')

import os
_v133 = Path(os.environ['GITHUB_WORKSPACE']) / 'memora_upgrade' / 'v133_exam_bottom_buttons_patch.py'
exec(compile(_v133.read_text(), str(_v133), 'exec'))
