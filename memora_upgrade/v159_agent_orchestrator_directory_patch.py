from pathlib import Path

# v159: turn the Agents tab into a directory of independent Agents and
# Orchestrators. Chats open per Agent. Multiple Orchestrators are supported and
# each keeps its own model, instructions and authorized Agents. Recommendations
# remain optional and never create/select Agents automatically.

profiles = r'''import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

const Set<String> memoraAiSources = {
  'global', 'private', 'shared', 'gemini', 'openai', 'local',
};

String memoraAiSourceLabel(String value) {
  switch (value) {
    case 'private': return 'GGUF privado';
    case 'shared': return 'GGUF compartido';
    case 'gemini': return 'Gemini';
    case 'openai': return 'OpenAI / compatible';
    case 'local': return 'Ollama / servidor local';
    default: return 'Configuración general';
  }
}

class AgentProfile {
  const AgentProfile({
    required this.id,
    required this.name,
    required this.prompt,
    this.modelSource = 'global',
    this.guideIds = const [],
  });
  final String id;
  final String name;
  final String prompt;
  final String modelSource;
  final List<String> guideIds;

  AgentProfile copyWith({String? name, String? prompt, String? modelSource, List<String>? guideIds}) => AgentProfile(
    id: id,
    name: name ?? this.name,
    prompt: prompt ?? this.prompt,
    modelSource: modelSource ?? this.modelSource,
    guideIds: guideIds ?? this.guideIds,
  );

  Map<String,dynamic> toJson() => {
    'id': id, 'name': name, 'prompt': prompt,
    'modelSource': modelSource, 'guideIds': guideIds,
  };

  factory AgentProfile.fromJson(Map<String,dynamic> json) {
    final source = json['modelSource']?.toString() ?? 'global';
    final rawGuides = json['guideIds'];
    return AgentProfile(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? 'Agente',
      prompt: json['prompt']?.toString() ?? '',
      modelSource: memoraAiSources.contains(source) ? source : 'global',
      guideIds: rawGuides is List ? rawGuides.map((e)=>e.toString()).where((e)=>e.isNotEmpty).toList() : const [],
    );
  }
}

class OrchestratorProfile {
  const OrchestratorProfile({
    required this.id,
    required this.name,
    required this.description,
    required this.prompt,
    this.modelSource = 'global',
    this.agentIds = const [],
  });
  final String id;
  final String name;
  final String description;
  final String prompt;
  final String modelSource;
  final List<String> agentIds;

  OrchestratorProfile copyWith({String? name, String? description, String? prompt, String? modelSource, List<String>? agentIds}) => OrchestratorProfile(
    id: id,
    name: name ?? this.name,
    description: description ?? this.description,
    prompt: prompt ?? this.prompt,
    modelSource: modelSource ?? this.modelSource,
    agentIds: agentIds ?? this.agentIds,
  );

  Map<String,dynamic> toJson() => {
    'id': id, 'name': name, 'description': description, 'prompt': prompt,
    'modelSource': modelSource, 'agentIds': agentIds,
  };

  factory OrchestratorProfile.fromJson(Map<String,dynamic> json) {
    final source = json['modelSource']?.toString() ?? 'global';
    final rawIds = json['agentIds'];
    return OrchestratorProfile(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? 'Orquestador',
      description: json['description']?.toString() ?? '',
      prompt: json['prompt']?.toString() ?? 'Coordina los agentes seleccionados y entrega un resultado final coherente.',
      modelSource: memoraAiSources.contains(source) ? source : 'global',
      agentIds: rawIds is List ? rawIds.map((e)=>e.toString()).where((e)=>e.isNotEmpty).toList() : const [],
    );
  }
}

class AgentProfileStore {
  static const key = 'memora_agent_profiles_v1';
  static Future<List<AgentProfile>> load() async {
    final p = await SharedPreferences.getInstance();
    final raw = p.getString(key);
    if (raw == null || raw.trim().isEmpty) return [];
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! List) return [];
      return decoded.whereType<Map>().map((e)=>AgentProfile.fromJson(Map<String,dynamic>.from(e))).where((a)=>a.id.isNotEmpty).toList();
    } catch (_) { return []; }
  }
  static Future<void> save(List<AgentProfile> items) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(key, jsonEncode(items.map((e)=>e.toJson()).toList()));
  }
}

class OrchestratorProfileStore {
  static const key = 'memora_orchestrator_profiles_v1';
  static const legacyEnabledKey = 'memora_orchestrator_enabled_agent_ids_v1';
  static Future<List<OrchestratorProfile>> load() async {
    final p = await SharedPreferences.getInstance();
    final raw = p.getString(key);
    if (raw != null && raw.trim().isNotEmpty) {
      try {
        final decoded = jsonDecode(raw);
        if (decoded is List) {
          return decoded.whereType<Map>().map((e)=>OrchestratorProfile.fromJson(Map<String,dynamic>.from(e))).where((o)=>o.id.isNotEmpty).toList();
        }
      } catch (_) {}
    }
    final legacy = p.getStringList(legacyEnabledKey) ?? const <String>[];
    if (legacy.isEmpty) return [];
    final first = OrchestratorProfile(
      id: 'orch_${DateTime.now().microsecondsSinceEpoch}',
      name: 'Orquestador principal',
      description: 'Migrado desde el Orquestador original de Memora.',
      prompt: 'Coordina los agentes autorizados y entrega un resultado final coherente.',
      agentIds: legacy,
    );
    await save([first]);
    return [first];
  }
  static Future<void> save(List<OrchestratorProfile> items) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(key, jsonEncode(items.map((e)=>e.toJson()).toList()));
  }
}
'''

agent_page = r'''import 'package:flutter/material.dart';

import 'agent_profiles.dart';
import 'agent_orchestrator_page.dart';
import 'ai_service.dart';
import 'chat_store.dart';
import 'chat_widgets.dart';
import 'guide_store.dart';
import 'knowledge_retriever.dart';
import 'llm_settings_page.dart';

export 'agent_profiles.dart';

class AgentPage extends StatefulWidget {
  const AgentPage({super.key, required this.store});
  final GuideStore store;
  @override State<AgentPage> createState() => _AgentPageState();
}

class _AgentPageState extends State<AgentPage> {
  List<AgentProfile> agents = [];
  List<OrchestratorProfile> orchestrators = [];
  bool loading = true;

  @override void initState(){ super.initState(); _load(); }
  Future<void> _load() async {
    agents = await AgentProfileStore.load();
    orchestrators = await OrchestratorProfileStore.load();
    if (mounted) setState(()=>loading=false);
  }

  Future<AgentProfile?> _agentDialog({AgentProfile? existing}) async {
    final name = TextEditingController(text: existing?.name ?? '');
    final prompt = TextEditingController(text: existing?.prompt ?? '');
    var source = existing?.modelSource ?? 'global';
    final result = await showDialog<AgentProfile>(context: context, builder: (dc)=>StatefulBuilder(
      builder:(context,setD)=>AlertDialog(
        title: Text(existing==null?'Crear agente':'Editar agente'),
        content: SingleChildScrollView(child: Column(mainAxisSize:MainAxisSize.min,children:[
          TextField(controller:name,decoration:const InputDecoration(labelText:'Nombre del agente')),
          const SizedBox(height:12),
          TextField(controller:prompt,minLines:5,maxLines:10,decoration:const InputDecoration(labelText:'Prompt / función',alignLabelWithHint:true)),
          const SizedBox(height:12),
          DropdownButtonFormField<String>(initialValue:source,decoration:const InputDecoration(labelText:'IA / modelo'),items:[
            for(final s in memoraAiSources) DropdownMenuItem(value:s,child:Text(memoraAiSourceLabel(s))),
          ],onChanged:(v)=>setD(()=>source=v??'global')),
        ])),
        actions:[
          TextButton(onPressed:()=>Navigator.pop(dc),child:const Text('Cancelar')),
          FilledButton(onPressed:(){
            if(name.text.trim().isEmpty||prompt.text.trim().isEmpty)return;
            Navigator.pop(dc,AgentProfile(
              id:existing?.id??'agent_${DateTime.now().microsecondsSinceEpoch}',
              name:name.text.trim(),prompt:prompt.text.trim(),modelSource:source,
              guideIds:existing?.guideIds??const [],
            ));
          },child:const Text('Guardar')),
        ],
      ),
    ));
    name.dispose(); prompt.dispose(); return result;
  }

  Future<OrchestratorProfile?> _orchestratorDialog({OrchestratorProfile? existing}) async {
    final name = TextEditingController(text: existing?.name ?? '');
    final description = TextEditingController(text: existing?.description ?? '');
    final prompt = TextEditingController(text: existing?.prompt ?? 'Coordina los agentes seleccionados y entrega un resultado final coherente.');
    var source = existing?.modelSource ?? 'global';
    final result = await showDialog<OrchestratorProfile>(context:context,builder:(dc)=>StatefulBuilder(
      builder:(context,setD)=>AlertDialog(
        title:Text(existing==null?'Crear orquestador':'Editar orquestador'),
        content:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[
          TextField(controller:name,decoration:const InputDecoration(labelText:'Nombre')),
          const SizedBox(height:12),
          TextField(controller:description,minLines:2,maxLines:4,decoration:const InputDecoration(labelText:'Descripción')),
          const SizedBox(height:12),
          TextField(controller:prompt,minLines:4,maxLines:8,decoration:const InputDecoration(labelText:'Instrucciones del orquestador',alignLabelWithHint:true)),
          const SizedBox(height:12),
          DropdownButtonFormField<String>(initialValue:source,decoration:const InputDecoration(labelText:'IA / modelo del orquestador'),items:[
            for(final s in memoraAiSources) DropdownMenuItem(value:s,child:Text(memoraAiSourceLabel(s))),
          ],onChanged:(v)=>setD(()=>source=v??'global')),
        ])),
        actions:[
          TextButton(onPressed:()=>Navigator.pop(dc),child:const Text('Cancelar')),
          FilledButton(onPressed:(){
            if(name.text.trim().isEmpty)return;
            Navigator.pop(dc,OrchestratorProfile(
              id:existing?.id??'orch_${DateTime.now().microsecondsSinceEpoch}',
              name:name.text.trim(),description:description.text.trim(),prompt:prompt.text.trim(),modelSource:source,
              agentIds:existing?.agentIds??const [],
            ));
          },child:const Text('Guardar')),
        ],
      ),
    ));
    name.dispose(); description.dispose(); prompt.dispose(); return result;
  }

  Future<void> _createAgent() async { final x=await _agentDialog(); if(x==null)return; agents=[...agents,x]; await AgentProfileStore.save(agents); if(mounted)setState((){}); }
  Future<void> _editAgent(AgentProfile a) async { final x=await _agentDialog(existing:a); if(x==null)return; agents=[for(final e in agents) if(e.id==a.id)x else e]; await AgentProfileStore.save(agents); if(mounted)setState((){}); }
  Future<void> _deleteAgent(AgentProfile a) async {
    final yes=await showDialog<bool>(context:context,builder:(c)=>AlertDialog(title:const Text('Eliminar agente'),content:Text('¿Eliminar a ${a.name}?'),actions:[TextButton(onPressed:()=>Navigator.pop(c,false),child:const Text('Cancelar')),FilledButton(onPressed:()=>Navigator.pop(c,true),child:const Text('Eliminar'))]));
    if(yes!=true)return; agents=agents.where((e)=>e.id!=a.id).toList(); await AgentProfileStore.save(agents);
    orchestrators=[for(final o in orchestrators)o.copyWith(agentIds:o.agentIds.where((id)=>id!=a.id).toList())]; await OrchestratorProfileStore.save(orchestrators); if(mounted)setState((){});
  }
  Future<void> _assignGuides(AgentProfile a) async {
    final work=a.guideIds.toSet();
    final result=await showModalBottomSheet<Set<String>>(context:context,isScrollControlled:true,builder:(bc)=>StatefulBuilder(builder:(context,setS)=>SafeArea(child:SizedBox(height:MediaQuery.of(context).size.height*.8,child:Column(children:[
      const Padding(padding:EdgeInsets.all(16),child:Text('Bases de conocimiento',style:TextStyle(fontSize:20,fontWeight:FontWeight.bold))),
      Expanded(child:widget.store.guides.isEmpty?const Center(child:Text('No hay guías en la biblioteca.')):ListView(children:[for(final g in widget.store.guides)CheckboxListTile(value:work.contains(g.id),title:Text(g.title),subtitle:Text(g.sourceType.toUpperCase()),onChanged:(v)=>setS(()=>v==true?work.add(g.id):work.remove(g.id)))])),
      Padding(padding:const EdgeInsets.all(16),child:FilledButton(onPressed:()=>Navigator.pop(bc,work),child:Text('Guardar ${work.length} base(s)'))),
    ])))));
    if(result==null)return; final updated=a.copyWith(guideIds:result.toList()); agents=[for(final e in agents)if(e.id==a.id)updated else e]; await AgentProfileStore.save(agents); if(mounted)setState((){});
  }
  Future<void> _createOrchestrator() async { final x=await _orchestratorDialog(); if(x==null)return; orchestrators=[...orchestrators,x]; await OrchestratorProfileStore.save(orchestrators); if(mounted)setState((){}); }
  Future<void> _editOrchestrator(OrchestratorProfile o) async { final x=await _orchestratorDialog(existing:o); if(x==null)return; orchestrators=[for(final e in orchestrators)if(e.id==o.id)x else e]; await OrchestratorProfileStore.save(orchestrators); if(mounted)setState((){}); }
  Future<void> _deleteOrchestrator(OrchestratorProfile o) async { final yes=await showDialog<bool>(context:context,builder:(c)=>AlertDialog(title:const Text('Eliminar orquestador'),content:Text('¿Eliminar ${o.name}?'),actions:[TextButton(onPressed:()=>Navigator.pop(c,false),child:const Text('Cancelar')),FilledButton(onPressed:()=>Navigator.pop(c,true),child:const Text('Eliminar'))])); if(yes!=true)return; orchestrators=orchestrators.where((e)=>e.id!=o.id).toList(); await OrchestratorProfileStore.save(orchestrators); if(mounted)setState((){}); }

  Future<void> _openAgentChat(AgentProfile a) async { await Navigator.push(context,MaterialPageRoute(builder:(_)=>AgentChatPage(store:widget.store,agent:a))); await _load(); }
  Future<void> _openOrchestrator(OrchestratorProfile o) async { await Navigator.push(context,MaterialPageRoute(builder:(_)=>AgentOrchestratorPage(store:widget.store,orchestratorId:o.id))); await _load(); }

  @override Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(title:const Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('Agentes'),Text('Orquestadores y agentes',style:TextStyle(fontSize:12,fontWeight:FontWeight.normal))]),actions:[IconButton(tooltip:'Ajustes de IA',onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const LlmSettingsPage())),icon:const Icon(Icons.settings_outlined))]),
    body:loading?const Center(child:CircularProgressIndicator()):ListView(padding:const EdgeInsets.fromLTRB(16,14,16,110),children:[
      _SectionTitle(title:'Orquestadores',subtitle:'Puedes crear varios. Cada uno tiene su propia IA, instrucciones y agentes.',onAdd:_createOrchestrator,addLabel:'Crear orquestador'),
      if(orchestrators.isEmpty)const _EmptyCard(icon:Icons.account_tree_outlined,text:'Todavía no has creado orquestadores.'),
      for(final o in orchestrators)_DirectoryCard(icon:Icons.account_tree_outlined,title:o.name,subtitle:'${memoraAiSourceLabel(o.modelSource)} • ${o.agentIds.length} agente(s)',onTap:()=>_openOrchestrator(o),trailing:[IconButton(tooltip:'Abrir',onPressed:()=>_openOrchestrator(o),icon:const Icon(Icons.arrow_forward_rounded)),PopupMenuButton<String>(onSelected:(v){if(v=='edit')_editOrchestrator(o);if(v=='delete')_deleteOrchestrator(o);},itemBuilder:(_)=>const[PopupMenuItem(value:'edit',child:Text('Editar')),PopupMenuItem(value:'delete',child:Text('Eliminar'))])]),
      const SizedBox(height:22),
      _SectionTitle(title:'Agentes',subtitle:'Toca un agente o el botón de chat para hablar con él.',onAdd:_createAgent,addLabel:'Crear agente'),
      if(agents.isEmpty)const _EmptyCard(icon:Icons.smart_toy_outlined,text:'Todavía no has creado agentes.'),
      for(final a in agents)_DirectoryCard(icon:Icons.smart_toy_outlined,title:a.name,subtitle:'${memoraAiSourceLabel(a.modelSource)} • ${a.guideIds.length} base(s)',onTap:()=>_openAgentChat(a),trailing:[IconButton(tooltip:'Chat',onPressed:()=>_openAgentChat(a),icon:const Icon(Icons.chat_bubble_outline)),PopupMenuButton<String>(onSelected:(v){if(v=='edit')_editAgent(a);if(v=='bases')_assignGuides(a);if(v=='delete')_deleteAgent(a);},itemBuilder:(_)=>const[PopupMenuItem(value:'edit',child:Text('Editar')),PopupMenuItem(value:'bases',child:Text('Bases de conocimiento')),PopupMenuItem(value:'delete',child:Text('Eliminar'))])]),
    ]),
  );
}

class _SectionTitle extends StatelessWidget { const _SectionTitle({required this.title,required this.subtitle,required this.onAdd,required this.addLabel}); final String title,subtitle,addLabel; final VoidCallback onAdd; @override Widget build(BuildContext context)=>Padding(padding:const EdgeInsets.only(bottom:10),child:Row(crossAxisAlignment:CrossAxisAlignment.start,children:[Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(title,style:const TextStyle(fontSize:21,fontWeight:FontWeight.w800)),const SizedBox(height:3),Text(subtitle)])),const SizedBox(width:8),FilledButton.tonalIcon(onPressed:onAdd,icon:const Icon(Icons.add),label:Text(addLabel))])); }
class _EmptyCard extends StatelessWidget { const _EmptyCard({required this.icon,required this.text}); final IconData icon; final String text; @override Widget build(BuildContext context)=>Card(child:Padding(padding:const EdgeInsets.all(22),child:Row(children:[Icon(icon,size:30),const SizedBox(width:12),Expanded(child:Text(text))]))); }
class _DirectoryCard extends StatelessWidget { const _DirectoryCard({required this.icon,required this.title,required this.subtitle,required this.onTap,required this.trailing}); final IconData icon; final String title,subtitle; final VoidCallback onTap; final List<Widget> trailing; @override Widget build(BuildContext context)=>Card(elevation:3,margin:const EdgeInsets.only(bottom:11),clipBehavior:Clip.antiAlias,child:InkWell(onTap:onTap,child:Padding(padding:const EdgeInsets.symmetric(horizontal:14,vertical:14),child:Row(children:[Container(width:48,height:48,decoration:BoxDecoration(color:Theme.of(context).colorScheme.primaryContainer,borderRadius:BorderRadius.circular(15)),child:Icon(icon)),const SizedBox(width:12),Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(title,style:const TextStyle(fontSize:17,fontWeight:FontWeight.w700)),const SizedBox(height:3),Text(subtitle,maxLines:2,overflow:TextOverflow.ellipsis)])),...trailing])))); }

class AgentChatPage extends StatefulWidget {
  const AgentChatPage({super.key,required this.store,required this.agent});
  final GuideStore store; final AgentProfile agent;
  @override State<AgentChatPage> createState()=>_AgentChatPageState();
}
class _AgentChatPageState extends State<AgentChatPage>{
  final input=TextEditingController(); List<ChatSession> chats=[]; String? activeId; bool busy=false; String responseMode='normal';
  ChatSession? get active=>chats.isEmpty?null:chats.firstWhere((c)=>c.id==activeId,orElse:()=>chats.first);
  @override void initState(){super.initState();_load();} @override void dispose(){input.dispose();super.dispose();}
  Future<void> _load()async{var x=await ChatStore.listFor('agent',widget.agent.id);if(x.isEmpty){x=[ChatSession.empty(ownerType:'agent',ownerId:widget.agent.id)];await ChatStore.save(x.first);}if(mounted)setState((){chats=x;activeId=x.first.id;});}
  void _put(ChatSession c){final x=List<ChatSession>.from(chats);final i=x.indexWhere((e)=>e.id==c.id);if(i<0)x.insert(0,c);else x[i]=c;if(mounted)setState((){chats=x;activeId=c.id;});}
  Future<void> _newChat()async{if(busy)return;final c=ChatSession.empty(ownerType:'agent',ownerId:widget.agent.id);await ChatStore.save(c);_put(c);}
  Future<void> _export(ChatSession c)async{if(c.messages.isEmpty)return;await ChatStore.exportPdf(c,participantName:widget.agent.name);if(mounted)ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('Chat exportado como PDF.')));}
  Future<void> _delete(ChatSession c)async{await ChatStore.delete(c.id);await _load();}
  Future<void> _history()async{await showModalBottomSheet<void>(context:context,isScrollControlled:true,builder:(bc)=>SafeArea(child:SizedBox(height:MediaQuery.of(bc).size.height*.72,child:Column(children:[Padding(padding:const EdgeInsets.all(12),child:Row(children:[const Expanded(child:Text('Historial',style:TextStyle(fontSize:20,fontWeight:FontWeight.bold))),IconButton(onPressed:(){Navigator.pop(bc);_newChat();},icon:const Icon(Icons.add_comment_outlined))])),Expanded(child:ListView(children:[for(final c in chats)ListTile(title:Text(c.title),subtitle:Text('${c.messages.length} mensaje(s)'),onTap:(){setState(()=>activeId=c.id);Navigator.pop(bc);},trailing:Wrap(children:[IconButton(onPressed:()=>_export(c),icon:const Icon(Icons.picture_as_pdf_outlined)),IconButton(onPressed:(){Navigator.pop(bc);_delete(c);},icon:const Icon(Icons.delete_outline))]))]))]))));}
  Future<void> _send()async{final q=input.text.trim(),c=active;if(q.isEmpty||c==null||busy)return;input.clear();var msgs=List<ChatMessage>.from(c.messages)..add(ChatMessage(role:'user',text:q,createdAt:DateTime.now()))..add(ChatMessage(role:'assistant',text:'Pensando…',createdAt:DateTime.now()));var cur=c.copyWith(title:c.messages.isEmpty?ChatSession.titleFrom(q):c.title,updatedAt:DateTime.now(),messages:msgs);_put(cur);setState(()=>busy=true);try{final guides=widget.store.guides.where((g)=>widget.agent.guideIds.contains(g.id)).toList();final ctx=KnowledgeRetriever.buildContext(guides:guides,query:q,maxChars:responseMode=='fast'?4500:responseMode=='deep'?12000:8000,maxChunks:responseMode=='fast'?4:responseMode=='deep'?10:6,allowUnmatchedFallback:false);final history=cur.conversationContext(maxChars:6500,maxMessages:14);final r=await AiService.askConfigured(providerOverride:widget.agent.modelSource,responseMode:responseMode,onPartial:(p){if(!mounted||p.isEmpty)return;final a=active;if(a==null)return;final m=List<ChatMessage>.from(a.messages);m[m.length-1]=m.last.copyWith(text:p);_put(a.copyWith(updatedAt:DateTime.now(),messages:m));},prompt:'''Eres ${widget.agent.name}, un agente personalizado de Memora.\nFUNCIÓN DEL AGENTE:\n${widget.agent.prompt}\n\nCONVERSACIÓN:\n$history\n\nBASES ASIGNADAS RELEVANTES:\n$ctx\n\nSOLICITUD:\n$q\nResponde siguiendo la función del agente. Si un dato debería venir de sus bases y no aparece, indícalo en vez de inventarlo.''');final a=active;if(a!=null){final m=List<ChatMessage>.from(a.messages);m[m.length-1]=m.last.copyWith(text:r);cur=a.copyWith(updatedAt:DateTime.now(),messages:m);_put(cur);await ChatStore.save(cur);}}catch(e){final a=active;if(a!=null){final m=List<ChatMessage>.from(a.messages);m[m.length-1]=m.last.copyWith(text:'No pude responder: ${AiService.userFacingError(e)}');cur=a.copyWith(updatedAt:DateTime.now(),messages:m);_put(cur);await ChatStore.save(cur);}}finally{if(mounted)setState(()=>busy=false);}}
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(widget.agent.name),Text(memoraAiSourceLabel(widget.agent.modelSource),style:const TextStyle(fontSize:12,fontWeight:FontWeight.normal))]),actions:[IconButton(tooltip:'Nuevo chat',onPressed:busy?null:_newChat,icon:const Icon(Icons.add_comment_outlined)),IconButton(tooltip:'Historial',onPressed:busy?null:_history,icon:const Icon(Icons.history)),IconButton(tooltip:'Exportar PDF',onPressed:active==null?null:()=>_export(active!),icon:const Icon(Icons.picture_as_pdf_outlined))]),body:Column(children:[Padding(padding:const EdgeInsets.fromLTRB(12,8,12,4),child:SegmentedButton<String>(segments:const[ButtonSegment(value:'fast',label:Text('Fast')),ButtonSegment(value:'normal',label:Text('Normal')),ButtonSegment(value:'deep',label:Text('Deep'))],selected:{responseMode},onSelectionChanged:busy?null:(v)=>setState(()=>responseMode=v.first))),Expanded(child:ChatTranscript(messages:active?.messages??const [],participantName:widget.agent.name,emptyText:'Empieza un chat con ${widget.agent.name}.')),SafeArea(top:false,child:Padding(padding:const EdgeInsets.fromLTRB(12,8,12,12),child:Row(children:[Expanded(child:TextField(controller:input,minLines:1,maxLines:5,decoration:const InputDecoration(hintText:'Escribe un mensaje…'),onSubmitted:(_)=>_send())),const SizedBox(width:8),busy?IconButton(onPressed:AiService.cancelCurrent,icon:const Icon(Icons.stop_circle_outlined)):IconButton(onPressed:_send,icon:const Icon(Icons.send_rounded))])))]));
}
'''

orchestrator = r'''import 'package:flutter/material.dart';

import 'agent_profiles.dart';
import 'ai_service.dart';
import 'chat_store.dart';
import 'guide_store.dart';
import 'knowledge_retriever.dart';
import 'llm_settings_page.dart';

class AgentOrchestratorPage extends StatefulWidget {
  const AgentOrchestratorPage({super.key,required this.store,required this.orchestratorId});
  final GuideStore store; final String orchestratorId;
  @override State<AgentOrchestratorPage> createState()=>_AgentOrchestratorPageState();
}
class _Recommendation { const _Recommendation(this.agent,this.score,this.matches); final AgentProfile agent; final int score; final List<String> matches; }
class _AgentOrchestratorPageState extends State<AgentOrchestratorPage>{
  final input=TextEditingController(); List<AgentProfile> agents=[]; List<OrchestratorProfile> all=[]; OrchestratorProfile? profile; List<_Recommendation> recommendations=[]; List<String> suggestedRoles=[]; List<String> trace=[]; String answer='Describe un trabajo complejo.'; bool busy=false; List<ChatSession> chats=[]; String? activeChatId;
  ChatSession? get activeChat=>chats.isEmpty?null:chats.firstWhere((c)=>c.id==activeChatId,orElse:()=>chats.first);
  @override void initState(){super.initState();_load();}@override void dispose(){input.dispose();super.dispose();}
  Future<void> _load()async{agents=await AgentProfileStore.load();all=await OrchestratorProfileStore.load();profile=all.where((o)=>o.id==widget.orchestratorId).cast<OrchestratorProfile?>().firstOrNull;profile??=all.isEmpty?null:all.first;var x=await ChatStore.listFor('orchestrator',widget.orchestratorId);if(x.isEmpty){x=[ChatSession.empty(ownerType:'orchestrator',ownerId:widget.orchestratorId)];await ChatStore.save(x.first);}chats=x;activeChatId=x.first.id;if(mounted)setState((){});}
  Future<void> _saveProfile(OrchestratorProfile updated)async{profile=updated;all=[for(final o in all)if(o.id==updated.id)updated else o];await OrchestratorProfileStore.save(all);if(mounted)setState((){});}
  Set<String> _words(String text)=>RegExp(r'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+').allMatches(text.toLowerCase()).map((m)=>m.group(0)??'').where((w)=>w.length>=4).toSet();
  void _recommend(){final task=input.text.trim();if(task.isEmpty){ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('Escribe primero la tarea.')));return;}final tw=_words(task);final ranked=< _Recommendation>[];for(final a in agents){final aw=_words('${a.name} ${a.prompt}');final hits=tw.where(aw.contains).toList()..sort();var score=hits.length;if(task.toLowerCase().contains(a.name.toLowerCase()))score+=5;if(score>0)ranked.add(_Recommendation(a,score,hits));}ranked.sort((a,b)=>b.score.compareTo(a.score));final lower=task.toLowerCase();final roles=<String>[];final hay=agents.map((a)=>'${a.name} ${a.prompt}'.toLowerCase()).join(' ');void s(List<String>tr,List<String>have,String role){if(tr.any(lower.contains)&&!have.any(hay.contains))roles.add(role);}s(['dato','data','excel','estadíst'],['dato','data','analista'],'Analista de datos');s(['finanza','presupuesto','gasto','rentabilidad'],['finanza','contable'],'Analista financiero');s(['código','codigo','flutter','android','software'],['desarroll','program','software'],'Desarrollador de software');s(['informe','reporte','documento'],['redactor','informe'],'Redactor de informes');setState((){recommendations=ranked.take(4).toList();suggestedRoles=roles.take(3).toList();});}
  Future<void> _toggle(String id,bool value)async{final p=profile;if(p==null)return;final ids=p.agentIds.toSet();value?ids.add(id):ids.remove(id);await _saveProfile(p.copyWith(agentIds:ids.toList()));}
  Future<void> _edit()async{final p=profile;if(p==null)return;final name=TextEditingController(text:p.name),desc=TextEditingController(text:p.description),prompt=TextEditingController(text:p.prompt);var source=p.modelSource;final updated=await showDialog<OrchestratorProfile>(context:context,builder:(dc)=>StatefulBuilder(builder:(context,setD)=>AlertDialog(title:const Text('Configurar orquestador'),content:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[TextField(controller:name,decoration:const InputDecoration(labelText:'Nombre')),const SizedBox(height:12),TextField(controller:desc,minLines:2,maxLines:4,decoration:const InputDecoration(labelText:'Descripción')),const SizedBox(height:12),TextField(controller:prompt,minLines:4,maxLines:8,decoration:const InputDecoration(labelText:'Instrucciones',alignLabelWithHint:true)),const SizedBox(height:12),DropdownButtonFormField<String>(initialValue:source,decoration:const InputDecoration(labelText:'IA / modelo'),items:[for(final s in memoraAiSources)DropdownMenuItem(value:s,child:Text(memoraAiSourceLabel(s)))],onChanged:(v)=>setD(()=>source=v??'global'))])),actions:[TextButton(onPressed:()=>Navigator.pop(dc),child:const Text('Cancelar')),FilledButton(onPressed:()=>Navigator.pop(dc,p.copyWith(name:name.text.trim().isEmpty?p.name:name.text.trim(),description:desc.text.trim(),prompt:prompt.text.trim(),modelSource:source)),child:const Text('Guardar'))])));name.dispose();desc.dispose();prompt.dispose();if(updated!=null)await _saveProfile(updated);}
  void _putChat(ChatSession c){final x=List<ChatSession>.from(chats);final i=x.indexWhere((e)=>e.id==c.id);if(i<0)x.insert(0,c);else x[i]=c;if(mounted)setState((){chats=x;activeChatId=c.id;});}
  Future<void> _newChat()async{if(busy)return;final c=ChatSession.empty(ownerType:'orchestrator',ownerId:widget.orchestratorId);await ChatStore.save(c);_putChat(c);answer='Describe un trabajo complejo.';trace=[];if(mounted)setState((){});}
  Future<void> _history()async{await showModalBottomSheet<void>(context:context,isScrollControlled:true,builder:(bc)=>SafeArea(child:SizedBox(height:MediaQuery.of(bc).size.height*.72,child:Column(children:[const Padding(padding:EdgeInsets.all(14),child:Text('Historial del orquestador',style:TextStyle(fontSize:20,fontWeight:FontWeight.bold))),Expanded(child:ListView(children:[for(final c in chats)ListTile(title:Text(c.title),subtitle:Text('${c.messages.length} mensaje(s)'),onTap:(){setState(()=>activeChatId=c.id);final last=c.messages.where((m)=>m.role=='assistant').toList();answer=last.isEmpty?'Describe un trabajo complejo.':last.last.text;Navigator.pop(bc);},trailing:IconButton(onPressed:()=>ChatStore.exportPdf(c,participantName:profile?.name??'Orquestador'),icon:const Icon(Icons.picture_as_pdf_outlined)))]))]))));}
  Future<void> _run()async{final p=profile,task=input.text.trim();if(p==null||task.isEmpty||busy)return;final chosen=agents.where((a)=>p.agentIds.contains(a.id)).toList();if(chosen.isEmpty){setState(()=>answer='Selecciona al menos un agente autorizado. Las recomendaciones nunca se aplican automáticamente.');return;}setState((){busy=true;trace=[];answer='Planificando y delegando…';});try{var shared='';for(final a in chosen){if(mounted)setState(()=>trace.add('${a.name}: trabajando…'));final guides=widget.store.guides.where((g)=>a.guideIds.contains(g.id)).toList();final ctx=guides.isEmpty?'':KnowledgeRetriever.buildContext(guides:guides,query:task,maxChars:5000,maxChunks:5,allowUnmatchedFallback:false);final r=await AiService.askConfigured(providerOverride:a.modelSource,responseMode:'normal',prompt:'''Eres ${a.name}, agente de un equipo coordinado por ${p.name}.\nTU FUNCIÓN:\n${a.prompt}\nTRABAJO GENERAL:\n$task\nRESULTADOS PREVIOS:\n$shared\nBASE ASIGNADA:\n$ctx\nRealiza la parte que corresponde a tu especialidad y devuelve resultados concretos.''');shared+='\n\n[${a.name}]\n$r';if(mounted)setState(()=>trace[trace.length-1]='${a.name}: completado');}final history=activeChat?.conversationContext(maxChars:3500,maxMessages:8)??'';final finalResult=await AiService.askConfigured(providerOverride:p.modelSource,responseMode:'deep',prompt:'''Eres ${p.name}, un orquestador de Memora.\nDESCRIPCIÓN:\n${p.description}\nINSTRUCCIONES:\n${p.prompt}\nHISTORIAL:\n$history\nSOLICITUD:\n$task\nTRABAJO DE LOS AGENTES:\n$shared\nIntegra todo en un resultado final coherente. No inventes resultados que los agentes no proporcionaron.''');answer=finalResult;var c=activeChat??ChatSession.empty(ownerType:'orchestrator',ownerId:widget.orchestratorId);final first=c.messages.isEmpty;c=c.copyWith(title:first?ChatSession.titleFrom(task):c.title,updatedAt:DateTime.now(),messages:[...c.messages,ChatMessage(role:'user',text:task,createdAt:DateTime.now()),ChatMessage(role:'assistant',text:finalResult,createdAt:DateTime.now())]);_putChat(c);await ChatStore.save(c);if(mounted)setState((){});}catch(e){if(mounted)setState(()=>answer='El Orquestador no pudo terminar: ${AiService.userFacingError(e)}');}finally{if(mounted)setState(()=>busy=false);}}
  @override Widget build(BuildContext context){final p=profile;if(p==null)return const Scaffold(body:Center(child:Text('Orquestador no encontrado.')));return Scaffold(appBar:AppBar(title:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(p.name),const Text('Orquestador',style:TextStyle(fontSize:12,fontWeight:FontWeight.normal))]),actions:[IconButton(tooltip:'Nuevo chat',onPressed:_newChat,icon:const Icon(Icons.add_comment_outlined)),IconButton(tooltip:'Historial',onPressed:_history,icon:const Icon(Icons.history)),IconButton(tooltip:'Ajustes de IA',onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const LlmSettingsPage())),icon:const Icon(Icons.settings_outlined))]),body:ListView(padding:const EdgeInsets.all(16),children:[Card(elevation:2,child:Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Row(children:[const Icon(Icons.account_tree_outlined),const SizedBox(width:10),Expanded(child:Text(p.name,style:const TextStyle(fontSize:19,fontWeight:FontWeight.bold))),IconButton(tooltip:'Modificar',onPressed:busy?null:_edit,icon:const Icon(Icons.edit_outlined))]),if(p.description.isNotEmpty)...[const SizedBox(height:6),Text(p.description)],const SizedBox(height:10),Text('Modelo: ${memoraAiSourceLabel(p.modelSource)}'),Text('Agentes autorizados: ${p.agentIds.length}'),const SizedBox(height:6),Text('Instrucciones: ${p.prompt}',maxLines:5,overflow:TextOverflow.ellipsis)]))),const SizedBox(height:12),TextField(controller:input,minLines:3,maxLines:7,onChanged:(_){if(recommendations.isNotEmpty||suggestedRoles.isNotEmpty)setState((){recommendations=[];suggestedRoles=[];});},decoration:const InputDecoration(labelText:'Trabajo complejo',hintText:'Describe lo que quieres que coordine…')),const SizedBox(height:10),Card(child:Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('Agentes recomendados (opcional)',style:TextStyle(fontSize:17,fontWeight:FontWeight.bold)),const SizedBox(height:5),const Text('Solo recomienda. No crea ni activa agentes automáticamente.'),const SizedBox(height:8),OutlinedButton.icon(onPressed:busy?null:_recommend,icon:const Icon(Icons.recommend_outlined),label:const Text('Recomendar para esta tarea')),for(final r in recommendations)ListTile(contentPadding:EdgeInsets.zero,title:Text(r.agent.name),subtitle:Text(r.matches.isEmpty?'Coincide con la tarea':'Coincide por: ${r.matches.take(4).join(', ')}'),trailing:p.agentIds.contains(r.agent.id)?const Text('Seleccionado'):TextButton(onPressed:()=>_toggle(r.agent.id,true),child:const Text('Usar'))),if(suggestedRoles.isNotEmpty)...[const Divider(),const Text('Especialidades que podrías crear manualmente:'),const SizedBox(height:6),Wrap(spacing:8,runSpacing:8,children:[for(final x in suggestedRoles)Chip(label:Text(x),avatar:const Icon(Icons.lightbulb_outline,size:18))])]]))),Card(child:Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('Agentes autorizados',style:TextStyle(fontSize:17,fontWeight:FontWeight.bold)),const SizedBox(height:5),const Text('Solo se ejecutarán los que marques tú.'),if(agents.isEmpty)const Padding(padding:EdgeInsets.only(top:10),child:Text('No hay agentes creados.')),for(final a in agents)CheckboxListTile(contentPadding:EdgeInsets.zero,title:Text(a.name),subtitle:Text(memoraAiSourceLabel(a.modelSource)),value:p.agentIds.contains(a.id),onChanged:busy?null:(v)=>_toggle(a.id,v==true))]))),const SizedBox(height:8),FilledButton.icon(onPressed:busy?null:_run,icon:const Icon(Icons.account_tree_outlined),label:Text(busy?'Coordinando agentes…':'Ejecutar con agentes')),if(trace.isNotEmpty)...[const SizedBox(height:14),const Text('Ejecución',style:TextStyle(fontWeight:FontWeight.bold)),for(final x in trace)ListTile(dense:true,leading:const Icon(Icons.subdirectory_arrow_right),title:Text(x))],const SizedBox(height:10),Card(child:Padding(padding:const EdgeInsets.all(16),child:SelectableText(answer))) ]));}
}
'''

Path('lib/agent_profiles.dart').write_text(profiles)
Path('lib/agent_page.dart').write_text(agent_page)
Path('lib/agent_orchestrator_page.dart').write_text(orchestrator)
print('v159 applied: Agents directory + per-agent chat + multiple editable Orchestrators')
