from pathlib import Path
import re

def read(name):
    p = Path('lib') / name
    return p, p.read_text()

def add_import(s):
    marker = "import 'chatgpt_sync_page.dart';"
    return s if marker in s else marker + '\n' + s

# Add the story field ONLY after the old provenance/model migrations have run.
p,s=read('models.dart')
if 'final String adventureStory;' not in s:
    replacements = [
        ("    this.streak = 0,\n", "    this.adventureStory = '',\n    this.streak = 0,\n"),
        ("  final String source;\n", "  final String source;\n  final String adventureStory;\n"),
        ("        'source': source,\n", "        'source': source,\n        'adventureStory': adventureStory,\n"),
        ("        source: (json['source'] as String?) ?? '',\n",
         "        source: (json['source'] as String?) ?? '',\n        adventureStory: (json['adventureStory'] as String?) ?? '',\n"),
    ]
    for old,new in replacements:
        if old not in s:
            raise RuntimeError('Memora-Sync model migration missing anchor: '+old)
        s=s.replace(old,new,1)
    p.write_text(s)

p,s=read('ai_service.dart')
s=add_import(s)
anchor="if (provider == 'openai') {"
if anchor not in s:
    raise RuntimeError('Memora-Sync provider route missing')
branch="""if (provider == 'memora_sync') {
      if (imagePaths.isNotEmpty) {
        throw Exception('Memora-Sync admite texto extraído, no imágenes adjuntas.');
      }
      final result = await _runOnline((client, requestId) => MemoraSyncModel.ask(
        prompt: prompt,
        mode: responseMode,
        cancelled: () => _cancelledOnline.contains(requestId),
      ));
      onPartial?.call(result);
      return result;
    }
    """
s=s.replace(anchor,branch+anchor,1)
p.write_text(s)

p,s=read('llm_settings_page.dart')
# Insert a new card before the existing OpenAI option, after legacy UI patches.
m=re.search(r"_choice\(\s*'openai',",s)
if not m:
    raise RuntimeError('Memora-Sync model selector anchor missing')
choice="""_choice(
                    'memora_sync',
                    Icons.sync_rounded,
                    'ChatGPT · Memora-Sync',
                    'Cola privada sin API de OpenAI. Comparte el texto de la tarea con tu repositorio privado. Configura la conexión en Biblioteca; ChatGPT debe procesar la cola.',
                  ),
                  """
s=s[:m.start()]+choice+s[m.start():]
p.write_text(s)

p,s=read('ai_card_service.dart')
s=add_import(s)
anchor="case 'openai':"
if anchor not in s:
    raise RuntimeError('Memora-Sync card model descriptor missing')
s=s.replace(anchor,"""case 'memora_sync':
        return SystemAiDescriptor(
          provider: 'memora_sync',
          label: 'ChatGPT · Memora-Sync',
          ready: await MemoraSyncModel.configured(),
        );
      """+anchor,1)
p.write_text(s)

# Explicit overrides in screens that offer a dropdown and a provider label.
for name in ['guide_creator_page.dart','agent_page.dart','tutor_page.dart','tutor_context_service.dart','study_plan_page.dart','daily_exam_page.dart']:
    p,s=read(name)
    s=re.sub(r"(?m)^(\s*)'openai',\s*$",r"\1'memora_sync',\n\1'openai',",s) if name in ['agent_page.dart','tutor_page.dart'] else s
    # Avoid inserting new items in sets other than explicit provider sets.
    s=re.sub(r"DropdownMenuItem\(\s*value: 'openai',", "DropdownMenuItem(value: 'memora_sync', child: Text('ChatGPT · Memora-Sync')),\n                    DropdownMenuItem(value: 'openai',",s)
    s=s.replace("case 'openai':","case 'memora_sync':\n        return 'ChatGPT · Memora-Sync';\n      case 'openai':") if name in ['guide_creator_page.dart','agent_page.dart','tutor_page.dart','tutor_context_service.dart'] else s
    p.write_text(s)

# Include a visible status warning and a shortcut for card creation from here.
p,s=read('chatgpt_sync_page.dart')
s=s.replace("Envía solicitudes y progreso de las guías sincronizadas. Tu biblioteca local no se comparte.","Envía solicitudes y progreso de las guías sincronizadas. Al elegir Memora-Sync como IA, el texto de cada tarea se enviará al repositorio privado. No se suben archivos locales automáticamente.")
s=s.replace("const Text('Después pide a ChatGPT revisar Memora-Sync; no se inicia un chat automáticamente.'),","const Text('Después pide a ChatGPT revisar Memora-Sync; no se inicia un chat automáticamente. Para usarlo como modelo, elige ChatGPT · Memora-Sync en Ajustes de IA.'),")
p.write_text(s)
print('Memora-Sync provider integrated after all legacy migrations')
