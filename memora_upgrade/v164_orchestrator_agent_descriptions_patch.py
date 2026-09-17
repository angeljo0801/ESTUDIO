from pathlib import Path

# v164: show each Agent description anywhere the Orchestrator is choosing or
# recommending Agents, not just the model/provider name.

p = Path('lib/agent_orchestrator_page.dart')
s = p.read_text()

old = """for(final r in recommendations)ListTile(contentPadding:EdgeInsets.zero,title:Text(r.agent.name),subtitle:Text(r.matches.isEmpty?'Coincide con la tarea':'Coincide por: ${r.matches.take(4).join(', ')}'),trailing:p.agentIds.contains(r.agent.id)?const Text('Seleccionado'):TextButton(onPressed:()=>_toggle(r.agent.id,true),child:const Text('Usar')))"""
new = """for(final r in recommendations)ListTile(contentPadding:EdgeInsets.zero,title:Text(r.agent.name),subtitle:Text(r.agent.description.trim().isEmpty?(r.matches.isEmpty?'Coincide con la tarea':'Coincide por: ${r.matches.take(4).join(', ')}'):'${r.agent.description}\\n${r.matches.isEmpty?'Coincide con la tarea':'Coincide por: ${r.matches.take(4).join(', ')}'}'),trailing:p.agentIds.contains(r.agent.id)?const Text('Seleccionado'):TextButton(onPressed:()=>_toggle(r.agent.id,true),child:const Text('Usar')))"""
if old not in s:
    raise SystemExit('v164 recommendation subtitle anchor missing')
s = s.replace(old, new, 1)

old = """for(final a in agents)CheckboxListTile(contentPadding:EdgeInsets.zero,title:Text(a.name),subtitle:Text(memoraAiSourceLabel(a.modelSource)),value:p.agentIds.contains(a.id),onChanged:busy?null:(v)=>_toggle(a.id,v==true))"""
new = """for(final a in agents)CheckboxListTile(contentPadding:EdgeInsets.zero,title:Text(a.name),subtitle:Text(a.description.trim().isEmpty?memoraAiSourceLabel(a.modelSource):'${a.description}\\n${memoraAiSourceLabel(a.modelSource)}'),value:p.agentIds.contains(a.id),onChanged:busy?null:(v)=>_toggle(a.id,v==true))"""
if old not in s:
    raise SystemExit('v164 authorized-agent subtitle anchor missing')
s = s.replace(old, new, 1)

p.write_text(s)
print('v164 applied: Agent descriptions visible in Orchestrator recommendations and authorized list')
