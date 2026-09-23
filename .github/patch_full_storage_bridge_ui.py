from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()

def repl(old, new, label):
    global s
    if old not in s:
        raise RuntimeError(f"{label} anchor not found")
    s = s.replace(old, new, 1)

repl(
    "class _FileBridgePageState extends State<FileBridgePage> {",
    "class _FileBridgePageState extends State<FileBridgePage> with WidgetsBindingObserver {",
    "state class",
)

repl(
    "  bool _running = false;\n  String _rootName = '';",
    "  bool _running = false;\n  String _mode = 'folder';\n  bool _allFilesGranted = false;\n  String _rootName = '';",
    "state fields",
)

repl(
    """  void initState() {
    super.initState();
    _load();
  }""",
    """  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _load();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _refreshStatus();
    }
  }""",
    "initState",
)

repl(
    """      setState(() {
        _running = raw['running'] == true;
        _rootName = (raw['rootName'] ?? '').toString();
        _rootUri = (raw['rootUri'] ?? '').toString();""",
    """      setState(() {
        _running = raw['running'] == true;
        _mode = (raw['mode'] ?? 'folder').toString();
        _allFilesGranted = raw['allFilesGranted'] == true;
        _rootName = (raw['rootName'] ?? '').toString();
        _rootUri = (raw['rootUri'] ?? '').toString();""",
    "refresh status",
)

pick = """  Future<void> _pickRoot() async {
    setState(() => _busy = true);
    try {
      final raw = await _bridgeChannel.invokeMapMethod<String, dynamic>('pickRoot');
      if (raw != null && mounted) {
        setState(() {
          _rootName = (raw['rootName'] ?? '').toString();
          _rootUri = (raw['rootUri'] ?? '').toString();
        });
      }
    } on PlatformException catch (e) {
      _snack(e.message ?? e.code);
    } finally {
      if (mounted) setState(() => _busy = false);
      await _refreshStatus();
    }
  }
"""
extra = pick + """
  Future<void> _setMode(String mode) async {
    if (_busy || mode == _mode) return;
    setState(() => _busy = true);
    try {
      await _bridgeChannel.invokeMethod('setMode', {'mode': mode});
      await _refreshStatus();
      if (mode == 'all' && !_allFilesGranted) {
        _snack('Autoriza "Administrar todos los archivos" para activar este modo.');
      }
    } on PlatformException catch (e) {
      _snack(e.message ?? e.code);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _requestAllFilesAccess() async {
    try {
      await _bridgeChannel.invokeMethod('requestAllFilesAccess');
      _snack('Activa el permiso para Local AI Manager y vuelve a la app.');
    } on PlatformException catch (e) {
      _snack(e.message ?? e.code);
    }
  }
"""
repl(pick, extra, "pick root")

repl(
    """      } else {
        if (_rootUri.isEmpty) {
          _snack('Primero selecciona la carpeta que quieres compartir.');
          return;
        }
        await _bridgeChannel.invokeMethod('startHost', {""",
    """      } else {
        if (_mode == 'all' && !_allFilesGranted) {
          await _requestAllFilesAccess();
          return;
        }
        if (_mode == 'folder' && _rootUri.isEmpty) {
          _snack('Primero selecciona la carpeta que quieres compartir.');
          return;
        }
        await _bridgeChannel.invokeMethod('startHost', {""",
    "host toggle",
)

repl(
    """  void dispose() {
    _remoteUrl.dispose();
    _remoteToken.dispose();
    super.dispose();
  }""",
    """  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _remoteUrl.dispose();
    _remoteToken.dispose();
    super.dispose();
  }""",
    "dispose",
)

repl(
    """                  const Text(
                    'Solo se comparte la carpeta que tú autorices. El resto del teléfono queda fuera del puente.',
                  ),
                  const SizedBox(height: 12),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.folder_outlined),
                    title: Text(_rootName.isEmpty ? 'Sin carpeta seleccionada' : _rootName),
                    subtitle: _rootUri.isEmpty
                        ? null
                        : Text(_rootUri, maxLines: 2, overflow: TextOverflow.ellipsis),
                    trailing: OutlinedButton(
                      onPressed: _busy ? null : _pickRoot,
                      child: const Text('Elegir'),
                    ),
                  ),
                  const Divider(),""",
    """                  const Text(
                    'Elige cuánto almacenamiento puede exponer este teléfono al otro dispositivo emparejado.',
                  ),
                  const SizedBox(height: 12),
                  SegmentedButton<String>(
                    segments: const [
                      ButtonSegment(
                        value: 'folder',
                        icon: Icon(Icons.folder_outlined),
                        label: Text('Carpeta'),
                      ),
                      ButtonSegment(
                        value: 'all',
                        icon: Icon(Icons.folder_copy_outlined),
                        label: Text('Todo'),
                      ),
                    ],
                    selected: {_mode},
                    onSelectionChanged: _busy
                        ? null
                        : (value) {
                            if (value.isNotEmpty) _setMode(value.first);
                          },
                  ),
                  const SizedBox(height: 12),
                  if (_mode == 'folder')
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.folder_outlined),
                      title: Text(_rootName.isEmpty ? 'Sin carpeta seleccionada' : _rootName),
                      subtitle: _rootUri.isEmpty
                          ? const Text('Solo esta carpeta y su contenido serán visibles.')
                          : Text(_rootUri, maxLines: 2, overflow: TextOverflow.ellipsis),
                      trailing: OutlinedButton(
                        onPressed: _busy ? null : _pickRoot,
                        child: const Text('Elegir'),
                      ),
                    )
                  else
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: Icon(
                        _allFilesGranted ? Icons.verified_user_outlined : Icons.admin_panel_settings_outlined,
                      ),
                      title: Text(
                        _allFilesGranted
                            ? 'Acceso a almacenamiento concedido'
                            : 'Falta autorizar acceso completo',
                      ),
                      subtitle: const Text(
                        'Permite navegar Download, Documents, DCIM, Pictures y otras carpetas del almacenamiento compartido. Android puede seguir bloqueando zonas privadas de otras apps.',
                      ),
                      trailing: _allFilesGranted
                          ? const Icon(Icons.check_circle_outline)
                          : FilledButton(
                              onPressed: _busy ? null : _requestAllFilesAccess,
                              child: const Text('Autorizar'),
                            ),
                    ),
                  const Divider(),""",
    "host mode UI",
)

repl(
    """                  Text('Puerto: $_port'),
                  const SizedBox(height: 8),
                  const Text(
                    'En la misma Wi‑Fi usa una de las direcciones locales. Por Internet puedes usar una dirección privada de Tailscale/VPN; no hace falta abrir el router.',
                  ),""",
    """                  Text('Puerto: $_port'),
                  const SizedBox(height: 8),
                  Text(
                    _mode == 'all'
                        ? 'Modo: todo el almacenamiento compartido. El token sigue siendo obligatorio.'
                        : 'Modo: carpeta seleccionada.',
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'En la misma Wi‑Fi usa una de las direcciones locales. Por Internet puedes usar una dirección privada de Tailscale/VPN; no hace falta abrir el router.',
                  ),""",
    "mode summary",
)

p.write_text(s)
print("Full-storage bridge UI patch applied")
