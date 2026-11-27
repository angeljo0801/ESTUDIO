import 'dart:math';
class DualState {
  int cash=0,stock=0,inventoryCost=0,day=0,xp=0,strength=4,defense=3,stamina=10,intelligence=5,rankPoints=0,chapter=0;
  int hp=40,energy=10,mana=5,enemyHp=0,turn=0,enemyIndex=-1,guardPower=0,guardTurns=0,speedPower=0,speedTurns=0;
  int enemyWeakTurns=0,enemyBleedTurns=0,enemyBleedPower=0,enemyGuard=0,enemyEvade=0;
  String world='school',place='Dormitorio',workoutDate='';
  final Set<String> skills={};
  final Set<String> spirits={},deadStudents={},rescuedStudents={},knownRaces={},rumors={};
  final Map<String,String> rescueMissions={};
  String activeSpirit='';
  bool returned=false;
  bool lethalBattle=false;
  int reputation=-30;
  final Map<String,int> trust={},affection={};
  final Map<String,String> decisions={};
  final Set<String> flags={};
  String pendingDuel='';
  String lastEvent='';
  final Set<String> appraised={};
  final Map<String,int> readPages={},grades={},attempts={};
  final Set<String> wins={};
  int relationship(String id)=>trust[id]??0;
  int warmth(String id)=>affection[id]??0;
  bool eligible(Map e){
    if(deadStudents.contains(e['person']))return false;
    if(e['maxClasses'] is int&&grades.length>(e['maxClasses'] as int))return false;
    if(decisions.containsKey(e['id'])||e['world']!=world||e['place']!=place)return false;
    if(grades.length<((e['minClasses'] as int?)??0)||reputation<((e['minRep'] as int?)??-100))return false;
    if(e['requiresFlag'] is String&&!flags.contains(e['requiresFlag']))return false;
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
    if(person.isNotEmpty){trust[person]=(relationship(person)+((choice['trust'] as int?)??0)).clamp(-100,100).toInt();affection[person]=(warmth(person)+((choice['affection'] as int?)??0)).clamp(0,100).toInt();}
    reputation=(reputation+((choice['rep'] as int?)??0)).clamp(-100,100).toInt();
    decisions[e['id'] as String]=choice['id'] as String;
    if(choice['flag'] is String)flags.add(choice['flag'] as String);
    if(choice['duel'] is String)pendingDuel=choice['duel'] as String;
    if(choice['rescue'] is String&&person.isNotEmpty)rescueMissions[person]=choice['rescue'] as String;
    if(choice['abandon']==true&&person.isNotEmpty){rescueMissions.remove(person);}
    if(choice['defer']==true){decisions.remove(e['id']);}
    if(choice['revealRace']==true&&person.isNotEmpty)knownRaces.add(person);
    if(choice['fatal']==true){hp=0;lethalBattle=true;returned=true;}
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
  DualState returnToBeginning(){final next=DualState();next.intelligence=intelligence;next.mana=intelligence;next.readPages.addAll(readPages);next.workoutDate=workoutDate;next.returned=false;return next;}
  int get level=>1+xp~/100;
  int get maxHp=>40+(level-1)*5;
  int get power=>strength+defense+stamina+intelligence+level*2+skills.length*3;
  int get examAverage=>grades.isEmpty?0:(grades.values.reduce((a,b)=>a+b)/grades.length).round();
  bool get inBattle=>enemyIndex>=0;
  bool get privatePlace=>place=='Dormitorio'||place=='Taller privado';
  bool travel(){if(inBattle||!privatePlace)return false;world=world=='school'?'trade':'school';place=world=='school'?'Dormitorio':'Taller privado';return true;}
  bool read(String id,int page,int count){final old=readPages[id]??0;if(count<=0||page!=old||page>=count)return false;final before=(old*5)~/count;final after=((old+1)*5)~/count;readPages[id]=old+1;intelligence+=after-before;mana=min(intelligence,mana+after-before);return true;}
  bool workout(String date){if(date.isEmpty||workoutDate.compareTo(date)>=0)return false;workoutDate=date;strength+=2;defense+=2;stamina+=2;return true;}
  int rewardExam(String id,bool correct){if(grades.containsKey(id))return grades[id]!;attempts[id]=(attempts[id]??0)+1;if(!correct)return 0;final grade=max(60,100-10*((attempts[id]??1)-1));grades[id]=grade;rankPoints+=grade;reputation=min(100,reputation+max(1,grade~/20));xp+=30;return grade;}
  int claimGuild(String id){final grade=grades[id];if(grade==null||!wins.add('guild_'+id))return 0;cash+=grade;return grade;}
  bool buySkill(String id,int price){if(!privatePlace||world!='school'||!appraised.contains(id)||skills.contains(id)||cash<price||price<=0)return false;cash-=price;skills.add(id);return true;}
  int commission(){final id='commission_'+day.toString();if(wins.contains(id))return 0;wins.add(id);cash+=30;day++;return 30;}
  Map<String,int>? trade(int qty,int price,int demand,int cost,int fixed){if(qty<0||qty>100||price<1||price>100||demand<0||cost<=0||fixed<0||cash<qty*cost+fixed||qty+stock<=0)return null;final total=stock+qty,combined=inventoryCost+qty*cost;final sold=min(total,demand);final cogs=(combined*sold/total).round();final revenue=sold*price;cash+=revenue-qty*cost-fixed;stock=total-sold;inventoryCost=combined-cogs;day++;return {'sold':sold,'revenue':revenue,'profit':revenue-cogs-fixed,'cash':cash,'stock':stock};}
  void rest(){if(inBattle)return;hp=maxHp;mana=intelligence;energy=stamina;}
  bool startBattle(int i,int health,{bool lethal=false}){if(inBattle||health<1||hp<1)return false;enemyIndex=i;lethalBattle=lethal;enemyHp=health;turn=0;guardPower=0;guardTurns=0;speedPower=0;speedTurns=0;enemyWeakTurns=0;enemyBleedTurns=0;enemyBleedPower=0;enemyGuard=0;enemyEvade=0;return true;}
  String action(Map skill,Map enemy){
    if(!inBattle)return 'No hay combate.';
    if(!skills.contains(skill['id'])&&!(skill['spirit'] is String&&spirits.contains(skill['spirit'])))return 'Aún no has adquirido esta técnica.';
    final cost=skill['cost'] as int,magic=skill['magic']==true;
    if(magic?mana<cost:energy<cost)return 'No tienes energía suficiente para esa habilidad.';
    if(magic){mana-=cost;}else{energy-=cost;}
    final kind=skill['type'] as String,damage=skill['damage'] as int;
    if(kind=='defense'){guardPower=damage;guardTurns=3;}
    if(kind=='speed'){speedPower=damage;speedTurns=3;}
    if(kind=='heal'){hp=min(maxHp,hp+damage);}
    if(kind=='hypnosis'||kind=='seal'){enemyWeakTurns=max(enemyWeakTurns,2);}
    final guard=guardTurns>0?guardPower:0,evade=speedTurns>0?speedPower:0;
    final rng=Random((turn+1)*31+xp*7+enemyHp);
    final offensive=const ['attack','drain','bleed'].contains(kind);
    final missed=offensive&&rng.nextInt(100)<min(35,((enemy['evasion'] as int?)??0)+enemyEvade);
    final dealt=offensive&&!missed?max(1,damage+(magic?intelligence:strength)~/2-(enemy['defense'] as int)-enemyGuard):0;
    enemyGuard=0;enemyEvade=0;
    enemyHp=max(0,enemyHp-dealt);
    if(kind=='drain'&&dealt>0)hp=min(maxHp,hp+max(1,dealt~/3));
    if(kind=='bleed'&&dealt>0){enemyBleedPower=max(1,damage~/4);enemyBleedTurns=2;}
    if(enemyBleedTurns>0){enemyHp=max(0,enemyHp-enemyBleedPower);enemyBleedTurns--;}
    turn++;
    if(enemyHp==0){final key=enemy['id'] as String;final first=wins.add('battle_'+key);xp+=first?(enemy['xp'] as int):0;rankPoints+=first?25:0;if(first)reputation=min(100,reputation+8);if(pendingDuel==key)pendingDuel='';for(final id in rescueMissions.keys.where((id)=>rescueMissions[id]==key).toList()){if(!deadStudents.contains(id)){rescuedStudents.add(id);trust[id]=(relationship(id)+15).clamp(-100,100).toInt();}rescueMissions.remove(id);}enemyIndex=-1;lethalBattle=false;return 'Victoria. '+(first?'Experiencia y ranking aumentados.':'Práctica sin recompensa repetida.');}
    final choices=(enemy['techniques'] is List?(enemy['techniques'] as List).whereType<Map>().toList():<Map>[]);
    Map? move;if(choices.isNotEmpty&&turn%2==0)move=choices[(turn~/2-1)%choices.length];
    final enemyType=move?['type'];final enemyPower=(move?['damage'] as int?)??0;
    int enemyAttack=(enemy['attack'] as int)+(turn%3==0?4:0);
    String note='';
    if(move!=null){note=' · Rival: '+move['name'].toString();
      if(enemyType=='defense'){enemyGuard=min(12,enemyPower~/2);enemyAttack=0;}
      else if(enemyType=='speed'){enemyEvade=min(20,enemyPower);enemyAttack=0;}
      else if(enemyType=='heal'){enemyHp=min(enemy['hp'] as int,enemyHp+min(8,enemyPower~/2));enemyAttack=0;}
      else if(enemyType=='hypnosis'||enemyType=='seal'){final loss=min(mana,2);mana-=loss;enemyAttack=max(1,enemyAttack~/2);note+=' · pierdes '+loss.toString()+' maná';}
      else {enemyAttack+=min(7,enemyPower~/5)+(move['magic']==true?((enemy['spellPower'] as int?)??0):0);}
    }
    if(enemyWeakTurns>0){enemyAttack=enemyAttack~/2;enemyWeakTurns--;}
    final hit=enemyAttack<=0||rng.nextInt(100)<min(70,10+evade*5)?0:max(1,enemyAttack-defense~/2-guard);
    if(guardTurns>0)guardTurns--;if(speedTurns>0)speedTurns--;
    hp=max(0,hp-hit);
    if(hit>0&&(((enemy['lifesteal'] as int?)??0)>0||enemyType=='drain'))enemyHp=min(enemy['hp'] as int,enemyHp+min(3,hit));
    final regen=(enemy['regen'] as int?)??0;
    if(regen>0&&turn%3==0)enemyHp=min(enemy['hp'] as int,enemyHp+regen);
    if(hp==0){enemyIndex=-1;if(lethalBattle){returned=true;return 'Tu vida terminó. Retorno se activa.';}return 'Derrota en un duelo protegido. Regresa al dormitorio para recuperarte.';}
    return (missed?'El rival esquivó. ':'')+'Daño directo: '+dealt.toString()+' · daño recibido: '+hit.toString()+note;
  }
  Map<String,dynamic> toJson()=>{'cash':cash,'stock':stock,'inventoryCost':inventoryCost,'day':day,'xp':xp,'strength':strength,'defense':defense,'stamina':stamina,'intelligence':intelligence,'rankPoints':rankPoints,'chapter':chapter,'hp':hp,'energy':energy,'mana':mana,'enemyHp':enemyHp,'turn':turn,'enemyIndex':enemyIndex,'guardPower':guardPower,'guardTurns':guardTurns,'speedPower':speedPower,'speedTurns':speedTurns,'enemyWeakTurns':enemyWeakTurns,'enemyBleedTurns':enemyBleedTurns,'enemyBleedPower':enemyBleedPower,'enemyGuard':enemyGuard,'enemyEvade':enemyEvade,'world':world,'place':place,'workoutDate':workoutDate,'skills':skills.toList(),'appraised':appraised.toList(),'readPages':readPages,'grades':grades,'attempts':attempts,'wins':wins.toList(),'reputation':reputation,'trust':trust,'affection':affection,'decisions':decisions,'flags':flags.toList(),'pendingDuel':pendingDuel,'lastEvent':lastEvent,'spirits':spirits.toList(),'deadStudents':deadStudents.toList(),'rescuedStudents':rescuedStudents.toList(),'knownRaces':knownRaces.toList(),'rumors':rumors.toList(),'rescueMissions':rescueMissions,'activeSpirit':activeSpirit,'lethalBattle':lethalBattle,'returned':returned};
  factory DualState.fromJson(Map j){final s=DualState();int n(String k,int fallback)=>j[k] is int?j[k] as int:fallback;
    s.cash=n('cash',0);s.stock=n('stock',0);s.inventoryCost=n('inventoryCost',0);s.day=n('day',0);s.xp=n('xp',0);s.strength=n('strength',4);s.defense=n('defense',3);s.stamina=n('stamina',10);s.intelligence=n('intelligence',5);s.rankPoints=n('rankPoints',0);s.chapter=n('chapter',0);s.hp=n('hp',40);s.energy=n('energy',10);s.mana=n('mana',5);s.enemyHp=n('enemyHp',0);s.turn=n('turn',0);s.enemyIndex=n('enemyIndex',-1);s.guardPower=n('guardPower',0);s.guardTurns=n('guardTurns',0);s.speedPower=n('speedPower',0);s.speedTurns=n('speedTurns',0);s.enemyWeakTurns=n('enemyWeakTurns',0);s.enemyBleedTurns=n('enemyBleedTurns',0);s.enemyBleedPower=n('enemyBleedPower',0);s.enemyGuard=n('enemyGuard',0);s.enemyEvade=n('enemyEvade',0);s.world=j['world']=='trade'?'trade':'school';s.place=j['place'] is String?j['place'] as String:'Dormitorio';s.workoutDate=j['workoutDate'] is String?j['workoutDate'] as String:'';
    for(final e in [MapEntry('skills',s.skills),MapEntry('appraised',s.appraised),MapEntry('wins',s.wins),MapEntry('flags',s.flags),MapEntry('spirits',s.spirits),MapEntry('deadStudents',s.deadStudents),MapEntry('rescuedStudents',s.rescuedStudents),MapEntry('knownRaces',s.knownRaces),MapEntry('rumors',s.rumors)]){if(j[e.key] is List)e.value.addAll((j[e.key] as List).whereType<String>());}
    for(final e in [MapEntry('readPages',s.readPages),MapEntry('grades',s.grades),MapEntry('attempts',s.attempts),MapEntry('trust',s.trust),MapEntry('affection',s.affection)]){if(j[e.key] is Map)for(final item in (j[e.key] as Map).entries){if(item.key is String&&item.value is int)e.value[item.key as String]=item.value as int;}}
    s.lethalBattle=j['lethalBattle']==true;s.returned=j['returned']==true;s.activeSpirit=j['activeSpirit'] is String?j['activeSpirit'] as String:'';if(j['rescueMissions'] is Map)for(final e in (j['rescueMissions'] as Map).entries){if(e.key is String&&e.value is String)s.rescueMissions[e.key as String]=e.value as String;}s.skills.remove('strike');s.reputation=n('reputation',-30);s.pendingDuel=j['pendingDuel'] is String?j['pendingDuel'] as String:'';s.lastEvent=j['lastEvent'] is String?j['lastEvent'] as String:'';if(j['decisions'] is Map)for(final e in (j['decisions'] as Map).entries){if(e.key is String&&e.value is String)s.decisions[e.key as String]=e.value as String;}return s;
  }
  DualState();
}
