from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()

if "import 'file_bridge.dart';" not in s:
    anchor = "import 'manager_backup.dart';"
    if anchor not in s:
        raise RuntimeError("manager_backup.dart import anchor not found")
    s = s.replace(anchor, anchor + "\nimport 'file_bridge.dart';", 1)

appbar_old = """      appBar: AppBar(
        title: const Text('Local AI Manager'),
        actions: [
          IconButton(
            tooltip: 'Copias de seguridad',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => const ManagerBackupPage(),
              ),
            ),
            icon: const Icon(Icons.backup_outlined),
          ),
        ],
      ),"""
appbar_new = """      appBar: AppBar(
        title: const Text('Local AI Manager'),
        actions: [
          IconButton(
            tooltip: 'Puente de archivos',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => const FileBridgePage(),
              ),
            ),
            icon: const Icon(Icons.swap_horiz),
          ),
          IconButton(
            tooltip: 'Copias de seguridad',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => const ManagerBackupPage(),
              ),
            ),
            icon: const Icon(Icons.backup_outlined),
          ),
        ],
      ),"""
if appbar_old in s:
    s = s.replace(appbar_old, appbar_new, 1)
elif "builder: (_) => const FileBridgePage()," not in s:
    backup_button = """          IconButton(
            tooltip: 'Copias de seguridad',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => const ManagerBackupPage(),
              ),
            ),
            icon: const Icon(Icons.backup_outlined),
          ),"""
    bridge_button = """          IconButton(
            tooltip: 'Puente de archivos',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => const FileBridgePage(),
              ),
            ),
            icon: const Icon(Icons.swap_horiz),
          ),
"""
    if backup_button not in s:
        raise RuntimeError("Local AI Manager AppBar backup anchor not found")
    s = s.replace(backup_button, bridge_button + backup_button, 1)

p.write_text(s)
print("Local AI Manager persistent file bridge UI patch applied")


# Remote screen: use the upstream VNC server and its browser viewer.
# The host starts screen sharing locally and grants Android's normal permissions.
# Never expose VNC to a public Internet address or pass credentials in a URL.
remote_page = r"""
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class RemoteScreenPage extends StatefulWidget {
  const RemoteScreenPage({super.key});

  @override
  State<RemoteScreenPage> createState() => _RemoteScreenPageState();
}

class _RemoteScreenPageState extends State<RemoteScreenPage> {
  final _address = TextEditingController();

  @override
  void dispose() {
    _address.dispose();
    super.dispose();
  }

  Uri? _privateViewerUri(String value) {
    final uri = Uri.tryParse(value.trim());
    if (uri == null ||
        !['http', 'https'].contains(uri.scheme) ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment ||
        uri.host.isEmpty) {
      return null;
    }
    final parts = uri.host.split('.');
    if (parts.length != 4) return null;
    final nums = parts.map(int.tryParse).toList();
    if (nums.any((n) => n == null || n < 0 || n > 255)) return null;
    // Only Tailscale CGNAT addresses; no public or forwarded VNC endpoints.
    if (nums[0] != 100 || nums[1]! < 64 || nums[1]! > 127) return null;
    if (!uri.hasPort || uri.port < 1 || uri.port > 65535) return null;
    return uri;
  }

  Future<void> _open(Uri uri) async {
    try {
      final opened = await const MethodChannel(
        'com.angelapps.local_ai_manager/file_bridge',
      ).invokeMethod<bool>('openScreenViewer', {'url': uri.toString()});
      if (opened != true) {
        throw StateError('No browser available');
      }
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No se pudo abrir el enlace.')),
      );
    }
  }

  Future<void> _connect() async {
    final uri = _privateViewerUri(_address.text);
    if (uri == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Introduce la URL del visor con una IP privada de Tailscale y su puerto. No incluyas contraseña ni parámetros.')),
      );
      return;
    }
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Conectar a tu dispositivo'),
        content: const Text('Confirma que el teléfono es tuyo o que tienes permiso de su propietario, que ambos están en tu red privada de Tailscale y que el host inició la sesión de pantalla. La contraseña se introduce únicamente en el visor.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Conectar')),
        ],
      ),
    );
    if (accepted == true && mounted) await _open(uri);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Pantalla remota')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Teléfono host', style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 8),
                  const Text('Instala droidVNC-NG en tu propio teléfono remoto. Conecta ambos teléfonos a tu red privada de Tailscale. Configura una contraseña, inicia la sesión localmente y concede los permisos que Android solicite.'),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: () => _open(Uri.parse('https://play.google.com/store/apps/details?id=net.christianbeier.droidvnc_ng')),
                    icon: const Icon(Icons.install_mobile),
                    label: const Text('Abrir droidVNC-NG en Google Play'),
                  ),
                  OutlinedButton.icon(
                    onPressed: () => _open(Uri.parse('https://play.google.com/store/apps/details?id=com.tailscale.ipn')),
                    icon: const Icon(Icons.vpn_key_outlined),
                    label: const Text('Abrir Tailscale en Google Play'),
                  ),
                  const Text('El host debe mantener visible la notificación de pantalla compartida. Puedes detener la sesión desde droidVNC-NG.'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Conectar al host', style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 8),
                  const Text('Usa el enlace del visor web noVNC que muestra droidVNC-NG, sustituyendo su dirección por la IP de Tailscale del host si es necesario.'),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _address,
                    keyboardType: TextInputType.url,
                    autocorrect: false,
                    enableSuggestions: false,
                    decoration: const InputDecoration(
                      labelText: 'URL privada del visor',
                      hintText: 'http://100.x.x.x:puerto/',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: _connect,
                    icon: const Icon(Icons.phonelink),
                    label: const Text('Abrir pantalla remota'),
                  ),
                  const Text('El visor externo permite interactuar si el host autorizó el control. No guardamos contraseñas.'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          const ListTile(
            leading: Icon(Icons.security),
            title: Text('Seguridad'),
            subtitle: Text('No abras puertos del router ni uses VNC sobre Internet público. Android puede pedir una nueva autorización al bloquear o reiniciar el teléfono. No se garantiza acceso desatendido.'),
          ),
        ],
      ),
    );
  }
}
"""
(p.parent / "remote_screen.dart").write_text(remote_page.lstrip(), encoding="utf-8")
s = p.read_text()
if "import 'remote_screen.dart';" not in s:
    s = s.replace("import 'file_bridge.dart';", "import 'file_bridge.dart';\nimport 'remote_screen.dart';", 1)
if "const RemoteScreenPage()" not in s:
    anchor = """          IconButton(
            tooltip: 'Puente de archivos',"""
    button = """          IconButton(
            tooltip: 'Pantalla remota',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const RemoteScreenPage()),
            ),
            icon: const Icon(Icons.phonelink),
          ),
"""
    if anchor not in s:
        raise RuntimeError("Remote screen AppBar anchor not found")
    s = s.replace(anchor, button + anchor, 1)
p.write_text(s)
print("Local AI Manager remote screen launcher added")
