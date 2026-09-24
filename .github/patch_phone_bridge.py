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
