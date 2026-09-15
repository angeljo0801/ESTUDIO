from pathlib import Path

# -----------------------------------------------------------------------------
# Guide details: expose the translation workflow from every guide.
# -----------------------------------------------------------------------------
p = Path('lib/guide_detail_page.dart')
s = p.read_text()

import_anchor = "import 'guide_file_service.dart';\n"
if import_anchor not in s:
    raise RuntimeError('Guide detail import anchor not found')
if "guide_translation_page.dart" not in s:
    s = s.replace(
        import_anchor,
        import_anchor + "import 'guide_translation_page.dart';\n",
        1,
    )

method_anchor = "  Future<void> _delete() async {\n"
translate_method = """  Future<void> _translateGuide() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => GuideTranslationPage(
          store: widget.store,
          guide: widget.guide,
        ),
      ),
    );
    if (mounted) setState(() {});
  }

"""
if method_anchor not in s:
    raise RuntimeError('Guide detail delete-method anchor not found')
if "Future<void> _translateGuide()" not in s:
    s = s.replace(method_anchor, translate_method + method_anchor, 1)

selected_anchor = "              if (value == 'export') _export();\n"
if selected_anchor not in s:
    raise RuntimeError('Guide detail popup selected anchor not found')
if "if (value == 'translate') _translateGuide();" not in s:
    s = s.replace(
        selected_anchor,
        selected_anchor + "              if (value == 'translate') _translateGuide();\n",
        1,
    )

menu_anchor = "              const PopupMenuItem(value: 'regen',"
if menu_anchor not in s:
    raise RuntimeError('Guide detail popup menu anchor not found')
if "value: 'translate'" not in s:
    s = s.replace(
        menu_anchor,
        "              const PopupMenuItem(value: 'translate', child: Text('Translate guide')),\n" + menu_anchor,
        1,
    )

body_anchor = """          const SizedBox(height: 12),
          Row(
            children: [
"""
body_replacement = """          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: _translateGuide,
            icon: const Icon(Icons.translate_rounded),
            label: const Text('Translate guide'),
            style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(52)),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
"""
if body_anchor not in s:
    raise RuntimeError('Guide detail body translation-button anchor not found')
if "label: const Text('Translate guide')" not in s:
    s = s.replace(body_anchor, body_replacement, 1)

p.write_text(s)

# -----------------------------------------------------------------------------
# AI Settings: one-tap setup for the recommended fast on-device Qwen model.
# -----------------------------------------------------------------------------
p = Path('lib/llm_settings_page.dart')
s = p.read_text()

settings_import_anchor = "import 'package:shared_preferences/shared_preferences.dart';\n"
if settings_import_anchor not in s:
    raise RuntimeError('AI settings import anchor not found')
if "fast_model_setup_page.dart" not in s:
    s = s.replace(
        settings_import_anchor,
        settings_import_anchor + "\nimport 'fast_model_setup_page.dart';\n",
        1,
    )

method_anchor = "  Future<void> _setDeviceMode(String? value) async {\n"
open_method = """  Future<void> _openFastModelSetup() async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const FastModelSetupPage()),
    );
    if (!mounted) return;
    await _load();
  }

"""
if method_anchor not in s:
    raise RuntimeError('AI settings device-mode anchor not found')
if "Future<void> _openFastModelSetup()" not in s:
    s = s.replace(method_anchor, open_method + method_anchor, 1)

device_anchor = """                  if (provider == 'device') ...[
                    const Text(
"""
fast_card = """                  if (provider == 'device') ...[
                    Card(
                      child: ListTile(
                        leading: const Icon(Icons.bolt_rounded),
                        title: const Text('Download a faster on-device model'),
                        subtitle: const Text(
                          'Qwen2.5 1.5B Instruct Q4_K_M • about 1.1 GB • multilingual',
                        ),
                        trailing: const Icon(Icons.chevron_right_rounded),
                        onTap: _openFastModelSetup,
                      ),
                    ),
                    const SizedBox(height: 12),
                    const Text(
"""
if device_anchor not in s:
    raise RuntimeError('AI settings device section anchor not found')
if "Download a faster on-device model" not in s:
    s = s.replace(device_anchor, fast_card, 1)

p.write_text(s)

print('Memora v1.19 guide translation and fast local model setup applied successfully')
