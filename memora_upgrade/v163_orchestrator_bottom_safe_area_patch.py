from pathlib import Path

# v163: keep the bottom of the Orchestrator fully reachable above Android's
# system navigation/gesture area. The page remains scrollable and gets a
# device-aware bottom inset plus breathing room.

p = Path('lib/agent_orchestrator_page.dart')
s = p.read_text()

old = "body:ListView(padding:const EdgeInsets.all(16),children:["
new = "body:ListView(padding:EdgeInsets.fromLTRB(16,16,16,MediaQuery.viewPaddingOf(context).bottom+72),children:["

if old not in s:
    raise SystemExit('v163 orchestrator ListView padding anchor missing')

s = s.replace(old, new, 1)
p.write_text(s)

print('v163 applied: Orchestrator bottom content stays above system navigation')
