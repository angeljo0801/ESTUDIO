from pathlib import Path
import re
import subprocess

# v155: compile fixes after v154.

# Library already has an Add/Create FAB that opens the creator menu. Remove the
# extra v154 FAB instead of defining floatingActionButton twice.
p = Path('lib/home_page.dart')
h = p.read_text()
extra = "floatingActionButton: FloatingActionButton(tooltip: 'Crear guía', onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GuideCreatorPage(store: widget.store))), child: const Icon(Icons.auto_awesome)),\n        "
h = h.replace(extra, '', 1)
p.write_text(h)

# Replace the compressed Chat IA build method with a structurally clear version.
p = Path('lib/general_ai_chat_page.dart')
g = p.read_text()
start = g.find(' @override Widget build(BuildContext context)')
if start < 0:
    raise SystemExit('Chat IA build method not found')
end = g.rfind('\n}')
if end < start:
    raise SystemExit('Chat IA class end not found')
new_build = r''' @override
 Widget build(BuildContext context) {
   final ms = active?.messages ?? const <ChatMessage>[];
   return Scaffold(
     appBar: AppBar(
       title: const Text('Chat IA'),
       actions: [
         IconButton(tooltip: 'Nuevo chat', onPressed: busy ? null : _newChat, icon: const Icon(Icons.add_comment_outlined)),
         IconButton(tooltip: 'Historial', onPressed: busy ? null : _history, icon: const Icon(Icons.history)),
         IconButton(tooltip: 'Exportar PDF', onPressed: active == null ? null : () => _export(active!), icon: const Icon(Icons.picture_as_pdf_outlined)),
         IconButton(tooltip: 'AI Settings', onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const LlmSettingsPage())), icon: const Icon(Icons.settings_outlined)),
       ],
     ),
     body: Column(
       children: [
         Padding(
           padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
           child: SegmentedButton<String>(
             segments: const [
               ButtonSegment(value: 'fast', label: Text('Fast')),
               ButtonSegment(value: 'normal', label: Text('Normal')),
               ButtonSegment(value: 'deep', label: Text('Deep')),
             ],
             selected: {responseMode},
             onSelectionChanged: busy ? null : (v) => setState(() => responseMode = v.first),
           ),
         ),
         SwitchListTile(
           dense: true,
           title: const Text('Usar biblioteca'),
           subtitle: Text(useLibrary ? 'Puede consultar tus guías cuando sean relevantes.' : 'Chat general sin depender de tus guías.'),
           value: useLibrary,
           onChanged: busy ? null : (v) => setState(() => useLibrary = v),
         ),
         const Divider(height: 1),
         Expanded(
           child: ms.isEmpty
               ? const Center(child: Text('Pregunta cualquier cosa.'))
               : ListView.builder(
                   padding: const EdgeInsets.all(12),
                   itemCount: ms.length,
                   itemBuilder: (c, i) {
                     final m = ms[i];
                     return Align(
                       alignment: m.role == 'user' ? Alignment.centerRight : Alignment.centerLeft,
                       child: Card(child: Padding(padding: const EdgeInsets.all(12), child: Text(m.text))),
                     );
                   },
                 ),
         ),
         SafeArea(
           top: false,
           child: Padding(
             padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
             child: Row(
               children: [
                 Expanded(
                   child: TextField(
                     controller: input,
                     minLines: 1,
                     maxLines: 5,
                     decoration: const InputDecoration(hintText: 'Pregúntale cualquier cosa…'),
                   ),
                 ),
                 const SizedBox(width: 8),
                 busy
                     ? IconButton(onPressed: AiService.cancelCurrent, icon: const Icon(Icons.stop_circle_outlined))
                     : IconButton(onPressed: _send, icon: const Icon(Icons.send_rounded)),
               ],
             ),
           ),
         ),
       ],
     ),
   );
 }
'''
g = g[:start] + new_build + g[end:]
p.write_text(g)

subprocess.run(['python3', 'v156_chat_history_compile_fix.py'], check=True)
print('v155 applied: Chat IA syntax and Library FAB conflict fixed')
