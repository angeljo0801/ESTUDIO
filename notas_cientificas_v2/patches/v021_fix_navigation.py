"""Corrección de navegación del editor para la versión v0.2.1.

Se aplica automáticamente sobre el archivo fuente v0.2 conservado en GitHub.
"""
from pathlib import Path

main = Path('notas_cientificas_v2/lib/main.dart')
s = main.read_text(encoding='utf-8')

def change(old, new):
    global s
    if old not in s:
        if new in s:
            return
        raise RuntimeError('Patrón no encontrado al actualizar main.dart: ' + old[:75])
    s = s.replace(old, new, 1)

change('  bool deleted = false;\n  Timer? _autoSave;',
       '  bool deleted = false;\n  bool _canLeave = false;\n  bool _closing = false;\n  Timer? _autoSave;')
change('  Future<void> _delete() async {', """  Future<void> _saveAndClose() async {
    if (_closing || !mounted) return;
    _closing = true;
    _autoSave?.cancel();
    try {
      await _save();
      if (!mounted) return;
      setState(() => _canLeave = true);
      await WidgetsBinding.instance.endOfFrame;
      if (mounted) Navigator.of(context).pop();
    } catch (_) {
      _closing = false;
      rethrow;
    }
  }

  Future<void> _delete() async {""")
change("""    deleted = true;
    await widget.onDelete(noteId);
    if (mounted) Navigator.pop(context);""", """    deleted = true;
    _autoSave?.cancel();
    await widget.onDelete(noteId);
    if (!mounted) return;
    setState(() => _canLeave = true);
    await WidgetsBinding.instance.endOfFrame;
    if (mounted) Navigator.of(context).pop();""")
change("""    return PopScope(canPop: false, onPopInvokedWithResult: (didPop, _) async {
      if (didPop) return;
      await _save();
      if (context.mounted) Navigator.pop(context);
    }, child: Scaffold(""", """    return PopScope(canPop: _canLeave, onPopInvokedWithResult: (didPop, _) {
      if (!didPop) _saveAndClose();
    }, child: Scaffold(""")
change("""        leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: () async {
          await _save();
          if (context.mounted) Navigator.pop(context);
        }),""", """        leading: IconButton(icon: const Icon(Icons.arrow_back),
          onPressed: _saveAndClose),""")
change("""          IconButton(tooltip: 'Guardar', icon: const Icon(Icons.check_rounded),
            onPressed: () async {await _save(); if (context.mounted) Navigator.pop(context);}),""", """          IconButton(tooltip: 'Guardar', icon: const Icon(Icons.check_rounded),
            onPressed: _saveAndClose),""")
main.write_text(s, encoding='utf-8')
p = Path('notas_cientificas_v2/pubspec.yaml')
p.write_text(p.read_text(encoding='utf-8').replace('version: 0.2.0+2', 'version: 0.2.1+3'), encoding='utf-8')
print('Aplicada la corrección de navegación de v0.2.1')
