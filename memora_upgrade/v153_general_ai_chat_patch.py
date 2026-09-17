from pathlib import Path
import os

# Add a general-purpose AI chat that is not grounded in the library unless the
# user explicitly enables library context. It reuses AiService and Fast/Normal/Deep.
chat = r'''import 'package:flutter/material.dart';

import 'ai_service.dart';
import 'guide_store.dart';
import 'knowledge_retriever.dart';

class GeneralAiChatPage extends StatefulWidget {
  const GeneralAiChatPage({super.key, required this.store});
  final GuideStore store;

  @override
  State<GeneralAiChatPage> createState() => _GeneralAiChatPageState();
}

class _GeneralAiChatPageState extends State<GeneralAiChatPage> {
  final input = TextEditingController();
  final messages = <({bool user, String text})>[];
  bool busy = false;
  bool useLibrary = false;
  String responseMode = 'normal';

  @override
  void dispose() {
    input.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final question = input.text.trim();
    if (question.isEmpty || busy) return;
    input.clear();
    setState(() {
      messages.add((user: true, text: question));
      messages.add((user: false, text: 'Thinking…'));
      busy = true;
    });
    final assistantIndex = messages.length - 1;
    try {
      var libraryContext = '';
      if (useLibrary && widget.store.guides.isNotEmpty) {
        libraryContext = KnowledgeRetriever.buildContext(
          guides: widget.store.guides,
          query: question,
          maxChars: responseMode == 'fast' ? 3000 : 7000,
          maxChunks: responseMode == 'fast' ? 3 : 7,
          allowUnmatchedFallback: false,
        );
        if (libraryContext.startsWith('(No matching evidence found')) {
          libraryContext = '';
        }
      }
      final history = messages
          .take(messages.length - 1)
          .toList()
          .reversed
          .take(8)
          .toList()
          .reversed
          .map((m) => '${m.user ? 'User' : 'Assistant'}: ${m.text}')
          .join('\n');
      final result = await AiService.askConfigured(
        providerOverride: 'global',
        responseMode: responseMode,
        onPartial: (partial) {
          if (!mounted || partial.isEmpty) return;
          setState(() => messages[assistantIndex] = (user: false, text: partial));
        },
        prompt: '''You are Memora AI, a general-purpose AI assistant. Answer the user's question normally; it does not need to be related to Memora's study library.

CONVERSATION:
$history

${libraryContext.isEmpty ? '' : 'OPTIONAL LIBRARY CONTEXT:\n$libraryContext\n'}
USER QUESTION:
$question

If optional library context is supplied, use it only when relevant. Otherwise answer from your normal capabilities. Do not pretend the library contains information that is not present.''',
      );
      if (mounted) setState(() => messages[assistantIndex] = (user: false, text: result));
    } catch (e) {
      if (mounted) {
        setState(() => messages[assistantIndex] = (
              user: false,
              text: 'No pude responder: ${AiService.userFacingError(e)}',
            ));
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Chat IA')),
        body: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
              child: Row(
                children: [
                  Expanded(
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
                ],
              ),
            ),
            SwitchListTile(
              dense: true,
              title: const Text('Usar biblioteca'),
              subtitle: Text(useLibrary
                  ? 'Puede consultar tus guías cuando sean relevantes.'
                  : 'Chat general sin depender de tus guías.'),
              value: useLibrary,
              onChanged: busy ? null : (v) => setState(() => useLibrary = v),
            ),
            const Divider(height: 1),
            Expanded(
              child: messages.isEmpty
                  ? const Center(
                      child: Padding(
                        padding: EdgeInsets.all(28),
                        child: Text(
                          'Pregunta cualquier cosa. No tiene que estar relacionada con tu biblioteca.',
                          textAlign: TextAlign.center,
                        ),
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.all(12),
                      itemCount: messages.length,
                      itemBuilder: (context, index) {
                        final m = messages[index];
                        return Align(
                          alignment: m.user ? Alignment.centerRight : Alignment.centerLeft,
                          child: Card(
                            child: Padding(
                              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                              child: Text(m.text),
                            ),
                          ),
                        );
                      },
                    ),
            ),
            SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Expanded(
                      child: TextField(
                        controller: input,
                        minLines: 1,
                        maxLines: 5,
                        textInputAction: TextInputAction.newline,
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
Path('lib/general_ai_chat_page.dart').write_text(chat)

p=Path('lib/app_shell.dart'); s=p.read_text()
if "import 'general_ai_chat_page.dart';" not in s:
    s=s.replace("import 'guide_store.dart';\n", "import 'guide_store.dart';\nimport 'general_ai_chat_page.dart';\n",1)
if 'GeneralAiChatPage(store: widget.store),' not in s:
    s=s.replace('            AgentPage(store: widget.store),\n', '            AgentPage(store: widget.store),\n            GeneralAiChatPage(store: widget.store),\n',1)
if "label: 'Chat IA'" not in s:
    s=s.replace("            NavigationDestination(icon: Icon(Icons.smart_toy_outlined), label: 'Agentes'),\n", "            NavigationDestination(icon: Icon(Icons.smart_toy_outlined), label: 'Agentes'),\n            NavigationDestination(icon: Icon(Icons.chat_bubble_outline), label: 'Chat IA'),\n",1)
p.write_text(s)
print('General AI chat added')
