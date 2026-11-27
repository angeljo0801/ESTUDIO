import 'dart:convert';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'models.dart';
import 'dual_world_engine.dart';

class DualWorldContent {
  const DualWorldContent(this.data,this.lessons,this.books,this.events,this.extraSkills,this.extraPeople,this.extraEnemies,this.spirits);
  final Map<String,dynamic> data;
  final List<Map<String,dynamic>> lessons,books,events,extraSkills,extraPeople,extraEnemies,spirits;
  List<Map<String,dynamic>> get people=>{for(final person in [...list(data['people']),...extraPeople]) person['id']:person}.values.toList();
  List<Map<String,dynamic>> get races=>list(data['races']);
  Map<String,dynamic> raceFor(dynamic id)=>races.firstWhere((r)=>r['id']==id,orElse:()=> <String,dynamic>{});
  List<Map<String,dynamic>> get skills=>{for(final sk in [...list(data['skills']),...extraSkills]) sk['id']:sk}.values.toList();
  List<Map<String,dynamic>> get enemies=>{for(final enemy in [...list(data['enemies']),...extraEnemies]) enemy['id']:enemy}.values.toList();
  static List<Map<String,dynamic>> list(dynamic raw)=>raw is List?raw.whereType<Map>().map((x)=>Map<String,dynamic>.from(x)).toList():[];
  static DualWorldContent? fromGuide(StudyGuide g){
    Map<String,dynamic>? root;final lessons=<Map<String,dynamic>>[],books=<Map<String,dynamic>>[],events=<Map<String,dynamic>>[],extraSkills=<Map<String,dynamic>>[],extraPeople=<Map<String,dynamic>>[],extraEnemies=<Map<String,dynamic>>[],spirits=<Map<String,dynamic>>[];
    for(final c in g.cards){try{final v=jsonDecode(c.adventureStory);if(v is! Map)continue;
      if(v['kind']=='memora_dual_world_v1')root=Map<String,dynamic>.from(v);
      if(v['kind']=='memora_dual_lesson_v1')lessons.add(Map<String,dynamic>.from(v));
      if(v['kind']=='memora_dual_book_v1')books.add(Map<String,dynamic>.from(v));
      if(v['kind']=='memora_dual_events_v1')events.addAll(list(v['events']));
      if(v['kind']=='memora_dual_skills_v1')extraSkills.addAll(list(v['skills']));
      if(v['kind']=='memora_dual_people_v1')extraPeople.addAll(list(v['people']));
      if(v['kind']=='memora_dual_enemies_v1')extraEnemies.addAll(list(v['enemies']));
      if(v['kind']=='memora_dual_spirits_v1')spirits.addAll(list(v['spirits']));
    }catch(_){}}
    if(root==null||lessons.isEmpty||list(root['skills']).isEmpty||list(root['enemies']).isEmpty)return null;
    return DualWorldContent(root,lessons,books,events,extraSkills,extraPeople,extraEnemies,spirits);
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
  String nameFilter='';
  final answer=TextEditingController();
  DualWorldContent get c=>widget.content;
  String get key=>'memora_dual_world_'+widget.guide.id;
  @override void initState(){super.initState();load();}
  @override void dispose(){answer.dispose();super.dispose();}
  Future<void> load()async{final p=await SharedPreferences.getInstance();try{final raw=p.getString(key);if(raw!=null)s=DualState.fromJson(jsonDecode(raw) as Map);}catch(_){}if(mounted)setState(()=>loading=false);}
  Future<void> act(String Function() fn)async{
    if(busy)return;setState(()=>busy=true);
    try{var next=fn();if(s.returned&&s.lethalBattle&&s.hp==0){s=s.returnToBeginning();next='RETORNO · Despiertas en tu dormitorio, el día de ingreso. Solo conservas inteligencia. '+next;raceFilter='all';nameFilter='';answer.clear();}s.resolveFates(c.events);final p=await SharedPreferences.getInstance();if(!await p.setString(key,jsonEncode(s.toJson())))throw StateError('No se pudo guardar');if(mounted)setState(()=>message=next);}
    catch(e){if(mounted)setState(()=>message=e.toString());}finally{if(mounted)setState(()=>busy=false);}
  }
  Widget btn(String label,String Function() fn)=>FilledButton(onPressed:busy?null:()=>act(fn),child:Text(label));
  Widget section(String title,List<Widget> children)=>Card(child:Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[Text(title,style:const TextStyle(fontSize:20,fontWeight:FontWeight.bold)),const SizedBox(height:10),...children])));
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
    return section(l['title'].toString(),[
      Text(l['teach'].toString()),const SizedBox(height:10),Text(l['example'].toString()),const Divider(),Text(l['question'].toString(),style:const TextStyle(fontWeight:FontWeight.bold)),
      if(grade==null)...[TextField(controller:answer,keyboardType:const TextInputType.numberWithOptions(decimal:true,signed:true),decoration:const InputDecoration(labelText:'Resultado numérico')),btn('Entregar examen',(){final n=double.tryParse(answer.text.trim().replaceAll(',','.'));if(n==null||!n.isFinite)return 'Introduce una cifra válida.';final ok=(n-(l['answer'] as num)).abs()<=0.011;final g=s.rewardExam(id,ok);answer.clear();if(ok){s.chapter=s.grades.length;return 'Nota: '+g.toString()+'/100. Desbloqueaste una revelación. Cobra tu encargo financiero en el gremio de Lumen.';}return 'Repasa el ejemplo e inténtalo otra vez.';})]else...[Text('Nota: '+grade.toString()+'/100'),const Divider(),Text(l['explanation'].toString()),const SizedBox(height:8),Text(l['reveal'].toString(),style:const TextStyle(fontWeight:FontWeight.w600))],
    ]);
  }
  Widget library()=>section('Biblioteca · inteligencia',[
    const Text('Cada libro completo otorga exactamente +5 inteligencia. Las páginas leídas quedan guardadas; releer no duplica la recompensa.'),
    for(final book in c.books)...[const Divider(),Text(book['title'].toString(),style:const TextStyle(fontWeight:FontWeight.bold)),Text('Páginas: '+(s.readPages[book['id']]??0).toString()+'/'+(book['pages'] as List).length.toString()),btn('Leer libro',(){final id=book['id'] as String;final i=s.readPages[id]??0;final pages=book['pages'] as List;if(i>=pages.length)return 'Libro completado.';showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:Text(book['title'].toString()+' · '+(i+1).toString()),content:SingleChildScrollView(child:Text(pages[i].toString())),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Cerrar')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Página leída'))])).then((v){if(v==true&&mounted)act(()=>s.read(id,i,pages.length)?'Página registrada.':'Sin recompensa duplicada.');});return 'Lee la página y confirma al terminar.';})]
  ]);
  String publicRace(Map person)=>person['hiddenRace']==true&&!s.knownRaces.contains(person['id'])?'human':(person['race']??'human').toString();
  List<Map<String,dynamic>> visibleSkills(Map person)=>c.skills.where((sk)=>sk['owner']==person['id']&&s.skillAvailable(sk)).toList();
  List<Map<String,dynamic>> discoverableSkills(Map person)=>visibleSkills(person).where((sk)=>(sk['secret']!=true||sk['revealFlag'] is String&&s.flags.contains(sk['revealFlag']))&&(person['hiddenRace']!=true||s.knownRaces.contains(person['id'])||sk['innate']!=true&&sk['concealed']!=true)).toList();
  bool spiritAffinity(Map sp){final affinity=sp['affinity'];if(affinity=='human'||affinity=='neutral')return true;return c.skills.any((sk)=>s.skills.contains(sk['id'])&&sk['innate']==true&&c.people.any((p)=>p['id']==sk['owner']&&p['race']==affinity));}
  bool spiritReady(Map sp)=>s.canCapture(sp)&&spiritAffinity(sp);
  List<Map<String,dynamic>> get combatSkills=>[...c.skills.where((sk)=>s.skills.contains(sk['id'])),for(final sp in c.spirits.where((sp)=>s.spirits.contains(sp['id'])))<String,dynamic>{'id':'spirit_'+sp['id'].toString(),'spirit':sp['id'],'name':'Invocar '+sp['name'].toString(),'type':sp['type'],'magic':true,'cost':sp['cost'],'damage':sp['damage']}];
  Map<String,dynamic> enemyProfile(int index){
    final e=Map<String,dynamic>.from(c.enemies[index]);
    final person=c.people.firstWhere((p)=>p['id']==e['person'],orElse:()=> <String,dynamic>{});
    final race=c.raceFor(person['race']??e['race']);
    final shown=c.raceFor(person.isEmpty?e['race']:publicRace(person));
    e['raceName']=shown['name'];
    e['racialTrait']=shown['trait'];
    for(final k in ['attack','defense','evasion','regen','spellPower','hypnosis','lifesteal']){if(race[k] is int)e[k]=((e[k] as int?)??0)+(race[k] as int);}
    if(person.isNotEmpty){final techniques=<Map<String,dynamic>>[...discoverableSkills(person)];final hidden=person['hiddenRace']==true&&!s.knownRaces.contains(person['id']);if(!hidden||e['lethal']==true){final compatible=c.spirits.where((sp)=>sp['affinity']==person['race']&&((person['spiritIntelligence'] as int?)??((person['level'] as int? ?? 1)*3+5))>(sp['intelligence'] as int)&&s.grades.length>=((sp['minClasses'] as int?)??0)).take(person['boss']==true?3:1);for(final sp in compatible)techniques.add({'name':'Invocar '+sp['name'].toString(),'type':sp['type'],'damage':sp['damage'],'magic':true});}e['techniques']=techniques;}
    if(e['lethal']==true||person.isEmpty||person['hiddenRace']!=true||s.knownRaces.contains(person['id'])){}else{for(final k in ['lifesteal','regen','spellPower','evasion','hypnosis'])e.remove(k);e['attack']=c.enemies[index]['attack'];e['defense']=c.enemies[index]['defense'];}
    return e;
  }
  int studentLevel(Map person)=>((person['level'] as int?)??1)+s.grades.length~/3;
  Widget appraisal()=>section('Apreciación y adquisición',[
    const Text('Apreciación revela las técnicas actuales de un estudiante. Al avanzar los arcos, sus capacidades evolucionan. Vuelve a apreciar a tus compañeros para descubrir técnicas nuevas.'),
    DropdownButton<String>(isExpanded:true,value:raceFilter,items:[const DropdownMenuItem(value:'all',child:Text('Todas las razas')),for(final r in c.races)DropdownMenuItem(value:r['id'].toString(),child:Text(r['name'].toString()))],onChanged:busy?null:(value)=>setState(()=>raceFilter=value??'all')),
    TextField(decoration:const InputDecoration(labelText:'Buscar estudiante'),onChanged:(value)=>setState(()=>nameFilter=value.toLowerCase().trim())),
    for(final person in c.people.where((p)=>!s.deadStudents.contains(p['id'])&&(raceFilter=='all'||publicRace(p)==raceFilter)&&p['name'].toString().toLowerCase().contains(nameFilter)))...[
      const Divider(),
      Text(person['name'].toString()+' · Año '+person['year'].toString()+' · Nv. '+studentLevel(person).toString()+' · '+(person['origin']??'Origen desconocido').toString(),style:const TextStyle(fontWeight:FontWeight.bold)),
      Text(person['intro'].toString()),
      if(person['race']!=null)Text('Raza: '+(c.raceFor(publicRace(person))['name']??publicRace(person)).toString()),
      if(person['appearance'] is String)Text(person['hiddenRace']==true&&!s.knownRaces.contains(person['id'])?(person['coverAppearance']??'Apariencia humana.').toString():person['appearance'] as String),
      if(discoverableSkills(person).any((sk)=>s.appraised.contains(sk['id']))&&c.raceFor(publicRace(person))['trait'] is String)Text('Rasgo innato: '+c.raceFor(publicRace(person))['trait'].toString()),
      Text('Confianza: '+s.relationship(person['id'] as String).toString()+(person['romance']==true?' · Afinidad: '+s.warmth(person['id'] as String).toString():'')),
      if(s.intelligence>=15&&s.relationship(person['id'] as String)>=7&&!s.knownRaces.contains(person['id']))btn('Apreciación profunda',(){s.knownRaces.add(person['id'] as String);return 'La apreciación profunda permite examinar el repertorio real.';}),
      if(discoverableSkills(person).any((sk)=>!s.appraised.contains(sk['id'])))btn('Apreciar '+person['name'].toString(),(){
        final discovered=discoverableSkills(person).where((sk)=>!s.appraised.contains(sk['id'])).toList();
        s.appraised.addAll(discovered.map((sk)=>sk['id'] as String));
        return 'Técnicas descubiertas: '+discovered.length.toString()+'.';
      }),
      for(final sk in discoverableSkills(person).where((x)=>s.appraised.contains(x['id'])))...[
        Text(sk['name'].toString()+' · '+sk['type'].toString()+' · potencia '+sk['damage'].toString()+' · '+sk['price'].toString()+' monedas · '+sk['cost'].toString()+(sk['magic']==true?' maná':' estamina')),
        if(sk['innate']==true)const Text('Técnica racial · copiable mediante Robo'),
        if(sk['description'] is String)Text(sk['description'] as String),
        Text(sk['copyable']==false?'Poder exclusivo · no se puede copiar':s.skills.contains(sk['id'])?'Aprendida':'Disponible para adquirir en tu dormitorio.')
      ]
    ]
  ]);
  Widget skillRoom()=>section('Poderes secretos · Apreciación y Robo',[
    const Text('Solo puedes adquirir las habilidades descubiertas en la academia cuando estás a solas en tu dormitorio. No tienes ninguna técnica de combate al empezar.'),
    if(s.skills.isEmpty)const Text('Habilidades de combate: ninguna.'),
    const Text('Retorno: una muerte real reinicia ambos mundos. Solo conservas inteligencia.'),
    for(final sk in c.skills.where((x)=>s.appraised.contains(x['id'])&&x['copyable']!=false))...[Text(sk['name'].toString()+' · '+sk['price'].toString()+' monedas · potencia '+sk['damage'].toString()+' · '+sk['cost'].toString()+(sk['magic']==true?' maná':' estamina')),if(!s.skills.contains(sk['id']))btn('Adquirir',()=>s.buySkill(sk['id'] as String,sk['price'] as int)?'Habilidad adquirida.':'No tienes dinero suficiente.')else const Text('Aprendida')]
  ]);
  String get arcTitle{final arcs=DualWorldContent.list(c.data['arcs']);String name='Arco I';for(final a in arcs){if(s.grades.length>=((a['afterClasses'] as int?)??0))name=a['title'].toString();}return name;}
  Widget storyEvents()=>Column(children:[for(final e in c.events.where(s.eligible))section(e['title'].toString(),[
    Text(e['scene'].toString()),const SizedBox(height:12),
    for(final choice in DualWorldContent.list(e['choices']))FilledButton(onPressed:busy||s.cash<((choice['cost'] as int?)??0)?null:()=>act(()=>s.chooseEvent(e,choice)?s.lastEvent:'No puedes elegir esta opción.'),child:Text(choice['label'].toString())),
  ])]);
  Widget dungeon()=>section('Dungeons · expediciones y espíritus',[
    const Text('Los combates aquí pueden terminar en muerte real. El Retorno reinicia ambos mundos. Los duelos de academia son protegidos.'),
    for(final sp in c.spirits.where((sp)=>s.grades.length>=((sp['minClasses'] as int?)??0)))...[Text(sp['name'].toString()+' · inteligencia '+sp['intelligence'].toString()+' · afinidad '+sp['affinity'].toString()),Text(s.spirits.contains(sp['id'])?'Vinculado':(spiritReady(sp)?'Puedes intentar vincularlo.':'Necesitas inteligencia superior, afinidad y superar su encuentro.')),if(spiritReady(sp))btn('Vincular espíritu',()=>s.capture(sp)?'Espíritu vinculado. Puedes invocarlo en combate.':'No cumples las condiciones.')],
    if(s.rescueMissions.isNotEmpty)const Text('Hay una expedición de rescate pendiente. Completa el combate antes de que termine el plazo.'),
    for(final person in c.people.where((p)=>s.rescuedStudents.contains(p['id'])))Text('Rescatado: '+person['name'].toString()),
    battle()
  ]);
  bool enemyVisible(Map enemy){if(s.deadStudents.contains(enemy['person']))return false;if((enemy['lethal']==true)!=(s.place=='Dungeon'))return false;if(s.grades.length<((enemy['minClasses'] as int?)??0))return false;if(enemy['requiresFlag'] is String&&!s.flags.contains(enemy['requiresFlag']))return false;if(enemy['rescueOnly']==true&&!s.rescueMissions.containsValue(enemy['id']))return false;return true;}
  Widget battle(){if(!s.inBattle)return section('Arena y monstruos',[
    const Text('Los combates son por turnos. Las victorias iniciales otorgan XP, reputación y clasificación.'),
    if(s.pendingDuel.isNotEmpty)const Text('Tienes un desafío personal pendiente. Busca a tu rival.'),
    if(!combatSkills.any((sk)=>const ['attack','drain','bleed'].contains(sk['type'])))const Text('No tienes ninguna técnica de ataque. Usa Apreciación, consigue monedas en Lumen y adquiere una en tu dormitorio.'),
    for(var i=0;i<c.enemies.length;i++)if(enemyVisible(c.enemies[i]))...[
      Text(c.enemies[i]['name'].toString()+' · nivel '+c.enemies[i]['level'].toString()+(enemyProfile(i)['raceName']!=null?' · '+enemyProfile(i)['raceName'].toString():'')),
      if(s.level>=(c.enemies[i]['level'] as int)&&combatSkills.any((sk)=>const ['attack','drain','bleed'].contains(sk['type'])))btn(s.pendingDuel==c.enemies[i]['id']?'Aceptar duelo pendiente':'Desafiar',()=>s.startBattle(i,enemyProfile(i)['hp'] as int,lethal:c.enemies[i]['lethal']==true)?'Comienza el combate.':'Debes recuperarte antes.')else const Text('Requiere nivel y una técnica de ataque')]
  ]);final e=enemyProfile(s.enemyIndex);return section('Combate · '+e['name'].toString(),[
    if(e['racialTrait'] is String)Text('Rasgo del rival: '+e['racialTrait'].toString()),
    Text('Tu vida: '+s.hp.toString()+'/'+s.maxHp.toString()+' · rival: '+s.enemyHp.toString()),
    Text('Estamina: '+s.energy.toString()+' · maná: '+s.mana.toString()),
    Text('Guardia: '+s.guardTurns.toString()+' turnos · evasión: '+s.speedTurns.toString()+' turnos · sello: '+s.enemyWeakTurns.toString()+' · hemorragia: '+s.enemyBleedTurns.toString()),
    if((s.turn+1)%3==0)const Text('El rival prepara un ataque fuerte. Considera defenderte o esquivar.'),
    for(final sk in combatSkills)btn(sk['name'].toString()+' · '+sk['cost'].toString()+(sk['magic']==true?' maná':' estamina'),()=>s.action(sk,e)),
    btn('Retirarte',(){s.enemyIndex=-1;s.lethalBattle=false;return 'Retirada sin recompensa. Un rescate pendiente sigue sujeto a su plazo.';})
  ]);}
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
    final locations=school?['Dormitorio','Clases','Biblioteca','Patio','Arena','Gimnasio','Ranking','Jardín','Consejo','Pasillo antiguo','Dungeon']:['Taller privado','Mercado','Gremio','Almacén','Puerto'];
    return Scaffold(appBar:AppBar(title:Text(school?'Academia · Entre dos mundos':'Mundo comercial')),body:ListView(padding:const EdgeInsets.all(14),children:[
      if(c.data['player'] is Map)section((c.data['player']['name']??'Valcrest').toString(),[Text((c.data['player']['appearance']??'').toString()),const Text('Becario · Casa de Valcrest')]),
      Text('Nivel '+s.level.toString()+' · XP '+s.xp.toString()+' · monedas '+s.cash.toString(),style:const TextStyle(fontSize:20,fontWeight:FontWeight.bold)),
      Text('Fuerza '+s.strength.toString()+' · defensa/resistencia '+s.defense.toString()+' · estamina '+s.stamina.toString()+' · inteligencia '+s.intelligence.toString()),
      Text('Lugar: '+current+' · notas '+s.examAverage.toString()+'/100 · reputación '+s.reputation.toString()),
      Text('Habilidades de combate: '+s.skills.length.toString()+' · poderes innatos: Apreciación, Robo y Retorno'),
      Text(arcTitle+' · '+s.decisions.length.toString()+' acontecimientos resueltos'),
      if(message.isNotEmpty)Card(child:Padding(padding:const EdgeInsets.all(12),child:Text(message))),
      if(s.inBattle)battle()else...[
        Wrap(spacing:6,children:[for(final l in locations)ChoiceChip(label:Text(l),selected:l==current,onSelected:busy?null:(_)=>act((){s.place=l;answer.clear();return 'Llegaste a '+l+'.';}))]),
        if(s.privatePlace)section('Lugar privado',[Text(c.data['intro'].toString()),btn('Viajar al otro mundo',()=>s.travel()?'Atravesaste el portal.':'No puedes viajar aquí.'),btn('Descansar',(){s.rest();return 'Vida, maná y estamina recuperados.';})]),
        if(current=='Dormitorio')skillRoom(),
        storyEvents(),
        if(current=='Gremio')section('Gremio · encargos financieros',[const Text('Los encargos se pagan aquí, una sola vez por examen superado.'),for(final l in c.lessons.where((x)=>s.grades.containsKey(x['id'])&&!s.wins.contains('guild_'+x['id'].toString())))btn('Cobrar '+l['title'].toString(),(){final n=s.claimGuild(l['id'] as String);return 'Recibiste '+n.toString()+' monedas por tu informe.';})]),
        if(current=='Clases')...[
          for(var i=0;i<c.lessons.length;i++)if(i<=s.grades.length&&(i!=2||s.wins.contains('battle_darian_practice'))&&(i!=4||s.wins.contains('battle_stone_beast'))&&(i!=6||s.wins.contains('battle_seren_duel')))lesson(c.lessons[i])else ListTile(leading:const Icon(Icons.lock),title:Text(c.lessons[i]['title'].toString()),subtitle:Text(i==2?'Supera el duelo de práctica de Darian.':i==4?'Derrota a la bestia de piedra.':i==6?'Supera el torneo de Seren.':'Supera las clases anteriores.'))
        ],
        if(current=='Biblioteca')library(),
        if(current=='Patio')appraisal(),
        if(current=='Arena')battle(),
        if(current=='Dungeon')dungeon(),
        if(current=='Patio'&&s.flags.any((x)=>x.startsWith('fallback_')))section('Noticias de expediciones',[for(final person in c.people.where((p)=>s.flags.contains('fallback_'+p['id'].toString())))Text(person['name'].toString()+' regresó gracias al equipo de rescate.')]),
        if(current=='Patio'&&c.events.any((e)=>e['deadline'] is int&&s.grades.length>=((e['minClasses'] as int?)??0)&&s.grades.length<(e['deadline'] as int)&&!s.rescuedStudents.contains(e['person'])))section('Avisos de expedición',[const Text('Hay búsquedas pendientes en el Dungeon. Consulta los avisos antes de avanzar las clases.')]),
        if(current=='Patio'&&s.rumors.isNotEmpty)section('Rumores de la academia',[for(final person in c.people.where((p)=>s.rumors.contains(p['id'])))Text(person['name'].toString()+' ya no asiste a clases. Se comenta que no sobrevivió a un incidente; nadie explica bien qué ocurrió.')]),
        if(current=='Mercado')market(),
        if(current=='Gimnasio')section('Entrenamiento real · FitRoutine',[const Text('Una recompensa por día local como máximo, solo por una sesión completa registrada en FitRoutine. No hace falta entrenar más para obtener más puntos.'),FilledButton(onPressed:busy||s.workoutDate.compareTo(today())>=0?null:workout,child:Text(s.workoutDate==today()?'Recompensa de hoy obtenida':'Verificar rutina completada'))]),
        if(current=='Ranking')section('Clasificación de la academia',[
          Text('Tus puntos: '+s.rankPoints.toString()+' · poder '+s.power.toString()),
          for(final row in ([{'name':'Tú','score':s.rankPoints},...c.people.where((x)=>!s.deadStudents.contains(x['id'])).map((x)=>{'name':x['name'],'score':x['rank']})]..sort((a,b)=>(b['score'] as int).compareTo(a['score'] as int))).asMap().entries)ListTile(title:Text((row.key+1).toString()+'. '+row.value['name'].toString()),trailing:Text(row.value['score'].toString()))
        ])
      ]
    ]));
  }
}
