from pathlib import Path
import os

# v1.47 — response duration belongs to the assistant message itself.
p=Path('lib/chat_widgets.dart'); s=p.read_text()
s=s.replace("    this.emptyText = 'Start a conversation.',\n  });","    this.emptyText = 'Start a conversation.',\n    this.liveResponseSeconds,\n    this.isResponding = false,\n  });",1)
s=s.replace("  final String emptyText;\n","  final String emptyText;\n  final double? liveResponseSeconds;\n  final bool isResponding;\n",1)
s=s.replace("          onAutoSpanishChanged: _setAutoSpanish,\n        );","          onAutoSpanishChanged: _setAutoSpanish,\n          liveResponseSeconds: index == 0 && message.role == 'assistant' ? widget.liveResponseSeconds : null,\n          isResponding: index == 0 && message.role == 'assistant' && widget.isResponding,\n        );",1)
s=s.replace("    required this.onAutoSpanishChanged,\n  });","    required this.onAutoSpanishChanged,\n    this.liveResponseSeconds,\n    this.isResponding = false,\n  });",1)
s=s.replace("  final Future<void> Function(bool value) onAutoSpanishChanged;\n","  final Future<void> Function(bool value) onAutoSpanishChanged;\n  final double? liveResponseSeconds;\n  final bool isResponding;\n",1)
end="""            ],
          ],
        ),
      ),
    );
"""
timer="""            ],
            if (!_mine && !widget.isResponding && widget.message.responseSeconds != null) ...[
              const SizedBox(height: 2),
              Align(
                alignment: Alignment.centerRight,
                child: Text(
                  '${widget.message.responseSeconds!.toStringAsFixed(1)} s',
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF7C4DFF)),
                ),
              ),
            ],
          ],
        ),
      ),
    );
"""
if end not in s: raise RuntimeError('v147 bubble end anchor missing')
s=s.replace(end,timer,1); p.write_text(s)

p=Path('lib/tutor_page.dart'); s=p.read_text()
old="""                              emptyText: 'Empieza un chat con ${activeTutor.name}. El historial se guardará automáticamente.',
                            ),
                          ),
                          const SizedBox(height: 6),
                          Align(
                            alignment: Alignment.centerRight,
                            child: Text(
                              '${_responseSeconds.toStringAsFixed(1)} s',
                              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: busy ? Theme.of(context).colorScheme.secondary : const Color(0xFF7C4DFF)),
                            ),
                          ),"""
new="""                              emptyText: 'Empieza un chat con ${activeTutor.name}. El historial se guardará automáticamente.',
                              liveResponseSeconds: _responseSeconds,
                              isResponding: busy,
                            ),
                          ),
                          if (busy) ...[
                            const SizedBox(height: 6),
                            Align(
                              alignment: Alignment.centerRight,
                              child: Text(
                                '${_responseSeconds.toStringAsFixed(1)} s',
                                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Theme.of(context).colorScheme.secondary),
                              ),
                            ),
                          ],"""
if old not in s: raise RuntimeError('v147 old external timer anchor missing')
s=s.replace(old,new,1)
old_final="""    } finally {
      _stopResponseTimer();
      if (mounted && token == _turnToken) setState(() => busy = false);
    }
"""
new_final="""    } finally {
      _stopResponseTimer();
      if (token == _turnToken) {
        final timed = _chatById(pending.id);
        if (timed != null && timed.messages.isNotEmpty && timed.messages.last.role == 'assistant') {
          final messages = List<ChatMessage>.from(timed.messages);
          messages[messages.length - 1] = messages.last.copyWith(responseSeconds: _responseSeconds);
          final saved = timed.copyWith(updatedAt: DateTime.now(), messages: messages);
          _putChat(saved);
          await ChatStore.save(saved);
        }
      }
      if (mounted && token == _turnToken) setState(() => busy = false);
    }
"""
if old_final not in s: raise RuntimeError('v147 tutor finally anchor missing')
s=s.replace(old_final,new_final,1); p.write_text(s)
p=Path('pubspec.yaml'); p.write_text(p.read_text().replace('version: 1.46.0+59','version: 1.47.0+60'))
print('Memora v1.47 per-message response timer applied successfully')
_v148=Path(os.environ['GITHUB_WORKSPACE'])/'memora_upgrade'/'v148_tutor_model_picker_patch.py'
exec(compile(_v148.read_text(),str(_v148),'exec'))
