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


# Add the headless Dart entrypoint used by the exported Android Binder service.
s = p.read_text()
if "import 'dart:ui';" not in s:
    s = s.replace("import 'dart:math';", "import 'dart:math';\nimport 'dart:ui';", 1)
if "package:flutter/services.dart" not in s:
    s = s.replace(
        "import 'package:flutter/material.dart';",
        "import 'package:flutter/material.dart';\nimport 'package:flutter/services.dart';",
        1,
    )

entrypoint = r"""
@pragma('vm:entry-point')
Future<void> managerServiceMain() async {
  WidgetsFlutterBinding.ensureInitialized();
  DartPluginRegistrant.ensureInitialized();
  await ManagerSettings.ensureDefaults();

  const channel = MethodChannel(
    'com.angelapps.local_ai_manager/service_engine',
  );

  channel.setMethodCallHandler((call) async {
    switch (call.method) {
      case 'ask':
        final args = Map<String, dynamic>.from(
          (call.arguments as Map?) ?? const <String, dynamic>{},
        );
        final prompt = (args['prompt'] ?? '').toString().trim();
        if (prompt.isEmpty) {
          throw StateError('La pregunta está vacía.');
        }
        final system = (args['system'] ?? '').toString().trim();
        final rawMax = args['maxTokens'];
        final maxTokens = rawMax is num ? rawMax.toInt() : 320;
        final rawTemp = args['temperature'];
        final temperature = rawTemp is num ? rawTemp.toDouble() : 0.2;

        final messages = <ChatMessage>[
          if (system.isNotEmpty)
            ChatMessage(role: 'system', content: system),
          ChatMessage(role: 'user', content: prompt),
        ];

        final answer = await sharedEngine.generate(
          messages: messages,
          maxTokens: maxTokens,
          temperature: temperature,
        );

        final prefs = await SharedPreferences.getInstance();
        await prefs.setInt(
          'manager_service_requests',
          (prefs.getInt('manager_service_requests') ?? 0) + 1,
        );
        await prefs.setBool('manager_service_model_loaded', sharedEngine.loaded);
        await prefs.setString(
          'manager_service_acceleration',
          sharedEngine.acceleration,
        );
        await prefs.setString(
          'manager_service_last_used',
          DateTime.now().toIso8601String(),
        );
        return answer;

      case 'unload':
        await sharedEngine.unload();
        final prefs = await SharedPreferences.getInstance();
        await prefs.setBool('manager_service_model_loaded', false);
        await prefs.setString('manager_service_acceleration', 'Sin cargar');
        return true;

      case 'status':
        final prefs = await SharedPreferences.getInstance();
        return <String, dynamic>{
          'loaded': sharedEngine.loaded,
          'generating': sharedEngine.generating,
          'acceleration': sharedEngine.acceleration,
          'requests': prefs.getInt('manager_service_requests') ?? 0,
          'model': await ManagerSettings.modelName(),
        };

      default:
        throw MissingPluginException(
          'Método no soportado: ${call.method}',
        );
    }
  });

  await channel.invokeMethod('ready');
}
"""

if "Future<void> managerServiceMain()" not in s:
    s += "\n" + entrypoint + "\n"

old_status = """  Future<void> _refreshStatus() async {
    if (!mounted) return;
    await localServer.ensureAlive();
    final reachable = await localServer.isReachable();
    final status = EngineStatus(
      serverRunning: reachable,
      modelLoaded: sharedEngine.loaded,
      generating: sharedEngine.generating,
      modelName: await ManagerSettings.modelName(),
      acceleration: sharedEngine.acceleration,
      rssMb: await processRssMb(),
      requestCount: sharedEngine.requestCount,
      lastUsed: sharedEngine.lastUsed,
      error: localServer.lastError,
    );
"""
new_status = """  Future<void> _refreshStatus() async {
    if (!mounted) return;
    await localServer.ensureAlive();
    final reachable = await localServer.isReachable();
    final prefs = await SharedPreferences.getInstance();
    final serviceLoaded =
        prefs.getBool('manager_service_model_loaded') ?? false;
    final serviceRequests =
        prefs.getInt('manager_service_requests') ?? 0;
    final serviceAcceleration =
        prefs.getString('manager_service_acceleration') ?? 'Sin cargar';
    final rawServiceLast =
        prefs.getString('manager_service_last_used') ?? '';
    final serviceLast = DateTime.tryParse(rawServiceLast);
    final status = EngineStatus(
      serverRunning: reachable,
      modelLoaded: sharedEngine.loaded || serviceLoaded,
      generating: sharedEngine.generating,
      modelName: await ManagerSettings.modelName(),
      acceleration: sharedEngine.loaded
          ? sharedEngine.acceleration
          : serviceAcceleration,
      rssMb: await processRssMb(),
      requestCount: sharedEngine.requestCount + serviceRequests,
      lastUsed: sharedEngine.lastUsed ?? serviceLast,
      error: localServer.lastError,
    );
"""
if old_status in s:
    s = s.replace(old_status, new_status, 1)

p.write_text(s)
print("Local AI Manager Binder Dart entrypoint patch applied")
