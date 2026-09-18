from pathlib import Path
import re

# v168: vector knowledge now feeds exams, flashcards, study plans and review banks.

p = Path('lib/vector_knowledge_store.dart')
s = p.read_text()

coverage = r"""  static Future<String> buildCoverageContext(
    List<StudyGuide> guides, {
    int maxChars = 18000,
    int maxChunks = 18,
  }) async {
    if (guides.isEmpty) return '';
    final safeChunks = maxChunks.clamp(1, 96).toInt();

    if (!await EmbeddingService.isReady()) {
      return _fallbackCoverage(guides, maxChars: maxChars, maxChunks: safeChunks);
    }

    final pool = <_CoverageChunk>[];
    for (final guide in guides) {
      await ensureIndexed(guide);
      final file = await _fileFor(guide.id);
      if (!await file.exists()) continue;
      try {
        final data = jsonDecode(await file.readAsString()) as Map<String, dynamic>;
        final chunks = (data['chunks'] as List<dynamic>? ?? const []);
        for (final raw in chunks) {
          final row = Map<String, dynamic>.from(raw as Map);
          final text = row['text']?.toString().trim() ?? '';
          final encoded = row['vector']?.toString() ?? '';
          if (text.isEmpty || encoded.isEmpty) continue;
          final vector = _decodeVector(encoded);
          if (vector.isEmpty) continue;
          pool.add(_CoverageChunk(
            guide: guide,
            text: text,
            vector: vector,
            order: (row['order'] as num?)?.toInt() ?? 0,
          ));
        }
      } catch (_) {}
    }

    if (pool.isEmpty) {
      return _fallbackCoverage(guides, maxChars: maxChars, maxChunks: safeChunks);
    }

    final selected = <_CoverageChunk>[];
    final selectedByGuide = <String, int>{};

    // One representative chunk per guide, chosen by closeness to the guide centroid.
    for (final guide in guides) {
      final group = pool.where((c) => c.guide.id == guide.id).toList();
      if (group.isEmpty || selected.length >= safeChunks) continue;
      final dims = group.first.vector.length;
      final centroid = List<double>.filled(dims, 0);
      for (final item in group) {
        final n = math.min(dims, item.vector.length);
        for (var i = 0; i < n; i++) {
          centroid[i] += item.vector[i];
        }
      }
      var norm2 = 0.0;
      for (var i = 0; i < dims; i++) {
        centroid[i] /= group.length;
        norm2 += centroid[i] * centroid[i];
      }
      final norm = math.sqrt(norm2);
      if (norm > 1e-12) {
        for (var i = 0; i < dims; i++) {
          centroid[i] /= norm;
        }
      }
      group.sort((a, b) => _dot(b.vector, centroid).compareTo(_dot(a.vector, centroid)));
      selected.add(group.first);
      selectedByGuide[guide.id] = 1;
    }

    // Semantic diversity + balance across guides.
    while (selected.length < safeChunks && selected.length < pool.length) {
      _CoverageChunk? best;
      var bestScore = -double.infinity;
      for (final candidate in pool) {
        if (selected.contains(candidate)) continue;
        var maxSimilarity = -1.0;
        for (final chosen in selected) {
          final similarity = _dot(candidate.vector, chosen.vector);
          if (similarity > maxSimilarity) maxSimilarity = similarity;
        }
        final usedFromGuide = selectedByGuide[candidate.guide.id] ?? 0;
        final diversity = selected.isEmpty ? 1.0 : 1.0 - maxSimilarity;
        final score = diversity + (0.22 / (usedFromGuide + 1));
        if (score > bestScore) {
          bestScore = score;
          best = candidate;
        }
      }
      if (best == null) break;
      selected.add(best);
      selectedByGuide[best.guide.id] = (selectedByGuide[best.guide.id] ?? 0) + 1;
    }

    selected.sort((a, b) {
      final guideCmp = a.guide.title.compareTo(b.guide.title);
      return guideCmp != 0 ? guideCmp : a.order.compareTo(b.order);
    });

    final out = StringBuffer();
    var used = 0;
    for (final item in selected) {
      final header =
          '\n=== ${item.guide.title} [${item.guide.sourceType}] • fragmento ${item.order + 1} ===\n';
      final remaining = maxChars - used - header.length;
      if (remaining <= 160) break;
      final body = item.text.length > remaining
          ? item.text.substring(0, remaining)
          : item.text;
      out.write(header);
      out.write(body);
      used += header.length + body.length;
      if (used >= maxChars) break;
    }
    return out.toString().trim();
  }

  static String _fallbackCoverage(
    List<StudyGuide> guides, {
    required int maxChars,
    required int maxChunks,
  }) {
    final all = <({StudyGuide guide, String text, int order})>[];
    for (final guide in guides) {
      final chunks = _chunk(guide.text);
      for (var i = 0; i < chunks.length; i++) {
        all.add((guide: guide, text: chunks[i], order: i));
      }
    }
    if (all.isEmpty) return '';

    final selected = <({StudyGuide guide, String text, int order})>[];
    final perGuide = math.max(1, (maxChunks / guides.length).ceil());
    for (final guide in guides) {
      final group = all.where((c) => c.guide.id == guide.id).toList();
      if (group.isEmpty) continue;
      final take = math.min(perGuide, group.length);
      if (take == 1) {
        selected.add(group[group.length ~/ 2]);
      } else {
        for (var i = 0; i < take; i++) {
          final index = ((group.length - 1) * i / (take - 1)).round();
          selected.add(group[index]);
        }
      }
    }
    if (selected.length > maxChunks) {
      selected.removeRange(maxChunks, selected.length);
    }

    final out = StringBuffer();
    var used = 0;
    for (final item in selected) {
      final header =
          '\n=== ${item.guide.title} [${item.guide.sourceType}] • fragmento ${item.order + 1} ===\n';
      final remaining = maxChars - used - header.length;
      if (remaining <= 160) break;
      final body = item.text.length > remaining
          ? item.text.substring(0, remaining)
          : item.text;
      out.write(header);
      out.write(body);
      used += header.length + body.length;
      if (used >= maxChars) break;
    }
    return out.toString().trim();
  }

"""
if 'static Future<String> buildCoverageContext(' not in s:
    anchor = "  static List<String> _chunk(String source) {\n"
    if anchor not in s:
        raise SystemExit('v168 vector coverage anchor missing')
    s = s.replace(anchor, coverage + anchor, 1)

if 'class _CoverageChunk {' not in s:
    s += r"""

class _CoverageChunk {
  const _CoverageChunk({
    required this.guide,
    required this.text,
    required this.vector,
    required this.order,
  });

  final StudyGuide guide;
  final String text;
  final List<double> vector;
  final int order;
}
"""
p.write_text(s)

# AI flashcards use diverse vector coverage.
p = Path('lib/ai_card_service.dart')
s = p.read_text()
if "import 'vector_knowledge_store.dart';" not in s:
    s = s.replace("import 'models.dart';\n", "import 'models.dart';\nimport 'vector_knowledge_store.dart';\n", 1)
old_material = r"    final material = guide.text.replaceAll('\\r', '').trim();" + "\n"
new_material = """    final material = (await VectorKnowledgeStore.buildCoverageContext(
      [guide],
      maxChars: guide.text.length.clamp(12000, 90000).toInt(),
      maxChunks: 72,
    )).trim();
"""
if old_material in s:
    s = s.replace(old_material, new_material, 1)
elif 'await VectorKnowledgeStore.buildCoverageContext(' not in s:
    raise SystemExit('v168 AI card material anchor missing')
p.write_text(s)

# AI exams use vector coverage across the tutor's assigned guides.
p = Path('lib/daily_exam_page.dart')
s = p.read_text()
if "import 'vector_knowledge_store.dart';" not in s:
    s = s.replace("import 'tutor_context_service.dart';\n", "import 'tutor_context_service.dart';\nimport 'vector_knowledge_store.dart';\n", 1)
if 'TutorContextService.contentForGuides(' in s:
    s = s.replace(
        'TutorContextService.contentForGuides(',
        'await VectorKnowledgeStore.buildCoverageContext(',
    )
s = s.replace(
    "var generatorLabel = 'Instant • indexed content';",
    "var generatorLabel = 'Instant • vector-backed card bank';",
)
p.write_text(s)

# Study plans see semantic coverage from the selected tutor library.
p = Path('lib/study_plan_page.dart')
s = p.read_text()
if "import 'vector_knowledge_store.dart';" not in s:
    if "import 'tutor_context_service.dart';\n" in s:
        s = s.replace(
            "import 'tutor_context_service.dart';\n",
            "import 'tutor_context_service.dart';\nimport 'vector_knowledge_store.dart';\n",
            1,
        )
    else:
        pos = s.find('\n', s.find('import '))
        s = s[:pos + 1] + "import 'vector_knowledge_store.dart';\n" + s[pos + 1:]
if 'TutorContextService.contentForGuides(' in s:
    s = s.replace(
        'TutorContextService.contentForGuides(',
        'await VectorKnowledgeStore.buildCoverageContext(',
    )
p.write_text(s)

# Manual parser-card regeneration also reads the vector corpus.
p = Path('lib/guide_detail_page.dart')
s = p.read_text()
if "import 'vector_knowledge_store.dart';" not in s:
    s = s.replace("import 'study_engine.dart';\n", "import 'study_engine.dart';\nimport 'vector_knowledge_store.dart';\n", 1)
old = "    final regenerated = StudyEngine.buildCards(widget.guide.text);\n"
new = """    final vectorMaterial = await VectorKnowledgeStore.buildCoverageContext(
      [widget.guide],
      maxChars: widget.guide.text.length.clamp(12000, 70000).toInt(),
      maxChunks: 64,
    );
    final regenerated = StudyEngine.buildCards(vectorMaterial);
"""
if old in s:
    s = s.replace(old, new, 1)
p.write_text(s)

# Empty legacy card banks are rebuilt from vector coverage during load.
p = Path('lib/guide_store.dart')
s = p.read_text()
old = """        if (guide.cards.isEmpty && guide.text.trim().isNotEmpty) {
          guide.cards = StudyEngine.buildCards(guide.text);
          repaired = true;
        }
"""
new = """        if (guide.cards.isEmpty && guide.text.trim().isNotEmpty) {
          final material = await VectorKnowledgeStore.buildCoverageContext(
            [guide],
            maxChars: guide.text.length.clamp(12000, 70000).toInt(),
            maxChunks: 64,
          );
          guide.cards = StudyEngine.buildCards(material);
          repaired = true;
        }
"""
if old in s:
    s = s.replace(old, new, 1)
p.write_text(s)

print('v168 applied: vector corpus now feeds exams, cards, study plans and review card banks')
