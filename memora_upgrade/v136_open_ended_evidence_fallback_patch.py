from pathlib import Path

p = Path('lib/tutor_page.dart')
s = p.read_text()

# v1.36: open-ended tutor requests must never reach the model with empty
# SOURCE EVIDENCE just because the random excerpt/card sampler found nothing.
# If that sampler is empty, fall back to the indexed coverage context that the
# retriever already maintains for the assigned guides.
old = """      var semanticIntentRouting = false;
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
"""

new = """      var semanticIntentRouting = false;
      var context = broad
          ? await _randomGuideContext(guides, maxChars: contextChars)
          : KnowledgeRetriever.buildContext(
              guides: guides,
              query: '$question\\n$attachmentText',
              maxChars: contextChars,
              maxChunks: contextChunks,
              allowUnmatchedFallback: false,
            );

      // Open-ended requests previously depended entirely on the random sampler.
      // Imported guides can still have indexed knowledge even when raw text or
      // persisted cards are unavailable to that sampler. Never send an empty
      // SOURCE EVIDENCE block in that case.
      if (broad && context.trim().isEmpty) {
        context = KnowledgeRetriever.buildCoverageContext(
          guides: guides,
          maxChars: 3600,
          maxChunks: 5,
        );
      }

      // If literal/fuzzy retrieval cannot map the wording to a specific excerpt,
"""

if old not in s:
    raise RuntimeError('v1.36 open-ended evidence anchor not found')

s = s.replace(old, new, 1)
p.write_text(s)
print('Memora v1.36 open-ended evidence fallback patch applied successfully')

import os
_v137 = Path(os.environ['GITHUB_WORKSPACE']) / 'memora_upgrade' / 'v137_exam_delete_reasoning_patch.py'
exec(compile(_v137.read_text(), str(_v137), 'exec'))
