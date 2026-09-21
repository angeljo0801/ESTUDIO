from pathlib import Path

# Memora v188: editable library content and explicit embedding replacement.

p = Path('lib/vector_knowledge_store.dart')
s = p.read_text()

if 'class GuideVectorIndexInfo {' not in s:
    marker = 'class VectorKnowledgeStore {\n'
    if marker not in s:
        raise SystemExit('v188 vector class anchor missing')
    block = r'''class GuideVectorIndexInfo {
  const GuideVectorIndexInfo({
    required this.modelReady,
    required this.hasIndex,
    required this.isCurrent,
    required this.chunkCount,
  });

  final bool modelReady;
  final bool hasIndex;
  final bool isCurrent;
  final int chunkCount;
}

'''
    s = s.replace(marker, block + marker, 1)

if 'static Future<GuideVectorIndexInfo> indexInfo(' not in s:
    anchor = '  static List<String> _chunk(String source) {\n'
    if anchor not in s:
        raise SystemExit('v188 vector chunk anchor missing')
    block = r'''  static Future<GuideVectorIndexInfo> indexInfo(StudyGuide guide) async {
    final ready = await EmbeddingService.isReady();
    final file = await _fileFor(guide.id);
    if (!await file.exists()) {
      return GuideVectorIndexInfo(
        modelReady: ready,
        hasIndex: false,
        isCurrent: false,
        chunkCount: 0,
      );
    }
    try {
      final data = jsonDecode(await file.readAsString()) as Map<String, dynamic>;
      final count = data['chunks'] is List
          ? (data['chunks'] as List<dynamic>).length
          : 0;
      return GuideVectorIndexInfo(
        modelReady: ready,
        hasIndex: count > 0,
        isCurrent: count > 0 &&
            data['fingerprint'] == _fingerprint(guide) &&
            data['modelId'] == EmbeddingService.modelId,
        chunkCount: count,
      );
    } catch (_) {
      return GuideVectorIndexInfo(
        modelReady: ready,
        hasIndex: false,
        isCurrent: false,
        chunkCount: 0,
      );
    }
  }

  static Future<int> rebuildGuide(
    StudyGuide guide, {
    void Function(int done, int total)? onProgress,
  }) async {
    if (!await EmbeddingService.isReady()) {
      throw StateError(
        'The embedding model is not installed. Download it in AI Settings first.',
      );
    }
    // Explicit rebuild always removes the previous automatic/manual index first.
    await deleteGuide(guide.id);
    return ensureIndexed(guide, onProgress: onProgress);
  }

'''
    s = s.replace(anchor, block + anchor, 1)

p.write_text(s)

p = Path('lib/guide_detail_page.dart')
s = p.read_text()

if "import 'embedding_service.dart';" not in s:
    anchor = "import 'guide_file_service.dart';\n"
    if anchor not in s:
        raise SystemExit('v188 embedding import anchor missing')
    s = s.replace(anchor, "import 'embedding_service.dart';\n" + anchor, 1)

if "import 'vector_knowledge_store.dart';" not in s:
    anchor = "import 'study_engine.dart';\n"
    if anchor not in s:
        raise SystemExit('v188 vector import anchor missing')
    s = s.replace(anchor, anchor + "import 'vector_knowledge_store.dart';\n", 1)

state_anchor = 'class _GuideDetailPageState extends State<GuideDetailPage> {\n'
if 'GuideVectorIndexInfo? _embeddingInfo;' not in s:
    if state_anchor not in s:
        raise SystemExit('v188 detail state anchor missing')
    block = r'''class _GuideDetailPageState extends State<GuideDetailPage> {
  GuideVectorIndexInfo? _embeddingInfo;
  bool _embeddingBusy = false;
  int _embeddingDone = 0;
  int _embeddingTotal = 0;

  @override
  void initState() {
    super.initState();
    _refreshEmbeddingInfo();
  }

  Future<void> _refreshEmbeddingInfo() async {
    final info = await VectorKnowledgeStore.indexInfo(widget.guide);
    if (mounted) setState(() => _embeddingInfo = info);
  }

'''
    s = s.replace(state_anchor, block, 1)

if 'Future<void> _editContent() async {' not in s:
    anchor = '  Future<void> _review() async {\n'
    if anchor not in s:
        raise SystemExit('v188 review anchor missing')
    block = r'''  Future<void> _editContent() async {
    final edited = await Navigator.of(context).push<String>(
      MaterialPageRoute(
        builder: (_) => _GuideTextEditorPage(
          title: widget.guide.title,
          initialText: widget.guide.text,
        ),
      ),
    );
    if (edited == null) return;

    final normalized = edited.replaceAll('\r\n', '\n').trim();
    if (normalized.isEmpty || normalized == widget.guide.text.trim()) return;

    widget.guide.text = normalized;
    widget.guide.summary = StudyEngine.buildSummary(normalized);
    // Original PDF/text provenance no longer maps exactly after a manual edit.
    widget.guide.sourceBlocks = const [];
    widget.guide.extractionVersion += 1;
    await widget.store.update(widget.guide);
    await _refreshEmbeddingInfo();

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'Content saved. Embeddings are now marked outdated until rebuilt.',
        ),
      ),
    );
  }

  Future<void> _regenerateEmbeddings() async {
    if (_embeddingBusy) return;
    if (!await EmbeddingService.isReady()) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Install the embedding model from AI Settings before creating embeddings.',
          ),
        ),
      );
      await _refreshEmbeddingInfo();
      return;
    }

    setState(() {
      _embeddingBusy = true;
      _embeddingDone = 0;
      _embeddingTotal = 0;
    });

    try {
      final count = await VectorKnowledgeStore.rebuildGuide(
        widget.guide,
        onProgress: (done, total) {
          if (!mounted) return;
          setState(() {
            _embeddingDone = done;
            _embeddingTotal = total;
          });
        },
      );
      await _refreshEmbeddingInfo();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Embeddings rebuilt from the current content ($count chunks). The old index was replaced.',
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not rebuild embeddings: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _embeddingBusy = false;
          _embeddingDone = 0;
          _embeddingTotal = 0;
        });
      }
    }
  }

'''
    s = s.replace(anchor, block + anchor, 1)

show_start = s.find('  void _showText() {')
if show_start < 0:
    show_start = s.find('  Future<void> _showText() async {')
build_anchor = s.find('\n  @override\n  Widget build(BuildContext context)', show_start)
if show_start < 0 or build_anchor < 0:
    raise SystemExit('v188 content viewer anchors missing')

viewer = r'''  Future<void> _showText() async {
    final action = await Navigator.of(context).push<String>(
      MaterialPageRoute(
        builder: (pageContext) => Scaffold(
          appBar: AppBar(
            title: Text(
              widget.guide.title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            actions: [
              IconButton(
                tooltip: 'Edit content',
                onPressed: () => Navigator.pop(pageContext, 'edit'),
                icon: const Icon(Icons.edit_outlined),
              ),
              IconButton(
                tooltip: 'Create embeddings',
                onPressed: () => Navigator.pop(pageContext, 'embeddings'),
                icon: const Icon(Icons.hub_outlined),
              ),
            ],
          ),
          body: Column(
            children: [
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(18),
                  child: SelectableText(
                    widget.guide.text,
                    style: const TextStyle(height: 1.55),
                  ),
                ),
              ),
              SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
                  child: Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => Navigator.pop(pageContext, 'edit'),
                          icon: const Icon(Icons.edit_outlined),
                          label: const Text('Edit content'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: FilledButton.icon(
                          onPressed: () =>
                              Navigator.pop(pageContext, 'embeddings'),
                          icon: const Icon(Icons.hub_outlined),
                          label: const Text('Create embeddings'),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );

    if (!mounted) return;
    if (action == 'edit') {
      await _editContent();
    } else if (action == 'embeddings') {
      await _regenerateEmbeddings();
    }
  }
'''
s = s[:show_start] + viewer + s[build_anchor:]

if "if (value == 'edit') _editContent();" not in s:
    anchor = "              if (value == 'delete') _delete();\n"
    if anchor not in s:
        raise SystemExit('v188 popup selection anchor missing')
    s = s.replace(
        anchor,
        "              if (value == 'edit') _editContent();\n"
        "              if (value == 'embeddings') _regenerateEmbeddings();\n"
        + anchor,
        1,
    )

if "value: 'embeddings'" not in s:
    marker = "              const PopupMenuItem(value: 'delete'"
    pos = s.find(marker)
    if pos < 0:
        raise SystemExit('v188 popup item anchor missing')
    menu = r'''              const PopupMenuItem(
                value: 'edit',
                child: Text('Edit library content'),
              ),
              const PopupMenuItem(
                value: 'embeddings',
                child: Text('Create / rebuild embeddings'),
              ),
'''
    s = s[:pos] + menu + s[pos:]

if "'Embedding index'" not in s:
    body_pos = s.find('      body: ListView(')
    if body_pos < 0:
        raise SystemExit('v188 ListView body anchor missing')
    children_marker = '        children: [\n'
    children_pos = s.find(children_marker, body_pos)
    if children_pos < 0:
        raise SystemExit('v188 ListView children anchor missing')
    insert_pos = children_pos + len(children_marker)
    card = r'''          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Builder(
                builder: (context) {
                  final info = _embeddingInfo;
                  final ready = info?.modelReady ?? false;
                  final current = info?.isCurrent ?? false;
                  final oldIndex = info?.hasIndex ?? false;
                  final status = info == null
                      ? 'Checking embedding index…'
                      : !ready
                          ? 'Embedding model not installed'
                          : current
                              ? 'Embeddings up to date • ${info.chunkCount} chunks'
                              : oldIndex
                                  ? 'Content changed • rebuild embeddings'
                                  : 'No embeddings created yet';
                  final progress = _embeddingBusy && _embeddingTotal > 0
                      ? _embeddingDone / _embeddingTotal
                      : null;

                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(current
                              ? Icons.check_circle_outline
                              : Icons.hub_outlined),
                          const SizedBox(width: 10),
                          const Expanded(
                            child: Text(
                              'Embedding index',
                              style: TextStyle(
                                fontWeight: FontWeight.w800,
                                fontSize: 17,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(status),
                      if (_embeddingBusy) ...[
                        const SizedBox(height: 10),
                        LinearProgressIndicator(value: progress),
                        const SizedBox(height: 6),
                        Text(_embeddingTotal > 0
                            ? '$_embeddingDone / $_embeddingTotal chunks'
                            : 'Preparing index…'),
                      ],
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: _embeddingBusy ? null : _editContent,
                              icon: const Icon(Icons.edit_outlined),
                              label: const Text('Edit content'),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: FilledButton.icon(
                              onPressed: _embeddingBusy || !ready
                                  ? null
                                  : _regenerateEmbeddings,
                              icon: const Icon(Icons.hub_outlined),
                              label: Text(current
                                  ? 'Rebuild embeddings'
                                  : 'Create embeddings'),
                            ),
                          ),
                        ],
                      ),
                      if (!ready) ...[
                        const SizedBox(height: 8),
                        const Text(
                          'Download the embedding model in AI Settings to enable this button.',
                          style: TextStyle(fontSize: 12),
                        ),
                      ],
                    ],
                  );
                },
              ),
            ),
          ),
          const SizedBox(height: 12),
'''
    s = s[:insert_pos] + card + s[insert_pos:]

if 'class _GuideTextEditorPage extends StatefulWidget' not in s:
    pos = s.find('\nclass _StatCard extends StatelessWidget')
    if pos < 0:
        raise SystemExit('v188 editor insert anchor missing')
    editor = r'''
class _GuideTextEditorPage extends StatefulWidget {
  const _GuideTextEditorPage({
    required this.title,
    required this.initialText,
  });

  final String title;
  final String initialText;

  @override
  State<_GuideTextEditorPage> createState() => _GuideTextEditorPageState();
}

class _GuideTextEditorPageState extends State<_GuideTextEditorPage> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.initialText);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _save() {
    final value = _controller.text.trim();
    if (value.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('The library content cannot be empty.')),
      );
      return;
    }
    Navigator.pop(context, value);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: Text(
            'Edit ${widget.title}',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          actions: [
            TextButton(onPressed: _save, child: const Text('Save')),
          ],
        ),
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: TextField(
              controller: _controller,
              expands: true,
              minLines: null,
              maxLines: null,
              textAlignVertical: TextAlignVertical.top,
              keyboardType: TextInputType.multiline,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                labelText: 'Library content',
                helperText:
                    'This is the content Memora uses for search, tutors, agents, cards and embeddings.',
              ),
            ),
          ),
        ),
      );
}

'''
    s = s[:pos] + editor + s[pos:]

p.write_text(s)
print('v188 applied: editable library content + replaceable embeddings')
