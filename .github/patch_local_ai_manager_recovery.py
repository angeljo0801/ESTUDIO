from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()

s = s.replace(
    "class LocalAiServer {\n  final SharedLlamaEngine engine;\n  HttpServer? _server;\n  String? lastError;",
    "class LocalAiServer {\n  final SharedLlamaEngine engine;\n  HttpServer? _server;\n  StreamSubscription<HttpRequest>? _subscription;\n  String? lastError;",
)

old = """  bool get running => _server != null;

  Future<void> start() async {
    if (_server != null) return;
    final port = await ManagerSettings.port();
    try {
      _server = await HttpServer.bind(InternetAddress.loopbackIPv4, port);
      _server!.listen(_handle, onError: (Object e) => lastError = e.toString());
      lastError = null;
    } catch (e) {
      lastError = e.toString();
      rethrow;
    }
  }

  Future<void> stop() async {
    await _server?.close(force: true);
    _server = null;
    await engine.unload();
  }
"""
new = """  bool get running => _server != null;

  Future<bool> isReachable() async {
    final port = await ManagerSettings.port();
    Socket? socket;
    try {
      socket = await Socket.connect(
        InternetAddress.loopbackIPv4,
        port,
        timeout: const Duration(milliseconds: 600),
      );
      return true;
    } catch (_) {
      return false;
    } finally {
      socket?.destroy();
    }
  }

  Future<void> start() async {
    if (_server != null && await isReachable()) return;
    await _closeServerOnly();
    final port = await ManagerSettings.port();
    try {
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, port);
      _server = server;
      _subscription = server.listen(
        _handle,
        onError: (Object e) {
          lastError = e.toString();
        },
        onDone: () {
          _server = null;
          _subscription = null;
        },
        cancelOnError: false,
      );
      lastError = null;
    } catch (e) {
      _server = null;
      _subscription = null;
      lastError = e.toString();
      rethrow;
    }
  }

  Future<void> ensureAlive() async {
    if (await isReachable()) return;
    try {
      await start();
    } catch (_) {}
  }

  Future<void> _closeServerOnly() async {
    try {
      await _subscription?.cancel();
    } catch (_) {}
    _subscription = null;
    try {
      await _server?.close(force: true);
    } catch (_) {}
    _server = null;
  }

  Future<void> stop() async {
    await _closeServerOnly();
    await engine.unload();
  }
"""
if old not in s:
    raise RuntimeError("LocalAiServer lifecycle anchor not found")
s = s.replace(old, new, 1)

s = s.replace(
    "if (request.method == 'GET' && (path == '/health' || path == '/status')) {",
    "if (request.method == 'GET' && (path == '/health' || path == '/status' || path == '/v1/health')) {",
    1,
)

old = """  Future<void> _refreshStatus() async {
    if (!mounted) return;
    final status = EngineStatus(
      serverRunning: localServer.running,
"""
new = """  Future<void> _refreshStatus() async {
    if (!mounted) return;
    await localServer.ensureAlive();
    final reachable = await localServer.isReachable();
    final status = EngineStatus(
      serverRunning: reachable,
"""
if old not in s:
    raise RuntimeError("status refresh anchor not found")
s = s.replace(old, new, 1)

p.write_text(s)
print("Local AI Manager recovery patch applied")


# Keep the Flutter isolate and localhost server alive while Memora/Finanzas
# are in the foreground. On Android/Samsung this requires opting out of Doze.
s = p.read_text()
s = s.replace(
    "shouldRequestBatteryOptimizationsOff: false,",
    "shouldRequestBatteryOptimizationsOff: true,\n      enableWifiLock: true,",
    1,
)
p.write_text(s)
print("Local AI Manager battery/background persistence patch applied")
