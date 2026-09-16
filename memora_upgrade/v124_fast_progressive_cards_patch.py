from pathlib import Path
import re


def required(text: str, old: str, new: str, label: str, count: int = 1) -> str:
    if old not in text:
        raise RuntimeError(f'{label} anchor not found')
    return text.replace(old, new, count)


# -----------------------------------------------------------------------------
# AI card generation: larger batches, shorter prompts, fewer retries, and a
# progressive batch callback so usable cards can be saved/shown immediately.
# -----------------------------------------------------------------------------
p = Path('lib/ai_card_service.dart')
s = p.read_text()

s = required(
    s,
    """    int target = defaultTarget,\n    void Function(int generated, int target)? onProgress,\n  }) async {""",
    """    int target = defaultTarget,\n    void Function(int generated, int target)? onProgress,\n    Future<void> Function(List<StudyCard> cards, int target)? onBatch,\n  }) async {""",
    'AI card progressive callback signature',
)

s = required(
    s,
    """    final safeTarget = target.clamp(10, 120).toInt();\n    final chunkChars = ai.isDirectGguf\n        ? 2600\n        : ai.isLocalServer\n            ? 4200\n            : 7200;\n    final batchSize = ai.isDirectGguf\n        ? 4\n        : ai.isLocalServer\n            ? 6\n            : 10;\n    final chunks = _chunks(material, chunkChars);\n""",
    """    final safeTarget = target.clamp(10, 120).toInt();\n    final prefs = await SharedPreferences.getInstance();\n    final generationMode = (prefs.getString('card_generation_mode') ?? 'balanced').trim();\n    final fast = generationMode == 'fast';\n    final maximum = generationMode == 'maximum';\n\n    final chunkChars = ai.isDirectGguf\n        ? (fast ? 2200 : maximum ? 3000 : 2600)\n        : ai.isLocalServer\n            ? (fast ? 3200 : maximum ? 5000 : 4000)\n            : (fast ? 5000 : maximum ? 8000 : 6200);\n    final batchSize = ai.isDirectGguf\n        ? (fast ? 10 : maximum ? 6 : 8)\n        : ai.isLocalServer\n            ? (fast ? 16 : maximum ? 10 : 14)\n            : (fast ? 24 : maximum ? 14 : 20);\n    final chunks = _chunks(material, chunkChars);\n""",
    'AI card batch sizing',
)

s = required(
    s,
    """    final minimumCalls = (safeTarget / batchSize).ceil();\n    final maxAttempts = max(minimumCalls + 8, chunks.length * 3).clamp(10, 32).toInt();\n""",
    """    final minimumCalls = (safeTarget / batchSize).ceil();\n    final retryAllowance = maximum ? 6 : fast ? 2 : 4;\n    final maxAttempts = (minimumCalls + retryAllowance).clamp(minimumCalls, 24).toInt();\n""",
    'AI card retry budget',
)

prompt_pattern = re.compile(
    r"      final recent = cards\.reversed\.take\(18\).*?\n      final prompt = '''Create .*?\n\$chunk''';",
    re.S,
)
prompt_replacement = r"""      final recent = cards.reversed.take(8).map((c) => c.question).toList().reversed;
      final prompt = '''Create $requestCount strong study flashcards from the MATERIAL below.

RULES:
- Use only ideas supported by the material, but you may paraphrase or combine directly related ideas.
- Make each question standalone, grammatical, and useful for learning.
- Prefer concepts, why/how, cause-effect, comparisons, applications, decisions, formulas, or calculations when supported.
- Answers should usually be 1-3 concise sentences.
- No sentence fragments, isolated-word trivia, vague wrappers, or close duplicates.
- Return ONLY a JSON array: {"question":"...","answer":"...","source":"short topic"}.

AVOID REPEATING:
${recent.isEmpty ? '(none)' : recent.map((q) => '- $q').join('\n')}

MATERIAL:
$chunk''';"""
s, n = prompt_pattern.subn(lambda _m: prompt_replacement, s, count=1)
if n != 1:
    raise RuntimeError('AI card compact prompt anchor not found')

s = required(
    s,
    """      final parsed = _parseCards(raw);\n      for (final item in parsed) {\n""",
    """      final beforeBatch = cards.length;\n      final parsed = _parseCards(raw);\n      for (final item in parsed) {\n""",
    'AI card batch start count',
)

s = required(
    s,
    """        cards.add(card);\n        onProgress?.call(cards.length, safeTarget);\n        await BackgroundTaskService.update(\n          title: 'Memora is creating study cards',\n          body: '${cards.length} of $safeTarget cards ready',\n          progress: cards.length,\n          max: safeTarget,\n        );\n""",
    """        cards.add(card);\n        onProgress?.call(cards.length, safeTarget);\n""",
    'Remove per-card native progress overhead',
)

s = required(
    s,
    """      }\n      attempt++;\n    }\n\n    if (cards.isEmpty) {\n""",
    """      }\n      if (cards.length > beforeBatch) {\n        await BackgroundTaskService.update(\n          title: 'Memora is creating study cards',\n          body: '${cards.length} of $safeTarget cards ready',\n          progress: cards.length,\n          max: safeTarget,\n        );\n        if (onBatch != null) {\n          await onBatch(List<StudyCard>.of(cards), safeTarget);\n        }\n      }\n      attempt++;\n    }\n\n    if (cards.isEmpty) {\n""",
    'AI card per-batch progress callback',
)
p.write_text(s)


# -----------------------------------------------------------------------------
# Home/import flow: persist every completed AI batch immediately so the user can
# open the guide and begin reviewing before all 50 cards are finished.
# -----------------------------------------------------------------------------
p = Path('lib/home_page.dart')
s = p.read_text()
s = required(
    s,
    """        onProgress: (generated, target) {\n          if (!mounted) return;\n          setState(() => _busyMessage = 'Generating AI cards… $generated/$target');\n        },\n      );\n""",
    """        onProgress: (generated, target) {\n          if (!mounted) return;\n          setState(() => _busyMessage = 'Generating AI cards… $generated/$target');\n        },\n        onBatch: (partial, target) async {\n          guide.cards = List<StudyCard>.of(partial);\n          await widget.store.update(guide);\n          if (mounted) {\n            setState(() => _busyMessage =\n                '${guide.cards.length}/$target cards ready • you can start reviewing now');\n          }\n        },\n      );\n""",
    'Home progressive card persistence',
)
p.write_text(s)


# -----------------------------------------------------------------------------
# Guide detail: show/save each batch immediately. Existing Review becomes enabled
# as soon as the first batch arrives while background generation keeps running.
# -----------------------------------------------------------------------------
p = Path('lib/guide_detail_page.dart')
s = p.read_text()
s = required(
    s,
    """        onProgress: (generated, _) {\n          if (mounted) setState(() => _cardProgress = generated);\n        },\n      );\n""",
    """        onProgress: (generated, _) {\n          if (mounted) setState(() => _cardProgress = generated);\n        },\n        onBatch: (partial, target) async {\n          widget.guide.cards = List<StudyCard>.of(partial);\n          await widget.store.update(widget.guide);\n          if (mounted) {\n            setState(() {\n              _cardProgress = partial.length;\n            });\n          }\n        },\n      );\n""",
    'Guide detail progressive card persistence',
)

s = required(
    s,
    """                    const SizedBox(height: 10),\n                    if (_generatingCards)\n                      LinearProgressIndicator(\n""",
    """                    const SizedBox(height: 10),\n                    if (_generatingCards && guide.cards.isNotEmpty) ...[\n                      Text(\n                        '${guide.cards.length} cards are ready now. You can start Review while Memora creates the rest.',\n                      ),\n                      const SizedBox(height: 10),\n                    ],\n                    if (_generatingCards)\n                      LinearProgressIndicator(\n""",
    'Guide detail live cards message',
)
p.write_text(s)


# -----------------------------------------------------------------------------
# AI Settings: Fast / Balanced / Maximum quality card generation modes.
# Balanced is the default and uses the larger v1.24 batches.
# -----------------------------------------------------------------------------
p = Path('lib/llm_settings_page.dart')
s = p.read_text()
s = required(
    s,
    "  String provider = 'gemini';\n",
    "  String provider = 'gemini';\n  String cardGenerationMode = 'balanced';\n",
    'Card generation mode state',
)
s = required(
    s,
    "    provider = p.getString('llm_provider') ?? 'gemini';\n",
    "    provider = p.getString('llm_provider') ?? 'gemini';\n    cardGenerationMode = p.getString('card_generation_mode') ?? 'balanced';\n",
    'Card generation mode load',
)
s = required(
    s,
    "    await p.setString('llm_provider', provider);\n",
    "    await p.setString('llm_provider', provider);\n    await p.setString('card_generation_mode', cardGenerationMode);\n",
    'Card generation mode save',
)

mode_ui = """                  const SizedBox(height: 22),
                  const Text(
                    'Card generation speed',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 6),
                  SegmentedButton<String>(
                    segments: const [
                      ButtonSegment(value: 'fast', label: Text('Fast')),
                      ButtonSegment(value: 'balanced', label: Text('Balanced')),
                      ButtonSegment(value: 'maximum', label: Text('Maximum quality')),
                    ],
                    selected: <String>{cardGenerationMode},
                    onSelectionChanged: (value) {
                      setState(() => cardGenerationMode = value.first);
                    },
                  ),
                  const SizedBox(height: 8),
                  Text(
                    cardGenerationMode == 'fast'
                        ? 'Largest batches and shortest answers for the fastest creation.'
                        : cardGenerationMode == 'maximum'
                            ? 'Smaller batches and more retries for maximum quality.'
                            : 'Recommended: fast large batches with strong quality checks.',
                  ),
                  const SizedBox(height: 22),
"""
save_call = "onPressed: _save"
call_index = s.rfind(save_call)
if call_index < 0:
    raise RuntimeError('Card generation mode save action not found')
safe_area_index = s.rfind('                  SafeArea(', 0, call_index)
if safe_area_index < 0:
    raise RuntimeError('Card generation mode save SafeArea not found')
s = s[:safe_area_index] + mode_ui + s[safe_area_index:]
p.write_text(s)

print('Memora v1.24 fast progressive card generation patch applied successfully')
