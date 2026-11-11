"""v0.2.2: scrollable note editor with a fixed, single-row toolbar."""
from pathlib import Path

base = Path('notas_cientificas_v2')
main = base / 'lib' / 'main.dart'
s = main.read_text(encoding='utf-8')
anchor = '  Timer? _autoSave;'
assert anchor in s and 'ScrollController _noteScrollController' not in s
s = s.replace(anchor, anchor + '\n  final ScrollController _noteScrollController = ScrollController();', 1)
anchor = '    title.dispose();\n    editor.dispose();'
assert anchor in s
s = s.replace(anchor, '    title.dispose();\n    _noteScrollController.dispose();\n    editor.dispose();', 1)
start = s.index('  @override\n  Widget build(BuildContext context) {\n    return PopScope(', s.index('class _NoteEditorPageState'))
end = s.index('\nclass CalculatorPage extends StatefulWidget', start)
new_build = '''  @override
  Widget build(BuildContext context) {
    final keyboardOpen = MediaQuery.viewInsetsOf(context).bottom > 0;
    final colors = Theme.of(context).colorScheme;
    return PopScope(
      canPop: _canLeave,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _saveAndClose();
      },
      child: Scaffold(
        resizeToAvoidBottomInset: true,
        appBar: AppBar(
          titleSpacing: 0,
          leading: IconButton(
            tooltip: 'Volver y guardar',
            icon: const Icon(Icons.arrow_back),
            onPressed: _saveAndClose,
          ),
          title: TextField(
            key: const Key('note-title-field'),
            controller: title,
            maxLines: 1,
            textCapitalization: TextCapitalization.sentences,
            textInputAction: TextInputAction.next,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.w600,
            ),
            decoration: const InputDecoration(
              hintText: 'Título',
              isDense: true,
              border: InputBorder.none,
              contentPadding: EdgeInsets.zero,
            ),
          ),
          actions: [
            IconButton(
              tooltip: 'Carpeta y etiquetas',
              onPressed: _editMeta,
              icon: const Icon(Icons.folder_open_outlined),
            ),
            IconButton(
              tooltip: 'Fijar nota',
              onPressed: () {
                setState(() => pinned = !pinned);
                _scheduleSave();
              },
              icon: Icon(pinned ? Icons.push_pin : Icons.push_pin_outlined),
            ),
            if (!trashed)
              IconButton(
                tooltip: 'Mover a papelera',
                icon: const Icon(Icons.delete_outline),
                onPressed: _delete,
              ),
            IconButton(
              tooltip: 'Guardar nota',
              icon: const Icon(Icons.check_rounded),
              onPressed: _saveAndClose,
            ),
          ],
        ),
        // The rich-text toolbar is outside the editor's vertical layout.
        body: SafeArea(
          top: false,
          bottom: false,
          child: Column(
            children: [
              if (!keyboardOpen)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 3, 16, 5),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      '${_date(createdAt)}  •  ${folder.isEmpty ? 'Sin carpeta' : folder}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: colors.onSurfaceVariant,
                      ),
                    ),
                  ),
                ),
              if (!keyboardOpen && (pdfPath != null || inkData != null))
                SizedBox(
                  height: 42,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    children: [
                      if (pdfPath != null)
                        TextButton.icon(
                          onPressed: () => Navigator.push(
                            context,
                            MaterialPageRoute<void>(
                              builder: (_) => AttachedPdfPage(path: pdfPath!),
                            ),
                          ),
                          icon: const Icon(Icons.picture_as_pdf_outlined),
                          label: const Text('PDF original'),
                        ),
                      if (inkData != null)
                        TextButton.icon(
                          onPressed: _openInk,
                          icon: const Icon(Icons.draw_outlined),
                          label: const Text('Editar dibujo S Pen'),
                        ),
                    ],
                  ),
                ),
              Expanded(
                child: ColoredBox(
                  color: colors.surface,
                  child: quill.QuillEditor.basic(
                    key: const Key('note-body-editor'),
                    controller: editor,
                    scrollController: _noteScrollController,
                    config: const quill.QuillEditorConfig(
                      placeholder: 'Escribe tus apuntes aquí…',
                      scrollable: true,
                      expands: true,
                      padding: EdgeInsets.fromLTRB(18, 16, 18, 32),
                      scrollBottomInset: 24,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        bottomNavigationBar: SafeArea(
          top: false,
          child: Container(
            key: const Key('note-fixed-toolbar'),
            height: 54,
            padding: const EdgeInsets.symmetric(horizontal: 4),
            decoration: BoxDecoration(
              color: colors.surfaceContainer,
              border: Border(top: BorderSide(color: colors.outlineVariant)),
            ),
            child: Row(
              children: [
                IconButton(
                  tooltip: 'Escritura con S Pen',
                  icon: const Icon(Icons.draw_outlined),
                  onPressed: _openInk,
                ),
                IconButton(
                  tooltip: 'Calculadora científica',
                  icon: const Icon(Icons.calculate_outlined),
                  onPressed: _openCalculator,
                ),
                SizedBox(
                  height: 28,
                  child: VerticalDivider(color: colors.outlineVariant, width: 8),
                ),
                Expanded(
                  child: ClipRect(
                    child: quill.QuillSimpleToolbar(
                      controller: editor,
                      config: const quill.QuillSimpleToolbarConfig(
                        multiRowsDisplay: false,
                        showDividers: false,
                        toolbarSize: 42,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
'''
# Remove JS escaping before writing the generated Dart string.
new_build = new_build.replace('\\'+ '$' + '{', '$' + '{')
s = s[:start] + new_build + s[end:]
main.write_text(s, encoding='utf-8')
p = base / 'pubspec.yaml'
v = p.read_text(encoding='utf-8')
assert 'version: 0.2.1+3' in v
p.write_text(v.replace('version: 0.2.1+3', 'version: 0.2.2+4', 1), encoding='utf-8')
print('Editor v0.2.2: toolbar fixed, scrollable, keyboard-aware')
