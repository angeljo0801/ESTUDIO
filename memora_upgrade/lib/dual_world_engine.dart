import 'dart:math';
import 'lumen_economy.dart';
class DualState {
  LumenEconomy economy=LumenEconomy();
  int cash=0,stock=0,inventoryCost=0,day=0,xp=0,strength=4,defense=3,stamina=10,intelligence=5,rankPoints=0,chapter=0;
  int hp=40,energy=10,mana=5,enemyHp=0,turn=0,enemyIndex=-1,guardPower=0,guardTurns=0,speedPower=0,speedTurns=0;
  int enemyWeakTurns=0,enemyBleedTurns=0,enemyBleedPower=0,enemyGuard=0,enemyEvade=0,enemyGuardTurns=0,enemyEvadeTurns=0;
  String world='school',place='Dormitorio',workoutDate='';
  final Set<String> skills={},weapons={};
  String equippedWeapon='',weaponElement='neutral';
  int appraisalRefinement=0,weaponStrength=0,weaponMagic=0,weaponDefense=0;
  final Set<String> spirits={},deadStudents={},rescuedStudents={},knownRaces={},rumors={};
  final Map<String,String> rescueMissions={};
  String activeSpirit='',spiritElement='neutral',spiritMode='',lastElement='neutral';
  int spiritEnergy=0,spiritDamage=0,precision=0,enemyEnergy=-1,enemyMana=-1,enemyMaxEnergy=0,enemyMaxMana=0,charisma=0,luck=0;
  final Map<String,int> playerStates={},enemyStates={},elementResistance={};
  static int numOf(Map m,String k,int d)=>m[k] is num?(m[k] as num).toInt():d;
  static const elementStates={'fire':'quemadura','lightning':'parálisis','ice':'congelación','poison':'veneno','blood':'hemorragia','water':'empapado','gravity':'inmovilización','dark':'maldición'};
  static int critChance(int base,int accuracy)=>(base+max(0,accuracy)~/2).clamp(0,65).toInt();
  static int missChance(int evasion,int accuracy)=>(2+max(0,evasion)-max(0,accuracy)~/10).clamp(1,65).toInt();
  static int statusChance(Map sk,bool match)=>(numOf(sk,'stateChance',elementStates.containsKey(sk['element'])||sk['status']!=null?15:0)+(match?8:0)).clamp(0,85).toInt();
  int resistanceFor(String el)=>((elementResistance[el]??0)+(activeSpirit.isNotEmpty&&spiritElement==el&&el!='neutral'?3:0)).clamp(0,80).toInt();
  bool selectSpirit(Map sp){if(inBattle||!spirits.contains(sp['id']))return false;activeSpirit=sp['id'].toString();spiritElement=sp['element']?.toString()??'neutral';spiritDamage=numOf(sp,'damage',4);return true;}
  String applyState(Map sk,Map<String,int> target,Random rng,bool match,{int resistance=0}){final state=sk['status']?.toString()??elementStates[sk['element']];if(state==null||rng.nextInt(100)>=max(0,statusChance(sk,match)-resistance))return '';target[state]=max(target[state]??0,max(1,numOf(sk,'stateTurns',2)));return ' · '+state;}
  int tickStates(Map<String,int> states,int maximum){int damage=0;for(final k in states.keys.toList()){if(const ['quemadura','veneno','hemorragia','maldición'].contains(k))damage+=max(1,maximum~/20);states[k]=states[k]!-1;if(states[k]!<=0)states.remove(k);}return damage;}
  bool blocked(Map<String,int> states,Random rng)=>states.containsKey('sueño')||states.containsKey('congelación')||states.containsKey('aturdimiento')||(states.containsKey('parálisis')&&rng.nextInt(100)<25);
  static const specializations=<String,List<Object>>{
    'Guerrero':[10,0,''],'Caballero':[25,0,'Guerrero'],'Maestro de armas':[50,0,'Caballero'],
    'Mago':[0,15,''],'Hechicero':[0,35,'Mago'],'Archimago':[0,80,'Hechicero'],
    'Explorador':[8,5,''],'Espadachín mágico':[30,30,'Guerrero'],'Invocador':[0,25,'Mago']
  };
  bool hasClass(String name)=>flags.contains('class:'+name);
  bool canLearnClass(String name){final req=specializations[name];return req!=null&&!inBattle&&world=='school'&&place=='Dormitorio'&&!hasClass(name)&&strength>=(req[0] as int)&&intelligence>=(req[1] as int)&&(req[2]==''||hasClass(req[2] as String))&&(name!='Espadachín mágico'||hasClass('Mago'));}
  bool learnClass(String name){if(!canLearnClass(name))return false;flags.add('class:'+name);return true;}
  int get charismaFee=>100+charisma*25;
  int get luckFee=>100+luck*25;
  bool improveSocial(String stat){if(inBattle||world!='school'||place!='Dormitorio'||!const ['charisma','luck'].contains(stat))return false;final fee=stat=='charisma'?charismaFee:luckFee;if(cash<fee)return false;cash-=fee;if(stat=='charisma'){charisma++;}else{luck++;}return true;}
  int trustGain(int base)=>base<=0?base:base+((base*charisma/(charisma+100)*0.5).round());
  static bool compatibleElements(String a,String b)=>a!='neutral'&&(a==b||const ['water:lightning','lightning:water','water:ice','ice:water','fire:wind','wind:fire','gravity:earth','earth:gravity','poison:blood','blood:poison','light:dark','dark:light','space:gravity','gravity:space'].contains('$a:$b'));
  static int staminaCost(Map sk)=>max(0,numOf(sk,'staminaCost',sk['magic']==true?0:max(1,numOf(sk,'cost',1))));
  static int manaCost(Map sk)=>max(0,numOf(sk,'manaCost',sk['magic']==true?max(1,numOf(sk,'cost',1)):0));
  bool usable(Map sk)=> energy>=staminaCost(sk)&&mana>=manaCost(sk)&&(staminaCost(sk)+manaCost(sk)>0)&&(sk['magic']!=true||intelligence>=numOf(sk,'minIntelligence',0))&&(sk['spirit']==null||sk['spirit']==activeSpirit)&&(sk['spiritMode']==null||spiritMode.isEmpty);

  bool returned=false;
  bool lethalBattle=false;
  int warWeek=0,warContribution=0,alliedContribution=0,warSeed=Random().nextInt(1000000);
  final List<String> alliedReports=[];
  static const alliedChampions=<Map<String,dynamic>>[
    {'id':'ally_orion','name':'Orion del Alba','role':'Vanguardia','rank':'L','level':95,'power':450,'week':0,'ability':'Espada del firmamento'},
    {'id':'ally_draeven','name':'Draeven Aster','role':'Vanguardia','rank':'SS','level':78,'power':340,'week':0,'ability':'Corte dimensional'},
    {'id':'ally_iria','name':'Iria Celest','role':'Elementalista','rank':'SS','level':76,'power':330,'week':0,'ability':'Sello de causalidad'},
    {'id':'ally_kaelen','name':'Kaelen Voss','role':'Vanguardia','rank':'A','level':38,'power':105,'week':0,'ability':'Espada del amanecer'},
    {'id':'ally_mirath','name':'Mirath Solenne','role':'Sanador','rank':'A','level':39,'power':110,'week':0,'ability':'Restauración del alma'},
    {'id':'ally_therak','name':'Therak Forjaestelar','role':'Vanguardia','rank':'A','level':40,'power':115,'week':0,'ability':'Armadura de estrella'},
    {'id':'ally_ashara','name':'Ashara Veyl','role':'Elementalista','rank':'A','level':42,'power':120,'week':0,'ability':'Fuego solar'},
    {'id':'ally_elysian','name':'Elysian Ardent','role':'Sanador','rank':'B+','level':29,'power':75,'week':0,'ability':'Santuario de vida'},
    {'id':'ally_bplus_1','name':'Neris Tal','role':'Elementalista','rank':'B+','level':27,'power':70,'week':0,'ability':'Lanza de escarcha'},
    {'id':'ally_bplus_2','name':'Garrik Dorn','role':'Vanguardia','rank':'B+','level':28,'power':72,'week':0,'ability':'Muro de hierro'},
    {'id':'ally_bplus_3','name':'Salia Vern','role':'Sanador','rank':'B+','level':26,'power':68,'week':0,'ability':'Luz vital'},
    {'id':'ally_b_1','name':'Taren Holt','role':'Vanguardia','rank':'B','level':21,'power':48,'week':0,'ability':'Filo de viento'},
    {'id':'ally_b_2','name':'Mira Thal','role':'Elementalista','rank':'B','level':22,'power':50,'week':0,'ability':'Chispa arcana'},
    {'id':'ally_b_3','name':'Oren Vale','role':'Sanador','rank':'B','level':20,'power':45,'week':0,'ability':'Bendición menor'},
    {'id':'ally_b_4','name':'Vanya Reed','role':'Vanguardia','rank':'B','level':23,'power':52,'week':0,'ability':'Escudo rúnico'},
    {'id':'ally_c_1','name':'Lian Crest','role':'Vanguardia','rank':'C','level':14,'power':26,'week':0,'ability':'Estocada veloz'},
    {'id':'ally_c_2','name':'Eris Moon','role':'Elementalista','rank':'C','level':15,'power':28,'week':0,'ability':'Pulso ígneo'},
    {'id':'ally_c_3','name':'Dorin Flint','role':'Vanguardia','rank':'C','level':13,'power':24,'week':0,'ability':'Guardia firme'},
    {'id':'ally_c_4','name':'Nalia Dawn','role':'Sanador','rank':'C','level':14,'power':25,'week':0,'ability':'Luz reparadora'},
    {'id':'ally_s_1','name':'Seren Ashford','role':'Vanguardia','rank':'S','level':58,'power':205,'week':0,'ability':'Lanza del trueno'},
    {'id':'ally_s_2','name':'Velena Frost','role':'Elementalista','rank':'S','level':55,'power':190,'week':0,'ability':'Tormenta glacial'},
    {'id':'ally_s_3','name':'Aurel Thorne','role':'Vanguardia','rank':'S','level':57,'power':200,'week':0,'ability':'Escudo solar'},
    {'id':'ally_s_4','name':'Lysandra Vale','role':'Sanador','rank':'S','level':54,'power':185,'week':0,'ability':'Luz del renacer'},
    {'id':'ally_a_1','name':'Ronan Blackwood','role':'Vanguardia','rank':'A','level':41,'power':118,'week':0,'ability':'Filo de obsidiana'},
    {'id':'ally_a_2','name':'Selene Ardent','role':'Elementalista','rank':'A','level':40,'power':115,'week':0,'ability':'Llama azul'},
    {'id':'ally_a_3','name':'Darius Holt','role':'Vanguardia','rank':'A','level':39,'power':110,'week':0,'ability':'Martillo rúnico'},
    {'id':'ally_a_4','name':'Evelia Rain','role':'Sanador','rank':'A','level':38,'power':105,'week':0,'ability':'Velo vital'},
    {'id':'ally_a_5','name':'Kieran Storm','role':'Elementalista','rank':'A','level':42,'power':120,'week':0,'ability':'Arco eléctrico'},
    {'id':'ally_a_6','name':'Maren Sol','role':'Vanguardia','rank':'A','level':37,'power':104,'week':0,'ability':'Guardia de cristal'},
    {'id':'ally_bplus_5','name':'Arlen Ember','role':'Vanguardia','rank':'B+','level':26,'power':68,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_bplus_6','name':'Brenna Ember','role':'Elementalista','rank':'B+','level':27,'power':69,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_bplus_7','name':'Corvin Ember','role':'Sanador','rank':'B+','level':28,'power':70,'week':0,'ability':'Luz protectora'},
    {'id':'ally_bplus_8','name':'Della Ember','role':'Vanguardia','rank':'B+','level':29,'power':71,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_bplus_9','name':'Edric Ember','role':'Elementalista','rank':'B+','level':30,'power':72,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_bplus_10','name':'Fenna Ember','role':'Sanador','rank':'B+','level':26,'power':73,'week':0,'ability':'Luz protectora'},
    {'id':'ally_bplus_11','name':'Galen Ember','role':'Vanguardia','rank':'B+','level':27,'power':74,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_bplus_12','name':'Hestia Ember','role':'Elementalista','rank':'B+','level':28,'power':68,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_b_5','name':'Arlen River','role':'Vanguardia','rank':'B','level':20,'power':45,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_b_6','name':'Brenna River','role':'Elementalista','rank':'B','level':21,'power':46,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_b_7','name':'Corvin River','role':'Sanador','rank':'B','level':22,'power':47,'week':0,'ability':'Luz protectora'},
    {'id':'ally_b_8','name':'Della River','role':'Vanguardia','rank':'B','level':23,'power':48,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_b_9','name':'Edric River','role':'Elementalista','rank':'B','level':24,'power':49,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_b_10','name':'Fenna River','role':'Sanador','rank':'B','level':20,'power':50,'week':0,'ability':'Luz protectora'},
    {'id':'ally_b_11','name':'Galen River','role':'Vanguardia','rank':'B','level':21,'power':51,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_b_12','name':'Hestia River','role':'Elementalista','rank':'B','level':22,'power':45,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_b_13','name':'Ivar River','role':'Sanador','rank':'B','level':23,'power':46,'week':0,'ability':'Luz protectora'},
    {'id':'ally_b_14','name':'Jora River','role':'Vanguardia','rank':'B','level':24,'power':47,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_b_15','name':'Kellan River','role':'Elementalista','rank':'B','level':20,'power':48,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_b_16','name':'Liora River','role':'Sanador','rank':'B','level':21,'power':49,'week':0,'ability':'Luz protectora'},
    {'id':'ally_b_17','name':'Merek River','role':'Vanguardia','rank':'B','level':22,'power':50,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_b_18','name':'Nessa River','role':'Elementalista','rank':'B','level':23,'power':51,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_b_19','name':'Osric River','role':'Sanador','rank':'B','level':24,'power':45,'week':0,'ability':'Luz protectora'},
    {'id':'ally_b_20','name':'Petra River','role':'Vanguardia','rank':'B','level':20,'power':46,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_b_21','name':'Quin River','role':'Elementalista','rank':'B','level':21,'power':47,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_b_22','name':'Rhea River','role':'Sanador','rank':'B','level':22,'power':48,'week':0,'ability':'Luz protectora'},
    {'id':'ally_b_23','name':'Soren River','role':'Vanguardia','rank':'B','level':23,'power':49,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_b_24','name':'Talia River','role':'Elementalista','rank':'B','level':24,'power':50,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_c_5','name':'Arlen Stone','role':'Vanguardia','rank':'C','level':13,'power':24,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_c_6','name':'Brenna Stone','role':'Elementalista','rank':'C','level':14,'power':25,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_c_7','name':'Corvin Stone','role':'Sanador','rank':'C','level':15,'power':26,'week':0,'ability':'Luz protectora'},
    {'id':'ally_c_8','name':'Della Stone','role':'Vanguardia','rank':'C','level':16,'power':27,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_c_9','name':'Edric Stone','role':'Elementalista','rank':'C','level':17,'power':28,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_c_10','name':'Fenna Stone','role':'Sanador','rank':'C','level':13,'power':29,'week':0,'ability':'Luz protectora'},
    {'id':'ally_c_11','name':'Galen Stone','role':'Vanguardia','rank':'C','level':14,'power':30,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_c_12','name':'Hestia Stone','role':'Elementalista','rank':'C','level':15,'power':24,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_c_13','name':'Ivar Stone','role':'Sanador','rank':'C','level':16,'power':25,'week':0,'ability':'Luz protectora'},
    {'id':'ally_c_14','name':'Jora Stone','role':'Vanguardia','rank':'C','level':17,'power':26,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_c_15','name':'Kellan Stone','role':'Elementalista','rank':'C','level':13,'power':27,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_c_16','name':'Liora Stone','role':'Sanador','rank':'C','level':14,'power':28,'week':0,'ability':'Luz protectora'},
    {'id':'ally_c_17','name':'Merek Stone','role':'Vanguardia','rank':'C','level':15,'power':29,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_c_18','name':'Nessa Stone','role':'Elementalista','rank':'C','level':16,'power':30,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_c_19','name':'Osric Stone','role':'Sanador','rank':'C','level':17,'power':24,'week':0,'ability':'Luz protectora'},
    {'id':'ally_c_20','name':'Petra Stone','role':'Vanguardia','rank':'C','level':13,'power':25,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_c_21','name':'Quin Stone','role':'Elementalista','rank':'C','level':14,'power':26,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_c_22','name':'Rhea Stone','role':'Sanador','rank':'C','level':15,'power':27,'week':0,'ability':'Luz protectora'},
    {'id':'ally_c_23','name':'Soren Stone','role':'Vanguardia','rank':'C','level':16,'power':28,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_c_24','name':'Talia Stone','role':'Elementalista','rank':'C','level':17,'power':29,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_c_25','name':'Ulric Stone','role':'Sanador','rank':'C','level':13,'power':30,'week':0,'ability':'Luz protectora'},
    {'id':'ally_c_26','name':'Vera Stone','role':'Vanguardia','rank':'C','level':14,'power':24,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_c_27','name':'Wren Stone','role':'Elementalista','rank':'C','level':15,'power':25,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_c_28','name':'Xara Stone','role':'Sanador','rank':'C','level':16,'power':26,'week':0,'ability':'Luz protectora'},
    {'id':'ally_c_29','name':'Yorin Stone','role':'Vanguardia','rank':'C','level':17,'power':27,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_c_30','name':'Zella Stone','role':'Elementalista','rank':'C','level':13,'power':28,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_c_31','name':'Aven Stone','role':'Sanador','rank':'C','level':14,'power':29,'week':0,'ability':'Luz protectora'},
    {'id':'ally_c_32','name':'Brisa Stone','role':'Vanguardia','rank':'C','level':15,'power':30,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_c_33','name':'Cyran Stone','role':'Elementalista','rank':'C','level':16,'power':24,'week':0,'ability':'Pulso elemental'},
    {'id':'ally_c_34','name':'Davin Stone','role':'Sanador','rank':'C','level':17,'power':25,'week':0,'ability':'Luz protectora'},
    {'id':'ally_c_35','name':'Elara Stone','role':'Vanguardia','rank':'C','level':13,'power':26,'week':0,'ability':'Guardia de acero'},
    {'id':'ally_c_36','name':'Faron Stone','role':'Elementalista','rank':'C','level':14,'power':27,'week':0,'ability':'Pulso elemental'},
  ];
  bool alliedDefeated(Map ally)=>flags.contains('ally_defeated_'+ally['id'].toString());
  List<Map<String,dynamic>> get activeAlliedChampions=>alliedChampions.where((a)=>!alliedDefeated(a)).toList();
  int get defenseTotal=>warContribution+alliedContribution;
  // Threat rises with the invasion, not with player or allied levels.
  static int invadingHordeSize(int week)=>week<2?180:week<4?420:week<6?850:week<8?1300:week<10?1800:week<12?2400:week<14?3200:week<16?4200:5200;
  int get remainingHorde=>max(0,invadingHordeSize(warWeek)-battleCounts.entries.where((e)=>e.key.startsWith('rupture_')||e.key.startsWith('war_')).fold<int>(0,(sum,e)=>sum+e.value));
  static int alliedFrontThreat(int week)=>week<4?80:week<6?180:week<8?310:week<10?470:week<12?850:week<14?1500:week<16?2400:4000;
  void simulateAlliedFront(){
    if(warWeek==0||warWeek%2!=0||warWon||worldDestroyed)return;
    final active=activeAlliedChampions..sort((a,b)=>numOf(b,'power',0).compareTo(numOf(a,'power',0)));
    if(active.isEmpty){alliedContribution=max(0,alliedContribution-2);alliedReports.add('Semana $warWeek · Las fuerzas aliadas ya no tienen campeones disponibles.');return;}
    final champion=active.first;
    final elite=active.take(3).toList();final strength=elite.fold<int>(0,(sum,a)=>sum+numOf(a,'power',0))~/max(1,elite.length);
    final threat=alliedFrontThreat(warWeek)+remainingHorde~/12;
    final helped=warContribution>=warPressure(warWeek)&&warContribution>0;
    final effectiveThreat=helped?threat*65~/100:threat;
    final divine=warWeek>=10;
    final roll=(warSeed+warWeek*17+warWeek*warWeek*7)%10;
    if(!divine&&strength>=effectiveThreat){
      alliedContribution+=roll<5?2:1;
      alliedReports.add('Semana $warWeek · '+champion['name'].toString()+': los héroes contienen a las numerosas criaturas y recuperan terreno.');
    }else if(!divine&&numOf(champion,'power',0)*2>=effectiveThreat){
      alliedContribution=max(0,alliedContribution-1);
      alliedReports.add('Semana $warWeek · '+champion['name'].toString()+': resiste las hordas y los monstruos colosales con grandes pérdidas.');
    }else{
      alliedContribution=max(0,alliedContribution-2);
      if(!helped||roll<3){flags.add('ally_defeated_'+champion['id'].toString());}
      alliedReports.add('Semana $warWeek · '+champion['name'].toString()+(alliedDefeated(champion)?' ha sido derrotado y queda fuera del frente.':' logra retirarse, pero no puede vencer al invasor.')+' Las defensas retroceden.');
    }
  }

  bool get warWon=>flags.contains('rupture_repulsed');
  bool get academyMobilized=>flags.contains('academy_mobilized')&&!warWon;
  bool get worldDestroyed=>flags.contains('rupture_world_destroyed');
  bool get canFightWar=>flags.contains('mercenary_member')||academyMobilized;
  static int warPressure(int week)=>week<4?0:week<8?2:week<12?5:week<18?9:15;
  int get warThreat=>max(0,warPressure(warWeek)-defenseTotal);
  bool warEnemyAvailable(Map enemy)=>enemy['location']!='Frente de guerra'||(!warWon&&!worldDestroyed&&warWeek>=numOf(enemy,'warMinWeek',0));
  Map<String,dynamic> warEnemyProfile(Map enemy){
    final result=Map<String,dynamic>.from(enemy);
    if(enemy['location']!='Frente de guerra'||enemy['warGrowth']!=true)return result;
    final stages=(max(0,warWeek-numOf(enemy,'warMinWeek',0))~/3).clamp(0,4).toInt();
    final scale=100+stages*15;
    for(final k in ['hp','attack','defense','stamina','intelligence','xp','goldReward']){
      if(enemy[k] is int)result[k]=max(1,numOf(enemy,k,1)*scale~/100);
    }
    if(enemy['techniques'] is List)result['techniques']=[for(final m in (enemy['techniques'] as List).whereType<Map>()) {...Map<String,dynamic>.from(m),'damage':numOf(m,'damage',0)*scale~/100}];
    result['warEvolution']=stages;
    return result;
  }
  List<String> get warNews=>[
    'La Guerra de la Ruptura lleva décadas activa. La academia permanece neutral.',
    if(warWeek>=2) 'Semana 2 · Los exploradores informan de nuevas criaturas y de una creciente concentración de energía en las grietas.',
    if(warWeek>=4) defenseTotal>=2?'Semana 4 · Las defensas resisten gracias a las victorias aliadas.':'Semana 4 · Los invasores han roto las primeras defensas fronterizas.',
    if(warWeek>=6) 'Semana 6 · Los primeros monstruos legendarios atraviesan las grietas. Las compañías necesitan refuerzos.',
    if(warWeek>=8) defenseTotal>=5?'Semana 8 · Los aliados recuperan posiciones.':'Semana 8 · Caen fortalezas y llegan refugiados a Asteria.',
    if(warWeek>=10) 'Semana 10 · Aparecen entidades de apariencia humana con poderes nunca vistos. Su presencia supera a la de los colosos.',
    if(warWeek>=12) defenseTotal>=9||warWon?'Semana 12 · La ofensiva ha sido contenida.':'Semana 12 · Las entidades avanzan hacia la academia; se declara la movilización de emergencia.',
    if(warWeek>=14&&!warWon) 'Semana 14 · Los supervivientes advierten que las deidades superiores están entrando al mundo.',
    if(warWeek>=16&&!warWon) 'Semana 16 · Se ha detectado una presencia divina de poder desconocido. La última línea defensiva está amenazada.',
    if(warWon)'Las grietas de esta ofensiva han sido selladas. El mundo ha sobrevivido.',
    if(worldDestroyed)'Semana 18 · La última defensa cae. La Ruptura consume el mundo.',
  ];
  void resolveWar(){
    if(warWon||worldDestroyed)return;
    if(warWeek>=12&&defenseTotal<9){flags.add('academy_mobilized');}
    if(warWeek>=18){
      if(warContribution>=15){flags.add('rupture_repulsed');return;}
      flags.add('rupture_world_destroyed');enemyIndex=-1;hp=0;lethalBattle=true;returned=true;
    }
  }
  bool advanceWarWeek(){if(inBattle||worldDestroyed||warWon)return false;warWeek++;simulateAlliedFront();resolveWar();return true;}
  void recordWarVictory(Map enemy,bool first){
    if(enemy['location']!='Frente de guerra'||!first)return;
    warContribution+=max(0,numOf(enemy,'warContribution',1));
    if(enemy['warFinal']==true||warContribution>=15){flags.add('rupture_repulsed');}
    resolveWar();
  }

  final List<Map<String,dynamic>> raidAllies=[];
  bool startRaid(int index,Map enemy,{required bool withTeam}){
    if(!canFightWar||place!='Frente de guerra'||enemy['raid']!=true||!warEnemyAvailable(enemy))return false;
    if(withTeam&&level<numOf(enemy,'teamMinLevel',1))return false;
    if(!startBattle(index,numOf(enemy,'hp',0),lethal:true))return false;
    if(withTeam){
      final target=numOf(enemy,'level',1);
      for(final role in ['Vanguardia','Elementalista','Sanador']){
        final candidates=activeAlliedChampions.where((a)=>a['role']==role).toList()
          ..sort((a,b)=>(numOf(a,'level',1)-target).abs().compareTo((numOf(b,'level',1)-target).abs()));
        if(candidates.isEmpty)continue;
        final member=candidates.first,power=numOf(member,'power',1);
        raidAllies.add({...member,'hp':power*20,'maxHp':power*20,'energy':power*3,'mana':power*3});
      }
    }
    return true;
  }
  int raidSupport(Map enemy){
    int damage=0;
    for(final ally in raidAllies){
      if(numOf(ally,'hp',0)<=0)continue;
      final power=numOf(ally,'power',1),role=ally['role'];
      if(role=='Sanador'&&hp<maxHp*3~/4&&numOf(ally,'mana',0)>=4){
        ally['mana']=numOf(ally,'mana',0)-4;hp=min(maxHp,hp+max(1,power~/2));continue;
      }
      final resource=role=='Vanguardia'?'energy':'mana';
      if(numOf(ally,resource,0)<3)continue;
      ally[resource]=numOf(ally,resource,0)-3;
      if(enemy['form']!='humanoid')damage+=max(0,power*2-numOf(enemy,'defense',0)~/2);
    }
    return damage;
  }
  int raidIntercept(int incoming,Map enemy){
    if(incoming<=0)return incoming;
    final living=raidAllies.where((a)=>numOf(a,'hp',0)>0).toList();
    if(living.isEmpty)return incoming;
    final share=max(1,incoming~/(living.length+1));
    for(final ally in living){
      final damage=enemy['form']=='humanoid'?max(share,numOf(enemy,'attack',1)):turn%3==0?max(share,numOf(enemy,'attack',1)~/3):share;
      ally['hp']=max(0,numOf(ally,'hp',0)-damage);
      if(ally['hp']==0&&ally['id'] is String)flags.add('ally_defeated_'+ally['id'].toString());
    }
    return share;
  }

  int reputation=-30;
  final Map<String,int> trust={},affection={};
  final Map<String,String> decisions={};
  final Set<String> flags={};
  String pendingDuel='';
  String lastEvent='';
  final Set<String> appraised={};
  final Map<String,int> readPages={},grades={},attempts={},battleCounts={},spiritAttempts={},factionStanding={};
  final Map<String,Map<String,dynamic>> readingLog={};
  int readingRemainder=0;
  final Set<String> wins={};
  static const royalFactions={'evelyne':'Facción de Evelyne','aldren':'Facción de Aldren','neutral':'Neutral'};
  String get royalAlignment=>decisions['royal_allegiance']??'neutral';
  bool get royalChoiceMade=>decisions.containsKey('royal_allegiance');
  static String? royalFaction(Map person){
    final name=person['name']?.toString().toLowerCase()??'';
    if(name.contains('evelyne')&&name.contains('aurel'))return 'evelyne';
    if(name.contains('aldren')&&name.contains('aurel'))return 'aldren';
    return null;
  }
  int royalStanding(String side)=>factionStanding['royal_'+side]??0;
  bool chooseRoyalFaction(String side){
    if(inBattle||world!='school'||!const ['Consejo','Palacio'].contains(place)||royalChoiceMade||!royalFactions.containsKey(side))return false;
    decisions['royal_allegiance']=side;
    if(side!='neutral'){final rival=side=='evelyne'?'aldren':'evelyne';factionStanding['royal_'+side]=(royalStanding(side)+8).clamp(-100,100).toInt();factionStanding['royal_'+rival]=(royalStanding(rival)-8).clamp(-100,100).toInt();}
    return true;
  }
  bool royalEventAvailable(String side)=>royalChoiceMade&&(royalAlignment=='neutral'||royalAlignment==side);
  int relationship(String id)=>trust[id]??0;
  int warmth(String id)=>affection[id]??0;
  bool eligible(Map e){
    if(deadStudents.contains(e['person']))return false;
    if(e['maxClasses'] is int&&grades.length>(e['maxClasses'] as int))return false;
    if(decisions.containsKey(e['id'])||e['world']!=world||e['place']!=place)return false;
    if(grades.length<((e['minClasses'] as int?)??0)||reputation<((e['minRep'] as int?)??-100))return false;
    if(e['requiresRoyalFaction'] is String&&!royalEventAvailable(e['requiresRoyalFaction'] as String))return false;
    if(e['requiresFlag'] is String&&!flags.contains(e['requiresFlag'])&&!(e['requiresFlag']=='mercenary_member'&&academyMobilized))return false;
    if(e['excludesFlag'] is String&&flags.contains(e['excludesFlag']))return false;
    if(e['requiresWin'] is String&&!wins.contains('battle_'+(e['requiresWin'] as String)))return false;
    if(e['requiresTrust'] is int&&relationship(e['person'] as String)<(e['requiresTrust'] as int))return false;
    if(e['requiresSkill'] is String&&!skills.contains(e['requiresSkill']))return false;
    if(e['requiresEvent'] is String&&!decisions.containsKey(e['requiresEvent']))return false;
    return true;
  }
  bool chooseEvent(Map e,Map choice){
    if(!eligible(e)||!(e['choices'] as List).any((x)=>x is Map&&x['id']==choice['id']))return false;
    final cost=(choice['cost'] as int?)??0;if(cost<0||cash<cost)return false;
    final person=e['person'] as String? ?? '';cash-=cost;
    if(person.isNotEmpty){final change=(choice['trust'] as int?)??0;if(change>=5)charisma++;trust[person]=(relationship(person)+trustGain(change)).clamp(-100,100).toInt();affection[person]=(warmth(person)+((choice['affection'] as int?)??0)).clamp(0,100).toInt();}
    reputation=(reputation+((choice['rep'] as int?)??0)).clamp(-100,100).toInt();
    decisions[e['id'] as String]=choice['id'] as String;
    if(choice['flag'] is String)flags.add(choice['flag'] as String);
    if(choice['duel'] is String)pendingDuel=choice['duel'] as String;
    if(choice['rescue'] is String&&person.isNotEmpty)rescueMissions[person]=choice['rescue'] as String;
    if(choice['abandon']==true&&person.isNotEmpty){rescueMissions.remove(person);}
    if(choice['defer']==true){decisions.remove(e['id']);}
    if(choice['revealRace']==true&&person.isNotEmpty)knownRaces.add(person);
    if(choice['fatal']==true){hp=0;lethalBattle=true;returned=true;}
    if(choice['faction'] is String){final id=choice['faction'] as String;factionStanding[id]=((factionStanding[id]??0)+((choice['standing'] as int?)??0)).clamp(-100,100).toInt();}
    lastEvent=choice['outcome'] as String? ?? '';return true;
  }
  bool skillAvailable(Map sk)=>grades.length>=((sk['minClasses'] as int?)??0);
  void resolveFates(List<Map<String,dynamic>> events){
    for(final e in events){if(e['deadline'] is! int||e['person'] is! String)continue;
      final id=e['person'] as String;
      if(rescuedStudents.contains(id)||deadStudents.contains(id))continue;
      if(e['requiresFlag'] is String&&!flags.contains(e['requiresFlag']))continue;
      if(e['excludesFlag'] is String&&flags.contains(e['excludesFlag']))continue;
      if(grades.length>=(e['deadline'] as int)){
        final rescuer=e['fallbackRescuer'];
        if(rescuer is String&&!deadStudents.contains(rescuer)&&!rescueMissions.containsKey(rescuer)){rescuedStudents.add(id);flags.add('fallback_'+id);}
        else{deadStudents.add(id);rumors.add(id);}
        rescueMissions.remove(id);
      }
    }
  }
  bool canCapture(Map spirit){final id=spirit['id'];return !inBattle&&place=='Dungeon'&&world=='school'&&!spirits.contains(id)&&intelligence>(spirit['intelligence'] as int)&&grades.length>=((spirit['minClasses'] as int?)??0)&&(spirit['requiresWin']==null||wins.contains('battle_'+spirit['requiresWin'].toString()));}
  bool capture(Map spirit){if(!canCapture(spirit))return false;spirits.add(spirit['id'] as String);return true;}
  static int spiritualCapacity(Map person,int intelligence){
    final affinity=(person['spiritualAffinity'] as int?)??35;
    final role=person['spiritClass']?.toString()??'ordinary';
    final cap=role=='elementalist'?15:role=='specialist'||role=='chosen'?10:person['race']=='elf'?5:1;
    if(cap==1)return 1;
    return min(cap,1+affinity~/20+max(0,intelligence)~/15);
  }
  static const powerRanks=['E','D','C','B','A','S','SS','SSS'];
  // Combat ranks are separate from existing technique/appraisal tiers.
  static const combatRanks=['E','D','C','B','B+','A','S','SS','SSS','L','Divino','Divino+'];
  static int combatRankIndex(dynamic value)=>max(0,combatRanks.indexOf(value?.toString()??'E'));
  static int combatAppraisalTier(String rank)=>rank=='B+'?3:rank=='L'||rank=='Divino'||rank=='Divino+'?7:rankIndex(rank);
  static const commonElements=['fire','water','earth','wind','lightning','ice','light','dark','nature','blood','metal','astral'];
  static String combatRank(Map person,int completed){final start=combatRankIndex(person['initialRank']),end=max(start,combatRankIndex(person['potentialRank']));return combatRanks[min(end,start+max(0,completed)~/3)];}
  static Map<String,dynamic> npcTechnique(Map sk,Map person,int completed){
    final base=rankIndex(sk['rank']),initial=rankIndex(person['initialRank']),potential=max(initial,rankIndex(person['potentialRank']));
    final room=potential-initial,age=max(0,completed-((sk['minClasses'] as int?)??0));
    final pace=room>=4?3:room>=2?4:6;
    final growth=sk['copyable']==false?0:min(min(room,max(0,potential-base)),age~/pace);
    final damage=(sk['damage'] as int?)??0;
    final price=(sk['price'] as int?)??0;
    final fees=[25,100,250,700,1800,5000,15000,50000];
    return {...Map<String,dynamic>.from(sk),'rank':powerRanks[base+growth],'damage':damage==0?0:damage+growth*max(1,damage~/5),'cost':((sk['cost'] as int?)??1)+growth,'effectTurns':((sk['effectTurns'] as int?)??2)+growth~/2,'price':growth==0||price==0?price:max(price,fees[base+growth]+growth*50)};
  }
  static bool npcTechniqueAvailable(Map sk,Map person,int completed){final start=(sk['minClasses'] as int?)??0;if(start==0||sk['copyable']==false)return completed>=start;final room=max(0,rankIndex(person['potentialRank'])-rankIndex(person['initialRank']));final delay=room<=1?min(2,9-start).clamp(0,2).toInt():room==2?1:0;return completed>=start+delay;}
  static int elementMastery(Map person,dynamic element){if(element==null||element=='neutral')return 100;if(person['singularElement']==element)return 100;if(element=='void'||element=='divine'){return person['elements'] is List&&(person['elements'] as List).contains(element)?100:0;}if(person['spiritClass']=='elementalist'&&commonElements.contains(element))return 100;final els=person['elements'] is List?person['elements'] as List:const [];if(els.contains(element))return els.indexOf(element)==0?100:65;return commonElements.contains(element)?25:0;}
  static int elementalAffinity(Map person,Map spirit){
    final base=((person['spiritualAffinity'] as int?)??35).clamp(0,100).toInt();
    final elements=person['elements'] is List?(person['elements'] as List):const [];
    final element=spirit['element']??'neutral';
    final matching=element=='neutral'||elementMastery(person,element)>=65;
    final racial=spirit['affinity']=='neutral'||spirit['affinity']==person['race'];
    final role=person['spiritClass']?.toString()??'ordinary';
    if(element!='neutral'&&!commonElements.contains(element)&&elementMastery(person,element)==0)return 0;
    if(role=='elementalist')return matching?min(100,base+15):base~/4;
    if(role=='specialist'||role=='chosen')return min(100,base+(matching?10:racial?0:-15));
    return matching?min(100,base+(racial?10:0)):racial?base~/2:base~/3;
  }
  static String spiritualRank(int affinity,int intelligence){return affinity>=98?'SS':affinity>=92?'S':affinity>=80?'A':affinity>=65?'B':affinity>=50?'C':affinity>=30?'D':'E';}
  static const appraisalThresholds=[5,20,45,80,125,180,260,400];
  static const appraisalFees=[0,500,2000,7500,25000,80000,250000,1000000];
  int get naturalAppraisal{var r=0;for(var i=0;i<appraisalThresholds.length;i++){if(intelligence>=appraisalThresholds[i])r=i;}return r;}
  int get appraisalTier=>appraisalRefinement.clamp(0,7).toInt();
  String get appraisalRank=>powerRanks[appraisalTier];
  bool refineAppraisal(){if(inBattle||place!='Dormitorio'||world!='school'||appraisalTier>=7)return false;final next=appraisalTier+1,fee=appraisalFees[next];if(cash<fee||intelligence<appraisalThresholds[next])return false;cash-=fee;appraisalRefinement=next;return true;}
  static int rankIndex(dynamic value)=>max(0,powerRanks.indexOf(value?.toString()??'E'));
  bool canAppraise(Map skill)=>rankIndex(skill['rank'])<=appraisalTier;
  final Map<String,int> skillUpgrades={},skillUses={};
  final Map<String,Map<String,dynamic>> fusedSkills={},copiedSkills={};
  final Map<String,int> appraisedRanks={},fusionAttempts={};
  int techniqueTier(Map sk)=>max(rankIndex(sk['rank']),skillUpgrades[sk['id']]??0).clamp(0,7).toInt();
  int upgradeFee(Map sk)=>appraisalFees[min(7,techniqueTier(sk)+1)]~/2;
  bool upgradeTechnique(Map sk){final id=sk['id'] as String,rank=techniqueTier(sk);if(inBattle||world!='school'||place!='Dormitorio'||!skills.contains(id)||rank>=7||cash<upgradeFee(sk)||intelligence<appraisalThresholds[rank+1]~/2)return false;cash-=upgradeFee(sk);skillUpgrades[id]=rank+1;return true;}
  Map<String,dynamic> effectiveTechnique(Map sk){final delta=techniqueTier(sk)-rankIndex(sk['rank']);final uses=skillUses[sk['id']]??0;return {...Map<String,dynamic>.from(sk),'rank':powerRanks[techniqueTier(sk)],'damage':((sk['damage'] as int?)??0)+delta*max(3,((sk['damage'] as int?)??0)~/2)+min(5,uses~/10),'cost':max(1,((sk['cost'] as int?)??1)-delta~/2),'stateChance':min(85,statusChance(sk,false)+delta*3),'criticalChance':min(65,numOf(sk,'criticalChance',5)+delta*2),'effectTurns':((sk['effectTurns'] as int?)??2)+delta~/2};}
  String fusionKey(Map a,Map b){final ids=[a['id'].toString(),b['id'].toString()]..sort();return 'fusion_'+ids.join('__');}
  bool compatibleFusion(Map a,Map b)=>a['id']!=b['id']&&a['type']==b['type']&&a['magic']==b['magic']&&(a['element']==null||b['element']==null||a['element']==b['element'])&&a['copyable']!=false&&b['copyable']!=false&&(a['specialEffect']==null||b['specialEffect']==null||a['specialEffect']==b['specialEffect'])&&!a['id'].toString().startsWith('fusion_')&&!b['id'].toString().startsWith('fusion_');
  static const fusionIntelligence=[0,30,60,100,150,220,320,450];
  int fusionTier(Map a,Map b)=>min(7,max(techniqueTier(a),techniqueTier(b))+1);
  int fusionMinimum(Map a,Map b)=>fusionIntelligence[fusionTier(a,b)];
  int fusionChance(Map a,Map b){final minimum=fusionMinimum(a,b);if(intelligence<minimum||!compatibleFusion(a,b))return 0;return min(100,25+(intelligence-minimum)*75~/max(30,minimum));}
  int fusionFee(Map a,Map b)=>max(500,appraisalFees[min(7,max(techniqueTier(a),techniqueTier(b))+1)]);
  bool fuse(Map a,Map b,{Random? random}){final id=fusionKey(a,b),tier=min(7,max(techniqueTier(a),techniqueTier(b))+1);if(inBattle||world!='school'||place!='Dormitorio'||!skills.contains(a['id'])||!skills.contains(b['id'])||!compatibleFusion(a,b)||fusedSkills.containsKey(id)||cash<fusionFee(a,b)||fusionChance(a,b)==0)return false;final x=effectiveTechnique(a),y=effectiveTechnique(b);cash-=fusionFee(a,b);fusionAttempts[id]=(fusionAttempts[id]??0)+1;if((random??Random()).nextInt(100)>=fusionChance(a,b))return false;fusedSkills[id]={'id':id,'name':a['name'].toString()+' × '+b['name'].toString(),'rank':powerRanks[tier],'type':a['type'],'magic':a['magic'],'element':a['element']??b['element'],'specialEffect':a['specialEffect']??b['specialEffect'],'damage':((x['damage'] as int)+(y['damage'] as int))*3~/4,'cost':max(x['cost'] as int,y['cost'] as int)+1,'stateChance':min(85,max(statusChance(x,false),statusChance(y,false))+(a['element']!=null&&a['element']==b['element']?8:0)),'status':x['status']??y['status'],'criticalChance':max(numOf(x,'criticalChance',5),numOf(y,'criticalChance',5))};skills.add(id);return true;}
  bool acquireRankedSkill(Map skill){if(skill['copyable']==false||!canAppraise(skill))return false;if(skill['element']=='divine'&&!flags.contains('divine_devotion'))return false;final id=skill['id'] as String;if((appraisedRanks[id]??rankIndex(skill['rank']))<rankIndex(skill['rank']))return false;if(!buySkill(id,skill['price'] as int))return false;copiedSkills[id]=Map<String,dynamic>.from(skill);return true;}
  bool buyWeapon(Map w){if(inBattle||world!='trade'||place!='Armería'||weapons.contains(w['id'])||grades.length<((w['minClasses'] as int?)??0)||w['requiresWin'] is String&&!wins.contains('battle_'+w['requiresWin'].toString()))return false;final price=w['price'] as int;if(price<=0||cash<price)return false;cash-=price;weapons.add(w['id'] as String);return true;}
  bool equipWeapon(Map w){if(inBattle||world!='school'||place!='Dormitorio'||!weapons.contains(w['id'])||strength<(w['minStrength'] as int)||intelligence<(w['minIntelligence'] as int))return false;equippedWeapon=w['id'] as String;weaponElement=w['element']?.toString()??'neutral';weaponStrength=w['strengthBonus'] as int;weaponMagic=w['magicBonus'] as int;weaponDefense=w['defenseBonus'] as int;return true;}
  void unequipWeapon(){if(inBattle)return;equippedWeapon='';weaponElement='neutral';weaponStrength=0;weaponMagic=0;weaponDefense=0;}
  int spiritChance(Map spirit,int affinity){if(!canCapture(spirit)||affinity<((spirit['minAffinity'] as int?)??25))return 0;return (20+affinity~/2+(intelligence-(spirit['intelligence'] as int))*2+min(10,luck~/5)).clamp(5,100).toInt();}
  bool freshSpiritAttempt(Map spirit){final encounter=spirit['requiresWin']?.toString()??'';final count=battleCounts[encounter]??(wins.contains('battle_'+encounter)?1:0);return count>(spiritAttempts[spirit['id']]??0);}
  String trySpirit(Map spirit,int affinity){final chance=spiritChance(spirit,affinity);if(chance==0||!freshSpiritAttempt(spirit))return 'Necesitas afinidad, inteligencia o superar de nuevo su encuentro.';final encounter=spirit['requiresWin']?.toString()??'',id=spirit['id'] as String;spiritAttempts[id]=battleCounts[encounter]??1;if(Random().nextInt(100)>=chance)return 'El espíritu no acepta el vínculo. Supera de nuevo el encuentro para intentar otra vez.';spirits.add(id);return 'Espíritu vinculado.';}
  int victoryXp(Map enemy,bool first){if(enemy['raid']==true||enemy['location']=='Frente de guerra')return first||enemy['repeatable']==true?max(0,numOf(enemy,'xp',0)):0;if(enemy['repeatable']==true){final l=(enemy['level'] as int?)??1;return 20+15*l*l+((enemy['hp'] as int?)??0)~/10;}return first?((enemy['xp'] as int?)??0):0;}
  DualState returnToBeginning(){final next=DualState();next.intelligence=intelligence;next.mana=intelligence;next.readPages.addAll(readPages);next.readingLog.addAll(readingLog.map((k,v)=>MapEntry(k,Map<String,dynamic>.from(v))));next.readingRemainder=readingRemainder;next.workoutDate=workoutDate;next.returned=false;return next;}
  int get level=>1+xp~/100;
  int get maxHp=>40+(level-1)*5;
  String get playerCombatRank{final score=strength+defense+stamina+(level-1)*8+skills.length*3+spirits.length*5;return score>=120000?'Divino+':score>=25000?'Divino':score>=1800?'L':score>=1000?'SSS':score>=650?'SS':score>=400?'S':score>=250?'A':score>=190?'B+':score>=140?'B':score>=75?'C':score>=35?'D':'E';}
  int get power=>strength+defense+stamina+intelligence+level*2+skills.length*3;
  int get examAverage=>grades.isEmpty?0:(grades.values.reduce((a,b)=>a+b)/grades.length).round();
  bool get inBattle=>enemyIndex>=0;
  bool get privatePlace=>place=='Dormitorio'||place=='Taller privado';
  bool travel(){if(inBattle||!privatePlace)return false;world=world=='school'?'trade':'school';place=world=='school'?'Dormitorio':'Taller privado';return true;}
  int pageReward(int page,int count)=>count<=0||page<0||page>=count?0:((page+1)*5)~/count-(page*5)~/count;
  bool read(String id,int page,int count){final old=readPages[id]??0;if(count<=0||page!=old||page>=count)return false;final before=(old*5)~/count;final after=((old+1)*5)~/count;readPages[id]=old+1;intelligence+=after-before;mana=min(intelligence,mana+after-before);return true;}
  static String bookKey(String title,String author)=>(title.trim().toLowerCase()+'|'+author.trim().toLowerCase()).replaceAll(RegExp(r'\s+'),' ');
  bool addReadingBook(String title,String author,int total,String category){final key=bookKey(title,author);if(title.trim().isEmpty||author.trim().isEmpty||total<1||total>20000||readingLog.containsKey(key))return false;readingLog[key]={'title':title.trim(),'author':author.trim(),'total':total,'page':0,'category':category};return true;}
  int? logReading(String key,int page){final b=readingLog[key];if(b==null)return null;final total=b['total'] as int,old=b['page'] as int;if(page<=old||page>total)return null;final gained=(page*5000)~/total-(old*5000)~/total;b['page']=page;final sum=readingRemainder+gained;final increase=sum~/1000;readingRemainder=sum%1000;intelligence+=increase;mana=min(intelligence,mana+increase);return gained;}
  bool workout(String date){if(date.isEmpty||workoutDate.compareTo(date)>=0)return false;workoutDate=date;strength+=2;defense+=2;stamina+=2;return true;}
  int rewardExam(String id,bool correct){if(grades.containsKey(id))return grades[id]!;attempts[id]=(attempts[id]??0)+1;if(!correct)return 0;final grade=max(60,100-10*((attempts[id]??1)-1));grades[id]=grade;rankPoints+=grade;reputation=min(100,reputation+max(1,grade~/20));xp+=30;advanceWarWeek();return grade;}
  int claimGuild(String id){final grade=grades[id];if(grade==null||!wins.add('guild_'+id))return 0;cash+=grade;return grade;}
  bool buySkill(String id,int price){if(!privatePlace||world!='school'||!appraised.contains(id)||skills.contains(id)||cash<price||price<=0)return false;cash-=price;skills.add(id);return true;}
  int commission(){final id='commission_'+day.toString();if(wins.contains(id))return 0;wins.add(id);cash+=30;day++;return 30;}
  Map<String,int>? trade(int qty,int price,int demand,int cost,int fixed){if(qty<0||qty>100||price<1||price>100||demand<0||cost<=0||fixed<0||cash<qty*cost+fixed||qty+stock<=0)return null;final total=stock+qty,combined=inventoryCost+qty*cost;final sold=min(total,demand);final cogs=(combined*sold/total).round();final revenue=sold*price;cash+=revenue-qty*cost-fixed;stock=total-sold;inventoryCost=combined-cogs;day++;return {'sold':sold,'revenue':revenue,'profit':revenue-cogs-fixed,'cash':cash,'stock':stock};}
  void rest(){if(inBattle)return;hp=maxHp;mana=intelligence;energy=stamina;}
  bool startBattle(int i,int health,{bool lethal=false}){if(inBattle||health<1||hp<1)return false;raidAllies.clear();enemyIndex=i;lethalBattle=lethal;enemyHp=health;turn=0;guardPower=0;guardTurns=0;speedPower=0;speedTurns=0;enemyWeakTurns=0;enemyBleedTurns=0;enemyBleedPower=0;enemyGuard=0;enemyEvade=0;enemyGuardTurns=0;enemyEvadeTurns=0;lastElement='neutral';spiritMode='';spiritEnergy=0;precision=0;enemyEnergy=-1;enemyMana=-1;enemyMaxEnergy=0;enemyMaxMana=0;playerStates.clear();enemyStates.clear();return true;}
  String battleVictory(Map enemy){final key=enemy['id'] as String;final first=wins.add('battle_'+key);final earned=victoryXp(enemy,first);xp+=earned;final gold=(first||enemy['repeatable']==true)?max(0,numOf(enemy,'goldReward',0)):0;cash+=gold;recordWarVictory(enemy,first);battleCounts[key]=(battleCounts[key]??(first?0:1))+1;rankPoints+=first?25:0;if(first)reputation=min(100,reputation+8);if(pendingDuel==key)pendingDuel='';for(final id in rescueMissions.keys.where((id)=>rescueMissions[id]==key).toList()){if(!deadStudents.contains(id)){rescuedStudents.add(id);trust[id]=(relationship(id)+15).clamp(-100,100).toInt();}rescueMissions.remove(id);}enemyIndex=-1;lethalBattle=false;return 'Victoria. +'+earned.toString()+' XP. '+(gold>0?'+'+gold.toString()+' monedas. ':'')+(first?'Reputación y ranking aumentados.':earned>0?'Experiencia de monstruo.':'Práctica sin recompensa repetida.');}
  String action(Map skill,Map enemy,{List<Map>? availableSkills,Random? random}){
    if(!inBattle)return 'No hay combate.';
    if(!skills.contains(skill['id'])&&!(skill['spirit'] is String&&spirits.contains(skill['spirit'])))return 'Aún no has adquirido esta técnica.';
    final cost=skill['cost'] as int,magic=skill['magic']==true;
    if(!usable(skill))return 'No tienes maná, estamina, inteligencia o vínculo suficiente.';
    mana-=manaCost(skill);energy-=staminaCost(skill);
    if(enemyEnergy<0){enemyMaxEnergy=max(1,numOf(enemy,'stamina',12+numOf(enemy,'level',1)*4));enemyMaxMana=max(0,numOf(enemy,'intelligence',5+numOf(enemy,'level',1)*3));enemyEnergy=enemyMaxEnergy;enemyMana=enemyMaxMana;}
    final rng=random??Random((turn+1)*31+xp*7+enemyHp);
    final interrupted=blocked(playerStates,rng)||(magic&&playerStates.containsKey('silencio'));
    final mode=skill['spiritMode']?.toString();if(!interrupted&&mode!=null){spiritMode=mode;if(mode=='manifest')spiritEnergy=max(1,numOf(skill,'spiritStamina',10));}
    if(!interrupted&&skill['precisionBoost'] is int)precision=min(60,precision+(skill['precisionBoost'] as int));
    final element=skill['element']?.toString()??'neutral';final el=element=='neutral'&&spiritMode=='enchant'?spiritElement:element;
    final matching=compatibleElements(el,lastElement)||(activeSpirit.isNotEmpty&&el==spiritElement&&el!='neutral');
    final kind=skill['type'] as String;final special=skill['specialEffect'];final damage=interrupted?0:skill['damage'] as int;final duration=(skill['effectTurns'] as int?)??2;if(skills.contains(skill['id'])){final id=skill['id'] as String;skillUses[id]=(skillUses[id]??0)+1;}
    if(!interrupted&&kind=='defense'){guardPower=damage;guardTurns=duration+1;}
    if(!interrupted&&kind=='speed'){speedPower=damage;speedTurns=duration+1;}
    if(!interrupted&&kind=='heal'){hp=min(maxHp,hp+damage);}
    if(!interrupted&&(kind=='hypnosis'||kind=='seal')){enemyWeakTurns=max(enemyWeakTurns,duration);}
    if(!interrupted&&kind=='void'){enemyGuard=0;enemyEvade=0;enemyGuardTurns=0;enemyEvadeTurns=0;enemyWeakTurns=max(enemyWeakTurns,2);}
    final guard=guardTurns>0?guardPower:0,evade=speedTurns>0?speedPower:0;
    final offensive=!interrupted&&const ['attack','drain','bleed','void'].contains(kind);
    final missed=offensive&&rng.nextInt(100)<missChance(numOf(enemy,'evasion',0)+enemyEvade,precision+numOf(skill,'precision',0));
    final critical=offensive&&!missed&&rng.nextInt(100)<critChance(numOf(skill,'criticalChance',5),precision+numOf(skill,'precision',0));
    final defenseFactor=special=='space'?2:1;
    int dealt=offensive&&!missed?max(1,damage+(magic?intelligence+((weaponElement=='neutral'||weaponElement==skill['element'])?weaponMagic:weaponMagic~/2):strength+weaponStrength)~/2-(kind=='void'?0:(enemy['defense'] as int)~/defenseFactor)-(special=='sound'?enemyGuard~/2:enemyGuard)):0;
    String stateNote=interrupted?' · Acción interrumpida':'';
    if(dealt>0){final resistance=enemy['resistances'] is Map?numOf(enemy['resistances'] as Map,el,0).clamp(0,80).toInt():0;
      dealt=max(1,dealt*(matching?110:100)*(100-resistance)~/10000);
      if(spiritMode=='fusion')dealt=max(1,dealt*115~/100);if(magic&&hasClass('Mago')||!magic&&hasClass('Guerrero'))dealt=max(1,dealt*105~/100);
      if(critical){dealt=max(1,dealt*numOf(skill,'criticalDamage',150)~/100);stateNote+=' · ¡Crítico!';}
      stateNote+=applyState({...skill,'element':el},enemyStates,rng,matching,resistance:resistance~/2);
      if(el!='neutral')lastElement=el;
    }
    if(!interrupted&&spiritMode=='manifest'&&spiritEnergy>0){final spent=min(3,spiritEnergy);spiritEnergy-=spent;dealt+=max(1,spiritDamage*spent~/3);stateNote+=' · Espíritu ataca';}
    if(enemyGuardTurns>0&&--enemyGuardTurns==0)enemyGuard=0;if(enemyEvadeTurns>0&&--enemyEvadeTurns==0)enemyEvade=0;
    enemyHp=max(0,enemyHp-dealt);
    if(enemy['raid']==true&&enemyHp>0){final support=raidSupport(enemy);enemyHp=max(0,enemyHp-support);if(support>0)stateNote+=' · Escuadrón: '+support.toString()+' daño';}
    if(dealt>0){if(special=='gravity'){enemyEvade=0;enemyEvadeTurns=0;enemyWeakTurns=max(enemyWeakTurns,duration);}if(special=='sound'||special=='magnetism'){enemyGuard=0;enemyGuardTurns=0;}}
    if(!interrupted&&special=='tempo'){enemyWeakTurns=max(enemyWeakTurns,duration+1);speedPower=max(speedPower,5);speedTurns=max(speedTurns,duration+1);}
    if(!interrupted&&special=='dream'){enemyWeakTurns=max(enemyWeakTurns,duration+1);}
    if(!interrupted&&special=='crystal'){guardPower=max(guardPower,damage);guardTurns=max(guardTurns,duration+2);}
    if(kind=='drain'&&dealt>0)hp=min(maxHp,hp+max(1,dealt~/3));
    if(kind=='bleed'&&dealt>0){enemyBleedPower=max(1,damage~/4);enemyBleedTurns=duration;}
    if(enemyBleedTurns>0){enemyHp=max(0,enemyHp-enemyBleedPower);enemyBleedTurns--;}
    final enemyBlocked=blocked(enemyStates,rng);
    final statusDamage=tickStates(enemyStates,enemy['hp'] as int);
    enemyHp=max(0,enemyHp-(enemy['raid']==true?min(statusDamage,max(1,numOf(enemy,'hp',1)~/100)):statusDamage));
    hp=max(0,hp-tickStates(playerStates,maxHp));
    turn++;
    if(enemyHp==0){return battleVictory(enemy);}
    if(hp==0|| (availableSkills!=null&&!availableSkills.any(usable))||(energy==0&&mana==0)){enemyIndex=-1;if(hp==0&&lethalBattle){returned=true;return 'Tu vida terminó. Retorno se activa.';}lethalBattle=false;return hp==0?'Derrota.':'Derrota por agotamiento.';}

    final choices=(enemy['techniques'] is List?(enemy['techniques'] as List).whereType<Map>().toList():<Map>[]);
    Map? move;final affordable=choices.where((m)=>enemyEnergy>=staminaCost(m)&&enemyMana>=manaCost(m)).toList();
    if(enemyEnergy<=0&&affordable.isEmpty)return battleVictory(enemy);
    if(affordable.isNotEmpty&&(turn%2==0||enemyEnergy<=0))move=affordable[(turn-1)%affordable.length];
    if(move==null){enemyEnergy=max(0,enemyEnergy-1);}else{enemyEnergy-=staminaCost(move);enemyMana-=manaCost(move);}
    final enemyType=move?['type'];final enemySpecial=move?['specialEffect'];final enemyPower=((move?['damage'] as int?)??0)*((move?['mastery'] as int?)??100)~/100;
    final enemyDuration=(move?['effectTurns'] as int?)??2;
    int enemyAttack=(enemy['attack'] as int)+(turn%3==0?4:0);
    String note='';
    if(move!=null){note=' · Rival: '+move['name'].toString();
      if(enemyType=='defense'){enemyGuard=min(30,enemyPower~/2);enemyGuardTurns=enemyDuration;enemyAttack=0;}
      else if(enemyType=='speed'){enemyEvade=min(30,enemyPower);enemyEvadeTurns=enemyDuration;enemyAttack=0;}
      else if(enemyType=='heal'){enemyHp=min(enemy['hp'] as int,enemyHp+min(35,enemyPower~/2));enemyAttack=0;}
      else if(enemyType=='void'){guardPower=0;guardTurns=0;speedPower=0;speedTurns=0;enemyAttack+=min(12,enemyPower~/4);note+=' · tu guardia se disipa';}
      else if(enemyType=='hypnosis'||enemyType=='seal'){final loss=min(mana,max(2,enemyDuration));mana-=loss;enemyAttack=max(1,enemyAttack~/2);note+=' · pierdes '+loss.toString()+' maná';}
      else {enemyAttack+=min(20,enemyPower~/5)+(move['magic']==true?((enemy['spellPower'] as int?)??0):0);}
    }
    if(move!=null){if(enemySpecial=='gravity'){speedPower=0;speedTurns=0;enemyAttack+=min(8,enemyPower~/6);note+=' · presión gravitatoria';}else if(enemySpecial=='space'){note+=' · distorsión espacial';}else if(enemySpecial=='sound'||enemySpecial=='magnetism'){guardPower=0;guardTurns=0;note+=' · guardia quebrada';}else if(enemySpecial=='tempo'){energy=max(0,energy-2);note+=' · ritmo alterado';}else if(enemySpecial=='dream'){mana=max(0,mana-3);note+=' · somnolencia mágica';}else if(enemySpecial=='crystal'){enemyGuard=max(enemyGuard,min(30,enemyPower~/2));enemyGuardTurns=max(enemyGuardTurns,enemyDuration+1);}else if(enemySpecial=='entropy'){enemyAttack+=min(8,enemyPower~/5);note+=' · desgaste';}}
    if(enemyWeakTurns>0){enemyAttack=enemyAttack~/2;enemyWeakTurns--;}
    int hit=enemyBlocked||enemyAttack<=0||rng.nextInt(100)<missChance(enemySpecial=='gravity'?0:evade*5,numOf(enemy,'precision',0))?0:max(1,enemyAttack-(defense+weaponDefense)~/2-(enemyType=='void'||enemySpecial=='sound'||enemySpecial=='magnetism'?0:enemySpecial=='space'?guard~/2:guard));
    if(guardTurns>0)guardTurns--;if(speedTurns>0)speedTurns--;
    if(hit>0){final rivalEl=move?['element']?.toString()??'neutral';hit=max(1,hit*(100-resistanceFor(rivalEl))~/100);
      if(rng.nextInt(100)<critChance(numOf(move??{},'criticalChance',5),numOf(enemy,'precision',0))){hit=max(1,hit*numOf(move??{},'criticalDamage',150)~/100);note+=' · Crítico rival';}
      if(move!=null)note+=applyState(move,playerStates,rng,false,resistance:resistanceFor(rivalEl));}
    if(enemy['raid']==true)hit=raidIntercept(hit,enemy);
    hp=max(0,hp-hit);
    if(hit>0&&(((enemy['lifesteal'] as int?)??0)>0||enemyType=='drain'))enemyHp=min(enemy['hp'] as int,enemyHp+min(3,hit));
    final regen=(enemy['regen'] as int?)??0;
    if(regen>0&&turn%3==0)enemyHp=min(enemy['hp'] as int,enemyHp+regen);
    if(hp==0){enemyIndex=-1;if(lethalBattle){returned=true;return 'Tu vida terminó. Retorno se activa.';}return 'Derrota en un duelo protegido. Regresa al dormitorio para recuperarte.';}
    if(enemyEnergy<=0&&!choices.any((m)=>enemyEnergy>=staminaCost(m)&&enemyMana>=manaCost(m)))return battleVictory(enemy);
    if((availableSkills!=null&&!availableSkills.any(usable))||(energy==0&&mana==0)){enemyIndex=-1;lethalBattle=false;return 'Derrota por agotamiento.';}
    return stateNote+' '+(missed?'El rival esquivó. ':'')+'Daño directo: '+dealt.toString()+' · daño recibido: '+hit.toString()+note;
  }
  Map<String,dynamic> toJson()=>{'cash':cash,'stock':stock,'inventoryCost':inventoryCost,'day':day,'xp':xp,'strength':strength,'defense':defense,'stamina':stamina,'intelligence':intelligence,'rankPoints':rankPoints,'chapter':chapter,'hp':hp,'energy':energy,'mana':mana,'enemyHp':enemyHp,'turn':turn,'enemyIndex':enemyIndex,'guardPower':guardPower,'guardTurns':guardTurns,'speedPower':speedPower,'speedTurns':speedTurns,'enemyWeakTurns':enemyWeakTurns,'enemyBleedTurns':enemyBleedTurns,'enemyBleedPower':enemyBleedPower,'enemyGuard':enemyGuard,'enemyEvade':enemyEvade,'enemyGuardTurns':enemyGuardTurns,'enemyEvadeTurns':enemyEvadeTurns,'world':world,'place':place,'workoutDate':workoutDate,'skills':skills.toList(),'appraised':appraised.toList(),'readPages':readPages,'grades':grades,'attempts':attempts,'wins':wins.toList(),'reputation':reputation,'trust':trust,'affection':affection,'decisions':decisions,'flags':flags.toList(),'pendingDuel':pendingDuel,'lastEvent':lastEvent,'spirits':spirits.toList(),'deadStudents':deadStudents.toList(),'rescuedStudents':rescuedStudents.toList(),'knownRaces':knownRaces.toList(),'rumors':rumors.toList(),'rescueMissions':rescueMissions,'activeSpirit':activeSpirit,'spiritElement':spiritElement,'spiritMode':spiritMode,'spiritEnergy':spiritEnergy,'spiritDamage':spiritDamage,'precision':precision,'enemyEnergy':enemyEnergy,'enemyMana':enemyMana,'enemyMaxEnergy':enemyMaxEnergy,'enemyMaxMana':enemyMaxMana,'charisma':charisma,'luck':luck,'lastElement':lastElement,'playerStates':playerStates,'enemyStates':enemyStates,'elementResistance':elementResistance,'lethalBattle':lethalBattle,'warWeek':warWeek,'warContribution':warContribution,'alliedContribution':alliedContribution,'warSeed':warSeed,'alliedReports':alliedReports,'raidAllies':raidAllies,'returned':returned,'readingLog':readingLog,'readingRemainder':readingRemainder,'battleCounts':battleCounts,'spiritAttempts':spiritAttempts,'factionStanding':factionStanding,'weapons':weapons.toList(),'equippedWeapon':equippedWeapon,'weaponElement':weaponElement,'weaponStrength':weaponStrength,'weaponMagic':weaponMagic,'weaponDefense':weaponDefense,'appraisalRefinement':appraisalRefinement,'skillUpgrades':skillUpgrades,'skillUses':skillUses,'fusedSkills':fusedSkills,'copiedSkills':copiedSkills,'appraisedRanks':appraisedRanks,'fusionAttempts':fusionAttempts,'economy':economy.toJson()};
  factory DualState.fromJson(Map j){final s=DualState();if(j['economy'] is Map)s.economy=LumenEconomy.fromJson(j['economy'] as Map);int n(String k,int fallback)=>j[k] is int?j[k] as int:fallback;
    s.cash=n('cash',0);s.stock=n('stock',0);s.inventoryCost=n('inventoryCost',0);s.day=n('day',0);s.xp=n('xp',0);s.strength=n('strength',4);s.defense=n('defense',3);s.stamina=n('stamina',10);s.intelligence=n('intelligence',5);s.rankPoints=n('rankPoints',0);s.chapter=n('chapter',0);s.hp=n('hp',40);s.energy=n('energy',10);s.mana=n('mana',5);s.enemyHp=n('enemyHp',0);s.turn=n('turn',0);s.enemyIndex=n('enemyIndex',-1);s.guardPower=n('guardPower',0);s.guardTurns=n('guardTurns',0);s.speedPower=n('speedPower',0);s.speedTurns=n('speedTurns',0);s.enemyWeakTurns=n('enemyWeakTurns',0);s.enemyBleedTurns=n('enemyBleedTurns',0);s.enemyBleedPower=n('enemyBleedPower',0);s.enemyGuard=n('enemyGuard',0);s.enemyEvade=n('enemyEvade',0);s.enemyGuardTurns=n('enemyGuardTurns',s.enemyGuard>0?1:0);s.enemyEvadeTurns=n('enemyEvadeTurns',s.enemyEvade>0?1:0);s.world=j['world']=='trade'?'trade':'school';s.place=j['place'] is String?j['place'] as String:'Dormitorio';s.workoutDate=j['workoutDate'] is String?j['workoutDate'] as String:'';
    for(final e in [MapEntry('skills',s.skills),MapEntry('weapons',s.weapons),MapEntry('appraised',s.appraised),MapEntry('wins',s.wins),MapEntry('flags',s.flags),MapEntry('spirits',s.spirits),MapEntry('deadStudents',s.deadStudents),MapEntry('rescuedStudents',s.rescuedStudents),MapEntry('knownRaces',s.knownRaces),MapEntry('rumors',s.rumors)]){if(j[e.key] is List)e.value.addAll((j[e.key] as List).whereType<String>());}
    for(final e in [MapEntry('readPages',s.readPages),MapEntry('grades',s.grades),MapEntry('attempts',s.attempts),MapEntry('trust',s.trust),MapEntry('affection',s.affection),MapEntry('battleCounts',s.battleCounts),MapEntry('spiritAttempts',s.spiritAttempts),MapEntry('factionStanding',s.factionStanding),MapEntry('skillUpgrades',s.skillUpgrades),MapEntry('skillUses',s.skillUses),MapEntry('appraisedRanks',s.appraisedRanks),MapEntry('fusionAttempts',s.fusionAttempts)]){if(j[e.key] is Map)for(final item in (j[e.key] as Map).entries){if(item.key is String&&item.value is int)e.value[item.key as String]=item.value as int;}}
    s.readingRemainder=n('readingRemainder',0).clamp(0,999).toInt();if(j['readingLog'] is Map)for(final item in (j['readingLog'] as Map).entries){if(item.key is String&&item.value is Map){final b=Map<String,dynamic>.from(item.value as Map);if(b['total'] is int&&b['page'] is int&&(b['total'] as int)>0&&(b['page'] as int)>=0&&(b['page'] as int)<=(b['total'] as int))s.readingLog[item.key as String]=b;}}s.lethalBattle=j['lethalBattle']==true;s.warWeek=max(0,n('warWeek',s.grades.length));s.warContribution=max(0,n('warContribution',0));s.alliedContribution=max(0,n('alliedContribution',0));s.warSeed=n('warSeed',s.warSeed);if(j['alliedReports'] is List)s.alliedReports.addAll((j['alliedReports'] as List).whereType<String>().take(20));if(j['raidAllies'] is List){s.raidAllies.addAll((j['raidAllies'] as List).whereType<Map>().take(3).map((a)=>Map<String,dynamic>.from(a)));}s.returned=j['returned']==true;s.activeSpirit=j['activeSpirit'] is String?j['activeSpirit'] as String:'';if(j['rescueMissions'] is Map)for(final e in (j['rescueMissions'] as Map).entries){if(e.key is String&&e.value is String)s.rescueMissions[e.key as String]=e.value as String;}s.spiritElement=j['spiritElement']?.toString()??'neutral';s.spiritMode=j['spiritMode']?.toString()??'';s.lastElement=j['lastElement']?.toString()??'neutral';s.spiritEnergy=n('spiritEnergy',0);s.spiritDamage=n('spiritDamage',0);s.precision=n('precision',0);s.enemyEnergy=n('enemyEnergy',-1);s.enemyMana=n('enemyMana',-1);s.enemyMaxEnergy=n('enemyMaxEnergy',0);s.enemyMaxMana=n('enemyMaxMana',0);s.charisma=n('charisma',0);s.luck=n('luck',0);for(final e in [MapEntry('playerStates',s.playerStates),MapEntry('enemyStates',s.enemyStates),MapEntry('elementResistance',s.elementResistance)]){if(j[e.key] is Map)for(final v in (j[e.key] as Map).entries){if(v.key is String&&v.value is int)e.value[v.key as String]=v.value as int;}}s.appraisalRefinement=n('appraisalRefinement',0).clamp(0,7).toInt();s.equippedWeapon=j['equippedWeapon']?.toString()??'';if(s.weapons.contains(s.equippedWeapon)){s.weaponElement=j['weaponElement']?.toString()??'neutral';s.weaponStrength=max(0,n('weaponStrength',0));s.weaponMagic=max(0,n('weaponMagic',0));s.weaponDefense=max(0,n('weaponDefense',0));}else{s.equippedWeapon='';}if(j['fusedSkills'] is Map)for(final entry in (j['fusedSkills'] as Map).entries){if(entry.key is String&&entry.value is Map)s.fusedSkills[entry.key as String]=Map<String,dynamic>.from(entry.value as Map);}if(j['copiedSkills'] is Map)for(final entry in (j['copiedSkills'] as Map).entries){if(entry.key is String&&entry.value is Map)s.copiedSkills[entry.key as String]=Map<String,dynamic>.from(entry.value as Map);}s.skills.remove('strike');s.reputation=n('reputation',-30);s.pendingDuel=j['pendingDuel'] is String?j['pendingDuel'] as String:'';s.lastEvent=j['lastEvent'] is String?j['lastEvent'] as String:'';if(j['decisions'] is Map)for(final e in (j['decisions'] as Map).entries){if(e.key is String&&e.value is String)s.decisions[e.key as String]=e.value as String;}return s;
  }
  DualState();
}
