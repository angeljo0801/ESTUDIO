from pathlib import Path

p = Path('lib/agent_orchestrator_page.dart')
s = p.read_text()
old = "profile=all.where((o)=>o.id==widget.orchestratorId).cast<OrchestratorProfile?>().firstOrNull;profile??=all.isEmpty?null:all.first;"
new = "final matches=all.where((o)=>o.id==widget.orchestratorId).toList();profile=matches.isNotEmpty?matches.first:(all.isEmpty?null:all.first);"
if old not in s:
    raise SystemExit('v160 orchestrator profile lookup anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)
print('v160 applied: multi-orchestrator profile lookup compile-safe')
