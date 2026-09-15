import 'dart:convert';
import 'dart:io';

import 'package:flutter_file_dialog/flutter_file_dialog.dart';
import 'package:path_provider/path_provider.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

class ChatMessage {
  const ChatMessage({
    required this.role,
    required this.text,
    required this.createdAt,
    this.attachments = const [],
  });

  final String role; // user | assistant
  final String text;
  final DateTime createdAt;
  final List<String> attachments;

  ChatMessage copyWith({String? text, List<String>? attachments}) => ChatMessage(
        role: role,
        text: text ?? this.text,
        createdAt: createdAt,
        attachments: attachments ?? this.attachments,
      );

  Map<String, dynamic> toJson() => {
        'role': role,
        'text': text,
        'createdAt': createdAt.toIso8601String(),
        'attachments': attachments,
      };

  factory ChatMessage.fromJson(Map<String, dynamic> json) => ChatMessage(
        role: json['role']?.toString() == 'assistant' ? 'assistant' : 'user',
        text: json['text']?.toString() ?? '',
        createdAt: DateTime.tryParse(json['createdAt']?.toString() ?? '') ?? DateTime.now(),
        attachments: (json['attachments'] is List)
            ? (json['attachments'] as List).map((e) => e.toString()).toList()
            : const [],
      );
}

class ChatSession {
  const ChatSession({
    required this.id,
    required this.ownerType,
    required this.ownerId,
    required this.title,
    required this.createdAt,
    required this.updatedAt,
    required this.messages,
  });

  final String id;
  final String ownerType; // tutor | agent
  final String ownerId;
  final String title;
  final DateTime createdAt;
  final DateTime updatedAt;
  final List<ChatMessage> messages;

  factory ChatSession.empty({required String ownerType, required String ownerId}) {
    final now = DateTime.now();
    return ChatSession(
      id: 'chat_${now.microsecondsSinceEpoch}',
      ownerType: ownerType,
      ownerId: ownerId,
      title: 'Nuevo chat',
      createdAt: now,
      updatedAt: now,
      messages: const [],
    );
  }

  ChatSession copyWith({
    String? title,
    DateTime? updatedAt,
    List<ChatMessage>? messages,
  }) =>
      ChatSession(
        id: id,
        ownerType: ownerType,
        ownerId: ownerId,
        title: title ?? this.title,
        createdAt: createdAt,
        updatedAt: updatedAt ?? this.updatedAt,
        messages: messages ?? this.messages,
      );

  String conversationContext({int maxChars = 6000, int maxMessages = 12}) {
    if (messages.isEmpty) return '(Sin mensajes anteriores)';
    final selected = messages.length > maxMessages
        ? messages.sublist(messages.length - maxMessages)
        : messages;
    final chunks = <String>[];
    var used = 0;
    for (final message in selected.reversed) {
      if (message.text.trim().isEmpty) continue;
      final label = message.role == 'assistant' ? 'ASISTENTE' : 'USUARIO';
      final line = '$label: ${message.text.trim()}';
      final remaining = maxChars - used;
      if (remaining <= 80) break;
      final clipped = line.length > remaining ? line.substring(0, remaining) : line;
      chunks.add(clipped);
      used += clipped.length + 1;
    }
    return chunks.reversed.join('\n');
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'ownerType': ownerType,
        'ownerId': ownerId,
        'title': title,
        'createdAt': createdAt.toIso8601String(),
        'updatedAt': updatedAt.toIso8601String(),
        'messages': messages.map((m) => m.toJson()).toList(),
      };

  factory ChatSession.fromJson(Map<String, dynamic> json) => ChatSession(
        id: json['id']?.toString() ?? '',
        ownerType: json['ownerType']?.toString() ?? '',
        ownerId: json['ownerId']?.toString() ?? '',
        title: json['title']?.toString() ?? 'Chat',
        createdAt: DateTime.tryParse(json['createdAt']?.toString() ?? '') ?? DateTime.now(),
        updatedAt: DateTime.tryParse(json['updatedAt']?.toString() ?? '') ?? DateTime.now(),
        messages: (json['messages'] is List)
            ? (json['messages'] as List)
                .whereType<Map>()
                .map((e) => ChatMessage.fromJson(Map<String, dynamic>.from(e)))
                .toList()
            : const [],
      );

  static String titleFrom(String text, {String fallback = 'Nuevo chat'}) {
    final clean = text.replaceAll(RegExp(r'\s+'), ' ').trim();
    if (clean.isEmpty) return fallback;
    return clean.length <= 46 ? clean : '${clean.substring(0, 46).trim()}…';
  }
}

class ChatStore {
  static Future<File> _file() async {
    final root = await getApplicationDocumentsDirectory();
    final dir = Directory('${root.path}/chat_history');
    await dir.create(recursive: true);
    return File('${dir.path}/sessions.json');
  }

  static Future<List<ChatSession>> _readAll() async {
    final file = await _file();
    if (!await file.exists()) return [];
    try {
      final raw = await file.readAsString();
      if (raw.trim().isEmpty) return [];
      final decoded = jsonDecode(raw);
      if (decoded is! List) return [];
      return decoded
          .whereType<Map>()
          .map((e) => ChatSession.fromJson(Map<String, dynamic>.from(e)))
          .where((e) => e.id.isNotEmpty && e.ownerId.isNotEmpty)
          .toList();
    } catch (_) {
      return [];
    }
  }

  static Future<void> _writeAll(List<ChatSession> sessions) async {
    final file = await _file();
    final temp = File('${file.path}.tmp');
    await temp.writeAsString(jsonEncode(sessions.map((e) => e.toJson()).toList()), flush: true);
    if (await file.exists()) await file.delete();
    await temp.rename(file.path);
  }

  static Future<List<ChatSession>> listFor(String ownerType, String ownerId) async {
    final all = await _readAll();
    final result = all
        .where((e) => e.ownerType == ownerType && e.ownerId == ownerId)
        .toList();
    result.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
    return result;
  }

  static Future<void> save(ChatSession session) async {
    final all = await _readAll();
    final index = all.indexWhere((e) => e.id == session.id);
    if (index >= 0) {
      all[index] = session;
    } else {
      all.add(session);
    }
    await _writeAll(all);
  }

  static Future<void> delete(String id) async {
    final all = await _readAll();
    all.removeWhere((e) => e.id == id);
    await _writeAll(all);
  }

  static Future<String?> exportPdf(ChatSession session, {required String participantName}) async {
    final doc = pw.Document();
    String clean(String value) {
      final out = StringBuffer();
      for (final rune in value.runes) {
        if (rune == 10 || rune == 13 || rune == 9 || (rune >= 32 && rune <= 255)) {
          out.writeCharCode(rune);
        } else {
          out.write('?');
        }
      }
      return out.toString();
    }

    doc.addPage(
      pw.MultiPage(
        pageFormat: PdfPageFormat.a4,
        margin: const pw.EdgeInsets.all(36),
        build: (_) => [
          pw.Text(clean(session.title), style: pw.TextStyle(fontSize: 20, fontWeight: pw.FontWeight.bold)),
          pw.SizedBox(height: 4),
          pw.Text(clean('Conversación con $participantName'), style: const pw.TextStyle(fontSize: 11)),
          pw.SizedBox(height: 18),
          for (final message in session.messages) ...[
            pw.Text(
              message.role == 'assistant' ? clean(participantName) : 'Usuario',
              style: pw.TextStyle(fontSize: 11, fontWeight: pw.FontWeight.bold),
            ),
            if (message.attachments.isNotEmpty)
              pw.Text(clean('Adjuntos: ${message.attachments.join(', ')}'), style: const pw.TextStyle(fontSize: 9)),
            pw.SizedBox(height: 3),
            pw.Text(clean(message.text), style: const pw.TextStyle(fontSize: 10.5, lineSpacing: 2)),
            pw.SizedBox(height: 12),
          ],
        ],
      ),
    );

    final root = await getTemporaryDirectory();
    final safe = session.title
        .replaceAll(RegExp(r'[^A-Za-z0-9_-]+'), '_')
        .replaceAll(RegExp(r'_+'), '_')
        .replaceAll(RegExp(r'^_|_$'), '');
    final file = File('${root.path}/${safe.isEmpty ? 'chat_memora' : safe}.pdf');
    await file.writeAsBytes(await doc.save(), flush: true);
    return FlutterFileDialog.saveFile(
      params: SaveFileDialogParams(sourceFilePath: file.path, fileName: file.uri.pathSegments.last),
    );
  }
}
