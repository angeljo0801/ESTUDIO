from pathlib import Path
import subprocess

# General Chat IA. It is added without replacing Study Plan or changing the
# existing page/destination ordering produced by the earlier patch chain.
chat = r"""import 'package:flutter/material.dart';
import 'ai_service.dart';
import 'guide_store.dart';
import 'knowledge_retriever.dart';
class GeneralAiChatPage extends StatefulWidget { const GeneralAiChatPage({super.key,required this.store}); final GuideStore store; @override State<GeneralAiChatPage> createState()=>_GeneralAiChatPageState(); }
class _GeneralAiChatPageState extends State<GeneralAiChatPage>{
 final input=TextEditingController(); final messages=<({bool user,String text})>[]; bool busy=false,useLibrary=false; String responseMode='normal';
 @override void dispose(){input.dispose();super.dispose();}
 Future<void> _send() async { final question=input.text.trim(); if(question.isEmpty||busy)return; input.clear(); setState((){messages.add((user:true,text:question));messages.add((user:false,text:'Thinking…'));busy=true;}); final ai=messages.length-1;
  try { var ctx=''; if(useLibrary&&widget.store.guides.isNotEmpty){ctx=KnowledgeRetriever.buildContext(guides:widget.store.guides,query:question,maxChars:responseMode=='fast'?3000:7000,maxChunks:responseMode=='fast'?3:7,allowUnmatchedFallback:false);if(ctx.startsWith('(No matching evidence found'))ctx='';}
   final history=messages.take(messages.length-1).toList().reversed.take(8).toList().reversed.map((m)=>'${m.user?'User':'Assistant'}: ${m.text}').join('\n');
   final result=await AiService.askConfigured(providerOverride:'global',responseMode:responseMode,onPartial:(p){if(!mounted||p.isEmpty)return;setState(()=>messages[ai]=(user:false,text:p));},prompt:'''You are Memora AI, a general-purpose AI assistant. Answer normally. The question does not need to relate to the study library.\nCONVERSATION:\n$history\n${ctx.isEmpty?'':'OPTIONAL LIBRARY CONTEXT:\n$ctx\n'}USER QUESTION:\n$question\nUse library context only when relevant.'''); if(mounted)setState(()=>messages[ai]=(user:false,text:result));
  }catch(e){if(mounted)setState(()=>messages[ai]=(user:false,text:'No pude responder: ${AiService.userFacingError(e)}'));}finally{if(mounted)setState(()=>busy=false);}
 }
 @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('Chat IA')),body:Column(children:[
  Padding(padding:const EdgeInsets.fromLTRB(12,8,12,4),child:SegmentedButton<String>(segments:const [ButtonSegment(value:'fast',label:Text('Fast')),ButtonSegment(value:'normal',label:Text('Normal')),ButtonSegment(value:'deep',label:Text('Deep'))],selected:{responseMode},onSelectionChanged:busy?null:(v)=>setState(()=>responseMode=v.first))),
  SwitchListTile(dense:true,title:const Text('Usar biblioteca'),subtitle:Text(useLibrary?'Puede consultar tus guías cuando sean relevantes.':'Chat general sin depender de tus guías.'),value:useLibrary,onChanged:busy?null:(v)=>setState(()=>useLibrary=v)),const Divider(height:1),
  Expanded(child:messages.isEmpty?const Center(child:Padding(padding:EdgeInsets.all(28),child:Text('Pregunta cualquier cosa. No tiene que estar relacionada con tu biblioteca.',textAlign:TextAlign.center))):ListView.builder(padding:const EdgeInsets.all(12),itemCount:messages.length,itemBuilder:(c,i){final m=messages[i];return Align(alignment:m.user?Alignment.centerRight:Alignment.centerLeft,child:Card(child:Padding(padding:const EdgeInsets.symmetric(horizontal:14,vertical:11),child:Text(m.text))));})),
  SafeArea(top:false,child:Padding(padding:const EdgeInsets.fromLTRB(12,8,12,12),child:Row(crossAxisAlignment:CrossAxisAlignment.end,children:[Expanded(child:TextField(controller:input,minLines:1,maxLines:5,textInputAction:TextInputAction.newline,decoration:const InputDecoration(hintText:'Pregúntale cualquier cosa…'))),const SizedBox(width:8),busy?IconButton(onPressed:AiService.cancelCurrent,icon:const Icon(Icons.stop_circle_outlined)):IconButton(onPressed:_send,icon:const Icon(Icons.send_rounded))]))),]));
}
"""
Path('lib/general_ai_chat_page.dart').write_text(chat)
p=Path('lib/app_shell.dart'); s=p.read_text()
if "import 'general_ai_chat_page.dart';" not in s:
 s=s.replace("import 'guide_store.dart';\n","import 'guide_store.dart';\nimport 'general_ai_chat_page.dart';\n",1)
if 'GeneralAiChatPage(store: widget.store)' not in s:
 marker='StudyPlanPage(store: widget.store),'
 if marker not in s: raise SystemExit('StudyPlanPage missing; refusing to modify navigation')
 s=s.replace(marker,marker+'\n            GeneralAiChatPage(store: widget.store),',1)
if "label: 'Chat IA'" not in s:
 lines=s.splitlines(True); pos=None
 for n,line in enumerate(lines):
  if 'NavigationDestination' in line and "label: 'Plan'" in line: pos=n+1; break
 if pos is None: raise SystemExit('Plan destination missing; refusing to modify navigation')
 indent=lines[pos-1][:len(lines[pos-1])-len(lines[pos-1].lstrip())]
 lines.insert(pos,indent+"NavigationDestination(icon: Icon(Icons.chat_bubble_outline), label: 'Chat IA'),\n"); s=''.join(lines)
for required in ['StudyPlanPage(store: widget.store)','GeneralAiChatPage(store: widget.store)',"label: 'Plan'","label: 'Chat IA'"]:
 if required not in s: raise SystemExit('Navigation invariant missing: '+required)
p.write_text(s)
print('Chat IA added after Study Plan; Plan preserved')

subprocess.run(['python3','v154_workspace_orchestrator_patch.py'],check=True)
