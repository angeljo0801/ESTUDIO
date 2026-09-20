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


# Install Binder MethodChannel on the same main FlutterEngine used by the UI.
s = p.read_text()
if "package:flutter/services.dart" not in s:
    s = s.replace(
        "import 'package:flutter/material.dart';",
        "import 'package:flutter/material.dart';\nimport 'package:flutter/services.dart';",
        1,
    )

main_old = """Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ManagerSettings.ensureDefaults();
  runApp(const LocalAiManagerApp());
}
"""
main_new = """Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ManagerSettings.ensureDefaults();
  _installSharedServiceChannel();
  runApp(const LocalAiManagerApp());
}
"""
if main_old not in s:
    raise RuntimeError("Manager main() anchor not found")
s = s.replace(main_old, main_new, 1)

channel_code = r"""
void _installSharedServiceChannel() {
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

        return sharedEngine.generate(
          messages: messages,
          maxTokens: maxTokens,
          temperature: temperature,
        );

      case 'unload':
        await sharedEngine.unload();
        return 'OK';

      case 'status':
        return <String, dynamic>{
          'loaded': sharedEngine.loaded,
          'generating': sharedEngine.generating,
          'acceleration': sharedEngine.acceleration,
          'requests': sharedEngine.requestCount,
          'model': await ManagerSettings.modelName(),
        };

      default:
        throw MissingPluginException(
          'Método no soportado: ${call.method}',
        );
    }
  });

  // This may run before the Android Service exists; that is harmless because
  // the native service also retries until the Dart handler is ready.
  channel.invokeMethod('ready').catchError((_) {});
}
"""

insert_before = "class LocalAiManagerApp extends StatelessWidget {"
if channel_code.strip() not in s:
    if insert_before not in s:
        raise RuntimeError("LocalAiManagerApp anchor not found")
    s = s.replace(insert_before, channel_code + "\n" + insert_before, 1)

p.write_text(s)
print("Local AI Manager single-engine Binder channel patch applied")


# Force a conservative CPU-only inference profile. Some Android/Vulkan drivers
# can terminate the native llama process when the first model load starts.
s = p.read_text()

s = s.replace(
    "final threads = max(2, min(8, Platform.numberOfProcessors - 2));",
    "final threads = max(2, min(4, Platform.numberOfProcessors - 2));",
    1,
)

gpu_block = """    var gpuLayers = 0;
    var gpuName = '';
    if (await ManagerSettings.useGpu()) {
      try {
        final gpu = await controller.detectGpu();
        if (gpu.vulkanSupported) {
          gpuLayers = gpu.recommendedGpuLayers;
          gpuName = gpu.gpuName;
        }
      } catch (_) {
        gpuLayers = 0;
      }
    }
"""
cpu_block = """    const gpuLayers = 0;
    const gpuName = '';
"""
if gpu_block not in s:
    raise RuntimeError("GPU inference block not found")
s = s.replace(gpu_block, cpu_block, 1)

s = s.replace(
    "contextSize: 4096,",
    "contextSize: 2048,",
    1,
)

# Existing installations can have manager_gpu=true saved from an older version.
# Reset it so the UI and persisted state agree with safe CPU mode.
defaults_anchor = """  static Future<void> ensureDefaults() async {
    final p = await SharedPreferences.getInstance();
"""
defaults_replacement = """  static Future<void> ensureDefaults() async {
    final p = await SharedPreferences.getInstance();
    await p.setBool(_gpu, false);
"""
if defaults_anchor not in s:
    raise RuntimeError("ManagerSettings.ensureDefaults anchor not found")
s = s.replace(defaults_anchor, defaults_replacement, 1)

old_switch = """                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          value: _gpu,
                          title: const Text('Usar GPU/Vulkan'),
                          subtitle: const Text('Desactivado por defecto para máxima estabilidad.'),
                          onChanged: (v) async {
                            await sharedEngine.unload();
                            await ManagerSettings.setGpu(v);
                            setState(() => _gpu = v);
                          },
                        ),
"""
new_switch = """                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          value: false,
                          title: const Text('GPU/Vulkan'),
                          subtitle: const Text(
                            'Desactivado en modo seguro. El modelo usa CPU para evitar cierres del proceso.',
                          ),
                          onChanged: null,
                        ),
"""
if old_switch not in s:
    raise RuntimeError("GPU switch block not found")
s = s.replace(old_switch, new_switch, 1)

p.write_text(s)
print("Local AI Manager safe CPU inference patch applied")
