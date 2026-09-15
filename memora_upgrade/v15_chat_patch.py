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

chat_methods = r"""
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

"""
s = replace_once(s, "  Future<void> _selectTutor(String? id) async {", chat_methods + "  Future<void> _selectTutor(String? id) async {", 'tutor chat methods')

new_select = r"""  Future<void> _selectTutor(String? id) async {
    if (id == null || !tutors.any((t) => t.id == id) || busy) return;
    setState(() => activeTutorId = id);
    await _saveTutors();
    await _loadChatsForTutor(id);
  }

"""
s = replace_regex(s, r"  Future<void> _selectTutor\(String\? id\) async \{.*?\n  \}\n\n  Future<void> _assignGuides", new_select + "  Future<void> _assignGuides", 'tutor switch')

new_cancel = r"""  Future<void> _cancel() async {
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

"""
s = replace_regex(s, r"  Future<void> _cancel\(\) async \{.*?\n  \}\n\n  Future<void> _ask", new_cancel + "  Future<void> _ask", 'tutor cancel')

new_ask = r"""  Future<void> _ask() async {
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

"""
s = replace_regex(s, r"  Future<void> _ask\(\) async \{.*?\n  \}\n\n  Future<TutorProfile\?> _editTutorDialog", new_ask + "  Future<TutorProfile?> _editTutorDialog", 'tutor ask chat')

s = replace_once(
    s,
    "          actions: [\n            IconButton(\n              onPressed: _openManager,",
    "          actions: [\n            IconButton(\n              onPressed: busy ? null : _newChat,\n              tooltip: 'Nuevo chat',\n              icon: const Icon(Icons.add_comment_outlined),\n            ),\n            IconButton(\n              onPressed: busy || _chatSessions.isEmpty ? null : _openChatHistory,\n              tooltip: 'Historial de chats',\n              icon: const Icon(Icons.history),\n            ),\n            IconButton(\n              onPressed: busy || _activeChat == null || _chatMessages.isEmpty ? null : () => _exportChat(_activeChat!),\n              tooltip: 'Exportar chat a PDF',\n              icon: const Icon(Icons.picture_as_pdf_outlined),\n            ),\n            IconButton(\n              onPressed: _openManager,",
    'tutor appbar chat actions',
)
s = replace_once(
    s,
    "                          SelectableText(answer),",
    "                          SizedBox(\n                            height: 420,\n                            child: ChatTranscript(\n                              messages: _chatMessages,\n                              participantName: activeTutor.name,\n                              emptyText: 'Empieza un chat con ${activeTutor.name}. El historial se guardará automáticamente.',\n                            ),\n                          ),",
    'tutor transcript',
)
p.write_text(s)

# -----------------------------------------------------------------------------
# Agent chat
# -----------------------------------------------------------------------------
p = ROOT / 'lib' / 'agent_page.dart'
s = p.read_text()
s = replace_once(
    s,
    "import 'query_extras_bar.dart';\n",
    "import 'query_extras_bar.dart';\nimport 'chat_store.dart';\nimport 'chat_widgets.dart';\n",
    'agent chat imports',
)
s = replace_once(
    s,
    "  final _extrasKey = GlobalKey<QueryExtrasBarState>();\n",
    "  final _extrasKey = GlobalKey<QueryExtrasBarState>();\n  List<ChatSession> _chatSessions = [];\n  String? _activeChatId;\n  int _turnToken = 0;\n  bool _cancelRequested = false;\n",
    'agent chat fields',
)
s = replace_once(
    s,
    "    if (mounted) setState(() => loading = false);",
    "    if (activeId != null) await _loadChatsForAgent(activeId!);\n    if (mounted) setState(() => loading = false);",
    'agent initial chat load',
)

agent_methods = r"""
  ChatSession? get _activeChat {
    if (_chatSessions.isEmpty) return null;
    return _chatSessions.firstWhere(
      (c) => c.id == _activeChatId,
      orElse: () => _chatSessions.first,
    );
  }

  List<ChatMessage> get _chatMessages => _activeChat?.messages ?? const [];

  Future<void> _loadChatsForAgent(String agentId) async {
    var sessions = await ChatStore.listFor('agent', agentId);
    if (sessions.isEmpty) {
      final created = ChatSession.empty(ownerType: 'agent', ownerId: agentId);
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

  Future<void> _switchAgent(String value) async {
    if (busy) return;
    setState(() => activeId = value);
    await _save();
    await _loadChatsForAgent(value);
  }

  Future<void> _newChat() async {
    final agent = activeAgent;
    if (agent == null || busy) return;
    final created = ChatSession.empty(ownerType: 'agent', ownerId: agent.id);
    await ChatStore.save(created);
    if (!mounted) return;
    setState(() {
      _chatSessions = [created, ..._chatSessions];
      _activeChatId = created.id;
    });
  }

  Future<void> _deleteChat(ChatSession chat) async {
    final agent = activeAgent;
    if (agent == null || busy) return;
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
      final created = ChatSession.empty(ownerType: 'agent', ownerId: agent.id);
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
    final agent = activeAgent;
    if (agent == null) return;
    if (chat.messages.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Este chat todavía está vacío.')),
      );
      return;
    }
    final result = await ChatStore.exportPdf(chat, participantName: agent.name);
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

"""
s = replace_once(s, "  Future<AgentProfile?> _agentDialog({AgentProfile? existing}) async {", agent_methods + "  Future<AgentProfile?> _agentDialog({AgentProfile? existing}) async {", 'agent chat methods')

s = replace_once(
    s,
    "    await _save();\n  }\n\n  Future<void> _editAgent() async {",
    "    await _save();\n    await _loadChatsForAgent(created.id);\n  }\n\n  Future<void> _editAgent() async {",
    'agent create load chat',
)
s = replace_once(
    s,
    "    await _save();\n  }\n\n  Future<void> _cancel() async {",
    "    await _save();\n    if (activeId != null) {\n      await _loadChatsForAgent(activeId!);\n    } else if (mounted) {\n      setState(() {\n        _chatSessions = [];\n        _activeChatId = null;\n      });\n    }\n  }\n\n  Future<void> _cancel() async {",
    'agent delete reload chat',
)

new_cancel = r"""  Future<void> _cancel() async {
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

"""
s = replace_regex(s, r"  Future<void> _cancel\(\) async \{.*?\n  \}\n\n  Future<void> _runAgent", new_cancel + "  Future<void> _runAgent", 'agent cancel')

new_run = r"""  Future<void> _runAgent() async {
    final agent = activeAgent;
    final request = input.text.trim();
    final attachments = _extrasKey.currentState?.attachments ?? const <QueryAttachment>[];
    if (agent == null || (request.isEmpty && attachments.isEmpty) || busy) return;
    final current = _activeChat;
    if (current == null) return;

    final token = ++_turnToken;
    _cancelRequested = false;
    final history = _conversationHistory();
    final shownRequest = request.isEmpty ? 'Analiza el contenido adjunto.' : request;
    final attachmentNames = attachments.map((a) => a.name).toList();
    final now = DateTime.now();
    final title = current.messages.isEmpty
        ? ChatSession.titleFrom(shownRequest, fallback: attachmentNames.isEmpty ? 'Nuevo chat' : attachmentNames.first)
        : current.title;
    final pending = current.copyWith(
      title: title,
      updatedAt: now,
      messages: [
        ...current.messages,
        ChatMessage(role: 'user', text: shownRequest, createdAt: now, attachments: attachmentNames),
        ChatMessage(role: 'assistant', text: '', createdAt: now),
      ],
    );
    _putChat(pending);
    await ChatStore.save(pending);
    input.clear();
    if (mounted) setState(() => busy = true);

    try {
      final limits = _retrievalLimits();
      final attachmentText = QueryAttachmentService.buildTextContext(attachments);
      final context = KnowledgeRetriever.buildContext(
        guides: activeGuides,
        query: '${agent.prompt}\n$request\n$attachmentText',
        maxChars: limits.$1,
        maxChunks: limits.$2,
      );
      final attachmentContext = QueryAttachmentService.buildTextContext(
        attachments,
        maxChars: responseMode == 'fast' ? 4500 : responseMode == 'deep' ? 10000 : 7000,
      );
      final imagePaths = <String>[
        ...activeGuides.where((g) => g.sourceType == 'image' && g.filePath != null).map((g) => g.filePath!).take(3),
        ...QueryAttachmentService.imagePaths(attachments),
      ].take(4).toList();

      final result = await AiService.askConfigured(
        providerOverride: agent.modelSource,
        responseMode: responseMode,
        imagePaths: imagePaths,
        onPartial: (partial) {
          if (partial.isNotEmpty) _updateAssistantBubble(pending.id, partial, token);
        },
        prompt: '''Eres un agente personalizado de Memora llamado ${agent.name}.
PROMPT DEL AGENTE:
${agent.prompt}

HISTORIAL DE ESTA CONVERSACIÓN:
$history

FRAGMENTOS RELEVANTES DE SUS BASES:
$context

ADJUNTOS DE ESTA SOLICITUD:
${attachmentContext.isEmpty ? '(Sin adjuntos temporales)' : attachmentContext}

MENSAJE ACTUAL DEL USUARIO:
$shownRequest

Sigue el prompt del agente y mantén continuidad con el historial. Usa las bases y adjuntos cuando sean relevantes. Las imágenes incluyen OCR y, con un modelo compatible con visión, también se envía la imagen original. Si falta un dato, indícalo en vez de inventarlo. En modo rápido prioriza una respuesta breve; en modo profundo puedes desarrollar más el análisis.''',
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
      _updateAssistantBubble(
        pending.id,
        'El agente no pudo responder: ${AiService.userFacingError(e)}',
        token,
      );
      final failed = _chatById(pending.id);
      if (failed != null) await ChatStore.save(failed);
    } finally {
      if (mounted && token == _turnToken) setState(() => busy = false);
    }
  }

"""
s = replace_regex(s, r"  Future<void> _runAgent\(\) async \{.*?\n  \}\n\n  @override\n  Widget build", new_run + "  @override\n  Widget build", 'agent run chat')

s = replace_once(
    s,
    "          actions: [\n            IconButton(\n              onPressed: _createAgent,",
    "          actions: [\n            IconButton(\n              onPressed: busy || activeAgent == null ? null : _newChat,\n              tooltip: 'Nuevo chat',\n              icon: const Icon(Icons.add_comment_outlined),\n            ),\n            IconButton(\n              onPressed: busy || _chatSessions.isEmpty ? null : _openChatHistory,\n              tooltip: 'Historial de chats',\n              icon: const Icon(Icons.history),\n            ),\n            IconButton(\n              onPressed: busy || _activeChat == null || _chatMessages.isEmpty ? null : () => _exportChat(_activeChat!),\n              tooltip: 'Exportar chat a PDF',\n              icon: const Icon(Icons.picture_as_pdf_outlined),\n            ),\n            IconButton(\n              onPressed: _createAgent,",
    'agent appbar chat actions',
)
s = replace_once(
    s,
    "                        onChanged: (value) async {\n                          if (value == null) return;\n                          setState(() => activeId = value);\n                          await _save();\n                        },",
    "                        onChanged: (value) async {\n                          if (value == null) return;\n                          await _switchAgent(value);\n                        },",
    'agent switch dropdown',
)
s = replace_once(
    s,
    "                          child: SelectableText(answer),",
    "                          child: SizedBox(\n                            height: 420,\n                            child: ChatTranscript(\n                              messages: _chatMessages,\n                              participantName: activeAgent!.name,\n                              emptyText: 'Empieza un chat con ${activeAgent!.name}. El historial se guardará automáticamente.',\n                            ),\n                          ),",
    'agent transcript',
)
p.write_text(s)

print('Memora v1.5 chat patch applied successfully')
