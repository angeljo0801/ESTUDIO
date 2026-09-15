import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';

import 'models.dart';
import 'study_engine.dart';

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

      var repaired = false;
      for (final guide in guides) {
        final cleaned = guide.cards.where(StudyEngine.isCardUsable).toList();
        if (cleaned.length != guide.cards.length) {
          guide.cards = cleaned;
          repaired = true;
        }
        if (guide.cards.isEmpty && guide.text.trim().isNotEmpty) {
          guide.cards = StudyEngine.buildCards(guide.text);
          repaired = true;
        }
      }

      guides.sort((a, b) => b.createdAt.compareTo(a.createdAt));
      if (repaired) await _persist();
    } catch (_) {
      guides.clear();
    }
  }

  StudyGuide? findById(String id) {
    for (final guide in guides) {
      if (guide.id == id) return guide;
    }
    return null;
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
    final existing = findById(id);
    guides.removeWhere((guide) => guide.id == id);
    await _persist();
    notifyListeners();
    final path = existing?.filePath;
    if (path != null && path.isNotEmpty) {
      try {
        final file = File(path);
        if (await file.exists()) await file.delete();
      } catch (_) {
        // La guía ya fue retirada de la biblioteca; un fallo al limpiar el archivo no debe bloquear la app.
      }
    }
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