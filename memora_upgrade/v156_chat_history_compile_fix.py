from pathlib import Path
import subprocess

p = Path('lib/general_ai_chat_page.dart')
s = p.read_text()
start = s.find(' Future<void> _history()')
end = s.find(' Future<void> _send()', start)
if start < 0 or end < 0:
    raise SystemExit('Chat IA history/send markers not found')

history = r''' Future<void> _history() async {
   await showModalBottomSheet<void>(
     context: context,
     isScrollControlled: true,
     builder: (bc) => SafeArea(
       child: SizedBox(
         height: MediaQuery.of(bc).size.height * .72,
         child: Column(
           children: [
             Padding(
               padding: const EdgeInsets.all(12),
               child: Row(
                 children: [
                   const Expanded(
                     child: Text(
                       'Historial de chats',
                       style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                     ),
                   ),
                   IconButton(
                     tooltip: 'Nuevo chat',
                     onPressed: () {
                       Navigator.pop(bc);
                       _newChat();
                     },
                     icon: const Icon(Icons.add_comment_outlined),
                   ),
                 ],
               ),
             ),
             Expanded(
               child: ListView(
                 children: [
                   for (final c in chats)
                     ListTile(
                       leading: Icon(c.id == activeId ? Icons.chat_bubble : Icons.chat_bubble_outline),
                       title: Text(c.title, maxLines: 1, overflow: TextOverflow.ellipsis),
                       subtitle: Text('${c.messages.length} mensaje(s)'),
                       onTap: () {
                         setState(() => activeId = c.id);
                         Navigator.pop(bc);
                       },
                       trailing: Wrap(
                         children: [
                           IconButton(tooltip: 'Exportar PDF', onPressed: () => _export(c), icon: const Icon(Icons.picture_as_pdf_outlined)),
                           IconButton(
                             tooltip: 'Borrar',
                             onPressed: () {
                               Navigator.pop(bc);
                               _delete(c);
                             },
                             icon: const Icon(Icons.delete_outline),
                           ),
                         ],
                       ),
                     ),
                 ],
               ),
             ),
           ],
         ),
       ),
     ),
   );
 }
'''

s = s[:start] + history + s[end:]
p.write_text(s)
subprocess.run(['python3', 'v157_bottom_navigation_fix.py'], check=True)
print('v156 applied: Chat IA history syntax fixed; v157 navigation fix chained')
