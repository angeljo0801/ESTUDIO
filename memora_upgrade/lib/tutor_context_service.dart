import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'guide_store.dart';
import 'models.dart';

class TutorContextProfile {
  const TutorContextProfile({
    required this.id,
    required this.name,
    required this.emoji,
    required this.modelSource,
    required this.guideIds,
    this.description = '',
    this.instructions = '',
  });

  final String id;
  final String name;
  final String emoji;
  final String modelSource;
  final List<String> guideIds;
  final String description;
  final String instructions;

  factory TutorContextProfile.fromJson(Map<String, dynamic> json) {
    final guides = json['guideIds'];
    return TutorContextProfile(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? 'Tutor',
      emoji: json['emoji']?.toString() ?? '🧠',
      modelSource: json['modelSource']?.toString() ?? 'global',
      guideIds: guides is List
          ? guides.map((e) => e.toString()).where((e) => e.isNotEmpty).toList()
          : const [],
      description: json['description']?.toString() ?? '',
      instructions: json['instructions']?.toString() ?? '',
    );
  }
}

class TutorContextService {
  static const _profilesKey = 'memora_tutor_profiles_v1';

  static const _fallback = <TutorContextProfile>[
    TutorContextProfile(
      id: 'memora_general',
      name: 'Memora',
      emoji: '🧠',
      modelSource: 'global',
      guideIds: [],
      description: 'Tutor general de Memora.',
    ),
    TutorContextProfile(
      id: 'finanzas',
      name: 'Tutor de Finanzas',
      emoji: '💰',
      modelSource: 'global',
      guideIds: [],
    ),
    TutorContextProfile(
      id: 'programacion',
      name: 'Tutor de Programación',
      emoji: '💻',
      modelSource: 'global',
      guideIds: [],
    ),
    TutorContextProfile(
      id: 'idiomas',
      name: 'Tutor de Idiomas',
      emoji: '🌍',
      modelSource: 'global',
      guideIds: [],
    ),
    TutorContextProfile(
      id: 'paso_a_paso',
      name: 'Profesor Paso a Paso',
      emoji: '🪜',
      modelSource: 'global',
      guideIds: [],
    ),
    TutorContextProfile(
      id: 'socratico',
      name: 'Tutor Socrático',
      emoji: '❓',
      modelSource: 'global',
      guideIds: [],
    ),
    TutorContextProfile(
      id: 'examinador',
      name: 'Examinador Estricto',
      emoji: '🎯',
      modelSource: 'global',
      guideIds: [],
    ),
    TutorContextProfile(
      id: 'repaso_express',
      name: 'Repaso Express',
      emoji: '⚡',
      modelSource: 'global',
      guideIds: [],
    ),
    TutorContextProfile(
      id: 'ejemplos',
      name: 'Tutor de Ejemplos',
      emoji: '💡',
      modelSource: 'global',
      guideIds: [],
    ),
  ];

  static Future<List<TutorContextProfile>> loadProfiles() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_profilesKey);
    if (raw == null || raw.trim().isEmpty) return List.of(_fallback);
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! List) return List.of(_fallback);
      final result = decoded
          .whereType<Map>()
          .map((e) => TutorContextProfile.fromJson(Map<String, dynamic>.from(e)))
          .where((e) => e.id.isNotEmpty)
          .toList();
      return result.isEmpty ? List.of(_fallback) : result;
    } catch (_) {
      return List.of(_fallback);
    }
  }

  static List<StudyGuide> guidesFor(GuideStore store, TutorContextProfile tutor) {
    final ids = tutor.guideIds.toSet();
    return store.guides.where((g) => ids.contains(g.id)).toList();
  }

  static Future<String?> bestAvailableProvider() async {
    final prefs = await SharedPreferences.getInstance();
    final gemini = prefs.getString('gemini_key')?.trim() ?? '';
    if (gemini.isNotEmpty) return 'gemini';

    final openAiKey = prefs.getString('openai_key')?.trim() ?? '';
    final openAiModel = prefs.getString('openai_model')?.trim() ?? '';
    if (openAiKey.isNotEmpty && openAiModel.isNotEmpty) return 'openai';

    final localModel = prefs.getString('local_model')?.trim() ?? '';
    if (localModel.isNotEmpty) return 'local';

    final provider = prefs.getString('llm_provider')?.trim();
    return (provider == null || provider.isEmpty) ? null : provider;
  }

  static String sourceLabel(String source) {
    switch (source) {
      case 'private':
        return 'GGUF privado';
      case 'shared':
        return 'GGUF compartido';
      case 'gemini':
        return 'Gemini';
      case 'openai':
        return 'OpenAI / compatible';
      case 'local':
      case 'ollama':
        return 'Ollama / servidor local';
      case 'device':
        return 'GGUF del dispositivo';
      case 'global':
      default:
        return 'Configuración general de IA';
    }
  }

  static String contentForGuides(
    List<StudyGuide> guides, {
    int maxChars = 18000,
  }) {
    if (guides.isEmpty) return '';
    final buffer = StringBuffer();
    var remaining = maxChars;
    for (final guide in guides) {
      if (remaining <= 200) break;
      final header = '\n===== ${guide.title} =====\n';
      buffer.write(header);
      remaining -= header.length;
      final source = guide.text.trim().isNotEmpty ? guide.text.trim() : guide.summary.trim();
      if (source.isEmpty) continue;
      final take = source.length.clamp(0, remaining).toInt();
      buffer.write(source.substring(0, take));
      remaining -= take;
      buffer.writeln();
    }
    return buffer.toString().trim();
  }
}
