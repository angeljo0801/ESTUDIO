import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

class FastModelSetupPage extends StatefulWidget {
  const FastModelSetupPage({super.key});

  @override
  State<FastModelSetupPage> createState() => _FastModelSetupPageState();
}

class _FastModelSetupPageState extends State<FastModelSetupPage> {
  static const _fileName = 'qwen2.5-1.5b-instruct-q4_k_m.gguf';
  static const _downloadUrl =
      'https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf?download=true';

  http.Client? _client;
  bool checking = true;
  bool downloading = false;
  bool installed = false;
  bool cancelled = false;
  int received = 0;
  int total = 0;
  String status = '';
  String installedPath = '';
  DateTime _lastPaint = DateTime.fromMillisecondsSinceEpoch(0);

  @override
  void initState() {
    super.initState();
    _checkInstalled();
  }

  Future<Directory> _modelDirectory() async {
    final root = await getApplicationSupportDirectory();
    final dir = Directory('${root.path}/models');
    await dir.create(recursive: true);
    return dir;
  }

  Future<void> _checkInstalled() async {
    try {
      final dir = await _modelDirectory();
      final file = File('${dir.path}/$_fileName');
      final exists = await file.exists() && await file.length() > 500000000;
      final prefs = await SharedPreferences.getInstance();
      if (exists) {
        await prefs.setString('device_model_path', file.path);
        if (mounted) {
          setState(() {
            installed = true;
            installedPath = file.path;
            status = 'The fast model is already downloaded and ready.';
          });
        }
      }
    } catch (_) {
      // The page can still offer a retry/download if the initial check fails.
    } finally {
      if (mounted) setState(() => checking = false);
    }
  }

  String _formatBytes(int bytes) {
    if (bytes <= 0) return '0 MB';
    const mb = 1024 * 1024;
    const gb = 1024 * mb;
    if (bytes >= gb) return '${(bytes / gb).toStringAsFixed(2)} GB';
    return '${(bytes / mb).toStringAsFixed(0)} MB';
  }

  Future<void> _download() async {
    if (downloading) return;
    final dir = await _modelDirectory();
    final finalFile = File('${dir.path}/$_fileName');
    final partialFile = File('${finalFile.path}.part');

    setState(() {
      downloading = true;
      cancelled = false;
      received = 0;
      total = 0;
      status = 'Connecting to the model repository…';
    });

    final client = http.Client();
    _client = client;
    IOSink? sink;
    try {
      if (await partialFile.exists()) await partialFile.delete();
      final request = http.Request('GET', Uri.parse(_downloadUrl));
      request.followRedirects = true;
      request.maxRedirects = 10;
      final response = await client.send(request).timeout(const Duration(minutes: 2));
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw HttpException('Model server returned HTTP ${response.statusCode}.');
      }
      total = response.contentLength ?? 0;
      sink = partialFile.openWrite();
      await for (final chunk in response.stream) {
        if (cancelled) throw const _DownloadCancelled();
        sink.add(chunk);
        received += chunk.length;
        final now = DateTime.now();
        if (mounted && now.difference(_lastPaint).inMilliseconds >= 250) {
          _lastPaint = now;
          setState(() {
            status = total > 0
                ? 'Downloading ${_formatBytes(received)} of ${_formatBytes(total)}…'
                : 'Downloading ${_formatBytes(received)}…';
          });
        }
      }
      await sink.flush();
      await sink.close();
      sink = null;

      if (await finalFile.exists()) await finalFile.delete();
      await partialFile.rename(finalFile.path);

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('device_model_path', finalFile.path);
      await prefs.setString('device_model_mode', 'private');
      await prefs.setString('llm_provider', 'device');

      if (!mounted) return;
      setState(() {
        installed = true;
        installedPath = finalFile.path;
        status = 'Ready. Memora is now configured to use this on-device model.';
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Fast on-device model installed.')),
      );
    } on _DownloadCancelled {
      try {
        await sink?.close();
      } catch (_) {}
      sink = null;
      try {
        if (await partialFile.exists()) await partialFile.delete();
      } catch (_) {}
      if (mounted) setState(() => status = 'Download cancelled.');
    } catch (e) {
      try {
        await sink?.close();
      } catch (_) {}
      sink = null;
      try {
        if (await partialFile.exists()) await partialFile.delete();
      } catch (_) {}
      if (mounted) {
        setState(() => status = 'Download failed: $e');
      }
    } finally {
      client.close();
      if (identical(_client, client)) _client = null;
      if (mounted) setState(() => downloading = false);
    }
  }

  Future<void> _useInstalled() async {
    if (!installed || installedPath.isEmpty) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('device_model_path', installedPath);
    await prefs.setString('device_model_mode', 'private');
    await prefs.setString('llm_provider', 'device');
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Qwen2.5 1.5B is now the general Memora AI.')),
    );
  }

  void _cancel() {
    if (!downloading) return;
    cancelled = true;
    _client?.close();
    setState(() => status = 'Cancelling download…');
  }

  @override
  void dispose() {
    cancelled = true;
    _client?.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final progress = total <= 0 ? null : (received / total).clamp(0.0, 1.0);
    return Scaffold(
      appBar: AppBar(title: const Text('Fast local model')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Card(
            child: Padding(
              padding: EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Qwen2.5 1.5B Instruct • Q4_K_M',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 8),
                  Text(
                    'A compact multilingual model chosen for faster on-device tutoring, translation, review, and plan generation. The download is about 1.1 GB.',
                  ),
                  SizedBox(height: 10),
                  Text(
                    'This is the GGUF version Memora can run directly on the phone. If you use an Ollama server instead, the matching model name is qwen2.5:1.5b.',
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          if (checking)
            const Center(child: CircularProgressIndicator())
          else if (!installed)
            FilledButton.icon(
              onPressed: downloading ? null : _download,
              icon: const Icon(Icons.download_rounded),
              label: const Text('Download fast model'),
              style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(54)),
            )
          else
            FilledButton.icon(
              onPressed: downloading ? null : _useInstalled,
              icon: const Icon(Icons.bolt_rounded),
              label: const Text('Use this model in Memora'),
              style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(54)),
            ),
          if (downloading) ...[
            const SizedBox(height: 14),
            LinearProgressIndicator(value: progress),
            const SizedBox(height: 10),
            Text(
              total > 0
                  ? '${_formatBytes(received)} / ${_formatBytes(total)}'
                  : _formatBytes(received),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _cancel,
              icon: const Icon(Icons.stop_circle_outlined),
              label: const Text('Cancel download'),
            ),
          ],
          if (status.isNotEmpty) ...[
            const SizedBox(height: 14),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(status),
              ),
            ),
          ],
          const SizedBox(height: 14),
          const Text(
            'Use Wi-Fi and keep enough free storage. The model is stored inside Memora as its private GGUF. You can export it later from AI Settings if you want to reuse the file elsewhere.',
          ),
        ],
      ),
    );
  }
}

class _DownloadCancelled implements Exception {
  const _DownloadCancelled();
}
