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
  String activeSpirit='',spiritElement='neutral',spiritMode='loan',lastElement='neutral',enemyLastElement='neutral';
  int spiritReserve=0,spiritMax=0,spiritPower=0,enemyEnergy=-1;
  final Map<String,int> playerStates={},enemyStates={};
  static int stat(Map m,String k,int fallback)=>m[k] is num?(m[k] as num).round():fallback;
  static int baseMiss(int evasion)=> (2+max(0,evasion)).clamp(2,60).toInt();
  static int criticalChance(Map sk)=> (stat(sk,'critChance',5)+max(0,stat(sk,'precision',95)-80)~/3).clamp(0,65).toInt();
  static int skillCost(Map sk)=>max(1,stat(sk,'cost',1));
  static int intelligenceRequired(Map sk)=>sk['magic']==true?max(0,stat(sk,'minIntelligence',max(1,rankIndex(sk['rank'])*5))):max(0,stat(sk,'minIntelligence',0));
  bool usable(Map sk)=>energy>=skillCost(sk)&&intelligence>=intelligenceRequired(sk)&&!(playerStates.containsKey('silence')&&sk['magic']==true);
  static String defaultStatus(String element)=>const {'fire':'burn','lightning':'paralysis','poison':'poison','ice':'freeze','water':'wet','blood':'bleed','dark':'blind','dream':'sleep','gravity':'immobilize','nature':'poison'}[element]??'';
  static int statusChance(Map sk,int synergy)=> (stat(sk,'statusChance',20)+synergy*8).clamp(0,85).toInt();
  static int synergy(String element,String previous,String spirit)=>element=='neutral'?0:(element==previous?1:0)+(element==spirit?1:0);
  static bool reaction(String a,String b)=>a!='neutral'&&b!='neutral'&&const ['water:lightning','lightning:water','water:ice','ice:water','fire:wind','wind:fire','gravity:earth','earth:gravity','poison:blood','blood:poison','light:dark','dark:light','space:gravity','gravity:space'].contains('$a:$b');
  int resistanceTo(String element,Map resistances)=> (stat(resistances,element,0)+(element!='neutral'&&element==spiritElement?3:0)).clamp(0,80).toInt();
  bool bindCombatSpirit(Map sp,String mode){
    if(inBattle||!spirits.contains(sp['id'])||!const ['loan','manifest','fusion','enchant'].contains(mode)||mode=='enchant'&&equippedWeapon.isEmpty)return false;
    activeSpirit=sp['id'].toString();spiritElement=sp['element']?.toString()??'neutral';spiritMode=mode;
    spiritPower=max(1,stat(sp,'damage',5));spiritMax=max(1,stat(sp,'stamina',max(5,stat(sp,'intelligence',5)~/2)));spiritReserve=spiritMax;return true;
  }
  void clearCombatSpirit(){if(inBattle)return;activeSpirit='';spiritElement='neutral';spiritMode='loan';spiritPower=0;spiritMax=0;spiritReserve=0;}
  static void tickStates(Map<String,int> states){for(final k in states.keys.toList()){if(states[k]!<=1){states.remove(k);}else{states[k]=states[k]!-1;}}}
  static bool unableToAct(Map<String,int> states,Random rng)=>states.containsKey('sleep')||states.containsKey('freeze')||states.containsKey('stun')||states.containsKey('paralysis')&&rng.nextInt(100)<25;
  static int periodicDamage(Map<String,int> states,int maxHealth)=>['burn','poison','bleed','curse'].where(states.containsKey).length*max(1,maxHealth~/20);
  static String applyState(Map sk,String element,Map<String,int> target,int boost,Random rng,{int resistance=0}){
    final name=sk['status']?.toString()??defaultStatus(element);
    if(name.isEmpty||rng.nextInt(100)>=max(0,statusChance(sk,boost)-resistance))return '';
    target[name]=max(target[name]??0,max(1,stat(sk,'statusTurns',2)));return ' · Estado: $name';
  }
  String exhaustion(){enemyIndex=-1;lethalBattle=false;return 'Derrota por agotamiento. El rival sigue en pie.';}
  static int enemyMaxEnergy(Map enemy)=>max(1,stat(enemy,'stamina',10+max(1,stat(enemy,'level',1))*5));

  bool returned=false;
  bool lethalBattle=false;
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
  static const commonElements=['fire','water','earth','wind','lightning','ice','light','dark','nature','blood','metal','astral'];
  static String combatRank(Map person,int completed){final initial=powerRanks.indexOf(person['initialRank']?.toString()??'E'),potential=powerRanks.indexOf(person['potentialRank']?.toString()??'E');final start=max(0,initial),end=max(start,potential);return powerRanks[min(end,start+max(0,completed)~/3)];}
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
  Map<String,dynamic> effectiveTechnique(Map sk){final delta=techniqueTier(sk)-rankIndex(sk['rank']);final uses=skillUses[sk['id']]??0;return {...Map<String,dynamic>.from(sk),'rank':powerRanks[techniqueTier(sk)],'damage':((sk['damage'] as int?)??0)+delta*max(3,((sk['damage'] as int?)??0)~/2)+min(5,uses~/10),'cost':((sk['cost'] as int?)??1)+delta,'effectTurns':((sk['effectTurns'] as int?)??2)+delta~/2,'statusChance':min(85,stat(sk,'statusChance',20)+delta*3),'critChance':min(65,stat(sk,'critChance',5)+delta*2),'precision':min(100,stat(sk,'precision',95)+delta),'statusTurns':stat(sk,'statusTurns',2)+delta~/3};}
  String fusionKey(Map a,Map b){final ids=[a['id'].toString(),b['id'].toString()]..sort();return 'fusion_'+ids.join('__');}
  bool compatibleFusion(Map a,Map b)=>a['id']!=b['id']&&a['type']==b['type']&&a['magic']==b['magic']&&(a['element']==null||b['element']==null||a['element']==b['element'])&&a['copyable']!=false&&b['copyable']!=false&&(a['specialEffect']==null||b['specialEffect']==null||a['specialEffect']==b['specialEffect'])&&!a['id'].toString().startsWith('fusion_')&&!b['id'].toString().startsWith('fusion_');
  static const fusionIntelligence=[0,30,60,100,150,220,320,450];
  int fusionTier(Map a,Map b)=>min(7,max(techniqueTier(a),techniqueTier(b))+1);
  int fusionMinimum(Map a,Map b)=>fusionIntelligence[fusionTier(a,b)];
  int fusionChance(Map a,Map b){final minimum=fusionMinimum(a,b);if(intelligence<minimum||!compatibleFusion(a,b))return 0;return min(100,25+(intelligence-minimum)*75~/max(30,minimum));}
  int fusionFee(Map a,Map b)=>max(500,appraisalFees[min(7,max(techniqueTier(a),techniqueTier(b))+1)]);
  bool fuse(Map a,Map b,{Random? random}){final id=fusionKey(a,b),tier=min(7,max(techniqueTier(a),techniqueTier(b))+1);if(inBattle||world!='school'||place!='Dormitorio'||!skills.contains(a['id'])||!skills.contains(b['id'])||!compatibleFusion(a,b)||fusedSkills.containsKey(id)||cash<fusionFee(a,b)||fusionChance(a,b)==0)return false;final x=effectiveTechnique(a),y=effectiveTechnique(b);cash-=fusionFee(a,b);fusionAttempts[id]=(fusionAttempts[id]??0)+1;if((random??Random()).nextInt(100)>=fusionChance(a,b))return false;fusedSkills[id]={'id':id,'name':a['name'].toString()+' × '+b['name'].toString(),'rank':powerRanks[tier],'type':a['type'],'magic':a['magic'],'element':a['element']??b['element'],'specialEffect':a['specialEffect']??b['specialEffect'],'status':a['status']??b['status'],'statusChance':min(85,max(stat(x,'statusChance',20),stat(y,'statusChance',20))+8),'precision':max(stat(x,'precision',95),stat(y,'precision',95)),'critChance':min(65,max(stat(x,'critChance',5),stat(y,'critChance',5))+3),'minIntelligence':max(intelligenceRequired(a),intelligenceRequired(b)),'damage':((x['damage'] as int)+(y['damage'] as int))*3~/4,'cost':max(x['cost'] as int,y['cost'] as int)+1};skills.add(id);return true;}
  bool acquireRankedSkill(Map skill){if(skill['copyable']==false||!canAppraise(skill))return false;if(skill['element']=='divine'&&!flags.contains('divine_devotion'))return false;final id=skill['id'] as String;if((appraisedRanks[id]??rankIndex(skill['rank']))<rankIndex(skill['rank']))return false;if(!buySkill(id,skill['price'] as int))return false;copiedSkills[id]=Map<String,dynamic>.from(skill);return true;}
  bool buyWeapon(Map w){if(inBattle||world!='trade'||place!='Armería'||weapons.contains(w['id'])||grades.length<((w['minClasses'] as int?)??0)||w['requiresWin'] is String&&!wins.contains('battle_'+w['requiresWin'].toString()))return false;final price=w['price'] as int;if(price<=0||cash<price)return false;cash-=price;weapons.add(w['id'] as String);return true;}
  bool equipWeapon(Map w){if(inBattle||world!='school'||place!='Dormitorio'||!weapons.contains(w['id'])||strength<(w['minStrength'] as int)||intelligence<(w['minIntelligence'] as int))return false;equippedWeapon=w['id'] as String;weaponElement=w['element']?.toString()??'neutral';weaponStrength=w['strengthBonus'] as int;weaponMagic=w['magicBonus'] as int;weaponDefense=w['defenseBonus'] as int;return true;}
  void unequipWeapon(){if(inBattle)return;equippedWeapon='';weaponElement='neutral';weaponStrength=0;weaponMagic=0;weaponDefense=0;}
  int spiritChance(Map spirit,int affinity){if(!canCapture(spirit)||affinity<((spirit['minAffinity'] as int?)??25))return 0;return (20+affinity~/2+(intelligence-(spirit['intelligence'] as int))*2).clamp(5,100).toInt();}
  bool freshSpiritAttempt(Map spirit){final encounter=spirit['requiresWin']?.toString()??'';final count=battleCounts[encounter]??(wins.contains('battle_'+encounter)?1:0);return count>(spiritAttempts[spirit['id']]??0);}
  String trySpirit(Map spirit,int affinity){final chance=spiritChance(spirit,affinity);if(chance==0||!freshSpiritAttempt(spirit))return 'Necesitas afinidad, inteligencia o superar de nuevo su encuentro.';final encounter=spirit['requiresWin']?.toString()??'',id=spirit['id'] as String;spiritAttempts[id]=battleCounts[encounter]??1;if(Random().nextInt(100)>=chance)return 'El espíritu no acepta el vínculo. Supera de nuevo el encuentro para intentar otra vez.';spirits.add(id);return 'Espíritu vinculado.';}
  int victoryXp(Map enemy,bool first){if(enemy['repeatable']==true){final l=(enemy['level'] as int?)??1;return 20+15*l*l+((enemy['hp'] as int?)??0)~/10;}return first?((enemy['xp'] as int?)??0):0;}
  DualState returnToBeginning(){final next=DualState();next.intelligence=intelligence;next.mana=intelligence;next.readPages.addAll(readPages);next.readingLog.addAll(readingLog.map((k,v)=>MapEntry(k,Map<String,dynamic>.from(v))));next.readingRemainder=readingRemainder;next.workoutDate=workoutDate;next.returned=false;return next;}
  int get level=>1+xp~/100;
  int get maxHp=>40+(level-1)*5;
  String get playerCombatRank{final score=strength+defense+stamina+(level-1)*8+skills.length*3+spirits.length*5;return score>=1000?'SSS':score>=650?'SS':score>=400?'S':score>=250?'A':score>=140?'B':score>=75?'C':score>=35?'D':'E';}
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
  int rewardExam(String id,bool correct){if(grades.containsKey(id))return grades[id]!;attempts[id]=(attempts[id]??0)+1;if(!correct)return 0;final grade=max(60,100-10*((attempts[id]??1)-1));grades[id]=grade;rankPoints+=grade;reputation=min(100,reputation+max(1,grade~/20));xp+=30;return grade;}
  int claimGuild(String id){final grade=grades[id];if(grade==null||!wins.add('guild_'+id))return 0;cash+=grade;return grade;}
  bool buySkill(String id,int price){if(!privatePlace||world!='school'||!appraised.contains(id)||skills.contains(id)||cash<price||price<=0)return false;cash-=price;skills.add(id);return true;}
  int commission(){final id='commission_'+day.toString();if(wins.contains(id))return 0;wins.add(id);cash+=30;day++;return 30;}
  Map<String,int>? trade(int qty,int price,int demand,int cost,int fixed){if(qty<0||qty>100||price<1||price>100||demand<0||cost<=0||fixed<0||cash<qty*cost+fixed||qty+stock<=0)return null;final total=stock+qty,combined=inventoryCost+qty*cost;final sold=min(total,demand);final cogs=(combined*sold/total).round();final revenue=sold*price;cash+=revenue-qty*cost-fixed;stock=total-sold;inventoryCost=combined-cogs;day++;return {'sold':sold,'revenue':revenue,'profit':revenue-cogs-fixed,'cash':cash,'stock':stock};}
  void rest(){if(inBattle)return;hp=maxHp;mana=intelligence;energy=stamina;}
  bool startBattle(int i,int health,{bool lethal=false}){if(inBattle||health<1||hp<1)return false;enemyIndex=i;lethalBattle=lethal;enemyHp=health;turn=0;guardPower=0;guardTurns=0;speedPower=0;speedTurns=0;enemyWeakTurns=0;enemyBleedTurns=0;enemyBleedPower=0;enemyGuard=0;enemyEvade=0;enemyGuardTurns=0;enemyEvadeTurns=0;energy=stamina;enemyEnergy=-1;spiritReserve=spiritMax;lastElement='neutral';enemyLastElement='neutral';playerStates.clear();enemyStates.clear();return true;}
  String action(Map skill,Map enemy,{List<Map<String,dynamic>>? available}){
    if(!inBattle)return 'No hay combate.';
    if(!skills.contains(skill['id'])&&!(skill['spirit'] is String&&spirits.contains(skill['spirit'])))return 'Aún no has adquirido esta técnica.';
    final cost=skillCost(skill),magic=skill['magic']==true;
    if(intelligence<intelligenceRequired(skill))return 'Inteligencia insuficiente para esta técnica.';
    if(!usable(skill))return 'No puedes usar esta técnica por estamina o estado.';
    if(enemyEnergy<0)enemyEnergy=enemyMaxEnergy(enemy);
    energy-=cost;
    final rng=Random();
    final playerBlocked=unableToAct(playerStates,rng);
    final element=(!magic&&spiritMode=='enchant'&&equippedWeapon.isNotEmpty&&skill['element']==null)?spiritElement:(skill['element']?.toString()??'neutral');
    final boost=synergy(element,lastElement,spiritElement)+(reaction(element,lastElement)?1:0);
    final playerStatusNote=<String>[];
    if(playerBlocked)playerStatusNote.add('No pudiste actuar por un estado.');
    final kind=skill['type'] as String;final special=skill['specialEffect'];final damage=skill['damage'] as int;final duration=(skill['effectTurns'] as int?)??2;if(skills.contains(skill['id'])){final id=skill['id'] as String;skillUses[id]=(skillUses[id]??0)+1;}
    if(!playerBlocked){if(kind=='defense'){guardPower=damage;guardTurns=duration+1;}
    if(kind=='speed'){speedPower=damage;speedTurns=duration+1;}
    if(kind=='heal'){hp=min(maxHp,hp+damage);}
    if(kind=='hypnosis'||kind=='seal'){enemyWeakTurns=max(enemyWeakTurns,duration);}
    if(kind=='void'){enemyGuard=0;enemyEvade=0;enemyGuardTurns=0;enemyEvadeTurns=0;enemyWeakTurns=max(enemyWeakTurns,2);}
    }
    final guard=guardTurns>0?guardPower:0,evade=speedTurns>0?speedPower:0;
    final offensive=const ['attack','drain','bleed','void'].contains(kind);
    final missed=offensive&&!playerBlocked&&rng.nextInt(100)<baseMiss(stat(enemy,'evasion',0)+enemyEvade+(playerStates.containsKey('blind')?12:0));
    final critical=offensive&&!missed&&!playerBlocked&&rng.nextInt(100)<criticalChance(skill);
    final defenseFactor=special=='space'?2:1;
    var dealt=offensive&&!missed&&!playerBlocked?max(1,damage+(magic?intelligence+((weaponElement=='neutral'||weaponElement==skill['element'])?weaponMagic:weaponMagic~/2):strength+weaponStrength)~/2-(kind=='void'?0:(enemy['defense'] as int)~/defenseFactor)-(special=='sound'?enemyGuard~/2:enemyGuard)):0;
    if(dealt>0){dealt=dealt*(100+boost*8)~/100;if(critical){dealt=dealt*max(100,stat(skill,'critDamage',150))~/100;playerStatusNote.add('Golpe crítico');}if(playerStates.containsKey('burn')&&!magic)dealt=max(1,dealt*85~/100);final resist=enemy['resistances'] is Map?enemy['resistances'] as Map:const {};dealt=max(1,dealt*(100-stat(resist,element,0).clamp(0,80).toInt())~/100);playerStatusNote.add(applyState(skill,element,enemyStates,boost,rng,resistance:stat(enemy,'statusResistance',0)));lastElement=element;}
    if(!playerBlocked&&spiritMode=='fusion'&&spiritReserve>0&&dealt>0){spiritReserve--;dealt+=max(1,dealt~/10);}
    if(!playerBlocked&&spiritMode=='manifest'&&spiritReserve>=2){spiritReserve-=2;dealt+=max(1,spiritPower~/3);playerStatusNote.add(applyState(const {},spiritElement,enemyStates,synergy(spiritElement,element,spiritElement),rng));}
    if(enemyGuardTurns>0&&--enemyGuardTurns==0)enemyGuard=0;if(enemyEvadeTurns>0&&--enemyEvadeTurns==0)enemyEvade=0;
    enemyHp=max(0,enemyHp-dealt);
    if(dealt>0){if(special=='gravity'){enemyEvade=0;enemyEvadeTurns=0;enemyWeakTurns=max(enemyWeakTurns,duration);}if(special=='sound'||special=='magnetism'){enemyGuard=0;enemyGuardTurns=0;}}
    if(!playerBlocked&&special=='tempo'){enemyWeakTurns=max(enemyWeakTurns,duration+1);speedPower=max(speedPower,5);speedTurns=max(speedTurns,duration+1);}
    if(!playerBlocked&&special=='dream'){enemyWeakTurns=max(enemyWeakTurns,duration+1);}
    if(!playerBlocked&&special=='crystal'){guardPower=max(guardPower,damage);guardTurns=max(guardTurns,duration+2);}
    if(kind=='drain'&&dealt>0)hp=min(maxHp,hp+max(1,dealt~/3));
    if(kind=='bleed'&&dealt>0){enemyBleedPower=max(1,damage~/4);enemyBleedTurns=duration;}
    if(enemyBleedTurns>0){enemyHp=max(0,enemyHp-enemyBleedPower);enemyBleedTurns--;}
    enemyHp=max(0,enemyHp-periodicDamage(enemyStates,stat(enemy,'hp',1)));
    turn++;
    if(enemyHp==0){final key=enemy['id'] as String;final first=wins.add('battle_'+key);final earned=victoryXp(enemy,first);xp+=earned;battleCounts[key]=(battleCounts[key]??(first?0:1))+1;rankPoints+=first?25:0;if(first)reputation=min(100,reputation+8);if(pendingDuel==key)pendingDuel='';for(final id in rescueMissions.keys.where((id)=>rescueMissions[id]==key).toList()){if(!deadStudents.contains(id)){rescuedStudents.add(id);trust[id]=(relationship(id)+15).clamp(-100,100).toInt();}rescueMissions.remove(id);}enemyIndex=-1;lethalBattle=false;return 'Victoria. +'+earned.toString()+' XP. '+(first?'Reputación y ranking aumentados.':earned>0?'Experiencia de monstruo.':'Práctica sin recompensa repetida.');}
    if(energy==0||available!=null&&!available.any((sk)=>energy>=skillCost(sk)&&intelligence>=intelligenceRequired(sk)))return exhaustion();
    final choices=(enemy['techniques'] is List?(enemy['techniques'] as List).whereType<Map>().toList():<Map>[]);
    Map? move;final affordable=choices.where((sk)=>skillCost(sk)<=enemyEnergy).toList();if(affordable.isNotEmpty&&turn%2==0)move=affordable[(turn~/2-1)%affordable.length];
    final rivalCost=move==null?1:skillCost(move);if(enemyEnergy<rivalCost){enemyHp=0;return _exhaustedEnemy(enemy);}enemyEnergy-=rivalCost;
    final enemyBlocked=unableToAct(enemyStates,rng);
    final enemyType=move?['type'];final enemySpecial=move?['specialEffect'];final enemyPower=((move?['damage'] as int?)??0)*((move?['mastery'] as int?)??100)~/100;
    final enemyDuration=(move?['effectTurns'] as int?)??2;
    int enemyAttack=(enemy['attack'] as int)+(turn%3==0?4:0);
    String note='';
    if(move!=null&&!enemyBlocked){note=' · Rival: '+move['name'].toString();
      if(enemyType=='defense'){enemyGuard=min(30,enemyPower~/2);enemyGuardTurns=enemyDuration;enemyAttack=0;}
      else if(enemyType=='speed'){enemyEvade=min(30,enemyPower);enemyEvadeTurns=enemyDuration;enemyAttack=0;}
      else if(enemyType=='heal'){enemyHp=min(enemy['hp'] as int,enemyHp+min(35,enemyPower~/2));enemyAttack=0;}
      else if(enemyType=='void'){guardPower=0;guardTurns=0;speedPower=0;speedTurns=0;enemyAttack+=min(12,enemyPower~/4);note+=' · tu guardia se disipa';}
      else if(enemyType=='hypnosis'||enemyType=='seal'){enemyAttack=max(1,enemyAttack~/2);playerStates['silence']=max(playerStates['silence']??0,enemyDuration);note+=' · silencio mágico';}
      else {enemyAttack+=min(20,enemyPower~/5)+(move['magic']==true?((enemy['spellPower'] as int?)??0):0);}
    }
    if(move!=null&&!enemyBlocked){if(enemySpecial=='gravity'){speedPower=0;speedTurns=0;enemyAttack+=min(8,enemyPower~/6);note+=' · presión gravitatoria';}else if(enemySpecial=='space'){note+=' · distorsión espacial';}else if(enemySpecial=='sound'||enemySpecial=='magnetism'){guardPower=0;guardTurns=0;note+=' · guardia quebrada';}else if(enemySpecial=='tempo'){energy=max(0,energy-2);note+=' · ritmo alterado';}else if(enemySpecial=='dream'){playerStates['sleep']=max(playerStates['sleep']??0,2);note+=' · somnolencia mágica';}else if(enemySpecial=='crystal'){enemyGuard=max(enemyGuard,min(30,enemyPower~/2));enemyGuardTurns=max(enemyGuardTurns,enemyDuration+1);}else if(enemySpecial=='entropy'){enemyAttack+=min(8,enemyPower~/5);note+=' · desgaste';}}
    if(enemyWeakTurns>0){enemyAttack=enemyAttack~/2;enemyWeakTurns--;}
    final enemyElement=move?['element']?.toString()??'neutral';final enemyBoost=synergy(enemyElement,enemyLastElement,move?['spiritElement']?.toString()??'neutral')+(reaction(enemyElement,enemyLastElement)?1:0);
    var hit=enemyBlocked||enemyAttack<=0||rng.nextInt(100)<baseMiss((enemySpecial=='gravity'?0:evade)*3+(enemyStates.containsKey('blind')?12:0))?0:max(1,enemyAttack-(defense+weaponDefense)~/2-(enemyType=='void'||enemySpecial=='sound'||enemySpecial=='magnetism'?0:enemySpecial=='space'?guard~/2:guard));
    if(hit>0){hit=hit*(100+enemyBoost*8)~/100;if(rng.nextInt(100)<criticalChance(move??const {})){hit=hit*max(100,stat(move??const {},'critDamage',150))~/100;note+=' · crítico rival';}if(enemyStates.containsKey('burn')&&move?['magic']!=true)hit=max(1,hit*85~/100);hit=max(1,hit*(100-resistanceTo(enemyElement,const {}))~/100);note+=applyState(move??const {},enemyElement,playerStates,enemyBoost,rng);enemyLastElement=enemyElement;}
    if(guardTurns>0)guardTurns--;if(speedTurns>0)speedTurns--;
    hp=max(0,hp-hit-periodicDamage(playerStates,maxHp));tickStates(playerStates);tickStates(enemyStates);
    if(hit>0&&(((enemy['lifesteal'] as int?)??0)>0||enemyType=='drain'))enemyHp=min(enemy['hp'] as int,enemyHp+min(3,hit));
    final regen=(enemy['regen'] as int?)??0;
    if(regen>0&&turn%3==0)enemyHp=min(enemy['hp'] as int,enemyHp+regen);
    if(hp==0){enemyIndex=-1;if(lethalBattle){returned=true;return 'Tu vida terminó. Retorno se activa.';}return 'Derrota en un duelo protegido. Regresa al dormitorio para recuperarte.';}
    if(enemyEnergy==0)return _exhaustedEnemy(enemy);
    if(energy==0||available!=null&&!available.any((sk)=>energy>=skillCost(sk)&&intelligence>=intelligenceRequired(sk)))return exhaustion();
    return playerStatusNote.where((x)=>x.isNotEmpty).join(' · ')+' '+(missed?'El rival esquivó. ':'')+'Daño directo: '+dealt.toString()+' · daño recibido: '+hit.toString()+note;
  }
  String _exhaustedEnemy(Map enemy){final key=enemy['id'] as String;final first=wins.add('battle_'+key);final earned=victoryXp(enemy,first);xp+=earned;battleCounts[key]=(battleCounts[key]??(first?0:1))+1;rankPoints+=first?25:0;if(first)reputation=min(100,reputation+8);if(pendingDuel==key)pendingDuel='';for(final id in rescueMissions.keys.where((id)=>rescueMissions[id]==key).toList()){if(!deadStudents.contains(id)){rescuedStudents.add(id);trust[id]=(relationship(id)+15).clamp(-100,100).toInt();}rescueMissions.remove(id);}enemyIndex=-1;lethalBattle=false;return 'Victoria por agotamiento rival. +'+earned.toString()+' XP. '+(first?'Reputación y ranking aumentados.':earned>0?'Experiencia de monstruo.':'Práctica sin recompensa repetida.');}
  Map<String,dynamic> toJson()=>{'cash':cash,'stock':stock,'inventoryCost':inventoryCost,'day':day,'xp':xp,'strength':strength,'defense':defense,'stamina':stamina,'intelligence':intelligence,'rankPoints':rankPoints,'chapter':chapter,'hp':hp,'energy':energy,'mana':mana,'enemyHp':enemyHp,'turn':turn,'enemyIndex':enemyIndex,'guardPower':guardPower,'guardTurns':guardTurns,'speedPower':speedPower,'speedTurns':speedTurns,'enemyWeakTurns':enemyWeakTurns,'enemyBleedTurns':enemyBleedTurns,'enemyBleedPower':enemyBleedPower,'enemyGuard':enemyGuard,'enemyEvade':enemyEvade,'enemyGuardTurns':enemyGuardTurns,'enemyEvadeTurns':enemyEvadeTurns,'world':world,'place':place,'workoutDate':workoutDate,'skills':skills.toList(),'appraised':appraised.toList(),'readPages':readPages,'grades':grades,'attempts':attempts,'wins':wins.toList(),'reputation':reputation,'trust':trust,'affection':affection,'decisions':decisions,'flags':flags.toList(),'pendingDuel':pendingDuel,'lastEvent':lastEvent,'spirits':spirits.toList(),'deadStudents':deadStudents.toList(),'rescuedStudents':rescuedStudents.toList(),'knownRaces':knownRaces.toList(),'rumors':rumors.toList(),'rescueMissions':rescueMissions,'activeSpirit':activeSpirit,'spiritElement':spiritElement,'spiritMode':spiritMode,'spiritReserve':spiritReserve,'spiritMax':spiritMax,'spiritPower':spiritPower,'enemyEnergy':enemyEnergy,'lastElement':lastElement,'enemyLastElement':enemyLastElement,'playerStates':playerStates,'enemyStates':enemyStates,'lethalBattle':lethalBattle,'returned':returned,'readingLog':readingLog,'readingRemainder':readingRemainder,'battleCounts':battleCounts,'spiritAttempts':spiritAttempts,'factionStanding':factionStanding,'weapons':weapons.toList(),'equippedWeapon':equippedWeapon,'weaponElement':weaponElement,'weaponStrength':weaponStrength,'weaponMagic':weaponMagic,'weaponDefense':weaponDefense,'appraisalRefinement':appraisalRefinement,'skillUpgrades':skillUpgrades,'skillUses':skillUses,'fusedSkills':fusedSkills,'copiedSkills':copiedSkills,'appraisedRanks':appraisedRanks,'fusionAttempts':fusionAttempts,'economy':economy.toJson()};
  factory DualState.fromJson(Map j){final s=DualState();if(j['economy'] is Map)s.economy=LumenEconomy.fromJson(j['economy'] as Map);int n(String k,int fallback)=>j[k] is int?j[k] as int:fallback;
    s.cash=n('cash',0);s.stock=n('stock',0);s.inventoryCost=n('inventoryCost',0);s.day=n('day',0);s.xp=n('xp',0);s.strength=n('strength',4);s.defense=n('defense',3);s.stamina=n('stamina',10);s.intelligence=n('intelligence',5);s.rankPoints=n('rankPoints',0);s.chapter=n('chapter',0);s.hp=n('hp',40);s.energy=n('energy',10);s.mana=n('mana',5);s.enemyHp=n('enemyHp',0);s.turn=n('turn',0);s.enemyIndex=n('enemyIndex',-1);s.guardPower=n('guardPower',0);s.guardTurns=n('guardTurns',0);s.speedPower=n('speedPower',0);s.speedTurns=n('speedTurns',0);s.enemyWeakTurns=n('enemyWeakTurns',0);s.enemyBleedTurns=n('enemyBleedTurns',0);s.enemyBleedPower=n('enemyBleedPower',0);s.enemyGuard=n('enemyGuard',0);s.enemyEvade=n('enemyEvade',0);s.enemyGuardTurns=n('enemyGuardTurns',s.enemyGuard>0?1:0);s.enemyEvadeTurns=n('enemyEvadeTurns',s.enemyEvade>0?1:0);s.world=j['world']=='trade'?'trade':'school';s.place=j['place'] is String?j['place'] as String:'Dormitorio';s.workoutDate=j['workoutDate'] is String?j['workoutDate'] as String:'';
    for(final e in [MapEntry('skills',s.skills),MapEntry('weapons',s.weapons),MapEntry('appraised',s.appraised),MapEntry('wins',s.wins),MapEntry('flags',s.flags),MapEntry('spirits',s.spirits),MapEntry('deadStudents',s.deadStudents),MapEntry('rescuedStudents',s.rescuedStudents),MapEntry('knownRaces',s.knownRaces),MapEntry('rumors',s.rumors)]){if(j[e.key] is List)e.value.addAll((j[e.key] as List).whereType<String>());}
    for(final e in [MapEntry('readPages',s.readPages),MapEntry('grades',s.grades),MapEntry('attempts',s.attempts),MapEntry('trust',s.trust),MapEntry('affection',s.affection),MapEntry('battleCounts',s.battleCounts),MapEntry('spiritAttempts',s.spiritAttempts),MapEntry('factionStanding',s.factionStanding),MapEntry('skillUpgrades',s.skillUpgrades),MapEntry('skillUses',s.skillUses),MapEntry('appraisedRanks',s.appraisedRanks),MapEntry('fusionAttempts',s.fusionAttempts)]){if(j[e.key] is Map)for(final item in (j[e.key] as Map).entries){if(item.key is String&&item.value is int)e.value[item.key as String]=item.value as int;}}
    s.readingRemainder=n('readingRemainder',0).clamp(0,999).toInt();if(j['readingLog'] is Map)for(final item in (j['readingLog'] as Map).entries){if(item.key is String&&item.value is Map){final b=Map<String,dynamic>.from(item.value as Map);if(b['total'] is int&&b['page'] is int&&(b['total'] as int)>0&&(b['page'] as int)>=0&&(b['page'] as int)<=(b['total'] as int))s.readingLog[item.key as String]=b;}}s.lethalBattle=j['lethalBattle']==true;s.returned=j['returned']==true;s.activeSpirit=j['activeSpirit'] is String?j['activeSpirit'] as String:'';s.spiritElement=j['spiritElement']?.toString()??'neutral';s.spiritMode=j['spiritMode']?.toString()??'loan';s.spiritReserve=n('spiritReserve',0);s.spiritMax=n('spiritMax',0);s.spiritPower=n('spiritPower',0);s.enemyEnergy=n('enemyEnergy',-1);s.lastElement=j['lastElement']?.toString()??'neutral';s.enemyLastElement=j['enemyLastElement']?.toString()??'neutral';for(final entry in [MapEntry('playerStates',s.playerStates),MapEntry('enemyStates',s.enemyStates)]){if(j[entry.key] is Map)for(final x in (j[entry.key] as Map).entries){if(x.key is String&&x.value is int&&(x.value as int)>0)entry.value[x.key as String]=x.value as int;}}if(j['rescueMissions'] is Map)for(final e in (j['rescueMissions'] as Map).entries){if(e.key is String&&e.value is String)s.rescueMissions[e.key as String]=e.value as String;}s.appraisalRefinement=n('appraisalRefinement',0).clamp(0,7).toInt();s.equippedWeapon=j['equippedWeapon']?.toString()??'';if(s.weapons.contains(s.equippedWeapon)){s.weaponElement=j['weaponElement']?.toString()??'neutral';s.weaponStrength=max(0,n('weaponStrength',0));s.weaponMagic=max(0,n('weaponMagic',0));s.weaponDefense=max(0,n('weaponDefense',0));}else{s.equippedWeapon='';}if(j['fusedSkills'] is Map)for(final entry in (j['fusedSkills'] as Map).entries){if(entry.key is String&&entry.value is Map)s.fusedSkills[entry.key as String]=Map<String,dynamic>.from(entry.value as Map);}if(j['copiedSkills'] is Map)for(final entry in (j['copiedSkills'] as Map).entries){if(entry.key is String&&entry.value is Map)s.copiedSkills[entry.key as String]=Map<String,dynamic>.from(entry.value as Map);}s.skills.remove('strike');s.reputation=n('reputation',-30);s.pendingDuel=j['pendingDuel'] is String?j['pendingDuel'] as String:'';s.lastEvent=j['lastEvent'] is String?j['lastEvent'] as String:'';if(j['decisions'] is Map)for(final e in (j['decisions'] as Map).entries){if(e.key is String&&e.value is String)s.decisions[e.key as String]=e.value as String;}return s;
  }
  DualState();
}
