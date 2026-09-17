from pathlib import Path
import re

# v154: navigation cleanup + shared chat tools + Agent Orchestrator.
# Runs after v153 so it edits the final assembled UI.

# 1) Move Guide Creator out of bottom navigation and into Library as a FAB.
p=Path('lib/app_shell.dart'); s=p.read_text()
s=s.replace("            GuideCreatorPage(store: widget.store),\n", "", 1)
s=re.sub(r"\s*NavigationDestination\(icon: Icon\(Icons\.auto_awesome\), label: 'Crear'\),\n", "\n", s, count=1)
p.write_text(s)

p=Path('lib/home_page.dart'); h=p.read_text()
if "import 'guide_creator_page.dart';" not in h:
    h=h.replace("import 'guide_store.dart';\n", "import 'guide_store.dart';\nimport 'guide_creator_page.dart';\n", 1)
if "tooltip: 'Crear guía'" not in h:
    marker='body:'
    scaffold=h.find('Scaffold(')
    body=h.find(marker, scaffold)
    if scaffold < 0 or body < 0: raise SystemExit('Library Scaffold/body not found')
    h=h[:body]+"floatingActionButton: FloatingActionButton(tooltip: 'Crear guía', onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => GuideCreatorPage(store: widget.store))), child: const Icon(Icons.auto_awesome)),\n        "+h[body:]
p.write_text(h)

# 2) General Chat IA: persistent sessions, new/history/PDF/settings toolbar.
p=Path('lib/general_ai_chat_page.dart')
g=r"""import 'package:flutter/material.dart';
import 'ai_service.dart';
import 'chat_store.dart';
import 'guide_store.dart';
import 'knowledge_retriever.dart';
import 'llm_settings_page.dart';

class GeneralAiChatPage extends StatefulWidget { const GeneralAiChatPage({super.key,required this.store}); final GuideStore store; @override State<GeneralAiChatPage> createState()=>_GeneralAiChatPageState(); }
class _GeneralAiChatPageState extends State<GeneralAiChatPage>{
 final input=TextEditingController(); List<ChatSession> chats=[]; String? activeId; bool busy=false,useLibrary=false; String responseMode='normal';
 ChatSession? get active { if(chats.isEmpty)return null; return chats.firstWhere((x)=>x.id==activeId,orElse:()=>chats.first); }
 @override void initState(){super.initState();_load();} @override void dispose(){input.dispose();super.dispose();}
 Future<void> _load()async{var x=await ChatStore.listFor('general_ai','main');if(x.isEmpty){x=[ChatSession.empty(ownerType:'general_ai',ownerId:'main')];await ChatStore.save(x.first);}if(mounted)setState((){chats=x;activeId=x.first.id;});}
 void _put(ChatSession c){final x=List<ChatSession>.from(chats);final i=x.indexWhere((e)=>e.id==c.id);if(i<0)x.insert(0,c);else x[i]=c;if(mounted)setState((){chats=x;activeId=c.id;});}
 Future<void> _newChat()async{if(busy)return;final c=ChatSession.empty(ownerType:'general_ai',ownerId:'main');await ChatStore.save(c);_put(c);}
 Future<void> _export(ChatSession c)async{if(c.messages.isEmpty){if(mounted)ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('Este chat todavía está vacío.')));return;}await ChatStore.exportPdf(c,participantName:'Memora AI');if(mounted)ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('Chat exportado como PDF.')));}
 Future<void> _delete(ChatSession c)async{await ChatStore.delete(c.id);var x=chats.where((e)=>e.id!=c.id).toList();if(x.isEmpty){x=[ChatSession.empty(ownerType:'general_ai',ownerId:'main')];await ChatStore.save(x.first);}if(mounted)setState((){chats=x;activeId=x.first.id;});}
 Future<void> _history()async{await showModalBottomSheet(context:context,isScrollControlled:true,builder:(bc)=>SafeArea(child:SizedBox(height:MediaQuery.of(bc).size.height*.72,child:Column(children:[Padding(padding:const EdgeInsets.all(12),child:Row(children:[const Expanded(child:Text('Historial de chats',style:TextStyle(fontSize:20,fontWeight:FontWeight.bold))),IconButton(tooltip:'Nuevo chat',onPressed:(){Navigator.pop(bc);_newChat();},icon:const Icon(Icons.add_comment_outlined))])),Expanded(child:ListView(children:[for(final c in chats) ListTile(leading:Icon(c.id==activeId?Icons.chat_bubble:Icons.chat_bubble_outline),title:Text(c.title,maxLines:1,overflow:TextOverflow.ellipsis),subtitle:Text('${c.messages.length} mensaje(s)'),onTap:(){setState(()=>activeId=c.id);Navigator.pop(bc);},trailing:Wrap(children:[IconButton(tooltip:'Exportar PDF',onPressed:()=>_export(c),icon:const Icon(Icons.picture_as_pdf_outlined)),IconButton(tooltip:'Borrar',onPressed:(){Navigator.pop(bc);_delete(c);},icon:const Icon(Icons.delete_outline))])))]))]))));}
 Future<void> _send()async{final q=input.text.trim(), c=active;if(q.isEmpty||busy||c==null)return;input.clear();var msgs=List<ChatMessage>.from(c.messages)..add(ChatMessage(role:'user',text:q,createdAt:DateTime.now()))..add(ChatMessage(role:'assistant',text:'Thinking…',createdAt:DateTime.now()));var cur=c.copyWith(updatedAt:DateTime.now(),messages:msgs);_put(cur);setState(()=>busy=true);try{var ctx='';if(useLibrary&&widget.store.guides.isNotEmpty){ctx=KnowledgeRetriever.buildContext(guides:widget.store.guides,query:q,maxChars:responseMode=='fast'?3000:7000,maxChunks:responseMode=='fast'?3:7,allowUnmatchedFallback:false);if(ctx.startsWith('(No matching evidence found'))ctx='';}final history=cur.conversationContext(maxChars:5000,maxMessages:12);final result=await AiService.askConfigured(providerOverride:'global',responseMode:responseMode,onPartial:(v){if(!mounted||v.isEmpty)return;final a=active;if(a==null)return;final m=List<ChatMessage>.from(a.messages);if(m.isNotEmpty&&m.last.role=='assistant'){m[m.length-1]=m.last.copyWith(text:v);_put(a.copyWith(updatedAt:DateTime.now(),messages:m));}},prompt:'''You are Memora AI, a general-purpose assistant.\nCONVERSATION:\n$history\n${ctx.isEmpty?'':'OPTIONAL LIBRARY CONTEXT:\n$ctx\n'}QUESTION:\n$q''');final a=active;if(a!=null){final m=List<ChatMessage>.from(a.messages);m[m.length-1]=m.last.copyWith(text:result);cur=a.copyWith(updatedAt:DateTime.now(),messages:m);_put(cur);await ChatStore.save(cur);}}catch(e){final a=active;if(a!=null){final m=List<ChatMessage>.from(a.messages);m[m.length-1]=m.last.copyWith(text:'No pude responder: ${AiService.userFacingError(e)}');cur=a.copyWith(updatedAt:DateTime.now(),messages:m);_put(cur);await ChatStore.save(cur);}}finally{if(mounted)setState(()=>busy=false);}}
 @override Widget build(BuildContext context){final ms=active?.messages??const <ChatMessage>[];return Scaffold(appBar:AppBar(title:const Text('Chat IA'),actions:[IconButton(tooltip:'Nuevo chat',onPressed:busy?null:_newChat,icon:const Icon(Icons.add_comment_outlined)),IconButton(tooltip:'Historial',onPressed:busy?null:_history,icon:const Icon(Icons.history)),IconButton(tooltip:'Exportar PDF',onPressed:active==null?null:()=>_export(active!),icon:const Icon(Icons.picture_as_pdf_outlined)),IconButton(tooltip:'AI Settings',onPressed:()=>Navigator.of(context).push(MaterialPageRoute(builder:(_)=>const LlmSettingsPage())),icon:const Icon(Icons.settings_outlined))]),body:Column(children:[Padding(padding:const EdgeInsets.fromLTRB(12,8,12,4),child:SegmentedButton<String>(segments:const[ButtonSegment(value:'fast',label:Text('Fast')),ButtonSegment(value:'normal',label:Text('Normal')),ButtonSegment(value:'deep',label:Text('Deep'))],selected:{responseMode},onSelectionChanged:busy?null:(v)=>setState(()=>responseMode=v.first))),SwitchListTile(dense:true,title:const Text('Usar biblioteca'),subtitle:Text(useLibrary?'Puede consultar tus guías cuando sean relevantes.':'Chat general sin depender de tus guías.'),value:useLibrary,onChanged:busy?null:(v)=>setState(()=>useLibrary=v)),const Divider(height:1),Expanded(child:ms.isEmpty?const Center(child:Text('Pregunta cualquier cosa.')):ListView.builder(padding:const EdgeInsets.all(12),itemCount:ms.length,itemBuilder:(c,i){final m=ms[i];return Align(alignment:m.role=='user'?Alignment.centerRight:Alignment.centerLeft,child:Card(child:Padding(padding:const EdgeInsets.all(12),child:Text(m.text))));})),SafeArea(top:false,child:Padding(padding:const EdgeInsets.fromLTRB(12,8,12,12),child:Row(children:[Expanded(child:TextField(controller:input,minLines:1,maxLines:5,decoration:const InputDecoration(hintText:'Pregúntale cualquier cosa…'))),const SizedBox(width:8),busy?IconButton(onPressed:AiService.cancelCurrent,icon:const Icon(Icons.stop_circle_outlined)):IconButton(onPressed:_send,icon:const Icon(Icons.send_rounded))])))]));}
}
"""
p.write_text(g)

# 3) Agent Orchestrator: real sequential delegation to selected agents.
orch=r"""import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'agent_page.dart';
import 'ai_service.dart';
import 'guide_store.dart';
import 'knowledge_retriever.dart';
import 'llm_settings_page.dart';

class AgentOrchestratorPage extends StatefulWidget{const AgentOrchestratorPage({super.key,required this.store});final GuideStore store;@override State<AgentOrchestratorPage> createState()=>_S();}
class _S extends State<AgentOrchestratorPage>{final input=TextEditingController();List<AgentProfile> agents=[];Set<String> enabled={};String answer='Describe un trabajo complejo. El Orquestador lo dividirá y delegará a tus agentes.';bool busy=false;List<String> trace=[];
@override void initState(){super.initState();_load();}@override void dispose(){input.dispose();super.dispose();}
Future<void>_load()async{final p=await SharedPreferences.getInstance();final raw=p.getString('memora_agent_profiles_v1');if(raw!=null){try{agents=(jsonDecode(raw)as List).whereType<Map>().map((e)=>AgentProfile.fromJson(Map<String,dynamic>.from(e))).toList();}catch(_){}}if(mounted)setState(()=>enabled=agents.map((e)=>e.id).toSet());}
Future<void>_run()async{final task=input.text.trim();if(task.isEmpty||busy)return;final chosen=agents.where((a)=>enabled.contains(a.id)).toList();if(chosen.isEmpty){setState(()=>answer='Selecciona al menos un agente.');return;}setState((){busy=true;trace=[];answer='Planificando y delegando…';});try{var shared='';for(final a in chosen){if(mounted)setState(()=>trace.add('${a.name}: trabajando…'));final guides=widget.store.guides.where((g)=>a.guideIds.contains(g.id)).toList();final ctx=guides.isEmpty?'':KnowledgeRetriever.buildContext(guides:guides,query:task,maxChars:5000,maxChunks:5,allowUnmatchedFallback:false);final r=await AiService.askConfigured(providerOverride:a.modelSource,responseMode:'normal',prompt:'''Eres ${a.name}, un agente especializado dentro de un equipo coordinado por Memora.\nTU FUNCIÓN:\n${a.prompt}\nTRABAJO GENERAL:\n$task\nRESULTADOS DE AGENTES ANTERIORES:\n$shared\nBASE ASIGNADA:\n$ctx\nRealiza la parte del trabajo que corresponde a tu especialidad. Devuelve resultados concretos que otro agente pueda continuar.''');shared+='\n\n[${a.name}]\n$r';if(mounted)setState(()=>trace[trace.length-1]='${a.name}: completado');}final finalResult=await AiService.askConfigured(providerOverride:'global',responseMode:'deep',prompt:'''Eres el Orquestador de Memora. Integra el trabajo de varios agentes en un único resultado final coherente. No inventes resultados que los agentes no proporcionaron.\nSOLICITUD:\n$task\nTRABAJO DE LOS AGENTES:\n$shared\nEntrega el trabajo final, resolviendo duplicaciones y contradicciones cuando sea posible.''');if(mounted)setState(()=>answer=finalResult);}catch(e){if(mounted)setState(()=>answer='El Orquestador no pudo terminar: ${AiService.userFacingError(e)}');}finally{if(mounted)setState(()=>busy=false);}}
@override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('Orquestador'),Text('Agente de agentes',style:TextStyle(fontSize:12,fontWeight:FontWeight.normal))]),actions:[IconButton(tooltip:'AI Settings',onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const LlmSettingsPage())),icon:const Icon(Icons.settings_outlined))]),body:ListView(padding:const EdgeInsets.all(16),children:[Card(child:Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('Agentes autorizados',style:TextStyle(fontWeight:FontWeight.bold,fontSize:17)),const SizedBox(height:6),const Text('El Orquestador puede encadenar sus resultados para completar trabajos complejos.'),for(final a in agents)CheckboxListTile(contentPadding:EdgeInsets.zero,title:Text(a.name),value:enabled.contains(a.id),onChanged:busy?null:(v)=>setState(()=>v==true?enabled.add(a.id):enabled.remove(a.id))) ]))),TextField(controller:input,minLines:3,maxLines:7,decoration:const InputDecoration(labelText:'Trabajo complejo',hintText:'Ej. Analiza estos datos y prepara un informe final…')),const SizedBox(height:10),FilledButton.icon(onPressed:busy?null:_run,icon:const Icon(Icons.account_tree_outlined),label:Text(busy?'Coordinando agentes…':'Ejecutar con agentes')),if(trace.isNotEmpty)...[const SizedBox(height:14),const Text('Ejecución',style:TextStyle(fontWeight:FontWeight.bold)),for(final x in trace)ListTile(dense:true,leading:const Icon(Icons.subdirectory_arrow_right),title:Text(x))],const SizedBox(height:12),Card(child:Padding(padding:const EdgeInsets.all(16),child:SelectableText(answer))) ]));}
"""
Path('lib/agent_orchestrator_page.dart').write_text(orch)

p=Path('lib/agent_page.dart'); a=p.read_text()
if "import 'agent_orchestrator_page.dart';" not in a:a=a.replace("import 'ai_service.dart';\n","import 'ai_service.dart';\nimport 'agent_orchestrator_page.dart';\nimport 'llm_settings_page.dart';\n",1)
needle="          actions: [\n            IconButton(\n              onPressed: _createAgent,"
if needle in a and "tooltip: 'Orquestador'" not in a:
 repl="          actions: [\n            IconButton(tooltip: 'Orquestador', onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AgentOrchestratorPage(store: widget.store))), icon: const Icon(Icons.account_tree_outlined)),\n            IconButton(tooltip: 'AI Settings', onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const LlmSettingsPage())), icon: const Icon(Icons.settings_outlined)),\n            IconButton(\n              onPressed: _createAgent,"
 a=a.replace(needle,repl,1)
p.write_text(a)

print('v154 applied: creator moved to Library, Chat IA tools, Agent tools and Orchestrator')
