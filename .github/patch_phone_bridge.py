from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()

if "import 'phone_bridge.dart';" not in s:
    anchor = "import 'manager_backup.dart';"
    if anchor not in s:
        raise RuntimeError("manager_backup.dart import anchor not found")
    s = s.replace(anchor, anchor + "\nimport 'phone_bridge.dart';", 1)

main_old = """Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ManagerSettings.ensureDefaults();
  runApp(const LocalAiManagerApp());
  try {
    await ManagerBackupService.autoBackupIfDue();
  } catch (_) {}
}
"""
main_new = """Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ManagerSettings.ensureDefaults();
  try {
    await PhoneBridgeService.autoStart();
  } catch (_) {}
  runApp(const LocalAiManagerApp());
  try {
    await ManagerBackupService.autoBackupIfDue();
  } catch (_) {}
}
"""
if main_old in s:
    s = s.replace(main_old, main_new, 1)
elif "await PhoneBridgeService.autoStart();" not in s:
    raise RuntimeError("main() anchor not found for phone bridge")

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
                builder: (_) => const PhoneBridgePage(),
              ),
            ),
            icon: const Icon(Icons.phonelink),
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
elif "builder: (_) => const PhoneBridgePage()," not in s:
    raise RuntimeError("Local AI Manager AppBar anchor not found")

s = s.replace(
    "notificationText: 'Compartiendo el modelo local con tus APKs',",
    "notificationText: 'IA local y puente de archivos disponibles',",
    1,
)

p.write_text(s)
print("Local AI Manager phone-to-phone file bridge patch applied")
