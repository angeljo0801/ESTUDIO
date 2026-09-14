import 'package:flutter/material.dart';

import 'guide_detail_page.dart';
import 'guide_importer.dart';
import 'guide_store.dart';
import 'study_engine.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key, required this.store});

  final GuideStore store;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  bool _busy = false;

  Future<void> _importFile() async {
    setState(() => _busy = true);
    try {
      final guide = await GuideImporter.pickAndBuild();
      if (guide == null) return;
      await widget.store.add(guide);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Listo: ${guide.cards.length} repasos creados.')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No pude importar la guía: $e')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pasteText() async {
    final titleController = TextEditingController();
    final textController = TextEditingController();
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Pegar una guía'),
        content: SizedBox(
          width: 520,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: titleController,
                decoration: const InputDecoration(labelText: 'Título'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: textController,
                minLines: 8,
                maxLines: 15,
                decoration: const InputDecoration(
                  labelText: 'Contenido de la guía',
                  alignLabelWithHint: true,
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Crear')),
        ],
      ),
    );
    if (result == true && textController.text.trim().length >= 40) {
      final guide = StudyEngine.buildGuide(
        title: titleController.text.trim().isEmpty ? 'Guía pegada' : titleController.text.trim(),
        sourceType: 'texto',
        sourceName: 'Texto pegado',
        text: textController.text,
      );
      await widget.store.add(guide);
    }
    titleController.dispose();
    textController.dispose();
  }

  Future<void> _showAddMenu() async {
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 22),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(Icons.upload_file_rounded),
                title: const Text('Importar archivo'),
                subtitle: const Text('PDF, DOCX, TXT o Markdown'),
                onTap: () {
                  Navigator.pop(context);
                  _importFile();
                },
              ),
              ListTile(
                leading: const Icon(Icons.content_paste_go_rounded),
                title: const Text('Pegar texto'),
                subtitle: const Text('Copia una guía desde cualquier app'),
                onTap: () {
                  Navigator.pop(context);
                  _pasteText();
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.store,
      builder: (context, _) {
        final guides = widget.store.guides;
        return Scaffold(
          appBar: AppBar(
            title: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Memora', style: TextStyle(fontWeight: FontWeight.w800)),
                Text('Tu biblioteca que te repasa', style: TextStyle(fontSize: 12)),
              ],
            ),
          ),
          floatingActionButton: FloatingActionButton.extended(
            onPressed: _busy ? null : _showAddMenu,
            icon: _busy
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.add_rounded),
            label: Text(_busy ? 'Procesando…' : 'Añadir guía'),
          ),
          body: guides.isEmpty
              ? _EmptyLibrary(onAdd: _showAddMenu)
              : ListView(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 110),
                  children: [
                    _LibraryHeader(total: guides.length),
                    const SizedBox(height: 14),
                    for (final guide in guides)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: Card(
                          child: InkWell(
                            borderRadius: BorderRadius.circular(22),
                            onTap: () async {
                              await Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => GuideDetailPage(store: widget.store, guide: guide),
                                ),
                              );
                            },
                            child: Padding(
                              padding: const EdgeInsets.all(18),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Container(
                                        width: 46,
                                        height: 46,
                                        decoration: BoxDecoration(
                                          color: Theme.of(context).colorScheme.primaryContainer,
                                          borderRadius: BorderRadius.circular(15),
                                        ),
                                        child: const Icon(Icons.menu_book_rounded),
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              guide.title,
                                              maxLines: 2,
                                              overflow: TextOverflow.ellipsis,
                                              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
                                            ),
                                            Text('${guide.sourceType.toUpperCase()} • ${guide.cards.length} tarjetas'),
                                          ],
                                        ),
                                      ),
                                      const Icon(Icons.chevron_right_rounded),
                                    ],
                                  ),
                                  const SizedBox(height: 14),
                                  Row(
                                    children: [
                                      _Pill(icon: Icons.schedule_rounded, text: '${guide.dueCount} por repasar'),
                                      const SizedBox(width: 8),
                                      _Pill(icon: Icons.school_rounded, text: '${guide.masteredCount} dominadas'),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
        );
      },
    );
  }
}

class _LibraryHeader extends StatelessWidget {
  const _LibraryHeader({required this.total});
  final int total;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Theme.of(context).colorScheme.primaryContainer,
              Theme.of(context).colorScheme.secondaryContainer,
            ],
          ),
          borderRadius: BorderRadius.circular(24),
        ),
        child: Row(
          children: [
            const Icon(Icons.auto_awesome_rounded, size: 32),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                '$total ${total == 1 ? 'guía lista' : 'guías listas'} para estudiar sin conexión.',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
              ),
            ),
          ],
        ),
      );
}

class _Pill extends StatelessWidget {
  const _Pill({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(99),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 15),
            const SizedBox(width: 5),
            Text(text, style: const TextStyle(fontSize: 12)),
          ],
        ),
      );
}

class _EmptyLibrary extends StatelessWidget {
  const _EmptyLibrary({required this.onAdd});
  final VoidCallback onAdd;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.library_books_rounded, size: 78),
              const SizedBox(height: 18),
              const Text('Pon una guía y Memora te la repasa', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800), textAlign: TextAlign.center),
              const SizedBox(height: 10),
              const Text(
                'Importa PDF, DOCX, TXT o Markdown. Memora extrae el texto, crea preguntas y guarda el progreso en tu teléfono.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 22),
              FilledButton.icon(onPressed: onAdd, icon: const Icon(Icons.add_rounded), label: const Text('Añadir mi primera guía')),
            ],
          ),
        ),
      );
}
