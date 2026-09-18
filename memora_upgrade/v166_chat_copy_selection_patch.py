from pathlib import Path

# v166: make chat text easy to copy everywhere.
# Shared chat bubbles already use SelectableText, so Android's native selection
# handles partial-copy. Add a one-tap copy action for the whole displayed
# message. Also add copy to the Orchestrator's current final response.

p = Path('lib/chat_widgets.dart')
s = p.read_text()

if "package:flutter/services.dart" not in s:
    s = s.replace(
        "import 'package:flutter/material.dart';\n",
        "import 'package:flutter/material.dart';\nimport 'package:flutter/services.dart';\n",
        1,
    )

anchor = "  Future<void> _toggleSpanish() async {\n"
method = r"""  Future<void> _copyMessage() async {
    final text = (_showSpanish && _spanish != null ? _spanish! : widget.message.text).trim();
    if (text.isEmpty) return;
    await Clipboard.setData(ClipboardData(text: text));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Copiado al portapapeles.'),
        duration: Duration(seconds: 1),
      ),
    );
  }

"""
if '_copyMessage()' not in s:
    if anchor not in s:
        raise SystemExit('v166 chat copy method anchor missing')
    s = s.replace(anchor, method + anchor, 1)

# Insert a copy button after Translate/Auto ES controls. It works for user and
# assistant messages and copies whichever version is currently displayed.
old = """            if (_canTranslate) ...[
              const SizedBox(height: 4),
              Wrap(
                spacing: 2,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  TextButton.icon(
                    onPressed: _translating ? null : _toggleSpanish,
                    style: TextButton.styleFrom(
                      visualDensity: VisualDensity.compact,
                      padding: const EdgeInsets.symmetric(horizontal: 6),
                    ),
                    icon: const Icon(Icons.translate, size: 17),
                    label: Text(_showSpanish ? 'Original' : 'ES'),
                  ),
                  TextButton.icon(
                    onPressed: () => widget.onAutoSpanishChanged(!widget.autoSpanish),
                    style: TextButton.styleFrom(
                      visualDensity: VisualDensity.compact,
                      padding: const EdgeInsets.symmetric(horizontal: 6),
                    ),
                    icon: Icon(
                      widget.autoSpanish
                          ? Icons.check_circle_outline
                          : Icons.autorenew_rounded,
                      size: 17,
                    ),
                    label: Text(widget.autoSpanish ? 'Auto ES on' : 'Auto ES'),
                  ),
                ],
              ),
            ],
"""
new = """            if (_canTranslate) ...[
              const SizedBox(height: 4),
              Wrap(
                spacing: 2,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  TextButton.icon(
                    onPressed: _translating ? null : _toggleSpanish,
                    style: TextButton.styleFrom(
                      visualDensity: VisualDensity.compact,
                      padding: const EdgeInsets.symmetric(horizontal: 6),
                    ),
                    icon: const Icon(Icons.translate, size: 17),
                    label: Text(_showSpanish ? 'Original' : 'ES'),
                  ),
                  TextButton.icon(
                    onPressed: () => widget.onAutoSpanishChanged(!widget.autoSpanish),
                    style: TextButton.styleFrom(
                      visualDensity: VisualDensity.compact,
                      padding: const EdgeInsets.symmetric(horizontal: 6),
                    ),
                    icon: Icon(
                      widget.autoSpanish
                          ? Icons.check_circle_outline
                          : Icons.autorenew_rounded,
                      size: 17,
                    ),
                    label: Text(widget.autoSpanish ? 'Auto ES on' : 'Auto ES'),
                  ),
                ],
              ),
            ],
            if (widget.message.text.trim().isNotEmpty) ...[
              const SizedBox(height: 2),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  onPressed: _copyMessage,
                  style: TextButton.styleFrom(
                    visualDensity: VisualDensity.compact,
                    padding: const EdgeInsets.symmetric(horizontal: 6),
                  ),
                  icon: const Icon(Icons.copy_outlined, size: 17),
                  label: const Text('Copiar'),
                ),
              ),
            ],
"""
if old not in s:
    raise SystemExit('v166 chat action block anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)

# Orchestrator: its final synthesized answer is not rendered by ChatTranscript,
# so keep it selectable and add an explicit copy-all button too.
p = Path('lib/agent_orchestrator_page.dart')
s = p.read_text()

if "package:flutter/services.dart" not in s:
    s = s.replace(
        "import 'package:flutter/material.dart';\n",
        "import 'package:flutter/material.dart';\nimport 'package:flutter/services.dart';\n",
        1,
    )

old = """Card(child:Padding(padding:const EdgeInsets.all(16),child:SelectableText(answer)))"""
new = """Card(child:Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
  Row(children:[
    const Expanded(child:Text('Respuesta',style:TextStyle(fontWeight:FontWeight.bold))),
    IconButton(
      tooltip:'Copiar respuesta',
      onPressed:answer.trim().isEmpty?null:() async {
        await Clipboard.setData(ClipboardData(text:answer));
        if(context.mounted)ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content:Text('Respuesta copiada al portapapeles.'),duration:Duration(seconds:1)),
        );
      },
      icon:const Icon(Icons.copy_outlined),
    ),
  ]),
  SelectableText(answer),
])))"""
if old not in s:
    raise SystemExit('v166 orchestrator answer card anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)

print('v166 applied: selectable chat text + copy buttons across Memora chats')
