from pathlib import Path

# v177: Library owns an independent AI Settings profile.
# Study-card generation itself remains deterministic/local. This Library AI is
# used by the optional FINAL card debugger that reviews suspicious cards.

# ---------------------------------------------------------------------------
# Library dashboard: visible AI Settings button.
# ---------------------------------------------------------------------------
p = Path('lib/home_page.dart')
s = p.read_text()

if "import 'llm_settings_page.dart';" not in s:
    # Add alongside another local page import.
    if "import 'guide_detail_page.dart';\n" in s:
        s = s.replace(
            "import 'guide_detail_page.dart';\n",
            "import 'guide_detail_page.dart';\nimport 'llm_settings_page.dart';\n",
            1,
        )
    else:
        # Fallback after package imports.
        marker = "import 'package:flutter/material.dart';\n"
        if marker not in s:
            raise SystemExit('v177 Home import anchor missing')
        s = s.replace(marker, marker + "\nimport 'llm_settings_page.dart';\n", 1)

app_start = s.find("          appBar: AppBar(")
fab_start = s.find("          floatingActionButton:", app_start)
if app_start < 0 or fab_start < 0:
    raise SystemExit('v177 Home AppBar anchor missing')

app_block = s[app_start:fab_start]
if "LlmSettingsPage(scope: 'library'" not in app_block:
    close = app_block.rfind("          ),")
    if close < 0:
        raise SystemExit('v177 Home AppBar close missing')
    actions = """            actions: [
              IconButton(
                tooltip: 'AI Settings · Library',
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => const LlmSettingsPage(
                      scope: 'library',
                      scopeLabel: 'Biblioteca / Tarjetas',
                    ),
                  ),
                ),
                icon: const Icon(Icons.settings_outlined),
              ),
            ],
"""
    app_block = app_block[:close] + actions + app_block[close:]
    s = s[:app_start] + app_block + s[fab_start:]

p.write_text(s)

# ---------------------------------------------------------------------------
# Final AI card debugger: use Library-scoped provider/model/API settings.
# ---------------------------------------------------------------------------
p = Path('lib/ai_card_review_service.dart')
s = p.read_text()

old = """        final raw = await AiService.askTaskConfigured(
          prompt: prompt,
          providerOverride: 'global',
          settingsScope: 'global',
          responseMode: 'fast',
        ).timeout(
"""
new = """        final raw = await AiService.askTaskConfigured(
          prompt: prompt,
          providerOverride: 'global',
          settingsScope: 'library',
          responseMode: 'fast',
        ).timeout(
"""
if old not in s:
    raise SystemExit('v177 AI card reviewer scope anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)

# ---------------------------------------------------------------------------
# Guide Detail: expose the same Library AI Settings directly from the Generate
# cards dialog so a missing model/API can be fixed without leaving the guide.
# ---------------------------------------------------------------------------
p = Path('lib/guide_detail_page.dart')
s = p.read_text()

if "import 'llm_settings_page.dart';" not in s:
    if "import 'ai_card_review_service.dart';\n" in s:
        s = s.replace(
            "import 'ai_card_review_service.dart';\n",
            "import 'ai_card_review_service.dart';\nimport 'llm_settings_page.dart';\n",
            1,
        )
    else:
        raise SystemExit('v177 GuideDetail import anchor missing')

old_switch = """                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    value: useAiReview,
                    onChanged: (value) =>
                        setDialogState(() => useAiReview = value),
                    title: const Text('AI Final Card Review'),
                    subtitle: const Text(
                      'The configured Memora AI reviews only suspicious cards. It can keep, repair from the exact source, or reject them. If AI is unavailable, local generation still works.',
                    ),
                  ),
"""
new_switch = """                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    value: useAiReview,
                    onChanged: (value) =>
                        setDialogState(() => useAiReview = value),
                    title: const Text('AI Final Card Review'),
                    subtitle: const Text(
                      'Uses the AI configured for Library / Cards to review only suspicious cards. It can keep, repair from the exact source, or reject them.',
                    ),
                  ),
                  if (useAiReview)
                    Align(
                      alignment: Alignment.centerLeft,
                      child: OutlinedButton.icon(
                        onPressed: () => Navigator.of(dialogContext).push(
                          MaterialPageRoute(
                            builder: (_) => const LlmSettingsPage(
                              scope: 'library',
                              scopeLabel: 'Biblioteca / Tarjetas',
                            ),
                          ),
                        ),
                        icon: const Icon(Icons.settings_outlined),
                        label: const Text('AI Settings · Library'),
                      ),
                    ),
"""
if old_switch not in s:
    raise SystemExit('v177 Generate-card AI switch anchor missing')
s = s.replace(old_switch, new_switch, 1)
p.write_text(s)

print('v177 applied: Library AI Settings now control final card review')
