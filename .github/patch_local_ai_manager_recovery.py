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
    "shouldRequestBatteryOptimizationsOff: false,",
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
main_new = """@pragma('vm:entry-point')
Future<void> sharedServiceMain() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ManagerSettings.ensureDefaults();
  _installSharedServiceChannel();
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ManagerSettings.ensureDefaults();
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
        final rawPrompt = (args['prompt'] ?? '').toString().trim();
        if (rawPrompt.isEmpty) {
          throw StateError('La pregunta está vacía.');
        }

        // Binder clients can send large app context (financial data, guides, etc.).
        // Keep the native llama context comfortably below 2048 tokens so the
        // Android process is not terminated by an oversized prompt.
        final prompt = rawPrompt.length <= 3000
            ? rawPrompt
            : '${rawPrompt.substring(0, 800)}\n\n'
                '[Contexto intermedio recortado para proteger la memoria]\n\n'
                '${rawPrompt.substring(rawPrompt.length - 2000)}';

        final rawSystem = (args['system'] ?? '').toString().trim();
        final system = rawSystem.length <= 600
            ? rawSystem
            : rawSystem.substring(0, 600);
        final rawMax = args['maxTokens'];
        final requestedMaxTokens = rawMax is num ? rawMax.toInt() : 320;
        final maxTokens = requestedMaxTokens.clamp(32, 256).toInt();
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
    "final threads = 2;",
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
    "contextSize: 1024,",
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


# Isolate the Manager UI from native llama crashes. The UI's own test/unload
# actions go through Binder into the :ai_engine process.
s = p.read_text()
if "com.angelapps.local_ai_manager/self_client" not in s:
    if "final SharedLlamaEngine sharedEngine = SharedLlamaEngine();" not in s:
        raise RuntimeError("shared engine global anchor not found")
    s = s.replace(
        "final SharedLlamaEngine sharedEngine = SharedLlamaEngine();",
        """final SharedLlamaEngine sharedEngine = SharedLlamaEngine();
const MethodChannel selfManagerChannel =
    MethodChannel('com.angelapps.local_ai_manager/self_client');""",
        1,
    )

old_test = """  Future<void> _testModel() async {
    setState(() => _busy = true);
    try {
      final text = await sharedEngine.generate(
        messages: [
          ChatMessage(role: 'user', content: 'Responde solamente: OK'),
        ],
        maxTokens: 24,
        temperature: 0.0,
      );
"""
new_test = """  Future<void> _testModel() async {
    setState(() => _busy = true);
    try {
      final text = (await selfManagerChannel
              .invokeMethod<String>('ask', {
                'prompt': 'Responde solamente: OK',
                'system': 'Prueba de estabilidad del motor local.',
                'maxTokens': 24,
                'temperature': 0.0,
              })
              .timeout(const Duration(minutes: 3))) ??
          '';
"""
if old_test not in s:
    raise RuntimeError("test model anchor not found")
s = s.replace(old_test, new_test, 1)

old_unload = """  Future<void> _unloadNow() async {
    await sharedEngine.unload();
    await _refreshStatus();
  }
"""
new_unload = """  Future<void> _unloadNow() async {
    try {
      await selfManagerChannel
          .invokeMethod<String>('unload')
          .timeout(const Duration(seconds: 20));
    } catch (_) {}
    await sharedEngine.unload();
    await _refreshStatus();
  }
"""
if old_unload not in s:
    raise RuntimeError("unload anchor not found")
s = s.replace(old_unload, new_unload, 1)

p.write_text(s)
print("Local AI Manager isolated-process UI bridge patch applied")

# Replace llama_flutter_android with llamadart's current native llama.cpp runtime.
# The previous plugin crashes the native process on this Android 16 device while
# loading Qwen2.5-1.5B Q4_K_M. Keep the isolated process, but change the engine.
s = p.read_text()
s = s.replace(
    "import 'package:llama_flutter_android/llama_flutter_android.dart';",
    "import 'package:llamadart/llamadart.dart';",
    1,
)

chat_anchor = "class EngineStatus {"
chat_class = """class ChatMessage {
  final String role;
  final String content;

  const ChatMessage({required this.role, required this.content});
}

"""
if "class ChatMessage {" not in s:
    if chat_anchor not in s:
        raise RuntimeError("EngineStatus anchor not found")
    s = s.replace(chat_anchor, chat_class + chat_anchor, 1)

start = s.find("class SharedLlamaEngine {")
end = s.find("class LocalAiServer {", start)
if start < 0 or end < 0:
    raise RuntimeError("SharedLlamaEngine boundaries not found")

new_engine = r"""class SharedLlamaEngine {
  LlamaEngine? _engine;
  String _loadedPath = '';
  bool _generating = false;
  String _acceleration = 'Sin cargar';
  DateTime? _lastUsed;
  int _requestCount = 0;
  Timer? _idleTimer;
  Future<void> _queue = Future<void>.value();

  bool get loaded => _engine != null;
  bool get generating => _generating;
  String get acceleration => _acceleration;
  DateTime? get lastUsed => _lastUsed;
  int get requestCount => _requestCount;

  Future<T> serial<T>(Future<T> Function() action) {
    final c = Completer<T>();
    _queue = _queue.then((_) async {
      try {
        c.complete(await action());
      } catch (e, st) {
        c.completeError(e, st);
      }
    }).catchError((_) {});
    return c.future;
  }

  Future<void> _validateModelFile(String path) async {
    final file = File(path);
    if (!await file.exists()) {
      throw StateError('No encuentro el archivo GGUF seleccionado.');
    }

    final length = await file.length();
    if (length < 64 * 1024 * 1024) {
      throw StateError(
        'El archivo GGUF parece incompleto (\${(length / 1024 / 1024).toStringAsFixed(1)} MB).',
      );
    }

    final handle = await file.open(mode: FileMode.read);
    try {
      final magic = await handle.read(4);
      if (magic.length != 4 ||
          magic[0] != 0x47 ||
          magic[1] != 0x47 ||
          magic[2] != 0x55 ||
          magic[3] != 0x46) {
        throw StateError(
          'El archivo seleccionado no tiene una cabecera GGUF válida.',
        );
      }
    } finally {
      await handle.close();
    }
  }

  Future<void> _ensureLoaded() async {
    final path = await ManagerSettings.modelPath();
    if (path.isEmpty) {
      throw StateError('No hay un modelo GGUF configurado en Local AI Manager.');
    }
    if (_engine != null && _loadedPath == path) return;

    await unload();
    await _validateModelFile(path);

    final engine = LlamaEngine(LlamaBackend());
    try {
      await engine.loadModel(
        path,
        modelParams: const ModelParams(
          contextSize: 1024,
          gpuLayers: 0,
          preferredBackend: GpuBackend.cpu,
          numberOfThreads: 2,
          numberOfThreadsBatch: 2,
          batchSize: 128,
          microBatchSize: 64,
          useMmap: true,
          useMlock: false,
          flashAttention: FlashAttention.disabled,
        ),
      );

      _engine = engine;
      _loadedPath = path;
      _acceleration = 'CPU • llamadart/llama.cpp • 2 hilos';
    } catch (_) {
      try {
        await engine.dispose();
      } catch (_) {}
      rethrow;
    }
  }

  LlamaChatRole _role(String role) {
    switch (role) {
      case 'system':
        return LlamaChatRole.system;
      case 'assistant':
        return LlamaChatRole.assistant;
      default:
        return LlamaChatRole.user;
    }
  }

  Future<String> generate({
    required List<ChatMessage> messages,
    required int maxTokens,
    required double temperature,
  }) {
    return serial(() async {
      await _ensureLoaded();
      final engine = _engine!;
      _generating = true;
      _idleTimer?.cancel();
      final out = StringBuffer();

      final llamaMessages = messages
          .map(
            (m) => LlamaChatMessage.fromText(
              role: _role(m.role),
              text: m.content,
            ),
          )
          .toList(growable: false);

      try {
        await for (final chunk in engine.create(
          llamaMessages,
          params: GenerationParams(
            maxTokens: maxTokens.clamp(16, 256).toInt(),
            temp: temperature.clamp(0.0, 2.0).toDouble(),
            topP: 0.9,
            topK: 40,
            penalty: 1.05,
          ),
          enableThinking: false,
        )) {
          if (chunk.choices.isEmpty) continue;
          final text = chunk.choices.first.delta.content;
          if (text != null && text.isNotEmpty) out.write(text);
        }

        _requestCount++;
        _lastUsed = DateTime.now();
        return out.toString().trim();
      } finally {
        _generating = false;
        _scheduleUnload();
      }
    });
  }

  Future<void> stop() async {
    try {
      _engine?.cancelGeneration();
    } catch (_) {}
  }

  Future<void> unload() async {
    _idleTimer?.cancel();
    _idleTimer = null;
    final current = _engine;
    _engine = null;
    _loadedPath = '';
    _acceleration = 'Sin cargar';
    if (current != null) {
      try {
        current.cancelGeneration();
      } catch (_) {}
      try {
        await current.dispose();
      } catch (_) {}
    }
  }

  Future<void> _scheduleUnload() async {
    _idleTimer?.cancel();
    final seconds = await ManagerSettings.idleSeconds();
    _idleTimer = Timer(Duration(seconds: seconds), () async {
      if (!_generating) await unload();
    });
  }
}

"""
s = s[:start] + new_engine + s[end:]
s = s.replace("import 'dart:math';\n", "", 1)
p.write_text(s)
print("Local AI Manager llamadart runtime patch applied")

# Remove the temporary diagnostic limits now that the stable llamadart runtime
# is in place. Keep the isolated :ai_engine process, but restore full prompts,
# model-selected context behavior, all CPU threads, and optional Vulkan.
s = p.read_text()

old_prompt = """        final prompt = rawPrompt.length <= 3000
            ? rawPrompt
            : '${rawPrompt.substring(0, 800)}\n\n'
                '[Contexto intermedio recortado para proteger la memoria]\n\n'
                '${rawPrompt.substring(rawPrompt.length - 2000)}';

        final rawSystem = (args['system'] ?? '').toString().trim();
        final system = rawSystem.length <= 600
            ? rawSystem
            : rawSystem.substring(0, 600);
        final rawMax = args['maxTokens'];
        final requestedMaxTokens = rawMax is num ? rawMax.toInt() : 320;
        final maxTokens = requestedMaxTokens.clamp(32, 256).toInt();
"""
new_prompt = """        final prompt = rawPrompt;
        final system = (args['system'] ?? '').toString().trim();
        final rawMax = args['maxTokens'];
        final requestedMaxTokens = rawMax is num ? rawMax.toInt() : 4096;
        final maxTokens = requestedMaxTokens > 0 ? requestedMaxTokens : 4096;
"""
if old_prompt not in s:
    raise RuntimeError("diagnostic prompt cap anchor not found")
s = s.replace(old_prompt, new_prompt, 1)

# Stop forcibly resetting GPU preference on every launch.
s = s.replace("    await p.setBool(_gpu, false);\n", "", 1)

old_load = """    final engine = LlamaEngine(LlamaBackend());
    try {
      await engine.loadModel(
        path,
        modelParams: const ModelParams(
          contextSize: 1024,
          gpuLayers: 0,
          preferredBackend: GpuBackend.cpu,
          numberOfThreads: 2,
          numberOfThreadsBatch: 2,
          batchSize: 128,
          microBatchSize: 64,
          useMmap: true,
          useMlock: false,
          flashAttention: FlashAttention.disabled,
        ),
      );

      _engine = engine;
      _loadedPath = path;
      _acceleration = 'CPU • llamadart/llama.cpp • 2 hilos';
"""
new_load = """    final useGpu = await ManagerSettings.useGpu();
    final threads = Platform.numberOfProcessors;
    final engine = LlamaEngine(LlamaBackend());
    try {
      await engine.loadModel(
        path,
        modelParams: ModelParams(
          contextSize: 0,
          gpuLayers: useGpu ? 99 : 0,
          preferredBackend:
              useGpu ? GpuBackend.vulkan : GpuBackend.cpu,
          numberOfThreads: threads,
          numberOfThreadsBatch: threads,
          useMmap: true,
          useMlock: false,
        ),
      );

      _engine = engine;
      _loadedPath = path;
      _acceleration = useGpu
          ? 'GPU/Vulkan • llamadart/llama.cpp'
          : 'CPU • llamadart/llama.cpp • ${threads} hilos';
"""
if old_load not in s:
    raise RuntimeError("llamadart safe load anchor not found")
s = s.replace(old_load, new_load, 1)

s = s.replace(
    "            maxTokens: maxTokens.clamp(16, 256).toInt(),",
    "            maxTokens: maxTokens > 0 ? maxTokens : 4096,",
    1,
)

old_switch = """                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          value: false,
                          title: const Text('GPU/Vulkan'),
                          subtitle: const Text(
                            'Desactivado en modo seguro. El modelo usa CPU para evitar cierres del proceso.',
                          ),
                          onChanged: null,
                        ),
"""
new_switch = """                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          value: _gpu,
                          title: const Text('GPU/Vulkan'),
                          subtitle: const Text(
                            'Opcional. Actívalo para descargar capas del modelo a Vulkan. CPU sigue siendo el modo predeterminado.',
                          ),
                          onChanged: _busy
                              ? null
                              : (v) async {
                                  try {
                                    await selfManagerChannel
                                        .invokeMethod<String>('unload')
                                        .timeout(const Duration(seconds: 20));
                                  } catch (_) {}
                                  await sharedEngine.unload();
                                  await ManagerSettings.setGpu(v);
                                  if (mounted) setState(() => _gpu = v);
                                  await _refreshStatus();
                                },
                        ),
"""
if old_switch not in s:
    raise RuntimeError("disabled GPU switch anchor not found")
s = s.replace(old_switch, new_switch, 1)

p.write_text(s)
print("Local AI Manager diagnostic limits removed; Vulkan toggle restored")


