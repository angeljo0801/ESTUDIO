from pathlib import Path
import re

# v172: restore the exact pre-AI card-generation method from Memora's earlier
# version, but make it manual-only. The old implementation used
# StudyEngine.buildCards(guide.text) directly on the extracted guide text.
# It did NOT use an LLM or the vector coverage wrapper.

p = Path('lib/study_engine.dart')
s = p.read_text()
old = "      cards: buildCards(clean),\n"
new = "      cards: const <StudyCard>[],\n"
if old in s:
    s = s.replace(old, new, 1)
elif "      cards: const [],\n" in s or "      cards: const <StudyCard>[],\n" in s:
    pass
else:
    raise SystemExit('v172 could not verify manual-only StudyEngine buildGuide cards')
p.write_text(s)

p = Path('lib/guide_detail_page.dart')
s = p.read_text()

start = s.find("  Future<void> _regenerate(")
end = s.find("  Future<void> _export()", start)
if start < 0 or end < 0:
    raise SystemExit('v172 guide regenerate method anchor missing')

method = r'''  Future<void> _regenerate({bool automatic = false}) async {
    if (_generatingCards) return;
    setState(() {
      _generatingCards = true;
      _cardProgress = 0;
    });
    try {
      // Original Memora method: parse the extracted guide text directly.
      final regenerated = StudyEngine.buildCards(widget.guide.text);
      if (!mounted) return;
      setState(() {
        widget.guide.cards = regenerated;
        _cardProgress = regenerated.length;
      });
      await _save();
      if (!mounted || automatic) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${regenerated.length} study cards generated.')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Card generation failed: $e')),
      );
    } finally {
      if (mounted) setState(() => _generatingCards = false);
    }
  }

'''
s = s[:start] + method + s[end:]

s = s.replace(
    "    WidgetsBinding.instance.addPostFrameCallback((_) => _autoGenerateCards());\n",
    "    // Card generation is manual-only.\n",
)

auto_start = s.find("  Future<void> _autoGenerateCards() async {")
if auto_start >= 0:
    auto_end = s.find("\n  Future<void> ", auto_start + 5)
    if auto_end > auto_start:
        s = s[:auto_start] + s[auto_end+1:]

replacements = {
    "'Generating cards from the index… $_cardProgress/${AiCardService.defaultTarget}'":
        "'Generating study cards…'",
    "'Generating study cards… $_cardProgress/${AiCardService.defaultTarget}'":
        "'Generating study cards…'",
    "'No indexed study cards yet.'":
        "'No study cards yet.'",
    "'No AI-generated study cards yet.'":
        "'No study cards yet.'",
    "const Text('Generate 50 cards from index')":
        "const Text('Generate study cards')",
    "const Text('Generate 50 AI cards')":
        "const Text('Generate study cards')",
    "Text('Regenerate cards from index')":
        "Text('Regenerate study cards')",
    "Text('Regenerate 50 AI cards')":
        "Text('Regenerate study cards')",
}
for old_text, new_text in replacements.items():
    s = s.replace(old_text, new_text)

p.write_text(s)

print('v172 applied: original StudyEngine card parser restored as manual-only generation')
