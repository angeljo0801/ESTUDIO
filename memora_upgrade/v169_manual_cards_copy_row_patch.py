from pathlib import Path
import re

# v169: manual-only study card generation + compact chat action row.

# ---------------------------------------------------------------------------
# 1) Study cards are no longer generated automatically when a guide is added.
# The existing Generate cards control inside Guide Detail remains the only trigger.
# ---------------------------------------------------------------------------
p = Path('lib/home_page.dart')
s = p.read_text()

# Remove every post-add automatic generation call injected by v122/v124.
s = re.sub(r'^[ \t]*await _generateCardsFor\([^)]+\);\n', '', s, flags=re.M)

# The Library add/create FAB must remain available and compact. Card generation
# should never take over this FAB or replace its label with generation progress.
s = s.replace(
    "onPressed: _busy ? null : _showAddMenu,",
    "onPressed: _showAddMenu,",
)
s = re.sub(
    r"icon:\s*_busy\s*\?\s*const SizedBox\([^;]+?CircularProgressIndicator\(strokeWidth: 2\)\)\s*:\s*const Icon\(Icons\.add_rounded\),",
    "icon: const Icon(Icons.add_rounded),",
    s,
    flags=re.S,
)
s = re.sub(
    r"label:\s*Text\(_busy\s*\?\s*_busyMessage\s*:\s*'[^']*'\),",
    "label: const Text('Añadir / crear'),",
    s,
)
s = re.sub(
    r"label:\s*Text\(_busy\s*\?\s*'[^']*'\s*:\s*'[^']*'\),",
    "label: const Text('Añadir / crear'),",
    s,
)
p.write_text(s)

# Do not auto-start card generation when an empty guide is opened.
p = Path('lib/guide_detail_page.dart')
s = p.read_text()
s = s.replace(
    "    WidgetsBinding.instance.addPostFrameCallback((_) => _autoGenerateCards());\n",
    "    // Study cards are generated only after the user taps Generate cards.\n",
)
p.write_text(s)

# AI-created and translated guides also wait for the explicit Generate cards action.
for filename, variable in [
    ('lib/guide_creator_page.dart', 'guide'),
    ('lib/guide_translation_page.dart', 'translatedGuide'),
]:
    p = Path(filename)
    if not p.exists():
        continue
    s = p.read_text()
    pattern = re.compile(
        rf"(      await widget\.store\.add\({variable}\);\n)"
        rf"\s*try \{{\n"
        rf"\s*final systemAi = await AiCardService\.systemAi\(\);\n"
        rf"\s*if \(systemAi\.ready\) \{{.*?"
        rf"\s*await widget\.store\.update\({variable}\);\n"
        rf"\s*\}}\n"
        rf"\s*\}} catch \(_\) \{{.*?\n"
        rf"\s*\}}\n",
        re.S,
    )
    s, _ = pattern.subn(r"\1", s, count=1)
    p.write_text(s)

# v168 could rebuild empty card banks during store load. Leave them empty so an
# imported guide never starts receiving cards until the user explicitly requests it.
p = Path('lib/guide_store.dart')
s = p.read_text()
pattern = re.compile(
    r"\s*if \(guide\.cards\.isEmpty && guide\.text\.trim\(\)\.isNotEmpty\) \{\n"
    r"\s*final material = await VectorKnowledgeStore\.buildCoverageContext\(.*?"
    r"\s*guide\.cards = StudyEngine\.buildCards\(material\);\n"
    r"\s*repaired = true;\n"
    r"\s*\}\n",
    re.S,
)
s = pattern.sub("\n", s)
p.write_text(s)

# ---------------------------------------------------------------------------
# 2) Copy is on the same action row as Translate / Auto ES in every shared chat.
# ---------------------------------------------------------------------------
p = Path('lib/chat_widgets.dart')
s = p.read_text()

old = """            if (_canTranslate) ...[
              const SizedBox(height: 4),
              Wrap(
                spacing: 2,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  TextButton.icon(
                    onPressed: _translating ? null : _toggleSpanish,
                    style: TextButton.styleFrom(
                      visualDensity: VisualDensity.compact,
                      padding: const EdgeInsets.symmetric(horizontal: 6),
                    ),
                    icon: const Icon(Icons.translate, size: 17),
                    label: Text(_showSpanish ? 'Original' : 'ES'),
                  ),
                  TextButton.icon(
                    onPressed: () => widget.onAutoSpanishChanged(!widget.autoSpanish),
                    style: TextButton.styleFrom(
                      visualDensity: VisualDensity.compact,
                      padding: const EdgeInsets.symmetric(horizontal: 6),
                    ),
                    icon: Icon(
                      widget.autoSpanish
                          ? Icons.check_circle_outline
                          : Icons.autorenew_rounded,
                      size: 17,
                    ),
                    label: Text(widget.autoSpanish ? 'Auto ES on' : 'Auto ES'),
                  ),
                ],
              ),
            ],
            if (widget.message.text.trim().isNotEmpty) ...[
              const SizedBox(height: 2),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  onPressed: _copyMessage,
                  style: TextButton.styleFrom(
                    visualDensity: VisualDensity.compact,
                    padding: const EdgeInsets.symmetric(horizontal: 6),
                  ),
                  icon: const Icon(Icons.copy_outlined, size: 17),
                  label: const Text('Copiar'),
                ),
              ),
            ],
"""
new = """            if (_canTranslate || widget.message.text.trim().isNotEmpty) ...[
              const SizedBox(height: 4),
              Wrap(
                spacing: 2,
                runSpacing: 0,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  if (_canTranslate)
                    TextButton.icon(
                      onPressed: _translating ? null : _toggleSpanish,
                      style: TextButton.styleFrom(
                        visualDensity: VisualDensity.compact,
                        padding: const EdgeInsets.symmetric(horizontal: 6),
                      ),
                      icon: const Icon(Icons.translate, size: 17),
                      label: Text(_showSpanish ? 'Original' : 'ES'),
                    ),
                  if (_canTranslate)
                    TextButton.icon(
                      onPressed: () => widget.onAutoSpanishChanged(!widget.autoSpanish),
                      style: TextButton.styleFrom(
                        visualDensity: VisualDensity.compact,
                        padding: const EdgeInsets.symmetric(horizontal: 6),
                      ),
                      icon: Icon(
                        widget.autoSpanish
                            ? Icons.check_circle_outline
                            : Icons.autorenew_rounded,
                        size: 17,
                      ),
                      label: Text(widget.autoSpanish ? 'Auto ES on' : 'Auto ES'),
                    ),
                  if (widget.message.text.trim().isNotEmpty)
                    TextButton.icon(
                      onPressed: _copyMessage,
                      style: TextButton.styleFrom(
                        visualDensity: VisualDensity.compact,
                        padding: const EdgeInsets.symmetric(horizontal: 6),
                      ),
                      icon: const Icon(Icons.copy_outlined, size: 17),
                      label: const Text('Copiar'),
                    ),
                ],
              ),
            ],
"""
if old not in s:
    raise SystemExit('v169 chat action-row anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)

print('v169 applied: cards are manual-only; Library FAB stays visible; Copy shares the Translate row')
