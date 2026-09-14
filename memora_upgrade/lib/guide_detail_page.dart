import 'package:flutter/material.dart';

import 'guide_store.dart';
import 'models.dart';
import 'quiz_page.dart';
import 'review_page.dart';
import 'study_engine.dart';

class GuideDetailPage extends StatefulWidget {
  const GuideDetailPage({super.key, required this.store, required this.guide});

  final GuideStore store;
  final StudyGuide guide;

  @override
  State<GuideDetailPage> createState() => _GuideDetailPageState();
}

class _GuideDetailPageState extends State<GuideDetailPage> {
  Future<void> _save() async {
    await widget.store.update(widget.guide);
    if (mounted) setState(() {});
  }

  Future<void> _review() async {
    if (widget.guide.cards.isEmpty) return;
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ReviewPage(
          guide: widget.guide,
          onSave: _save,
        ),
      ),
    );
    if (mounted) setState(() {});
  }

  Future<void> _quiz() async {
    if (widget.guide.cards.length < 2) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Necesito al menos 2 tarjetas para crear un examen.')),
      );
      return;
    }
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => QuizPage(guide: widget.guide, onSave: _save),
      ),
    );
    if (mounted) setState(() {});
  }

  Future<void> _regenerate() async {
    final regenerated = StudyEngine.buildCards(widget.guide.text);
    setState(() => widget.guide.cards = regenerated);
    await _save();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('${regenerated.length} tarjetas regeneradas.')),
    );
  }

  Future<void> _delete() async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Eliminar guía'),
        content: Text('¿Eliminar “${widget.guide.title}” y su progreso?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Eliminar')),
        ],
      ),
    );
    if (yes != true) return;
    await widget.store.remove(widget.guide.id);
    if (mounted) Navigator.pop(context);
  }

  void _showText() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => Scaffold(
          appBar: AppBar(title: Text(widget.guide.title)),
          body: SingleChildScrollView(
            padding: const EdgeInsets.all(18),
            child: SelectableText(widget.guide.text, style: const TextStyle(height: 1.55)),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final guide = widget.guide;
    final accuracy = (guide.accuracy * 100).round();
    return Scaffold(
      appBar: AppBar(
        title: Text(guide.title, maxLines: 1, overflow: TextOverflow.ellipsis),
        actions: [
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'text') _showText();
              if (value == 'regen') _regenerate();
              if (value == 'delete') _delete();
            },
            itemBuilder: (context) => const [
              PopupMenuItem(value: 'text', child: Text('Ver texto original')),
              PopupMenuItem(value: 'regen', child: Text('Regenerar preguntas')),
              PopupMenuItem(value: 'delete', child: Text('Eliminar guía')),
            ],
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(guide.sourceName, style: Theme.of(context).textTheme.bodySmall),
                      ),
                      Chip(label: Text(guide.sourceType.toUpperCase())),
                    ],
                  ),
                  const SizedBox(height: 8),
                  const Text('Resumen automático', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18)),
                  const SizedBox(height: 10),
                  Text(guide.summary, style: const TextStyle(height: 1.45)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: _StatCard(value: '${guide.cards.length}', label: 'Tarjetas', icon: Icons.style_rounded)),
              const SizedBox(width: 10),
              Expanded(child: _StatCard(value: '${guide.dueCount}', label: 'Pendientes', icon: Icons.schedule_rounded)),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(child: _StatCard(value: '${guide.masteredCount}', label: 'Dominadas', icon: Icons.school_rounded)),
              const SizedBox(width: 10),
              Expanded(child: _StatCard(value: '$accuracy%', label: 'Precisión', icon: Icons.track_changes_rounded)),
            ],
          ),
          const SizedBox(height: 18),
          FilledButton.icon(
            onPressed: guide.cards.isEmpty ? null : _review,
            icon: const Icon(Icons.psychology_alt_rounded),
            label: Text(guide.dueCount > 0 ? 'Repasar ${guide.dueCount} ahora' : 'Repaso libre'),
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(54)),
          ),
          const SizedBox(height: 10),
          OutlinedButton.icon(
            onPressed: guide.cards.length < 2 ? null : _quiz,
            icon: const Icon(Icons.quiz_rounded),
            label: const Text('Hacer examen'),
            style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(54)),
          ),
          const SizedBox(height: 20),
          const Text('Cómo funciona el repaso', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18)),
          const SizedBox(height: 8),
          const Text(
            'Memora vuelve a mostrar antes lo que fallas y separa por más días lo que ya dominas. Todo el progreso se guarda en el teléfono y puedes seguir estudiando sin conexión.',
            style: TextStyle(height: 1.45),
          ),
        ],
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({required this.value, required this.label, required this.icon});

  final String value;
  final String label;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, size: 22),
              const SizedBox(height: 10),
              Text(value, style: const TextStyle(fontSize: 25, fontWeight: FontWeight.w900)),
              Text(label),
            ],
          ),
        ),
      );
}
