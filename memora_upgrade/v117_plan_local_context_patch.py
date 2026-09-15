from pathlib import Path

# Memora v1.17
# Fix study-plan generation with on-device GGUF models. A 4096-token local
# context cannot safely receive the old ~18k-character library dump. Build a
# balanced digest that represents every guide and keep local prompts compact.

# -----------------------------------------------------------------------------
# Study plan: balanced source digest + local-safe prompt budget + live provider
# status while "Best AI" tries its fallbacks.
# -----------------------------------------------------------------------------
p = Path('lib/study_plan_page.dart')
s = p.read_text()

import_anchor = "import 'guide_store.dart';\n"
if import_anchor not in s:
    raise RuntimeError('StudyPlan models import anchor not found')
s = s.replace(import_anchor, import_anchor + "import 'models.dart';\n", 1)

helper_anchor = "  Future<void> _copyPlan() async {"
helper = r'''  static bool _isLocalPlanProvider(String provider) {
    return provider == 'private' ||
        provider == 'shared' ||
        provider == 'device';
  }

  String _planSourceDigest(
    List<StudyGuide> guides, {
    required int maxChars,
  }) {
    final usable = guides
        .where(
          (guide) =>
              guide.summary.trim().isNotEmpty || guide.text.trim().isNotEmpty,
        )
        .toList();
    if (usable.isEmpty || maxChars <= 0) return '';

    // Divide the budget across all guides so "Toda mi Biblioteca" does not
    // silently use only the first few files. Prefer each guide's summary, then
    // add source text when space remains.
    final rawShare = maxChars ~/ usable.length;
    final share = rawShare < 120 ? 120 : rawShare;
    final buffer = StringBuffer();

    for (final guide in usable) {
      if (buffer.length >= maxChars) break;
      final header = '===== ${guide.title} =====\n';
      final remainingGlobal = maxChars - buffer.length;
      if (remainingGlobal <= header.length + 20) break;

      var available = share - header.length - 1;
      if (available < 70) available = 70;
      final maxForThisGuide = remainingGlobal - header.length - 1;
      if (available > maxForThisGuide) available = maxForThisGuide;

      final summary = guide.summary.trim();
      final sourceText = guide.text.trim();
      var source = summary;
      if (source.isEmpty) {
        source = sourceText;
      } else if (sourceText.isNotEmpty && source.length < (available * 0.55)) {
        source = '$source\n$sourceText';
      }
      if (source.isEmpty) continue;

      String excerpt;
      if (source.length <= available) {
        excerpt = source;
      } else if (available < 180) {
        excerpt = source.substring(0, available);
      } else {
        final headLength = (available * 0.72).floor();
        final tailLength = available - headLength - 3;
        excerpt = '${source.substring(0, headLength)} … ${source.substring(source.length - tailLength)}';
      }

      buffer.write(header);
      buffer.write(excerpt);
      buffer.writeln();
    }

    final result = buffer.toString().trim();
    return result.length <= maxChars ? result : result.substring(0, maxChars);
  }

'''
if helper_anchor not in s:
    raise RuntimeError('StudyPlan helper insertion anchor not found')
s = s.replace(helper_anchor, helper + helper_anchor, 1)

old = """    final content = TutorContextService.contentForGuides(guides, maxChars: 18000);
"""
new = """    final hasLocalCandidate = providerCandidates.any(_isLocalPlanProvider);
    // The bundled GGUF runtime uses a 4096-token context. Keep enough room for
    // Memora's instructions and for the generated plan itself.
    final content = _planSourceDigest(
      guides,
      maxChars: hasLocalCandidate ? 6000 : 18000,
    );
"""
if old not in s:
    raise RuntimeError('StudyPlan content budget anchor not found')
s = s.replace(old, new, 1)

old = """      for (final candidate in providerCandidates) {
        try {
"""
new = """      for (final candidate in providerCandidates) {
        if (mounted) {
          setState(() {
            usedSource = 'Probando ${TutorContextService.sourceLabel(candidate)}…';
          });
        }
        try {
"""
if old not in s:
    raise RuntimeError('StudyPlan provider loop anchor not found')
s = s.replace(old, new, 1)

p.write_text(s)

# -----------------------------------------------------------------------------
# Friendly error for prompt/context overflows if a user selects a particularly
# small-context GGUF model manually elsewhere in Memora.
# -----------------------------------------------------------------------------
p = Path('lib/ai_service.dart')
s = p.read_text()
anchor = """    if (lower.contains('already generating') ||
        lower.contains('context is busy') ||
        lower.contains('context busy')) {
"""
insert = """    if (lower.contains('failed to decode prompt') ||
        lower.contains('prompt is too long') ||
        lower.contains('prompt too long') ||
        lower.contains('context length') ||
        lower.contains('context window')) {
      return 'El contenido supera el contexto de este modelo local. Memora reducirá el contexto en las tareas compatibles; si vuelve a ocurrir, usa un modelo con una ventana de contexto mayor.';
    }
"""
if anchor not in s:
    raise RuntimeError('AiService error mapping anchor not found')
s = s.replace(anchor, insert + anchor, 1)
p.write_text(s)

print('Memora v1.17 local study-plan context patch applied successfully')
