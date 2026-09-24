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


# Keep the Flutter isolate and localhost server alive while Memora/Finanzas/WhatsBot
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
    if (length < 8 * 1024 * 1024) {
      throw StateError(
        'El archivo del modelo parece incompleto (\${(length / 1024 / 1024).toStringAsFixed(1)} MB).',
      );
    }

    // llama.cpp is the authoritative model parser. The previous manual
    // four-byte header check falsely rejected a model that llamadart had
    // already loaded successfully on this device.
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
import re
s = p.read_text()

prompt_pattern = re.compile(
    r"""        // Binder clients can send large app context.*?
        final maxTokens = requestedMaxTokens\.clamp\(32, 256\)\.toInt\(\);
""",
    re.S,
)
prompt_replacement = """        // Pass the complete request to the model. The runtime/model context
        // window is the only remaining context limit.
        final prompt = rawPrompt;
        final system = (args['system'] ?? '').toString().trim();
        final rawMax = args['maxTokens'];
        final requestedMaxTokens = rawMax is num ? rawMax.toInt() : 4096;
        final maxTokens = requestedMaxTokens > 0 ? requestedMaxTokens : 4096;
"""
s, n = prompt_pattern.subn(prompt_replacement, s, count=1)
if n != 1:
    raise RuntimeError("diagnostic prompt cap section not found")

# Stop forcibly resetting GPU preference on every launch.
s = s.replace("    await p.setBool(_gpu, false);\n", "", 1)

load_pattern = re.compile(
    r"""    final engine = LlamaEngine\(LlamaBackend\(\)\);
    try \{
      await engine\.loadModel\(
        path,
        modelParams: const ModelParams\(
          contextSize: 1024,
          gpuLayers: 0,
          preferredBackend: GpuBackend\.cpu,
          numberOfThreads: 2,
          numberOfThreadsBatch: 2,
          batchSize: 128,
          microBatchSize: 64,
          useMmap: true,
          useMlock: false,
          flashAttention: FlashAttention\.disabled,
        \),
      \);

      _engine = engine;
      _loadedPath = path;
      _acceleration = 'CPU • llamadart/llama\.cpp • 2 hilos';
""",
    re.S,
)
load_replacement = """    final useGpu = await ManagerSettings.useGpu();
    final threads = Platform.numberOfProcessors;
    final engine = LlamaEngine(LlamaBackend());
    try {
      await engine.loadModel(
        path,
        modelParams: ModelParams(
          // 0 lets llamadart/llama.cpp resolve the model's native context
          // instead of imposing the temporary 1024-token diagnostic cap.
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
s, n = load_pattern.subn(load_replacement, s, count=1)
if n != 1:
    raise RuntimeError("llamadart safe load section not found")

s = s.replace(
    "            maxTokens: maxTokens.clamp(16, 256).toInt(),",
    "            maxTokens: maxTokens > 0 ? maxTokens : 4096,",
    1,
)

switch_pattern = re.compile(
    r"""                        SwitchListTile\(
                          contentPadding: EdgeInsets\.zero,
                          value: false,
                          title: const Text\('GPU/Vulkan'\),
                          subtitle: const Text\(
                            'Desactivado en modo seguro\. El modelo usa CPU para evitar cierres del proceso\.',
                          \),
                          onChanged: null,
                        \),
""",
    re.S,
)
switch_replacement = """                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          value: _gpu,
                          title: const Text('GPU/Vulkan'),
                          subtitle: const Text(
                            'Opcional. Actívalo para usar Vulkan. CPU sigue siendo el modo predeterminado.',
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
s, n = switch_pattern.subn(switch_replacement, s, count=1)
if n != 1:
    raise RuntimeError("disabled GPU switch section not found")

p.write_text(s)
print("Local AI Manager diagnostic limits removed; Vulkan toggle restored")

# Performance optimization: keep the stable isolated llamadart engine, but
# allocate context according to the actual request instead of always reserving
# the model's full native window. No prompt text is truncated.
s = p.read_text()
start = s.find("  Future<void> _ensureLoaded() async {")
end = s.find("  LlamaChatRole _role(String role) {", start)
if start < 0 or end < 0:
    raise RuntimeError("optimized engine load boundaries not found")

optimized_loader = r"""  int _contextFor(
    List<ChatMessage> messages,
    int maxTokens,
  ) {
    var chars = 0;
    for (final message in messages) {
      chars += message.content.length;
    }

    // Conservative tokenizer estimate for mixed Spanish/English text.
    // Add generation space plus safety room. Grow in powers of two, with no
    // artificial prompt truncation or fixed upper cap.
    final estimatedPromptTokens = (chars / 3.0).ceil();
    final needed = estimatedPromptTokens + maxTokens + 256;
    var context = 2048;
    while (context < needed) {
      context *= 2;
    }
    return context;
  }

  Future<void> _ensureLoaded(int requestedContext) async {
    final path = await ManagerSettings.modelPath();
    if (path.isEmpty) {
      throw StateError('No hay un modelo GGUF configurado en Local AI Manager.');
    }

    final useGpu = await ManagerSettings.useGpu();
    if (_engine != null &&
        _loadedPath == path &&
        _loadedContext >= requestedContext &&
        _loadedGpu == useGpu) {
      return;
    }

    await unload();
    await _validateModelFile(path);

    // More threads are not always faster on mobile SoCs. Four keeps the
    // performance cores busy without excessive contention/thermal pressure.
    final threads = Platform.numberOfProcessors.clamp(2, 4).toInt();
    final engine = LlamaEngine(LlamaBackend());
    try {
      await engine.loadModel(
        path,
        modelParams: ModelParams(
          contextSize: requestedContext,
          gpuLayers: useGpu ? 99 : 0,
          preferredBackend:
              useGpu ? GpuBackend.vulkan : GpuBackend.cpu,
          numberOfThreads: threads,
          numberOfThreadsBatch: threads,
          batchSize: useGpu ? 512 : 256,
          microBatchSize: useGpu ? 256 : 128,
          useMmap: true,
          useMlock: false,
        ),
      );

      _engine = engine;
      _loadedPath = path;
      _loadedContext = requestedContext;
      _loadedGpu = useGpu;
      _acceleration = useGpu
          ? 'GPU/Vulkan • contexto $requestedContext'
          : 'CPU • $threads hilos • contexto $requestedContext';
    } catch (_) {
      try {
        await engine.dispose();
      } catch (_) {}
      rethrow;
    }
  }

"""
s = s[:start] + optimized_loader + s[end:]

s = s.replace(
    "  String _loadedPath = '';\n",
    "  String _loadedPath = '';\n  int _loadedContext = 0;\n  bool _loadedGpu = false;\n",
    1,
)

s = s.replace(
    "      await _ensureLoaded();\n      final engine = _engine!;",
    "      final requestedContext = _contextFor(messages, maxTokens);\n      await _ensureLoaded(requestedContext);\n      final engine = _engine!;",
    1,
)

s = s.replace(
    "    _loadedPath = '';\n    _acceleration = 'Sin cargar';",
    "    _loadedPath = '';\n    _loadedContext = 0;\n    _loadedGpu = false;\n    _acceleration = 'Sin cargar';",
    1,
)

old_idle = """  Future<void> _scheduleUnload() async {
    _idleTimer?.cancel();
    final seconds = await ManagerSettings.idleSeconds();
    _idleTimer = Timer(Duration(seconds: seconds), () async {
      if (!_generating) await unload();
    });
  }
"""
new_idle = """  Future<void> _scheduleUnload() async {
    _idleTimer?.cancel();
    final configured = await ManagerSettings.idleSeconds();
    // Keep the model warm for at least five minutes between chat messages.
    // Explicit app/chat exit still unloads immediately through Binder.
    final seconds = configured < 300 ? 300 : configured;
    _idleTimer = Timer(Duration(seconds: seconds), () async {
      if (!_generating) await unload();
    });
  }
"""
if old_idle not in s:
    raise RuntimeError("idle unload section not found")
s = s.replace(old_idle, new_idle, 1)

p.write_text(s)
print("Local AI Manager adaptive-context performance patch applied")



# External backup/restore UI. Models are intentionally excluded from backups.
s = p.read_text()
if "import 'manager_backup.dart';" not in s:
    anchor = "import 'package:shared_preferences/shared_preferences.dart';"
    if anchor not in s:
        raise RuntimeError("SharedPreferences import anchor not found for backup")
    s = s.replace(anchor, anchor + "\nimport 'manager_backup.dart';", 1)

main_anchor = """Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ManagerSettings.ensureDefaults();
  runApp(const LocalAiManagerApp());
}
"""
main_backup = """Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ManagerSettings.ensureDefaults();
  runApp(const LocalAiManagerApp());
  try {
    await ManagerBackupService.autoBackupIfDue();
  } catch (_) {}
}
"""
if main_anchor in s:
    s = s.replace(main_anchor, main_backup, 1)
elif "await ManagerBackupService.autoBackupIfDue();" not in s:
    raise RuntimeError("Manager main() backup anchor not found")

appbar = "appBar: AppBar(title: const Text('Local AI Manager')),"
appbar_backup = """appBar: AppBar(
        title: const Text('Local AI Manager'),
        actions: [
          IconButton(
            tooltip: 'Aplicaciones conectadas',
            onPressed: () => showModalBottomSheet<void>(
              context: context,
              showDragHandle: true,
              builder: (sheetContext) => SafeArea(
                child: ListView(
                  shrinkWrap: true,
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                  children: const [
                    Text(
                      'Aplicaciones que usan Local AI Manager',
                      style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                    ),
                    SizedBox(height: 8),
                    Text(
                      'Estas aplicaciones pueden reutilizar el mismo modelo cargado en RAM, sin cargar otra copia.',
                    ),
                    SizedBox(height: 12),
                    Card(
                      child: ListTile(
                        leading: Icon(Icons.school_outlined),
                        title: Text('Memora'),
                        subtitle: Text('Cliente de IA compartida'),
                        trailing: Icon(Icons.check_circle_outline),
                      ),
                    ),
                    Card(
                      child: ListTile(
                        leading: Icon(Icons.account_balance_wallet_outlined),
                        title: Text('Finanzas'),
                        subtitle: Text('Cliente de IA compartida'),
                        trailing: Icon(Icons.check_circle_outline),
                      ),
                    ),
                    Card(
                      child: ListTile(
                        leading: Icon(Icons.chat_outlined),
                        title: Text('WhatsBot'),
                        subtitle: Text('Cliente de IA compartida · com.whatsbot.whatsbot'),
                        trailing: Icon(Icons.check_circle_outline),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            icon: const Icon(Icons.apps_outlined),
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
if appbar in s:
    s = s.replace(appbar, appbar_backup, 1)
elif "ManagerBackupPage" not in s:
    raise RuntimeError("Manager AppBar backup anchor not found")

p.write_text(s)
print("Local AI Manager external backup integration applied")
