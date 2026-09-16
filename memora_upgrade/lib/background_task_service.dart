import 'dart:async';

import 'package:flutter/services.dart';

class BackgroundTaskService {
  static const MethodChannel _channel = MethodChannel('com.memora/background_tasks');

  static int _depth = 0;
  static Timer? _stopTimer;
  static String _title = 'Memora is working';
  static String _body = 'Keeping this task active in the background…';

  static Future<T> run<T>({
    required String title,
    required String body,
    required Future<T> Function() task,
  }) async {
    await begin(title: title, body: body);
    try {
      return await task();
    } finally {
      await finish();
    }
  }

  static Future<void> begin({
    required String title,
    required String body,
  }) async {
    _stopTimer?.cancel();
    _stopTimer = null;
    final first = _depth == 0;
    _depth += 1;
    if (!first) return;

    _title = title;
    _body = body;
    try {
      await _channel.invokeMethod<void>('start', <String, dynamic>{
        'title': title,
        'body': body,
      });
    } catch (_) {
      // Background execution is an enhancement. The user task itself should
      // still be allowed to continue if an Android service cannot start.
    }
  }

  static Future<void> update({
    String? title,
    String? body,
    int? progress,
    int? max,
  }) async {
    if (title != null && title.trim().isNotEmpty) _title = title.trim();
    if (body != null && body.trim().isNotEmpty) _body = body.trim();
    try {
      await _channel.invokeMethod<void>('update', <String, dynamic>{
        'title': _title,
        'body': _body,
        if (progress != null) 'progress': progress,
        if (max != null) 'max': max,
      });
    } catch (_) {}
  }

  static Future<void> finish({bool immediately = false}) async {
    if (_depth > 0) _depth -= 1;
    if (_depth > 0) return;

    _stopTimer?.cancel();
    if (immediately) {
      await _stopNative();
      return;
    }

    // A short grace period keeps the foreground service alive across batched
    // model calls (for example 50-card generation) instead of flashing the
    // notification on/off between every batch.
    _stopTimer = Timer(const Duration(seconds: 5), () {
      unawaited(_stopNative());
    });
  }

  static Future<void> stopNow() async {
    _depth = 0;
    _stopTimer?.cancel();
    _stopTimer = null;
    await _stopNative();
  }

  static Future<void> _stopNative() async {
    _stopTimer?.cancel();
    _stopTimer = null;
    try {
      await _channel.invokeMethod<void>('stop');
    } catch (_) {}
  }
}
