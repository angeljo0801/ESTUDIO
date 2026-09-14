import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';

import 'models.dart';

class GuideStore extends ChangeNotifier {
  final List<StudyGuide> guides = [];
  File? _storageFile;

  Future<void> load() async {
    final directory = await getApplicationDocumentsDirectory();
    _storageFile = File('${directory.path}/memora_guides_v3.json');
    if (!await _storageFile!.exists()) return;

    try {
      final raw = await _storageFile!.readAsString();
      if (raw.trim().isEmpty) return;
      final decoded = jsonDecode(raw) as List<dynamic>;
      guides
        ..clear()
        ..addAll(
          decoded.map(
            (item) => StudyGuide.fromJson(Map<String, dynamic>.from(item as Map)),
          ),
        );
      guides.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    } catch (_) {
      // Keep the app usable even if an older/corrupt local file cannot be read.
      guides.clear();
    }
  }

  Future<void> add(StudyGuide guide) async {
    guides.insert(0, guide);
    await _persist();
    notifyListeners();
  }

  Future<void> update(StudyGuide guide) async {
    final index = guides.indexWhere((item) => item.id == guide.id);
    if (index >= 0) guides[index] = guide;
    await _persist();
    notifyListeners();
  }

  Future<void> remove(String id) async {
    guides.removeWhere((guide) => guide.id == id);
    await _persist();
    notifyListeners();
  }

  Future<void> _persist() async {
    if (_storageFile == null) {
      final directory = await getApplicationDocumentsDirectory();
      _storageFile = File('${directory.path}/memora_guides_v3.json');
    }
    final payload = jsonEncode(guides.map((guide) => guide.toJson()).toList());
    await _storageFile!.writeAsString(payload, flush: true);
  }
}
