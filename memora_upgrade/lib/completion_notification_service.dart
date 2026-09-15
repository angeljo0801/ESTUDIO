import 'package:flutter/services.dart';

class CompletionNotificationService {
  static const MethodChannel _channel = MethodChannel('com.memora/notifications');
  static int _serial = 2000;

  static Future<void> initialize() async {
    try {
      await _channel.invokeMethod<void>('ensurePermission');
    } catch (_) {
      // Notifications are an enhancement; never block Memora if Android rejects
      // a permission request or the channel is unavailable.
    }
  }

  static Future<void> show({
    required String title,
    required String body,
  }) async {
    try {
      await _channel.invokeMethod<void>('notify', <String, dynamic>{
        'id': ++_serial,
        'title': title,
        'body': body,
      });
    } catch (_) {
      // The task itself has already completed. Notification failures must not
      // turn a successful exam/plan/guide into an application error.
    }
  }
}
