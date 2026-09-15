from pathlib import Path
import re

ROOT = Path('.')


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f'Pattern not found for {label}')
    return text.replace(old, new, 1)

# Tutor -----------------------------------------------------------------------
p = ROOT / 'lib' / 'tutor_page.dart'
s = p.read_text()
s = replace_once(
    s,
    "import 'models.dart';\n",
    "import 'models.dart';\nimport 'query_attachment_service.dart';\nimport 'query_extras_bar.dart';\n",
    'tutor imports',
)
s = replace_once(
    s,
    "  final q = TextEditingController();\n",
    "  final q = TextEditingController();\n  final _extrasKey = GlobalKey<QueryExtrasBarState>();\n",
    'tutor extras key',
)

new_ask = r'''  Future<void> _ask() async {
    final question = q.text.trim();
    final guides = activeGuides;
    final attachments =
        _extrasKey.currentState?.attachments ?? const <QueryAttachment>[];
    if ((question.isEmpty && attachments.isEmpty) || busy) return;
    if (guides.isEmpty && attachments.isEmpty) {
      setState(() => answer =
          'Asigna una guía o adjunta un PDF, foto o screenshot antes de preguntar.');
      return;
    }

    setState(() {
      busy = true;
      answer = 'Preparando respuesta…';
    });

    try {
      final tutor = activeTutor;
      final limits = _retrievalLimits();
      final context = KnowledgeRetriever.buildContext(
        guides: guides,
        query: question.isEmpty ? QueryAttachmentService.buildTextContext(attachments) : question,
        maxChars: limits.$1,
        maxChunks: limits.$2,
      );
      final attachmentContext = QueryAttachmentService.buildTextContext(
        attachments,
        maxChars: responseMode == 'fast' ? 4500 : responseMode == 'deep' ? 10000 : 7000,
      );
      final imagePaths = <String>[
        ...guides
            .where((g) => g.sourceType == 'image' && g.filePath != null)
            .map((g) => g.filePath!)
            .take(3),
        ...QueryAttachmentService.imagePaths(attachments),
      ].take(4).toList();

      final result = await AiService.askConfigured(
        providerOverride: tutor.modelSource,
        responseMode: responseMode,
        imagePaths: imagePaths,
        onPartial: (partial) {
          if (mounted && partial.isNotEmpty) setState(() => answer = partial);
        },
        prompt: '''Eres ${tutor.name}, uno de los tutores de Memora.
TU ESTILO: ${tutor.description}
INSTRUCCIONES: ${tutor.instructions}

REGLAS:
- Por defecto responde en español, excepto si el tutor requiere practicar otro idioma.
- Usa prioritariamente los fragmentos relevantes de las bases asignadas y los adjuntos de esta pregunta.
- Las fotos y screenshots incluyen OCR. Si recibes la imagen visual directamente, analiza también elementos no textuales relevantes.
- Si la respuesta no está en las fuentes disponibles, dilo claramente y no inventes datos.
- En modo rápido, responde de forma breve y directa.
- En modo profundo, puedes desarrollar más el razonamiento y los ejemplos.

FRAGMENTOS RELEVANTES DE LA BIBLIOTECA:
$context

ADJUNTOS DE ESTA PREGUNTA:
${attachmentContext.isEmpty ? '(Sin adjuntos temporales)' : attachmentContext}

PREGUNTA: ${question.isEmpty ? 'Analiza el contenido adjunto y explícame lo importante.' : question}''',
      );
      if (mounted) {
        setState(() {
          answer = result;
          accelerationLabel = AiService.localAccelerationLabel;
        });
        _extrasKey.currentState?.clearAttachments();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          answer =
              'No pude consultar ${_sourceLabel(activeTutor.modelSource)}: ${AiService.userFacingError(e)}';
        });
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

'''
s, n = re.subn(
    r"  Future<void> _ask\(\) async \{.*?\n  \}\n\n  Future<TutorProfile\?> _editTutorDialog",
    new_ask + "  Future<TutorProfile?> _editTutorDialog",
    s,
    count=1,
    flags=re.S,
)
if n != 1:
    raise RuntimeError('Could not replace tutor _ask')

s = replace_once(
    s,
    "                  const SizedBox(height: 12),\n                  TextField(\n                    controller: q,",
    "                  const SizedBox(height: 12),\n                  QueryExtrasBar(\n                    key: _extrasKey,\n                    controller: q,\n                    enabled: !busy,\n                  ),\n                  const SizedBox(height: 4),\n                  TextField(\n                    controller: q,",
    'tutor extras UI',
)
p.write_text(s)

# Agent -----------------------------------------------------------------------
p = ROOT / 'lib' / 'agent_page.dart'
s = p.read_text()
s = replace_once(
    s,
    "import 'models.dart';\n",
    "import 'models.dart';\nimport 'query_attachment_service.dart';\nimport 'query_extras_bar.dart';\n",
    'agent imports',
)
s = replace_once(
    s,
    "  final input = TextEditingController();\n",
    "  final input = TextEditingController();\n  final _extrasKey = GlobalKey<QueryExtrasBarState>();\n",
    'agent extras key',
)

new_run = r'''  Future<void> _runAgent() async {
    final agent = activeAgent;
    final request = input.text.trim();
    final attachments =
        _extrasKey.currentState?.attachments ?? const <QueryAttachment>[];
    if (agent == null || (request.isEmpty && attachments.isEmpty) || busy) return;

    setState(() {
      busy = true;
      answer = 'Preparando respuesta…';
    });

    try {
      final limits = _retrievalLimits();
      final context = KnowledgeRetriever.buildContext(
        guides: activeGuides,
        query: '${agent.prompt}\n$request\n${QueryAttachmentService.buildTextContext(attachments)}',
        maxChars: limits.$1,
        maxChunks: limits.$2,
      );
      final attachmentContext = QueryAttachmentService.buildTextContext(
        attachments,
        maxChars: responseMode == 'fast' ? 4500 : responseMode == 'deep' ? 10000 : 7000,
      );
      final imagePaths = <String>[
        ...activeGuides
            .where((g) => g.sourceType == 'image' && g.filePath != null)
            .map((g) => g.filePath!)
            .take(3),
        ...QueryAttachmentService.imagePaths(attachments),
      ].take(4).toList();

      final result = await AiService.askConfigured(
        providerOverride: agent.modelSource,
        responseMode: responseMode,
        imagePaths: imagePaths,
        onPartial: (partial) {
          if (mounted && partial.isNotEmpty) setState(() => answer = partial);
        },
        prompt: '''Eres un agente personalizado de Memora llamado ${agent.name}.
PROMPT DEL AGENTE:
${agent.prompt}

FRAGMENTOS RELEVANTES DE SUS BASES:
$context

ADJUNTOS DE ESTA SOLICITUD:
${attachmentContext.isEmpty ? '(Sin adjuntos temporales)' : attachmentContext}

SOLICITUD DEL USUARIO:
${request.isEmpty ? 'Analiza el contenido adjunto de acuerdo con tu prompt.' : request}

Sigue el prompt del agente. Usa las bases y adjuntos cuando sean relevantes. Las imágenes incluyen OCR y, con un modelo compatible con visión, también se envía la imagen original. Si falta un dato, indícalo en vez de inventarlo. En modo rápido prioriza una respuesta breve; en modo profundo puedes desarrollar más el análisis.''',
      );
      if (mounted) {
        setState(() {
          answer = result;
          accelerationLabel = AiService.localAccelerationLabel;
        });
        _extrasKey.currentState?.clearAttachments();
      }
    } catch (e) {
      if (mounted) {
        setState(() => answer =
            'El agente no pudo responder: ${AiService.userFacingError(e)}');
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

'''
s, n = re.subn(
    r"  Future<void> _runAgent\(\) async \{.*?\n  \}\n\n  @override\n  Widget build",
    new_run + "  @override\n  Widget build",
    s,
    count=1,
    flags=re.S,
)
if n != 1:
    raise RuntimeError('Could not replace agent _runAgent')

s = replace_once(
    s,
    "                      const SizedBox(height: 12),\n                      TextField(\n                        controller: input,",
    "                      const SizedBox(height: 12),\n                      QueryExtrasBar(\n                        key: _extrasKey,\n                        controller: input,\n                        enabled: !busy,\n                      ),\n                      const SizedBox(height: 4),\n                      TextField(\n                        controller: input,",
    'agent extras UI',
)
p.write_text(s)

# Library ---------------------------------------------------------------------
p = ROOT / 'lib' / 'home_page.dart'
s = p.read_text()
s = replace_once(
    s,
    "import 'guide_store.dart';\n",
    "import 'guide_store.dart';\nimport 'query_attachment_service.dart';\n",
    'library image import',
)

image_method = r'''  Future<void> _importImage({required bool camera}) async {
    setState(() => _busy = true);
    try {
      final attachment = camera
          ? await QueryAttachmentService.takePhoto()
          : await QueryAttachmentService.pickImageFromGallery();
      if (attachment == null) return;
      final guide = await QueryAttachmentService.saveImageToLibrary(attachment);
      await widget.store.add(guide);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(camera
              ? 'Foto guardada en Biblioteca con OCR.'
              : 'Imagen / screenshot guardado en Biblioteca con OCR.'),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No pude guardar la imagen: $e')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

'''
s = replace_once(
    s,
    "  Future<void> _pasteText() async {",
    image_method + "  Future<void> _pasteText() async {",
    'library image method',
)

menu_anchor = '''              ListTile(
                leading: const Icon(Icons.auto_awesome),
                title: const Text('Crear PDF o Excel con IA'),'''
menu_insert = '''              ListTile(
                leading: const Icon(Icons.photo_camera_rounded),
                title: const Text('Tomar foto'),
                subtitle: const Text('Guarda la foto en Biblioteca y extrae su texto con OCR'),
                onTap: () {
                  Navigator.pop(context);
                  _importImage(camera: true);
                },
              ),
              ListTile(
                leading: const Icon(Icons.image_rounded),
                title: const Text('Imagen / screenshot'),
                subtitle: const Text('Importa desde Galería y guarda el texto detectado'),
                onTap: () {
                  Navigator.pop(context);
                  _importImage(camera: false);
                },
              ),
              ListTile(
                leading: const Icon(Icons.auto_awesome),
                title: const Text('Crear PDF o Excel con IA'),'''
s = replace_once(s, menu_anchor, menu_insert, 'library add menu')

s = s.replace(
    "guide.sourceType == 'pdf'\n                                                  ? Icons.picture_as_pdf_rounded\n                                                  : Icons.menu_book_rounded,",
    "guide.sourceType == 'pdf'\n                                                  ? Icons.picture_as_pdf_rounded\n                                                  : guide.sourceType == 'image'\n                                                      ? Icons.image_rounded\n                                                      : Icons.menu_book_rounded,",
    1,
)
s = s.replace(
    "Importa PDF, Excel, DOCX, TXT o Markdown; o deja que una IA cree un PDF/Excel por ti.",
    "Importa PDF, Excel, DOCX, TXT, fotos o screenshots; o deja que una IA cree un PDF/Excel por ti.",
    1,
)
p.write_text(s)

print('Memora v1.4 patch applied successfully')
