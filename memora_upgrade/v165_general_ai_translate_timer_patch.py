from pathlib import Path

# v165: General Chat IA parity with Tutors for exactly two features:
# 1) assistant-message Translate / Auto ES controls via ChatTranscript
# 2) live + persisted per-message response-time counter.

p = Path('lib/general_ai_chat_page.dart')
s = p.read_text()

if "import 'dart:async';" not in s:
    s = "import 'dart:async';\n" + s
if "import 'chat_widgets.dart';" not in s:
    s = s.replace("import 'chat_store.dart';\n", "import 'chat_store.dart';\nimport 'chat_widgets.dart';\n", 1)

old = """ final input=TextEditingController(); List<ChatSession> chats=[]; String? activeId; bool busy=false,useLibrary=false; String responseMode='normal';
"""
new = """ final input=TextEditingController(); List<ChatSession> chats=[]; String? activeId; bool busy=false,useLibrary=false; String responseMode='normal';
 Timer? _responseTimer;
 DateTime? _responseStartedAt;
 double _responseSeconds=0;

 void _startResponseTimer(){
   _responseTimer?.cancel();
   _responseStartedAt=DateTime.now();
   _responseSeconds=0;
   _responseTimer=Timer.periodic(const Duration(milliseconds:100),(_){
     if(!mounted||_responseStartedAt==null)return;
     setState(()=>_responseSeconds=DateTime.now().difference(_responseStartedAt!).inMilliseconds/1000.0);
   });
 }
 void _stopResponseTimer(){
   if(_responseStartedAt!=null){
     _responseSeconds=DateTime.now().difference(_responseStartedAt!).inMilliseconds/1000.0;
   }
   _responseTimer?.cancel();
   _responseTimer=null;
 }
"""
if old not in s:
    raise SystemExit('v165 general chat state anchor missing')
s = s.replace(old,new,1)

old = """ @override void initState(){super.initState();_load();} @override void dispose(){input.dispose();super.dispose();}
"""
new = """ @override void initState(){super.initState();_load();} @override void dispose(){_responseTimer?.cancel();input.dispose();super.dispose();}
"""
if old not in s:
    raise SystemExit('v165 general chat dispose anchor missing')
s = s.replace(old,new,1)

old = """_put(cur);setState(()=>busy=true);try{"""
new = """_put(cur);setState(()=>busy=true);_startResponseTimer();try{"""
if old not in s:
    raise SystemExit('v165 general chat timer start anchor missing')
s = s.replace(old,new,1)

old = """}finally{if(mounted)setState(()=>busy=false);}}"""
new = """}finally{
   _stopResponseTimer();
   final timed=active;
   if(timed!=null&&timed.messages.isNotEmpty&&timed.messages.last.role=='assistant'){
     final m=List<ChatMessage>.from(timed.messages);
     m[m.length-1]=m.last.copyWith(responseSeconds:_responseSeconds);
     final saved=timed.copyWith(updatedAt:DateTime.now(),messages:m);
     _put(saved);
     await ChatStore.save(saved);
   }
   if(mounted)setState(()=>busy=false);
 }}"""
if old not in s:
    raise SystemExit('v165 general chat timer finish anchor missing')
s = s.replace(old,new,1)

old = """         Expanded(
           child: ms.isEmpty
               ? const Center(child: Text('Pregunta cualquier cosa.'))
               : ListView.builder(
                   padding: const EdgeInsets.all(12),
                   itemCount: ms.length,
                   itemBuilder: (c, i) {
                     final m = ms[i];
                     return Align(
                       alignment: m.role == 'user' ? Alignment.centerRight : Alignment.centerLeft,
                       child: Card(child: Padding(padding: const EdgeInsets.all(12), child: Text(m.text))),
                     );
                   },
                 ),
         ),
"""
new = """         Expanded(
           child: ChatTranscript(
             messages: ms,
             participantName: 'Memora AI',
             emptyText: 'Pregunta cualquier cosa.',
             liveResponseSeconds: _responseSeconds,
             isResponding: busy,
           ),
         ),
         if(busy)
           Padding(
             padding: const EdgeInsets.fromLTRB(12,2,16,2),
             child: Align(
               alignment: Alignment.centerRight,
               child: Text(
                 '${_responseSeconds.toStringAsFixed(1)} s',
                 style: TextStyle(
                   fontSize:12,
                   fontWeight:FontWeight.w600,
                   color:Theme.of(context).colorScheme.secondary,
                 ),
               ),
             ),
           ),
"""
if old not in s:
    raise SystemExit('v165 general chat transcript anchor missing')
s = s.replace(old,new,1)

p.write_text(s)
print('v165 applied: Chat IA Translate/Auto ES + response counter')
