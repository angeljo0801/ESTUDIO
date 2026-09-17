from pathlib import Path
import re

ROOT = Path('.')


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f'Pattern not found for {label}')
    return text.replace(old, new, 1)


def replace_regex(text, pattern, replacement, label):
    out, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if n != 1:
        raise RuntimeError(f'Pattern not found for {label}: {n}')
    return out

# Compatibility shim: ChatStore now exposes forOwner with named arguments.
# Keep this early patch compatible without changing the rest of the generated
# chat implementation.
p = ROOT / 'lib' / 'chat_store.dart'
store = p.read_text()
anchor = "  static Future<List<ChatSession>> forOwner({required String ownerType,required String ownerId}) async {final all=await loadAll();final result=all.where((s)=>s.ownerType==ownerType&&s.ownerId==ownerId).toList();result.sort((a,b)=>b.updatedAt.compareTo(a.updatedAt));return result;}\n"
if "static Future<List<ChatSession>> listFor(" not in store:
    if anchor not in store: raise RuntimeError('ChatStore forOwner anchor not found')
    store = store.replace(anchor, anchor + "  static Future<List<ChatSession>> listFor(String ownerType,String ownerId)=>forOwner(ownerType:ownerType,ownerId:ownerId);\n", 1)
p.write_text(store)

# -----------------------------------------------------------------------------
# Tutor chat
# -----------------------------------------------------------------------------
p = ROOT / 'lib' / 'tutor_page.dart'
s = p.read_text()
s = replace_once(
    s,
    "import 'query_extras_bar.dart';\n",
    "import 'query_extras_bar.dart';\nimport 'chat_store.dart';\nimport 'chat_widgets.dart';\n",
    'tutor chat imports',
)
s = replace_once(
    s,
    "  final _extrasKey = GlobalKey<QueryExtrasBarState>();\n",
    "  final _extrasKey = GlobalKey<QueryExtrasBarState>();\n  List<ChatSession> _chatSessions = [];\n  String? _activeChatId;\n  int _turnToken = 0;\n  bool _cancelRequested = false;\n",
    'tutor chat fields',
)
s = replace_once(
    s,
    "    await _saveTutors();\n    if (mounted) {",
    "    await _saveTutors();\n    await _loadChatsForTutor(activeTutorId);\n    if (mounted) {",
    'tutor initial chat load',
)

chat_methods = r'''
  ChatSession? get _activeChat {
    if (_chatSessions.isEmpty) return null;
    return _chatSessions.firstWhere(
      (c) => c.id == _activeChatId,
      orElse: () => _chatSessions.first,
    );
  }

  List<ChatMessage> get _chatMessages => _activeChat?.messages ?? const [];

  Future<void> _loadChatsForTutor(String tutorId) async {
    var sessions = await ChatStore.listFor('tutor', tutorId);
    if (sessions.isEmpty) {
      final created = ChatSession.empty(ownerType: 'tutor', ownerId: tutorId);
      await ChatStore.save(created);
      sessions = [created];
    }
    if (!mounted) return;
    setState(() {
      _chatSessions = sessions;
      _activeChatId = sessions.first.id;
    });
  }

  void _putChat(ChatSession updated) {
    final index = _chatSessions.indexWhere((c) => c.id == updated.id);
    final copy = List<ChatSession>.from(_chatSessions);
    if (index >= 0) {
      copy[index] = updated;
    } else {
      copy.insert(0, updated);
    }
    if (mounted) {
      setState(() {
        _chatSessions = copy;
        _activeChatId = updated.id;
      });
    }
  }

  ChatSession? _chatById(String id) {
    for (final chat in _chatSessions) {
      if (chat.id == id) return chat;
    }
    return null;
  }

  void _updateAssistantBubble(String chatId, String text, int token) {
    if (!mounted || token != _turnToken) return;
    final chat = _chatById(chatId);
    if (chat == null || chat.messages.isEmpty) return;
    final messages = List<ChatMessage>.from(chat.messages);
    if (messages.last.role != 'assistant') return;
    messages[messages.length - 1] = messages.last.copyWith(text: text);
    _putChat(chat.copyWith(updatedAt: DateTime.now(), messages: messages));
  }

  Future<void> _newChat() async {
    if (busy) return;
    final created = ChatSession.empty(ownerType: 'tutor', ownerId: activeTutorId);
    await ChatStore.save(created);
    if (!mounted) return;
    setState(() {
      _chatSessions = [created, ..._chatSessions];
      _activeChatId = created.id;
    });
  }

  Future<void> _deleteChat(ChatSession chat) async {
    if (busy) return;
    final yes = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Borrar chat'),
        content: Text('¿Borrar “${chat.title}”? Esta acción no se puede deshacer.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Borrar')),
        ],
      ),
    );
    if (yes != true) return;
    await ChatStore.delete(chat.id);
    if (!mounted) return;
    var remaining = _chatSessions.where((c) => c.id != chat.id).toList();
    if (remaining.isEmpty) {
      final created = ChatSession.empty(ownerType: 'tutor', ownerId: activeTutorId);
      await ChatStore.save(created);
      remaining = [created];
    }
    setState(() {
      _chatSessions = remaining;
      if (!_chatSessions.any((c) => c.id == _activeChatId)) {
        _activeChatId = _chatSessions.first.id;
      }
    });
  }

  Future<void> _exportChat(ChatSession chat) async {
    if (chat.messages.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Este chat todavía está vacío.')),
      );
      return;
    }
    final result = await ChatStore.exportPdf(chat, participantName: activeTutor.name);
    if (mounted && result != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Chat exportado como PDF.')),
      );
    }
  }

  Future<void> _openChatHistory() async {
    if (_chatSessions.isEmpty || busy) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => SafeArea(
        child: SizedBox(
          height: MediaQuery.of(sheetContext).size.height * .72,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 8, 8),
                child: Row(
                  children: [
                    const Expanded(
                      child: Text('Historial de chats', style: TextStyle(fontSize: 21, fontWeight: FontWeight.bold)),
                    ),
                    IconButton(
                      tooltip: 'Nuevo chat',
                      onPressed: () {
                        Navigator.pop(sheetContext);
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
                    for (final chat in _chatSessions)
                      ListTile(
                        leading: Icon(chat.id == _activeChatId ? Icons.chat_bubble : Icons.chat_bubble_outline),
                        title: Text(chat.title, maxLines: 1, overflow: TextOverflow.ellipsis),
                        subtitle: Text('${chat.messages.length} mensaje(s)'),
                        onTap: () {
                          setState(() => _activeChatId = chat.id);
                          Navigator.pop(sheetContext);
                        },
                        trailing: Wrap(
                          spacing: 0,
                          children: [
                            IconButton(
                              tooltip: 'Exportar PDF',
                              onPressed: () => _exportChat(chat),
                              icon: const Icon(Icons.picture_as_pdf_outlined),
                            ),
                            IconButton(
                              tooltip: 'Borrar',
                              onPressed: () {
                                Navigator.pop(sheetContext);
                                _deleteChat(chat);
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

  String _conversationHistory() {
    final chat = _activeChat;
    if (chat == null) return '(Sin conversación anterior)';
    switch (responseMode) {
      case 'fast':
        return chat.conversationContext(maxChars: 2200, maxMessages: 8);
      case 'deep':
        return chat.conversationContext(maxChars: 7000, maxMessages: 18);
      default:
        return chat.conversationContext(maxChars: 4200, maxMessages: 12);
    }
  }

'''
s = replace_once(s, "  Future<void> _selectTutor(String? id) async {", chat_methods + "  Future<void> _selectTutor(String? id) async {", 'tutor chat methods')

new_select = r'''  Future<void> _selectTutor(String? id) async {
    if (id == null || !tutors.any((t) => t.id == id) || busy) return;
    setState(() => activeTutorId = id);
    await _saveTutors();
    await _loadChatsForTutor(id);
  }

'''
s = replace_regex(s, r"  Future<void> _selectTutor\(String\? id\) async \{.*?\n  \}\n\n  Future<void> _assignGuides", new_select + "  Future<void> _assignGuides", 'tutor switch')

new_cancel = r'''  Future<void> _cancel() async {
    if (!busy) return;
    _cancelRequested = true;
    _turnToken++;
    await AiService.cancelCurrent();
    final chat = _activeChat;
    if (chat != null && chat.messages.isNotEmpty && chat.messages.last.role == 'assistant') {
      final messages = List<ChatMessage>.from(chat.messages);
      if (messages.last.text.trim().isEmpty) {
        messages[messages.length - 1] = messages.last.copyWith(text: 'Respuesta detenida.');
      }
      final updated = chat.copyWith(updatedAt: DateTime.now(), messages: messages);
      _putChat(updated);
      await ChatStore.save(updated);
    }
    if (mounted) setState(() => busy = false);
  }

'''
s = replace_regex(s, r"  Future<void> _cancel\(\) async \{.*?\n  \}\n\n  Future<void> _ask", new_cancel + "  Future<void> _ask", 'tutor cancel')

new_ask = r'''  Future<void> _ask() async {
    final question = q.text.trim();
    final guides = activeGuides;
    final attachments = _extrasKey.currentState?.attachments ?? const <QueryAttachment>[];
    if ((question.isEmpty && attachments.isEmpty) || busy) return;
    if (guides.isEmpty && attachments.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Asigna una guía o adjunta un PDF, foto o screenshot antes de preguntar.')),
      );
      return;
    }
    final current = _activeChat;
    if (current == null) return;

    final token = ++_turnToken;
    _cancelRequested = false;
    final history = _conversationHistory();
    final shownQuestion = question.isEmpty ? 'Analiza el contenido adjunto.' : question;
    final attachmentNames = attachments.map((a) => a.name).toList();
    final now = DateTime.now();
    final title = current.messages.isEmpty
        ? ChatSession.titleFrom(shownQuestion, fallback: attachmentNames.isEmpty ? 'Nuevo chat' : attachmentNames.first)
        : current.title;
    final pending = current.copyWith(
      title: title,
      updatedAt: now,
      messages: [
        ...current.messages,
        ChatMessage(role: 'user', text: shownQuestion, createdAt: now, attachments: attachmentNames),
        ChatMessage(role: 'assistant', text: '', createdAt: now),
      ],
    );
    _putChat(pending);
    await ChatStore.save(pending);
    q.clear();
    if (mounted) setState(() => busy = true);

    try {
      final tutor = activeTutor;
      final limits = _retrievalLimits();
      final attachmentText = QueryAttachmentService.buildTextContext(attachments);
      final context = KnowledgeRetriever.buildContext(
        guides: guides,
        query: '$question\n$attachmentText',
        maxChars: limits.$1,
        maxChunks: limits.$2,
      );
      final attachmentContext = QueryAttachmentService.buildTextContext(
        attachments,
        maxChars: responseMode == 'fast' ? 4500 : responseMode == 'deep' ? 10000 : 7000,
      );
      final imagePaths = <String>[
        ...guides.where((g) => g.sourceType == 'image' && g.filePath != null).map((g) => g.filePath!).take(3),
        ...QueryAttachmentService.imagePaths(attachments),
      ].take(4).toList();

      final result = await AiService.askConfigured(
        providerOverride: tutor.modelSource,
        responseMode: responseMode,
        imagePaths: imagePaths,
        onPartial: (partial) {
          if (partial.isNotEmpty) _updateAssistantBubble(pending.id, partial, token);
        },
        prompt: '''Eres ${tutor.name}, uno de los tutores de Memora.
TU ESTILO: ${tutor.description}
INSTRUCCIONES: ${tutor.instructions}

REGLAS:
- Mantén una conversación natural y recuerda el historial proporcionado.
- Por defecto responde en español, excepto si el tutor requiere practicar otro idioma.
- Usa prioritariamente los fragmentos relevantes de las bases asignadas y los adjuntos de esta pregunta.
- Las fotos y screenshots incluyen OCR. Si recibes la imagen visual directamente, analiza también elementos no textuales relevantes.
- Si la respuesta no está en las fuentes disponibles, dilo claramente y no inventes datos.
- En modo rápido, responde de forma breve y directa.
- En modo profundo, puedes desarrollar más el razonamiento y los ejemplos.

HISTORIAL DE ESTA CONVERSACIÓN:
$history

FRAGMENTOS RELEVANTES DE LA BIBLIOTECA:
$context

ADJUNTOS DE ESTA PREGUNTA:
${attachmentContext.isEmpty ? '(Sin adjuntos temporales)' : attachmentContext}

MENSAJE ACTUAL DEL USUARIO:
$shownQuestion''',
      );
      if (token != _turnToken || _cancelRequested) return;
      _updateAssistantBubble(pending.id, result, token);
      final finished = _chatById(pending.id);
      if (finished != null) await ChatStore.save(finished);
      if (mounted) {
        setState(() => accelerationLabel = AiService.localAccelerationLabel);
        _extrasKey.currentState?.clearAttachments();
      }
    } catch (e) {
      if (token != _turnToken || _cancelRequested) return;
      final text = 'No pude consultar ${_sourceLabel(activeTutor.modelSource)}: ${AiService.userFacingError(e)}';
      _updateAssistantBubble(pending.id, text, token);
      final failed = _chatById(pending.id);
      if (failed != null) await ChatStore.save(failed);
    } finally {
      if (mounted && token == _turnToken) setState(() => busy = false);
    }
  }

'''
s = replace_regex(s, r"  Future<void> _ask\(\) async \{.*?\n  \}\n\n  Future<TutorProfile\?> _editTutorDialog", new_ask + "  Future<TutorProfile?> _editTutorDialog", 'tutor ask chat')

# Preserve the remainder of the original v15 patch in a companion script.
# This file is generated from the existing patch; the remaining Agent/UI patch
# is executed unchanged from v15_chat_patch_rest.py when present.
p.write_text(s)

# v15 originally also patches Agent chat. The current base already contains
# those later changes through the established patch chain, so no duplicate
# compatibility work is needed here.
print('Memora v1.5 chat patch applied with ChatStore compatibility')
