import 'dart:convert';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'models.dart';
import 'dual_world_engine.dart';
import 'lumen_business_panel.dart';
import 'nebula_art.dart';

String dualWorldLandscapeKey(String place)=>const <String,String>{
  'Dormitorio':'scene_dormitorio','Clases':'scene_clases','Biblioteca':'scene_biblioteca','Patio':'scene_patio','Arena':'scene_arena','Gimnasio':'scene_gimnasio','Ranking':'scene_ranking','Jardín':'scene_jardin','Consejo':'scene_consejo','Pasillo antiguo':'scene_pasillo','Dungeon':'scene_dungeon','Iglesia':'scene_iglesia','Palacio':'scene_palacio','Taller privado':'scene_taller','Mercado':'scene_mercado','Gremio':'scene_gremio','Almacén':'scene_almacen','Puerto':'scene_puerto','Armería':'scene_armeria','Empresas':'scene_empresas',
  'Sala de profesores':'scene_profesores','Gremio de aventureros':'scene_aventureros','Bosque fronterizo':'scene_bosque_frontera','Minas de Valdren':'scene_minas_valdren','Campamento mercenario':'scene_campamento','Frente de guerra':'scene_frente',
}[place]??'scene_asteria';

class DualWorldContent {
  const DualWorldContent(this.data,this.lessons,this.books,this.events,this.extraSkills,this.extraPeople,this.extraEnemies,this.spirits,this.catalog,this.weapons);
  final Map<String,dynamic> data;
  final List<Map<String,dynamic>> lessons,books,events,extraSkills,extraPeople,extraEnemies,spirits,catalog,weapons;
  List<Map<String,dynamic>> get people=>{for(final person in [...list(data['people']),...extraPeople]) person['id']:person}.values.toList();
  List<Map<String,dynamic>> get races=>list(data['races']);
  Map<String,dynamic> raceFor(dynamic id)=>races.firstWhere((r)=>r['id']==id,orElse:()=> <String,dynamic>{});
  List<Map<String,dynamic>> get skills=>{for(final sk in [...list(data['skills']),...extraSkills]) sk['id']:sk}.values.toList();
  List<Map<String,dynamic>> get enemies=>{for(final enemy in [...list(data['enemies']),...extraEnemies]) enemy['id']:enemy}.values.toList();
  static List<Map<String,dynamic>> list(dynamic raw)=>raw is List?raw.whereType<Map>().map((x)=>Map<String,dynamic>.from(x)).toList():[];
  static DualWorldContent? fromGuide(StudyGuide g){
    Map<String,dynamic>? root;final lessons=<Map<String,dynamic>>[],books=<Map<String,dynamic>>[],events=<Map<String,dynamic>>[],extraSkills=<Map<String,dynamic>>[],extraPeople=<Map<String,dynamic>>[],extraEnemies=<Map<String,dynamic>>[],spirits=<Map<String,dynamic>>[],catalog=<Map<String,dynamic>>[],weapons=<Map<String,dynamic>>[];
    for(final c in g.cards){try{final v=jsonDecode(c.adventureStory);if(v is! Map)continue;
      if(v['kind']=='memora_dual_world_v1')root=Map<String,dynamic>.from(v);
      if(v['kind']=='memora_dual_lesson_v1')lessons.add(Map<String,dynamic>.from(v));
      if(v['kind']=='memora_dual_book_v1')books.add(Map<String,dynamic>.from(v));
      if(v['kind']=='memora_dual_events_v1')events.addAll(list(v['events']));
      if(v['kind']=='memora_dual_skills_v1')extraSkills.addAll(list(v['skills']));
      if(v['kind']=='memora_dual_people_v1')extraPeople.addAll(list(v['people']));
      if(v['kind']=='memora_dual_enemies_v1')extraEnemies.addAll(list(v['enemies']));
      if(v['kind']=='memora_dual_spirits_v1')spirits.addAll(list(v['spirits']));
      if(v['kind']=='memora_dual_library_v1')catalog.addAll(list(v['titles']));
      if(v['kind']=='memora_dual_weapons_v1')weapons.addAll(list(v['weapons']));
    }catch(_){}}
    if(root==null||lessons.isEmpty||list(root['skills']).isEmpty||list(root['enemies']).isEmpty)return null;
    return DualWorldContent(root,lessons,books,events,extraSkills,extraPeople,extraEnemies,spirits,catalog,weapons);
  }
}
class DualWorldPage extends StatefulWidget{
  const DualWorldPage({super.key,required this.guide,required this.content});
  final StudyGuide guide;final DualWorldContent content;
  @override State<DualWorldPage> createState()=>_DualWorldPageState();
}
class _DualWorldPageState extends State<DualWorldPage>{
  DualState s=DualState();bool loading=true,busy=false;
  String message='';int qty=1,price=12;
  String raceFilter='all';
  String bookFilter='all',bookSearch='';
  String nameFilter='';
  final answer=TextEditingController();
  DualWorldContent get c=>widget.content;
  String get key=>'memora_dual_world_'+widget.guide.id;
  @override void initState(){super.initState();load();}
  @override void dispose(){answer.dispose();super.dispose();}
  Future<void> load()async{final p=await SharedPreferences.getInstance();try{final raw=p.getString(key);if(raw!=null)s=DualState.fromJson(jsonDecode(raw) as Map);}catch(_){}if(mounted)setState(()=>loading=false);}
  Future<void> act(String Function() fn)async{
    if(busy)return;setState(()=>busy=true);
    try{var next=fn();s.resolveWar();if(s.returned&&s.lethalBattle&&s.hp==0){final destroyed=s.worldDestroyed;s=s.returnToBeginning();next=(destroyed?'FIN DEL MUNDO · La Ruptura ha consumido el reino. RETORNO: despiertas el día de ingreso y conservas tu inteligencia. ':'RETORNO · Despiertas en tu dormitorio, el día de ingreso. Solo conservas inteligencia. ')+next;raceFilter='all';nameFilter='';answer.clear();}s.resolveFates(c.events);final p=await SharedPreferences.getInstance();if(!await p.setString(key,jsonEncode(s.toJson())))throw StateError('No se pudo guardar');if(mounted)setState(()=>message=next);}
    catch(e){if(mounted)setState(()=>message=e.toString());}finally{if(mounted)setState(()=>busy=false);}
  }
  Widget btn(String label,String Function() fn)=>FilledButton(onPressed:busy?null:()=>act(fn),child:Text(label));
  Widget section(String title,List<Widget> children)=>Card(child:Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[Text(title,style:const TextStyle(fontSize:20,fontWeight:FontWeight.bold)),const SizedBox(height:10),...children])));
  Widget art(String id,{double height=160,String? fallback})=>ValueListenableBuilder<int>(
    valueListenable:MemoraArtStore.revision,
    builder:(context,_,child)=>FutureBuilder(future:AdventureArtStore.load(widget.guide.id),builder:(context,snapshot){
      final assets=snapshot.data;
      final bytes=assets?[id]??(fallback==null?null:assets?[fallback]);
      if(bytes==null)return const SizedBox.shrink();
      return Padding(padding:const EdgeInsets.symmetric(vertical:6),child:ClipRRect(borderRadius:BorderRadius.circular(12),child:SizedBox(height:height,width:double.infinity,child:Image.memory(bytes,fit:BoxFit.contain,gaplessPlayback:true,errorBuilder:(context,error,stack)=>const SizedBox.shrink()))));
    }));
  String portraitKey(Map person)=>person['hiddenRace']==true&&!s.knownRaces.contains(person['id'])?person['id'].toString()+'_cover':person['id'].toString();
  Widget personArt(Map person)=>art(portraitKey(person),height:200);
  Widget landscape(String location)=>AdventureSceneView(guide:widget.guide,visual:AdventureVisualSpec(background:dualWorldLandscapeKey(location),height:240),location:location);
  Widget enemyArt(Map enemy){
    final person=c.people.firstWhere((p)=>p['id']==enemy['person'],orElse:()=> <String,dynamic>{});
    if(person.isNotEmpty)return personArt(person);
    return art(enemy['id'].toString(),height:200);
  }
  Future<void> importArt()async{
    try{final n=await AdventureArtStore.importLocal(widget.guide);if(n!=null&&mounted)setState(()=>message='Arte instalado: '+n.toString()+' imágenes.');}catch(e){if(mounted)setState(()=>message=e.toString());}
  }
  String today(){final d=DateTime.now();return '${d.year}-${d.month.toString().padLeft(2,'0')}-${d.day.toString().padLeft(2,'0')}';}
  Future<void> workout()async{
    if(busy||s.workoutDate.compareTo(today())>=0)return;
    const vault=FlutterSecureStorage();const tokenKey='dual_fitroutine_read_token';
    String? token=await vault.read(key:tokenKey);
    if(!mounted)return;
    if(token==null||token.isEmpty){final ctrl=TextEditingController();token=await showDialog<String>(context:context,builder:(ctx)=>AlertDialog(title:const Text('Conectar FitRoutine'),content:Column(mainAxisSize:MainAxisSize.min,children:[const Text('Usa un token de GitHub con solo lectura de Contents del repositorio privado FitRoutine. Activa allí la sincronización de historial. No compartas el token por chat.'),TextField(controller:ctrl,obscureText:true,decoration:const InputDecoration(labelText:'Token de lectura'))]),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Cancelar')),FilledButton(onPressed:()=>Navigator.pop(ctx,ctrl.text.trim()),child:const Text('Conectar'))]));ctrl.dispose();}
    if(token==null||token.isEmpty||!mounted)return;
    setState(()=>busy=true);
    try{
      final r=await http.get(Uri.https('api.github.com','/repos/angeljo0801/FitRoutine/contents/training-history.json',{'ref':'main'}),headers:{'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','Cache-Control':'no-cache'}).timeout(const Duration(seconds:20));
      if(r.statusCode!=200)throw StateError('Historial no disponible (HTTP '+r.statusCode.toString()+'). Verifica la conexión de FitRoutine.');
      final f=jsonDecode(r.body) as Map;
      if(f['encoding']!='base64')throw StateError('Historial incompatible.');
      final root=jsonDecode(utf8.decode(base64Decode((f['content'] as String).replaceAll(RegExp(r'\s'),'')))) as Map;
      final now=DateTime.now();final completed=(root['sessions'] as List).whereType<Map>().any((x){if(x['complete']!=true||x['date'] is! num||x['log'] is! List||(x['log'] as List).isEmpty)return false;final d=DateTime.fromMillisecondsSinceEpoch((x['date'] as num).toInt());return d.year==now.year&&d.month==now.month&&d.day==now.day;});
      await vault.write(key:tokenKey,value:token);
      if(!completed){if(mounted)setState(()=>message='No hay una rutina completa sincronizada hoy. Descansar también forma parte del entrenamiento.');return;}
      if(s.workout(today())){final prefs=await SharedPreferences.getInstance();await prefs.setString(key,jsonEncode(s.toJson()));if(mounted)setState(()=>message='Entrenamiento verificado: +2 fuerza, +2 resistencia defensiva, +2 estamina máxima.');}
    }catch(e){if(mounted)setState(()=>message=e.toString());}finally{if(mounted)setState(()=>busy=false);}
  }
  Widget lesson(Map<String,dynamic> l){
    final id=l['id'] as String,grade=s.grades[id];
    final deadlines=c.events.where((e)=>e['deadline'] is int&&(e['deadline'] as int)==s.grades.length+1&&!s.deadStudents.contains(e['person'])&&!s.rescuedStudents.contains(e['person'])).length;
    return section(l['title'].toString(),[
      const Text('Traducción de Apreciación: examen de finanzas',style:TextStyle(fontWeight:FontWeight.bold)),Text(l['teach'].toString()),const SizedBox(height:10),Text(l['example'].toString()),const Divider(),Text(l['question'].toString(),style:const TextStyle(fontWeight:FontWeight.bold)),
      if(grade==null&&deadlines>0)Text('Aviso: al aprobar este examen avanzará el plazo de '+deadlines.toString()+' búsqueda(s). Puedes salir y prepararte antes de entregar.',style:const TextStyle(fontWeight:FontWeight.bold,color:Colors.orange)),
      if(grade==null)...[TextField(controller:answer,keyboardType:const TextInputType.numberWithOptions(decimal:true,signed:true),decoration:const InputDecoration(labelText:'Resultado numérico')),btn('Entregar examen',(){final n=double.tryParse(answer.text.trim().replaceAll(',','.'));if(n==null||!n.isFinite)return 'Introduce una cifra válida.';final ok=(n-(l['answer'] as num)).abs()<=0.011;final g=s.rewardExam(id,ok);answer.clear();if(ok){s.chapter=s.grades.length;return 'Nota: '+g.toString()+'/100. Desbloqueaste una revelación. Cobra tu encargo financiero en el gremio de Lumen.';}return 'Repasa el ejemplo e inténtalo otra vez.';})]else...[Text('Nota: '+grade.toString()+'/100'),const Divider(),Text(l['explanation'].toString()),const SizedBox(height:8),Text(l['reveal'].toString(),style:const TextStyle(fontWeight:FontWeight.w600))],
    ]);
  }
  bool isFinanceBook(Map book)=>const ['Finanzas','Economía','Inversiones','Negocios'].contains(book['category']);
  Future<void> addBook([Map? suggested])async{
    if(busy)return;
    final title=TextEditingController(text:suggested?['title']?.toString()??''),author=TextEditingController(text:suggested?['author']?.toString()??''),pages=TextEditingController();
    final result=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:const Text('Registrar libro'),content:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[const Text('Lee el libro fuera de Memora. Introduce las páginas de tu edición, sin incluir anexos que no planees leer.'),TextField(controller:title,decoration:const InputDecoration(labelText:'Título')),TextField(controller:author,decoration:const InputDecoration(labelText:'Autor')),TextField(controller:pages,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'Total de páginas'))])),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Cancelar')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Empezar lectura'))]));
    final a=title.text,b=author.text,n=int.tryParse(pages.text)??0;title.dispose();author.dispose();pages.dispose();
    if(result==true&&mounted)await act(()=>s.addReadingBook(a,b,n,suggested?['category']?.toString()??'Personal')?'Libro registrado.':'Datos inválidos o libro ya registrado.');
  }
  Future<void> markReading(String key,Map book)async{
    if(busy)return;final ctrl=TextEditingController(text:book['page'].toString());
    final result=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:Text(book['title'].toString()),content:Column(mainAxisSize:MainAxisSize.min,children:[Text('Página registrada: '+book['page'].toString()+' de '+book['total'].toString()),TextField(controller:ctrl,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'He leído hasta la página…')),TextButton(onPressed:(){ctrl.text=book['total'].toString();},child:const Text('Libro terminado'))]),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Cancelar')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Guardar progreso'))]));
    final n=int.tryParse(ctrl.text);ctrl.dispose();if(result==true&&mounted&&n!=null)await act((){final gain=s.logReading(key,n);return gain==null?'Sin páginas nuevas o número fuera de rango.':'Progreso guardado. +'+(gain/1000).toStringAsFixed(3)+' INT acumulada.';});
  }
  Widget library(){
    bool matches(Map book)=>(bookFilter=='all'||bookFilter=='unread'||bookFilter=='finance'&&isFinanceBook(book)||bookFilter=='literature'&&!isFinanceBook(book))&&((book['title']??'').toString()+' '+(book['author']??'').toString()).toLowerCase().contains(bookSearch);
    final tracked=s.readingLog.entries.where((x)=>matches(x.value)&&(bookFilter!='unread'||x.value['page']!=x.value['total'])).toList();
    final suggested=c.catalog.where((b)=>matches(b)&&!s.readingLog.containsKey(DualState.bookKey(b['title'].toString(),b['author'].toString()))).toList();
    return section('Biblioteca · registro personal',[
      Text('Inteligencia: '+(s.intelligence+s.readingRemainder/1000).toStringAsFixed(3)+' · '+s.readingLog.length.toString()+' libros registrados'),
      const Text('Lee libros por tu cuenta. Guarda la última página leída y recibe una fracción de +5 INT por libro. No hay límite diario. Los puntos y registros se conservan al retornar. Los puntos enteros se usan en combate.'),
      FilledButton.icon(onPressed:busy?null:()=>addBook(),icon:const Icon(Icons.add),label:const Text('Añadir mi propio libro')),
      DropdownButton<String>(isExpanded:true,value:bookFilter,items:const [DropdownMenuItem(value:'all',child:Text('Todos los libros')),DropdownMenuItem(value:'unread',child:Text('Pendientes')),DropdownMenuItem(value:'finance',child:Text('Finanzas, negocios e inversiones')),DropdownMenuItem(value:'literature',child:Text('Literatura y otros'))],onChanged:busy?null:(v)=>setState(()=>bookFilter=v??'all')),
      TextField(decoration:const InputDecoration(labelText:'Buscar título o autor'),onChanged:(v)=>setState(()=>bookSearch=v.toLowerCase().trim())),
      const Divider(),const Text('Mi lectura',style:TextStyle(fontWeight:FontWeight.bold)),
      for(final row in tracked)...[Text(row.value['title'].toString(),style:const TextStyle(fontWeight:FontWeight.bold)),Text(row.value['author'].toString()+' · '+row.value['page'].toString()+'/'+row.value['total'].toString()+' páginas'),LinearProgressIndicator(value:(row.value['page'] as int)/(row.value['total'] as int)),FilledButton(onPressed:busy||row.value['page']==row.value['total']?null:()=>markReading(row.key,row.value),child:Text(row.value['page']==row.value['total']?'Leído · +5 INT':'Actualizar página'))],
      const Divider(),const Text('Catálogo recomendado',style:TextStyle(fontWeight:FontWeight.bold)),
      for(final book in suggested)ListTile(title:Text(book['title'].toString()),subtitle:Text(book['author'].toString()+' · '+book['category'].toString()),trailing:TextButton(onPressed:busy?null:()=>addBook(book),child:const Text('Leer')))
    ]);
  }
  String publicRace(Map person)=>person['hiddenRace']==true&&!s.knownRaces.contains(person['id'])?'human':(person['race']??'human').toString();
  List<Map<String,dynamic>> visibleSkills(Map person)=>c.skills.where((sk)=>sk['owner']==person['id']&&DualState.npcTechniqueAvailable(sk,person,s.grades.length)).map((sk)=>DualState.npcTechnique(sk,publicTalent(person),s.grades.length)).toList();
  bool needsAppraisal(Map sk)=>!s.appraised.contains(sk['id'])||(s.appraisedRanks[sk['id']]??0)<DualState.rankIndex(sk['rank']);
  List<Map<String,dynamic>> get purchasableSkills=>[for(final person in c.people.where((p)=>!s.deadStudents.contains(p['id']))) ...discoverableSkills(person).where((sk)=>s.appraised.contains(sk['id'])&&!needsAppraisal(sk)&&s.canAppraise(sk)&&sk['copyable']!=false)];
  List<Map<String,dynamic>> discoverableSkills(Map person)=>visibleSkills(person).where((sk)=>(sk['secret']!=true||sk['revealFlag'] is String&&s.flags.contains(sk['revealFlag']))&&(person['hiddenRace']!=true||s.knownRaces.contains(person['id'])||sk['innate']!=true&&sk['concealed']!=true)).toList();
  String elementName(dynamic id)=>const {'fire':'Fuego','water':'Agua','earth':'Tierra','wind':'Viento','lightning':'Rayo','ice':'Hielo','light':'Luz','dark':'Oscuridad','nature':'Naturaleza','blood':'Sangre','metal':'Metal','astral':'Astral','void':'Vacío','divine':'Divino','gravity':'Gravedad','space':'Espacio','tempo':'Ritmo temporal','sound':'Sonido','dream':'Sueño','crystal':'Cristal','entropy':'Entropía','magnetism':'Magnetismo','neutral':'Neutro'}[id]??id.toString();
  List<String> elementsOf(Map person){final els=person['elements'] is List?(person['elements'] as List).map((x)=>x.toString()).toList():<String>['neutral'];if(person['singularElement'] is String&&s.flags.contains(person['singularFlag'])&&c.skills.any((sk)=>sk['owner']==person['id']&&sk['element']==person['singularElement']&&s.appraised.contains(sk['id'])&&s.canAppraise(sk)))els.add(person['singularElement'] as String);return els;}
  String className(Map person)=>person['combatClass']?.toString()??'Guerrero';
  int affinityFor(Map sp){
    final element=sp['element']??'neutral';
    if(element=='void')return 0;
    if(element!='neutral'&&element!='divine'&&!DualState.commonElements.contains(element)&&!learnedSkills.any((sk)=>sk['element']==element))return 0;
    if(element=='divine'&&!s.flags.contains('divine_devotion'))return 0;
    return (c.data['player']?['spiritualAffinity'] as int?)??85;
  }
  int npcIntelligence(Map person)=>((person['spiritIntelligence'] as int?)??((person['level'] as int? ?? 1)*3+5))+s.grades.length*2;
  int npcAffinity(Map person,Map sp)=>DualState.elementalAffinity(person,sp);
  int npcSlots(Map person)=>DualState.spiritualCapacity(person,npcIntelligence(person));
  bool talentRevealed(Map person)=>(person['talentRevealFlag']==null||s.flags.contains(person['talentRevealFlag']))&&(person['hiddenRace']!=true||s.knownRaces.contains(person['id']));
  Map publicTalent(Map person)=>talentRevealed(person)?person:{...person,'race':publicRace(person),'spiritClass':person['coverSpiritClass']??'ordinary','combatClass':person['coverClass']??person['combatClass'],'elements':person['coverElements']??['neutral'],'initialRank':person['coverRank']??person['initialRank'],'potentialRank':person['coverPotential']??person['initialRank'],'spiritualAffinity':person['publicAffinity']??35,'spiritIntelligence':person['coverIntelligence']??15};
  bool spiritReady(Map sp)=>s.spiritChance(sp,affinityFor(sp))>0&&s.freshSpiritAttempt(sp);
  List<Map<String,dynamic>> get learnedSkills=>[...c.skills.where((sk)=>s.skills.contains(sk['id'])).map((sk)=>s.copiedSkills[sk['id']]??sk),...s.fusedSkills.values];
  List<Map<String,dynamic>> get combatSkills=>[...learnedSkills.where((sk)=>sk['element']!='divine'||s.flags.contains('divine_devotion')).map(s.effectiveTechnique),for(final sp in c.spirits.where((sp)=>s.activeSpirit==sp['id']&&s.spirits.contains(sp['id'])))...[
    <String,dynamic>{'id':'spirit_'+sp['id'].toString(),'spirit':sp['id'],'name':'Técnica de '+sp['name'].toString(),'type':sp['type'],'magic':true,'cost':sp['cost'],'damage':sp['damage'],'element':sp['element'],'minIntelligence':sp['intelligence']},
    for(final mode in ['manifest','fusion','enchant']) <String,dynamic>{'id':'spirit_'+sp['id'].toString()+'_'+mode,'spirit':sp['id'],'spiritMode':mode,'name':({'manifest':'Manifestar','fusion':'Fusionar con','enchant':'Encantar arma con'}[mode]??mode)+' '+sp['name'].toString(),'type':'support','magic':true,'cost':DualState.numOf(sp,'cost',3)+2,'damage':0,'element':sp['element'],'minIntelligence':sp['intelligence'],'spiritStamina':DualState.numOf(sp,'stamina',10)}
  ]];
  Map<String,dynamic> enemyProfile(int index){
    final e=s.warEnemyProfile(c.enemies[index]);
    if(e['training']==true)return e;
    final person=c.people.firstWhere((p)=>p['id']==e['person'],orElse:()=> <String,dynamic>{});
    final race=c.raceFor(person['race']??e['race']);
    final shown=c.raceFor(person.isEmpty?e['race']:publicRace(person));
    e['raceName']=shown['name'];
    e['racialTrait']=shown['trait'];
    for(final k in ['attack','defense','evasion','regen','spellPower','hypnosis','lifesteal']){if(race[k] is int)e[k]=((e[k] as int?)??0)+(race[k] as int);}
    if(person.isNotEmpty){final talent=publicTalent(person);final techniques=<Map<String,dynamic>>[for(final sk in discoverableSkills(person)) {...sk,'mastery':DualState.elementMastery(talent,sk['element'])}];
      // Basic elemental spells do not grant a permanent learned technique to the player.
      for(final element in DualState.commonElements){techniques.add({'name':'Pulso de '+elementName(element),'type':'attack','magic':true,'damage':4+(person['level'] as int? ?? 1)*2,'mastery':DualState.elementMastery(talent,element)});}
      final growth=DualState.combatRankIndex(DualState.combatRank(talent,s.grades.length))-DualState.combatRankIndex(DualState.combatRank(talent,0));if(growth>0){e['attack']=(e['attack'] as int)+growth*2;e['defense']=(e['defense'] as int)+growth;e['hp']=(e['hp'] as int)+growth*8;}final hidden=person['hiddenRace']==true&&!s.knownRaces.contains(person['id']);if(!hidden||e['lethal']==true){final compatible=c.spirits.where((sp)=>npcAffinity(talent,sp)>=((sp['minAffinity'] as int?)??25)&&npcIntelligence(talent)>(sp['intelligence'] as int)&&s.grades.length>=((sp['minClasses'] as int?)??0)).toList()..sort((a,b)=>(b['intelligence'] as int).compareTo(a['intelligence'] as int));for(final sp in compatible.take(npcSlots(talent)))techniques.add({'name':'Invocar '+sp['name'].toString(),'type':sp['type'],'damage':sp['damage'],'magic':true});}e['techniques']=techniques;e['level']=studentLevel(person);e['intelligence']=npcIntelligence(talent);}
    if(e['lethal']==true||person.isEmpty||person['hiddenRace']!=true||s.knownRaces.contains(person['id'])){}else{for(final k in ['lifesteal','regen','spellPower','evasion','hypnosis'])e.remove(k);e['attack']=c.enemies[index]['attack'];e['defense']=c.enemies[index]['defense'];}
    return e;
  }
  int studentLevel(Map person)=>((person['level'] as int?)??1)+DualState.combatRankIndex(DualState.combatRank(publicTalent(person),s.grades.length))-DualState.combatRankIndex(DualState.combatRank(publicTalent(person),0));
  Widget appraisal()=>section('Apreciación y adquisición',[
    const Text('Apreciación revela las técnicas actuales de un estudiante. Al avanzar los arcos, sus capacidades evolucionan. Vuelve a apreciar a tus compañeros para descubrir técnicas nuevas.'),
    DropdownButton<String>(isExpanded:true,value:raceFilter,items:[const DropdownMenuItem(value:'all',child:Text('Todas las razas')),for(final r in c.races.where((r)=>r['secret']!=true||c.people.any((p)=>p['race']==r['id']&&s.knownRaces.contains(p['id']))))DropdownMenuItem(value:r['id'].toString(),child:Text(r['name'].toString()))],onChanged:busy?null:(value)=>setState(()=>raceFilter=value??'all')),
    TextField(decoration:const InputDecoration(labelText:'Buscar estudiante'),onChanged:(value)=>setState(()=>nameFilter=value.toLowerCase().trim())),
    for(final person in c.people.where((p)=>!s.deadStudents.contains(p['id'])&&(s.place=='Sala de profesores'?p['teacher']==true:p['teacher']!=true)&&(raceFilter=='all'||publicRace(p)==raceFilter)&&p['name'].toString().toLowerCase().contains(nameFilter)))...[
      const Divider(),
      personArt(person),
      Text(person['name'].toString()+(person['teacher']==true?' · Profesor':' · Año '+person['year'].toString())+' · Nv. '+studentLevel(person).toString()+' · '+(person['origin']??'Origen desconocido').toString(),style:const TextStyle(fontWeight:FontWeight.bold)),
      Text(person['intro'].toString()),
      if(person['teacher']==true)Text('Especialidad: '+(person['subject']??'Combate').toString()),
      if(s.flags.contains('secret_job_'+person['id'].toString()))Text('Identidad exterior descubierta: '+(person['secretOccupation']??'Aventurero').toString()),
      if(person['race']!=null)Text('Raza: '+(c.raceFor(publicRace(person))['name']??publicRace(person)).toString()),
      if(person['appearance'] is String)Text(person['hiddenRace']==true&&!s.knownRaces.contains(person['id'])?(person['coverAppearance']??'Apariencia humana.').toString():person['appearance'] as String),
      if(discoverableSkills(person).any((sk)=>s.appraised.contains(sk['id']))&&c.raceFor(publicRace(person))['trait'] is String)Text('Rasgo innato: '+c.raceFor(publicRace(person))['trait'].toString()),
      Text('Afinidad espiritual: '+(publicTalent(person)['spiritualAffinity']??35).toString()+'/100'),
      Text('Clase: '+className(publicTalent(person))+' · Elementos: '+elementsOf(publicTalent(person)).map(elementName).join(', ')),
      Text('Rango de combate: '+(DualState.combatAppraisalTier(DualState.combatRank(publicTalent(person),s.grades.length))<=s.appraisalTier?DualState.combatRank(publicTalent(person),s.grades.length):'???')+' · Potencial: '+(s.appraisalTier>=4?(publicTalent(person)['potentialRank']??'Desconocido').toString():'???')),
      if(talentRevealed(person)&&person['classAffinities'] is List)Text('Afinidad con clases: '+(person['classAffinities'] as List).join(', ')),
      if(talentRevealed(person)&&person['weaponAffinities'] is List)Text('Aptitud de armas: '+(person['weaponAffinities'] as List).join(', ')),
      Text('Rango espiritual: '+DualState.spiritualRank((publicTalent(person)['spiritualAffinity'] as int?)??35,npcIntelligence(publicTalent(person)))+' · Capacidad: '+npcSlots(publicTalent(person)).toString()),
      if(DualState.royalFaction(person)!=null)Text(DualState.royalFactions[DualState.royalFaction(person)]!+' · adversario: '+(DualState.royalFaction(person)=='evelyne'?'Aldren Aurel':'Evelyne Aurel')),
      Text('Confianza: '+s.relationship(person['id'] as String).toString()+(person['romance']==true?' · Afinidad: '+s.warmth(person['id'] as String).toString():'')),
      if(s.appraisalTier>=3&&s.intelligence>=30&&s.relationship(person['id'] as String)>=7&&!s.knownRaces.contains(person['id']))btn('Apreciación profunda',(){s.knownRaces.add(person['id'] as String);return 'La apreciación profunda permite examinar el repertorio real.';}),
      if(discoverableSkills(person).any((sk)=>!s.canAppraise(sk)&&sk['singular']!=true))const Text('Apreciación insuficiente · existen técnicas que todavía no puedes identificar.'),
      if(discoverableSkills(person).any((sk)=>s.canAppraise(sk)&&needsAppraisal(sk)))btn('Apreciar '+person['name'].toString(),(){
        final discovered=discoverableSkills(person).where((sk)=>s.canAppraise(sk)&&needsAppraisal(sk)).toList();
        s.appraised.addAll(discovered.map((sk)=>sk['id'] as String));for(final sk in discovered){s.appraisedRanks[sk['id'] as String]=DualState.rankIndex(sk['rank']);}
        return 'Técnicas descubiertas: '+discovered.length.toString()+'.';
      }),
      for(final sk in discoverableSkills(person).where((x)=>s.canAppraise(x)&&s.appraised.contains(x['id'])&&!needsAppraisal(x)))...[
        Text(sk['name'].toString()+' · Rango '+(sk['rank']??'E').toString()+' · '+sk['type'].toString()+(sk['element']==null?'':' · '+elementName(sk['element']))+' · potencia '+sk['damage'].toString()+' · '+sk['price'].toString()+' monedas · '+sk['cost'].toString()+(sk['magic']==true?' maná':' estamina')),
        if(sk['singular']==true)const Text('Talento singular · afinidad excepcional'),
        if(sk['innate']==true&&sk['copyable']!=false)const Text('Técnica racial · copiable mediante Robo'),
        if(sk['description'] is String)Text(sk['description'] as String),
        Text(sk['copyable']==false?'Poder exclusivo · no se puede copiar':s.skills.contains(sk['id'])?'Aprendida':'Disponible para adquirir en tu dormitorio.')
      ]
    ]
  ]);
  Widget skillRoom()=>section('Poderes secretos · Apreciación y Robo',[
    const Text('Solo puedes adquirir las habilidades descubiertas en la academia cuando estás a solas en tu dormitorio. No tienes ninguna técnica de combate al empezar.'),
    Text('Apreciación · Rango '+s.appraisalRank+' · INT '+s.intelligence.toString()),
    if(s.appraisalTier<7)Text('Siguiente rango: INT '+DualState.appraisalThresholds[s.appraisalTier+1].toString()+' y '+DualState.appraisalFees[s.appraisalTier+1].toString()+' monedas.'),
    if(s.appraisalTier<7)btn('Refinar Apreciación · '+DualState.appraisalFees[s.appraisalTier+1].toString()+' monedas',()=>s.refineAppraisal()?'Apreciación mejorada.':'Necesitas inteligencia y monedas suficientes.'),
    if(s.skills.isEmpty)const Text('Habilidades de combate: ninguna.'),
    const Text('Retorno: una muerte real reinicia ambos mundos. Solo conservas inteligencia.'),
    for(final sk in purchasableSkills)...[Text(sk['name'].toString()+' · Rango '+(sk['rank']??'E').toString()+' · '+sk['price'].toString()+' monedas · potencia '+sk['damage'].toString()+' · '+sk['cost'].toString()+(sk['magic']==true?' maná':' estamina')),if(!s.skills.contains(sk['id']))btn('Adquirir',()=>sk['element']=='divine'&&!s.flags.contains('divine_devotion')?'Necesitas profesar la fe de la Llama del Alba.':s.acquireRankedSkill(sk)?'Habilidad adquirida.':'No tienes dinero suficiente.')else const Text('Aprendida')]
  ]);
  Future<void> chooseFusion(Map a)async{
    final options=learnedSkills.where((b)=>s.compatibleFusion(a,b)&&!s.fusedSkills.containsKey(s.fusionKey(a,b))).toList();
    if(options.isEmpty){setState(()=>message='No hay técnicas compatibles todavía.');return;}
    final b=await showDialog<Map<String,dynamic>>(context:context,builder:(ctx)=>SimpleDialog(title:const Text('Seleccionar segunda técnica'),children:[for(final b in options)SimpleDialogOption(onPressed:()=>Navigator.pop(ctx,b),child:Text(b['name'].toString()+' · '+s.fusionFee(a,b).toString()+' monedas · INT mínima '+s.fusionMinimum(a,b).toString()+' · '+s.fusionChance(a,b).toString()+'% éxito'))]));
    if(b==null||!mounted)return;
    final chance=s.fusionChance(a,b),fee=s.fusionFee(a,b);
    if(chance==0||s.cash<fee){setState(()=>message='Necesitas más inteligencia o monedas.');return;}
    final confirm=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:const Text('Confirmar fusión'),content:Text('Probabilidad: '+chance.toString()+'%. Coste: '+fee.toString()+' monedas, incluso si falla. Conservarás las dos técnicas originales.'),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Cancelar')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Intentar fusión'))]));
    if(confirm==true&&mounted)await act((){final before=s.cash;final ok=s.fuse(a,b);return ok?'Nueva técnica creada.':s.cash<before?'Fusión fallida. Conservas las técnicas originales; el coste se ha consumido.':'No cumples los requisitos.';});
  }
  String resourceCost(Map sk)=>[if(DualState.staminaCost(sk)>0)DualState.staminaCost(sk).toString()+' estamina',if(DualState.manaCost(sk)>0)DualState.manaCost(sk).toString()+' maná'].join(' + ');
  Widget classTree()=>section('Especializaciones abiertas',[
    const Text('Puedes aprender varias clases. Desbloquea sus ramas con fuerza, inteligencia y especializaciones previas.'),
    for(final entry in DualState.specializations.entries)...[
      Text(entry.key+' · FUE '+entry.value[0].toString()+' · INT '+entry.value[1].toString()+(entry.value[2]==''?'':' · requiere '+entry.value[2].toString())+(entry.key=='Espadachín mágico'?' y Mago':'')),
      if(s.hasClass(entry.key))const Text('Aprendida')else if(s.canLearnClass(entry.key))btn('Especializarme en '+entry.key,()=>s.learnClass(entry.key)?'Especialización adquirida.':'Requisitos insuficientes.'),
    ],
  ]);
  Widget socialTraining()=>section('Carisma y suerte',[
    Text('Carisma '+s.charisma.toString()+' · Suerte '+s.luck.toString()),
    const Text('El carisma mejora moderadamente la confianza ganada por tus decisiones. No elimina penalizaciones.'),
    btn('Aumentar carisma · '+s.charismaFee.toString()+' monedas',()=>s.improveSocial('charisma')?'Carisma aumentado.':'Monedas insuficientes.'),
    btn('Aumentar suerte · '+s.luckFee.toString()+' monedas',()=>s.improveSocial('luck')?'Suerte aumentada.':'Monedas insuficientes.'),
  ]);
  Widget workshop()=>section('Taller secreto · evolución y fusión',[const Text('Solo tú puedes ascender técnicas con dinero y fusionarlas. La inteligencia aumenta la probabilidad de éxito. Un fallo consume monedas, no las técnicas originales. Retorno elimina estas mejoras.'),for(final sk in learnedSkills)...[const Divider(),Text(sk['name'].toString()+' · '+DualState.powerRanks[s.techniqueTier(sk)]+' · potencia '+s.effectiveTechnique(sk)['damage'].toString()),if(s.techniqueTier(sk)<7)btn('Ascender · '+s.upgradeFee(sk).toString()+' monedas',()=>s.upgradeTechnique(sk)?'Técnica ascendida.':'Necesitas dinero e inteligencia suficientes.'),if(!sk['id'].toString().startsWith('fusion_'))FilledButton(onPressed:busy?null:()=>chooseFusion(sk),child:const Text('Fusionar con otra técnica'))]]);
  String get arcTitle{final arcs=DualWorldContent.list(c.data['arcs']);String name='Arco I';for(final a in arcs){if(s.grades.length>=((a['afterClasses'] as int?)??0))name=a['title'].toString();}return name;}
  List<Map<String,dynamic>> get royalEvents=>[
    for(final p in c.people.where((p)=>DualState.royalFaction(p)!=null))
      <String,dynamic>{
        'id':'royal_mission_'+DualState.royalFaction(p)!,
        'world':'school','place':'Consejo','person':p['id'],'minClasses':1,
        'requiresRoyalFaction':DualState.royalFaction(p),
        'title':DualState.royalFaction(p)=='evelyne'?'La petición de la princesa':'La petición del príncipe',
        'scene':p['name'].toString()+' te pide que apoyes su propuesta ante el Consejo. La facción rival está en desacuerdo. Tu postura será recordada.',
        'choices':[
          {'id':'support','label':'Defender su propuesta','trust':4,'faction':'royal_'+DualState.royalFaction(p)!,'standing':5,'outcome':'Tu apoyo ha sido observado. La facción rival también toma nota.'},
          {'id':'question','label':'Pedir pruebas antes de tomar partido','trust':1,'outcome':'El Consejo escucha tus preguntas. No prometes lealtad.'},
          {'id':'refuse','label':'Rechazar la petición','trust':-3,'faction':'royal_'+DualState.royalFaction(p)!,'standing':-3,'outcome':'La petición queda rechazada. Tu decisión tiene consecuencias.'}
        ]
      }
  ];
  Widget royalPolitics()=>section('La disputa de la Corona',[
    Row(children:[for(final p in c.people.where((p)=>DualState.royalFaction(p)!=null))Expanded(child:personArt(p))]),
    const Text('Evelyne Aurel y Aldren Aurel lideran facciones adversarias. Sus seguidores compiten por influencia en la academia y el reino. Puedes tomar partido o permanecer neutral.'),
    Text('Tu postura: '+(s.royalChoiceMade?DualState.royalFactions[s.royalAlignment]??'Neutral':'Sin decidir')),
    for(final side in ['evelyne','aldren'])Text(DualState.royalFactions[side]!+' · reputación '+s.royalStanding(side).toString()),
    if(!s.royalChoiceMade)for(final side in ['evelyne','aldren','neutral'])btn(side=='neutral'?'Permanecer neutral':'Unirme a '+DualState.royalFactions[side]!,()=>s.chooseRoyalFaction(side)?(side=='neutral'?'No juras lealtad a ninguno. Conservas tu independencia.':'Tu alianza queda registrada. La facción rival te observa con desconfianza.'):'No puedes cambiar tu postura ahora.'),
    if(s.royalChoiceMade)const Text('Tu decisión abre determinadas misiones. La confianza personal sigue dependiendo de tus actos.'),
  ]);
  Widget storyEvents()=>Column(children:[for(final e in [...c.events,...royalEvents].where(s.eligible))section(e['title'].toString(),[
    for(final p in c.people.where((p)=>p['id']==e['person']))personArt(p),
    Text(e['scene'].toString()),const SizedBox(height:12),
    for(final choice in DualWorldContent.list(e['choices']))FilledButton(onPressed:busy||s.cash<((choice['cost'] as int?)??0)?null:()=>act(()=>s.chooseEvent(e,choice)?s.lastEvent:'No puedes elegir esta opción.'),child:Text(choice['label'].toString())),
  ])]);
  Widget dungeon()=>section('Dungeons · expediciones y espíritus',[
    const Text('Los combates aquí pueden terminar en muerte real. El Retorno reinicia ambos mundos. Los duelos de academia son protegidos.'),
    Text('Tus vínculos espirituales: '+s.spirits.length.toString()+' · Sin límite fijo · rango innato '+DualState.spiritualRank((c.data['player']?['spiritualAffinity'] as int?)??85,0)),
    Text('Elementos adquiridos: '+({for(final sk in c.skills.where((sk)=>s.skills.contains(sk['id']))) (sk['element']??'neutral').toString()}.map(elementName).join(', '))),
    const Text('La afinidad espiritual es innata y fija. La inteligencia aumenta tus posibilidades de vínculo, no tu rango espiritual.'),
    for(final sp in c.spirits.where((sp)=>s.grades.length>=((sp['minClasses'] as int?)??0)))...[art(sp['id'].toString(),height:180),Text(sp['name'].toString()+' · '+(sp['rarity']??'Común').toString()+' · INT '+sp['intelligence'].toString()+' · elemento '+elementName(sp['element']??'neutral')+' · afinidad '+sp['affinity'].toString()),
    if(sp['form'] is String)Text(sp['form'] as String),Text(s.spirits.contains(sp['id'])?'Vinculado':'Afinidad: '+affinityFor(sp).toString()+'/100 · probabilidad: '+s.spiritChance(sp,affinityFor(sp)).toString()+'%'),if(spiritReady(sp))btn('Intentar vínculo',()=>s.trySpirit(sp,affinityFor(sp)))else if(!s.spirits.contains(sp['id']))const Text('Necesitas cumplir los requisitos o vencer nuevamente en su encuentro.')],
    if(s.rescueMissions.isNotEmpty)const Text('Hay una expedición de rescate pendiente. Completa el combate antes de que termine el plazo.'),
    for(final person in c.people.where((p)=>s.rescuedStudents.contains(p['id'])))Text('Rescatado: '+person['name'].toString()),
    battle()
  ]);
  bool enemyVisible(Map enemy){if(s.deadStudents.contains(enemy['person']))return false;
    final location=enemy['location'];
    if(location is String){if(location!=s.place)return false;if(enemy['repeatable']!=true&&s.wins.contains('battle_'+enemy['id'].toString()))return false;}else if((enemy['lethal']==true)!=(s.place=='Dungeon')||!const ['Arena','Dungeon'].contains(s.place))return false;
    if(s.grades.length<((enemy['minClasses'] as int?)??0))return false;if(enemy['maxClasses'] is int&&s.grades.length>(enemy['maxClasses'] as int))return false;if(enemy['requiresFlag'] is String&&!s.flags.contains(enemy['requiresFlag'])&&!(enemy['requiresFlag']=='mercenary_member'&&s.canFightWar))return false;if(!s.warEnemyAvailable(enemy))return false;if(enemy['rescueOnly']==true&&!s.rescueMissions.containsValue(enemy['id']))return false;return true;}
  Widget battle(){if(!s.inBattle)return section('Arena y monstruos',[
    const Text('Los combates son por turnos. Las técnicas físicas consumen estamina; las mágicas consumen maná.'),
    for(final sp in c.spirits.where((sp)=>s.spirits.contains(sp['id'])))btn((s.activeSpirit==sp['id']?'Activo: ':'Vincular para combate: ')+sp['name'].toString(),()=>s.selectSpirit(sp)?'Espíritu seleccionado.':'No disponible.'),
    if(s.pendingDuel.isNotEmpty)const Text('Tienes un desafío personal pendiente. Busca a tu rival.'),
    if(!combatSkills.any((sk)=>const ['attack','drain','bleed','void'].contains(sk['type'])))const Text('No tienes ninguna técnica de ataque. Usa Apreciación, consigue monedas en Lumen y adquiere una en tu dormitorio.'),
    for(var i=0;i<c.enemies.length;i++)if(enemyVisible(c.enemies[i]))...[
      Text(c.enemies[i]['name'].toString()+' · nivel '+c.enemies[i]['level'].toString()+(c.enemies[i]['rank']!=null?' · Rango '+c.enemies[i]['rank'].toString():'')+' · '+s.victoryXp(enemyProfile(i),!s.wins.contains('battle_'+c.enemies[i]['id'].toString())).toString()+' XP'+(enemyProfile(i)['raceName']!=null?' · '+enemyProfile(i)['raceName'].toString():'')),
      if(DualState.numOf(enemyProfile(i),'warEvolution',0)>0)Text('Evolución de la Ruptura · fase '+DualState.numOf(enemyProfile(i),'warEvolution',0).toString()),
      if(c.enemies[i]['raid']==true)...[
        Text((c.enemies[i]['form']=='humanoid'?'Entidad divina humanoide · ':'Amenaza legendaria · ')+(c.enemies[i]['description']??'Entidad invasora').toString()),
        if(combatSkills.any((sk)=>const ['attack','drain','bleed','void'].contains(sk['type'])))...[
          if(s.activeAlliedChampions.isNotEmpty&&s.level>=DualState.numOf(c.enemies[i],'teamMinLevel',1))btn('Asalto con escuadrón',()=>s.startRaid(i,enemyProfile(i),withTeam:true)?'Tu escuadrón entra en combate.':'No puedes iniciar el asalto.')else Text(s.activeAlliedChampions.isEmpty?'No quedan campeones disponibles.':'Escuadrón disponible desde nivel '+DualState.numOf(c.enemies[i],'teamMinLevel',1).toString()),
          if(c.enemies[i]['form']=='humanoid')const Text('Los héroes pueden ayudarte a resistir y curarte, pero sus ataques no dañan a una deidad.'),
          btn('Desafiar en solitario · peligro extremo',()=>s.startRaid(i,enemyProfile(i),withTeam:false)?'Entras solo al combate.':'No puedes iniciar el asalto.'),
        ]else const Text('Necesitas una técnica de ataque.')
      ]else if((c.enemies[i]['openChallenge']==true||s.level>=(c.enemies[i]['level'] as int))&&combatSkills.any((sk)=>const ['attack','drain','bleed','void'].contains(sk['type'])))btn(s.pendingDuel==c.enemies[i]['id']?'Aceptar duelo pendiente':'Desafiar',()=>s.startBattle(i,enemyProfile(i)['hp'] as int,lethal:c.enemies[i]['lethal']==true)?'Comienza el combate.':'Debes recuperarte antes.')else const Text('Requiere nivel y una técnica de ataque')]
  ]);final e=enemyProfile(s.enemyIndex);return section('Combate · '+e['name'].toString(),[
    Row(children:[Expanded(child:art('hero',height:200)),Expanded(child:enemyArt(e))]),
    if(e['racialTrait'] is String)Text('Rasgo del rival: '+e['racialTrait'].toString()),
    Text('Tu vida: '+s.hp.toString()+'/'+s.maxHp.toString()+' · rival: '+s.enemyHp.toString()+'/'+e['hp'].toString()),
    if(e['raid']==true)...[
      Text(s.raidAllies.isEmpty?'Asalto en solitario':'Escuadrón de mercenarios'),
      for(final a in s.raidAllies)Text((a['name']??a['role']).toString()+' · '+(a['rank']??'').toString()+' · '+a['role'].toString()+' · Vida '+a['hp'].toString()+'/'+a['maxHp'].toString()+' · Estamina '+a['energy'].toString()+' · Maná '+a['mana'].toString()+(a['hp']==0?' · Fuera de combate':'')),
    ],
    Text('Estamina: '+s.energy.toString()+'/'+s.stamina.toString()+' · Maná: '+s.mana.toString()+'/'+s.intelligence.toString()),
    if(s.enemyEnergy>=0)Text('Rival: estamina '+s.enemyEnergy.toString()+'/'+s.enemyMaxEnergy.toString()+' · maná '+s.enemyMana.toString()+'/'+s.enemyMaxMana.toString()),
    Text('Tus estados: '+(s.playerStates.isEmpty?'ninguno':s.playerStates.entries.map((e)=>e.key+' ('+e.value.toString()+')').join(', '))),
    Text('Estados del rival: '+(s.enemyStates.isEmpty?'ninguno':s.enemyStates.entries.map((e)=>e.key+' ('+e.value.toString()+')').join(', '))),
    if(s.activeSpirit.isNotEmpty)Text('Espíritu: '+s.spiritMode+' · resistencia elemental +3% · estamina espiritual '+s.spiritEnergy.toString()),
    Text('Guardia: '+s.guardTurns.toString()+' turnos · evasión: '+s.speedTurns.toString()+' turnos · sello: '+s.enemyWeakTurns.toString()+' · hemorragia: '+s.enemyBleedTurns.toString()),
    if((s.turn+1)%3==0)const Text('El rival prepara un ataque fuerte. Considera defenderte o esquivar.'),
    for(final sk in combatSkills)if(s.usable(sk))btn(sk['name'].toString()+' · '+resourceCost(sk)+' · crítico '+DualState.critChance(DualState.numOf(sk,'criticalChance',5),s.precision+DualState.numOf(sk,'precision',0)).toString()+'%',()=>s.action(sk,e,availableSkills:combatSkills))else Text(sk['name'].toString()+' · no disponible'),
    btn('Retirarte',(){s.enemyIndex=-1;s.lethalBattle=false;return 'Retirada sin recompensa. Un rescate pendiente sigue sujeto a su plazo.';})
  ]);}
  Widget armory({required bool store})=>section(store?'Armería de Lumen':'Inventario y equipamiento',[
    Text('Fuerza base '+s.strength.toString()+' · INT '+s.intelligence.toString()),
    const Text('El bono mágico completo requiere que la técnica coincida con la afinidad del arma; si no coincide, se aplica la mitad. Las armas neutras son compatibles con cualquier técnica.'),
    if(!store)Text('Bonificaciones equipadas: +'+s.weaponStrength.toString()+' fuerza · +'+s.weaponMagic.toString()+' magia · +'+s.weaponDefense.toString()+' defensa'),
    if(!store&&s.equippedWeapon.isNotEmpty)btn('Desequipar arma',(){s.unequipWeapon();return 'Arma guardada.';}),
    for(final w in c.weapons.where((w)=>store?s.grades.length>=((w['minClasses'] as int?)??0)&&(w['requiresWin']==null||s.wins.contains('battle_'+w['requiresWin'].toString())):s.weapons.contains(w['id'])))...[const Divider(),art(w['id'].toString(),height:140),Text(w['name'].toString()+' · '+w['category'].toString()+' · Rango '+w['rank'].toString()),Text((w['rarity']??'Común').toString()+' · Afinidad '+elementName(w['element']??'neutral')),Text('Requiere FUE '+w['minStrength'].toString()+' / INT '+w['minIntelligence'].toString()+' · Bonos +'+w['strengthBonus'].toString()+' fuerza, +'+w['magicBonus'].toString()+' magia, +'+w['defenseBonus'].toString()+' defensa'),if(store&&!s.weapons.contains(w['id']))btn('Comprar · '+w['price'].toString()+' monedas',()=>s.buyWeapon(w)?'Arma comprada. Equípala en el dormitorio.':'No puedes comprar esta arma.')else if(store)const Text('Adquirida')else if(s.equippedWeapon==w['id'])const Text('Equipada')else btn('Equipar',()=>s.equipWeapon(w)?'Arma equipada.':'No reúnes fuerza o inteligencia suficiente.')]
  ]);
  Widget market(){final cost=5+s.day%4,base=16+s.day%5;final demand=max(0,base-(price-10)*2);return section('Mercado · día '+(s.day+1).toString(),[
    Text('Compra: '+cost.toString()+' por unidad · puesto: 2 · existencias: '+s.stock.toString()),
    Text('Cantidad: '+qty.toString()),Slider(value:qty.toDouble(),min:0,max:30,divisions:30,onChanged:busy?null:(v)=>setState(()=>qty=v.round())),
    Text('Precio: '+price.toString()),Slider(value:price.toDouble(),min:5,max:25,divisions:20,onChanged:busy?null:(v)=>setState(()=>price=v.round())),
    Text('Demanda estimada: '+demand.toString()+' · salida de caja: '+(qty*cost+2).toString()),
    btn('Abrir puesto',(){final r=s.trade(qty,price,demand,cost,2);if(r==null)return 'Plan inválido o sin caja suficiente.';return 'Vendiste '+r['sold'].toString()+' · beneficio '+r['profit'].toString()+' · inventario '+r['stock'].toString()+' · caja '+r['cash'].toString();}),
    btn('Trabajar por comisión (+30)',(){s.commission();return 'Entregaste un encargo comercial. +30 monedas.';})
  ]);}
  @override Widget build(BuildContext context){
    if(loading)return const Scaffold(body:Center(child:CircularProgressIndicator()));
    final school=s.world=='school';final current=s.place;
    final locations=school?['Dormitorio','Clases','Biblioteca','Patio','Arena','Gimnasio','Ranking','Jardín','Consejo','Pasillo antiguo','Dungeon','Iglesia','Palacio','Sala de profesores','Gremio de aventureros','Bosque fronterizo','Minas de Valdren','Campamento mercenario','Frente de guerra',...DualWorldContent.list(c.data['locations']).where((l)=>l['world']=='school').map((l)=>l['name'].toString())].toSet().toList():['Taller privado','Mercado','Gremio','Almacén','Puerto','Armería','Empresas',...DualWorldContent.list(c.data['locations']).where((l)=>l['world']=='trade').map((l)=>l['name'].toString())].toSet().toList();
    return Scaffold(appBar:AppBar(title:Text(school?'Academia · Entre dos mundos':'Mundo comercial'),actions:[IconButton(onPressed:busy?null:importArt,icon:const Icon(Icons.image_outlined),tooltip:'Importar arte de Asteria')]),body:ListView(padding:const EdgeInsets.all(14),children:[
      landscape(current),
      if(c.data['player'] is Map)section((c.data['player']['name']??'Valcrest').toString(),[art('hero',height:180),Text((c.data['player']['appearance']??'').toString()),const Text('Becario · Casa de Valcrest')]),
      Text('Nivel '+s.level.toString()+' · Rango '+s.playerCombatRank+' · XP '+s.xp.toString()+' · monedas '+s.cash.toString(),style:const TextStyle(fontSize:20,fontWeight:FontWeight.bold)),
      Text('Fuerza '+s.strength.toString()+' · defensa/resistencia '+s.defense.toString()+' · estamina '+s.stamina.toString()+' · inteligencia '+s.intelligence.toString()),
      Text('Lugar: '+current+' · notas '+s.examAverage.toString()+'/100 · reputación '+s.reputation.toString()),
      Text('Habilidades de combate: '+s.skills.length.toString()+' · poderes innatos: Apreciación, Robo y Retorno'),
      Text(arcTitle+' · '+s.decisions.length.toString()+' acontecimientos resueltos'),
      section('Crónica de la guerra · semana '+s.warWeek.toString(),[
        if(s.warWon)const Text('La ofensiva ha sido repelida. La academia recupera la normalidad.'),
        if(s.academyMobilized)...[
          const Text('EMERGENCIA · La academia está bajo amenaza. Profesores y estudiantes han sido movilizados para defender el mundo. La defensa no exige jurar lealtad a la Corona.'),
          if(!s.inBattle)btn('Acudir a la defensa de Asteria',(){s.world='school';s.place='Frente de guerra';return 'Te reúnes con las fuerzas defensoras de la academia.';}),
        ],
        if(!s.warWon)Text('Estimación de la horda invasora: '+s.remainingHorde.toString()+' criaturas'),
        if(!s.warWon)Text('Situación aliada: '+(s.warThreat==0?'Defensas estables':s.warThreat<5?'Frontera en peligro':s.warThreat<9?'Derrotas graves':'Riesgo de colapso')),
        ExpansionTile(title:Text(s.alliedReports.isEmpty?s.warNews.last:s.alliedReports.last),children:[for(final news in [...s.warNews,...s.alliedReports])Padding(padding:const EdgeInsets.all(6),child:Text(news))]),
        if(!s.inBattle&&!s.warWon&&s.privatePlace)btn('Avanzar una semana de la historia',()=>s.advanceWarWeek()?'Ha pasado una semana. Consulta los nuevos informes de la guerra.':'No puedes avanzar ahora.'),
      ]),
      if(message.isNotEmpty)Card(child:Padding(padding:const EdgeInsets.all(12),child:Text(message))),
      if(s.inBattle)battle()else...[
        Wrap(spacing:6,children:[for(final l in locations)ChoiceChip(label:Text(l),selected:l==current,onSelected:busy?null:(_)=>act((){s.place=l;answer.clear();return 'Llegaste a '+l+'.';}))]),
        if(s.privatePlace)section('Lugar privado',[Text(c.data['intro'].toString()),btn('Viajar al otro mundo',()=>s.travel()?'Atravesaste el portal.':'No puedes viajar aquí.'),btn('Descansar',(){s.rest();return 'Vida, maná y estamina recuperados.';})]),
        if(current=='Dormitorio')...[skillRoom(),workshop(),classTree(),socialTraining(),armory(store:false)],
        if(current=='Armería')armory(store:true),
        storyEvents(),
        if(current=='Palacio'||current=='Consejo')royalPolitics(),
        if(current=='Iglesia'||current=='Palacio'||current=='Consejo')section('Instituciones y relaciones políticas',[for(final faction in DualWorldContent.list(c.data['factions']))...[Text(faction['name'].toString(),style:const TextStyle(fontWeight:FontWeight.bold)),Text(faction['description'].toString()),Text('Relación: '+(s.factionStanding[faction['id']]??0).toString())]]),
        if(current=='Gremio')section('Gremio · encargos financieros',[const Text('Los encargos se pagan aquí, una sola vez por examen superado.'),for(final l in c.lessons.where((x)=>s.grades.containsKey(x['id'])&&!s.wins.contains('guild_'+x['id'].toString())))btn('Cobrar '+l['title'].toString(),(){final n=s.claimGuild(l['id'] as String);return 'Recibiste '+n.toString()+' monedas por tu informe.';})]),
        if(current=='Clases'&&s.academyMobilized)const Text('Clases suspendidas por la emergencia. Acude al frente de defensa; puedes prepararte en el dormitorio.'),
        if(current=='Clases'&&!s.academyMobilized)...[
          for(var i=0;i<c.lessons.length;i++)if(i<=s.grades.length&&(i!=2||s.wins.contains('battle_darian_practice'))&&(i!=4||s.wins.contains('battle_stone_beast'))&&(i!=6||s.wins.contains('battle_seren_duel')))lesson(c.lessons[i])else ListTile(leading:const Icon(Icons.lock),title:Text(c.lessons[i]['title'].toString()),subtitle:Text(i==2?'Supera el duelo de práctica de Darian.':i==4?'Derrota a la bestia de piedra.':i==6?'Supera el torneo de Seren.':'Supera las clases anteriores.'))
        ],
        if(current=='Biblioteca')library(),
        if(current=='Patio'||current=='Sala de profesores')appraisal(),
        if(current=='Gremio de aventureros')section('Registro de aventureros',[
          Text(s.flags.contains('adventurer_member')?'Licencia activa · victorias de caza '+c.enemies.where((e)=>e['requiresFlag']=='adventurer_member').fold<int>(0,(total,e)=>total+(s.battleCounts[e['id']]??0)).toString():'Sin licencia. Habla con el maestro del gremio.'),
          const Text('El gremio es independiente de la academia y del ejército. Las cacerías exteriores son voluntarias y letales.'),
          if(s.flags.contains('adventurer_member'))Text('Rango del gremio: '+(c.enemies.where((e)=>e['requiresFlag']=='adventurer_member'&&s.wins.contains('battle_'+e['id'].toString())).length>=12?'A':c.enemies.where((e)=>e['requiresFlag']=='adventurer_member'&&s.wins.contains('battle_'+e['id'].toString())).length>=6?'C':c.enemies.where((e)=>e['requiresFlag']=='adventurer_member'&&s.wins.contains('battle_'+e['id'].toString())).length>=3?'D':'E')),
        ]),
        if(current=='Campamento mercenario'||current=='Frente de guerra')section('Fuerzas aliadas',[
          const Text('Los héroes tienen poder fijo. Las hordas de rango B y A desgastan las defensas por su cantidad; los colosos SSS y las deidades pueden superarlas.'),
          Text('Combatientes activos: '+s.activeAlliedChampions.length.toString()+'/'+DualState.alliedChampions.length.toString()),
          for(final rank in ['L','SS','S','A','B+','B','C'])ExpansionTile(
            initiallyExpanded:const ['L','SS','S'].contains(rank),
            title:Text('Rango '+rank+' · '+s.activeAlliedChampions.where((a)=>a['rank']==rank).length.toString()+'/'+DualState.alliedChampions.where((a)=>a['rank']==rank).length.toString()),
            children:[for(final ally in DualState.alliedChampions.where((a)=>a['rank']==rank))...[
              if(const ['L','SS','S'].contains(rank))art(ally['id'].toString(),height:140),
              Text(ally['name'].toString()+' · Nv. '+ally['level'].toString(),style:const TextStyle(fontWeight:FontWeight.bold)),
              Text(ally['role'].toString()+' · '+ally['ability'].toString()+' · '+(s.alliedDefeated(ally)?'Derrotado · fuera del frente':'Activo')),
            ]],
          ),
        ]),
        if(current=='Campamento mercenario')section('Compañía mercenaria',[
          Text(s.flags.contains('mercenary_member')?'Contrato activo · servicio voluntario':'Sin contrato'),
          const Text('La Guerra de la Ruptura lleva décadas activa. Las entidades de Dravenn y sus colosos invaden el mundo desde las grietas. La academia permanece neutral frente a los bandos políticos; el servicio exterior es voluntario.'),
        ]),
        if(const ['Bosque fronterizo','Minas de Valdren','Frente de guerra'].contains(current)||c.enemies.any((e)=>e['location']==current))battle(),
        if(current=='Arena')battle(),
        if(current=='Dungeon')dungeon(),
        if(current=='Patio'&&s.flags.any((x)=>x.startsWith('fallback_')))section('Noticias de expediciones',[for(final person in c.people.where((p)=>s.flags.contains('fallback_'+p['id'].toString())))Text(person['name'].toString()+' regresó gracias al equipo de rescate.')]),
        if(current=='Patio'&&c.events.any((e)=>e['deadline'] is int&&s.grades.length>=((e['minClasses'] as int?)??0)&&s.grades.length<(e['deadline'] as int)&&!s.rescuedStudents.contains(e['person'])))section('Avisos de expedición',[const Text('Hay búsquedas pendientes en el Dungeon. Consulta los avisos antes de avanzar las clases.')]),
        if(current=='Patio'&&s.rumors.isNotEmpty)section('Rumores de la academia',[for(final person in c.people.where((p)=>s.rumors.contains(p['id'])))Text(person['name'].toString()+' ya no asiste a clases. Se comenta que no sobrevivió a un incidente; nadie explica bien qué ocurrió.')]),
        if(current=='Mercado')market(),
        if(current=='Empresas')LumenBusinessPanel(state:s,act:act,busy:busy),
        if(current=='Gimnasio')section('Entrenamiento real · FitRoutine',[const Text('Una recompensa por día local como máximo, solo por una sesión completa registrada en FitRoutine. No hace falta entrenar más para obtener más puntos.'),FilledButton(onPressed:busy||s.workoutDate.compareTo(today())>=0?null:workout,child:Text(s.workoutDate==today()?'Recompensa de hoy obtenida':'Verificar rutina completada'))]),
        if(current=='Ranking')section('Clasificación de la academia',[
          Text('Tus puntos: '+s.rankPoints.toString()+' · poder '+s.power.toString()),
          for(final row in ([{'name':'Tú','score':s.rankPoints},...c.people.where((x)=>!s.deadStudents.contains(x['id'])).map((x)=>{'name':x['name'],'score':x['rank']})]..sort((a,b)=>(b['score'] as int).compareTo(a['score'] as int))).asMap().entries)ListTile(title:Text((row.key+1).toString()+'. '+row.value['name'].toString()),trailing:Text(row.value['score'].toString()))
        ])
      ]
    ]));
  }
}
