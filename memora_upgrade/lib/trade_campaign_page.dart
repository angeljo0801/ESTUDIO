import 'dart:convert';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'models.dart';
import 'nebula_art.dart';
import 'adventure_music.dart';

class TradeChoice {
  const TradeChoice(this.name,this.note,this.fee,this.rep,this.boost);
  final String name,note;
  final int fee,rep,boost;
}
class TradeDay {
  const TradeDay(this.title,this.speaker,this.place,this.biome,this.story,this.cost,this.demand,this.marketPrice,this.rent,this.choices,{this.visual,this.music});
  final String title,speaker,place,biome,story;
  final int cost,demand,marketPrice,rent;
  final List<TradeChoice> choices;
  final AdventureVisualSpec? visual;
  final String? music;
}
class TradeCampaign {
  const TradeCampaign(this.title,this.subtitle,this.intro,this.product,this.version,this.initialCash,this.initialDebt,this.targetCash,this.targetReputation,this.liquidation,this.loanCash,this.loanDebt,this.days);
  final String title,subtitle,intro,product;
  final int version,initialCash,initialDebt,targetCash,targetReputation,liquidation,loanCash,loanDebt;
  final List<TradeDay> days;
  static TradeCampaign? fromGuide(StudyGuide guide) {
    for(final card in guide.cards){
      try{
        final v=jsonDecode(card.adventureStory);
        if(v is! Map || v['kind']!='memora_trade_campaign_v1')continue;
        String str(Map m,String k){final x=m[k];if(x is! String || x.trim().isEmpty || x.length>5000)throw const FormatException('Texto inválido');return x;}
        int num(Map m,String k,int lo,int hi){final x=m[k];if(x is! int || x<lo || x>hi)throw const FormatException('Número inválido');return x;}
        final raw=v['days'];
        if(raw is! List || raw.length<2 || raw.length>30)continue;
        final days=<TradeDay>[];
        for(final d in raw){
          if(d is! Map)throw const FormatException('Jornada inválida');
          final rawChoices=d['choices'];
          if(rawChoices is! List || rawChoices.isEmpty || rawChoices.length>5)throw const FormatException('Decisiones inválidas');
          final choices=<TradeChoice>[];
          for(final c in rawChoices){
            if(c is! Map)throw const FormatException('Decisión inválida');
            choices.add(TradeChoice(str(c,'name'),str(c,'note'),num(c,'fee',0,500),num(c,'rep',-40,40),num(c,'boost',-50,60)));
          }
          days.add(TradeDay(str(d,'title'),str(d,'speaker'),str(d,'place'),str(d,'biome'),str(d,'story'),num(d,'cost',1,100),num(d,'demand',0,100),num(d,'marketPrice',1,100),num(d,'rent',0,300),choices,visual:AdventureVisualSpec.parse(d['visual']),music:d['music'] is String ? d['music'] as String : null));
        }
        return TradeCampaign(str(v,'title'),str(v,'subtitle'),str(v,'intro'),str(v,'product'),num(v,'version',1,100000),num(v,'initialCash',1,10000),num(v,'initialDebt',0,10000),num(v,'targetCash',0,100000),num(v,'targetReputation',0,100),num(v,'liquidation',0,100),num(v,'loanCash',0,1000),num(v,'loanDebt',0,2000),days);
      }catch(_){}
    }
    return null;
  }
}

class TradeLesson {
  const TradeLesson(this.day,this.title,this.mentor,this.teach,this.example,this.question,this.answer,this.choices,this.explanation);
  final int day;
  final String title,mentor,teach,example,question,answer,explanation;
  final List<String> choices;
  static Map<int,TradeLesson> fromGuide(StudyGuide guide,int dayCount){
    final out=<int,TradeLesson>{};
    for(final card in guide.cards){
      try{
        final root=jsonDecode(card.adventureStory);
        if(root is! Map||root['kind']!='memora_trade_lessons_v1'||root['lessons'] is! List)continue;
        for(final item in (root['lessons'] as List).take(30)){
          if(item is! Map)continue;
          final day=item['day'];
          if(day is! int||day<1||day>dayCount||out.containsKey(day))continue;
          String str(String k){final v=item[k];if(v is! String||v.trim().isEmpty||v.length>3000)throw const FormatException('Lección inválida');return v.trim();}
          final raw=item['choices'];
          if(raw is! List)continue;
          final choices=raw.whereType<String>().map((v)=>v.trim()).where((v)=>v.isNotEmpty&&v.length<=300).toSet().toList();
          final answer=str('answer');
          if(choices.length<2||choices.length>6||!choices.contains(answer))continue;
          out[day]=TradeLesson(day,str('title'),str('mentor'),str('teach'),str('example'),str('question'),answer,choices,str('explanation'));
        }
      }catch(_){}
    }
    return out;
  }
}

class TradeState {
  TradeState({required this.cash,required this.debt,required this.seed,this.day=0,this.stock=0,this.inventoryCost=0,this.reputation=40,this.loanUsed=false,this.insolvent=false,this.history=const []});
  final int cash,debt,seed,day,stock,inventoryCost,reputation;
  final bool loanUsed,insolvent;
  final List<Map<String,dynamic>> history;
  Map<String,dynamic> toJson()=>{'cash':cash,'debt':debt,'seed':seed,'day':day,'stock':stock,'inventoryCost':inventoryCost,'reputation':reputation,'loanUsed':loanUsed,'insolvent':insolvent,'history':history};
  factory TradeState.fromJson(Map m)=>TradeState(cash:m['cash'] as int,debt:m['debt'] as int,seed:m['seed'] as int,day:m['day'] as int,stock:m['stock'] as int,inventoryCost:m['inventoryCost'] as int,reputation:m['reputation'] as int,loanUsed:m['loanUsed']==true,insolvent:m['insolvent']==true,history:(m['history'] as List).map((x)=>Map<String,dynamic>.from(x as Map)).toList());
}
class TradeEngine {
  static TradeState start(TradeCampaign c,int seed)=>TradeState(cash:c.initialCash,debt:c.initialDebt,seed:seed);
  static int forecast(TradeState s,TradeDay d,TradeChoice c,int price)=>
    max(0,d.demand+c.boost+(s.reputation-40)~/5+(d.marketPrice-price)*3);
  static TradeState turn(TradeCampaign campaign,TradeState state,{required int choice,required int quantity,required int price,required bool borrow}){
    if(state.insolvent||state.day>=campaign.days.length)throw StateError('Partida terminada');
    final d=campaign.days[state.day],c=d.choices[choice];
    if(quantity<0||quantity>100||price<1||price>200||borrow&&state.loanUsed)throw ArgumentError('Movimiento inválido');
    final credit=borrow?campaign.loanCash:0;
    final expenses=quantity*d.cost+c.fee+d.rent;
    if(expenses>state.cash+credit)throw StateError('No hay efectivo suficiente para este plan.');
    final random=Random(state.seed+state.day*973);
    final demand=max(0,forecast(state,d,c,price)+random.nextInt(9)-4);
    final available=state.stock+quantity;
    final sold=min(available,demand),revenue=sold*price;
    final totalCost=state.inventoryCost+quantity*d.cost;
    final cogs=available==0?0:(totalCost*sold/available).round();
    final remaining=available-sold;
    final rep=(state.reputation+c.rep+(sold>=demand&&demand>0?2:0)-(demand-sold>=10?4:0)).clamp(0,100).toInt();
    final cash=state.cash+credit-expenses+revenue;
    final debt=state.debt+(borrow?campaign.loanDebt:0);
    final row=<String,dynamic>{'day':state.day+1,'title':d.title,'decision':c.name,'price':price,'quantity':quantity,'purchase':quantity*d.cost,'rent':d.rent,'fee':c.fee,'credit':credit,'revenue':revenue,'demand':demand,'sold':sold,'remaining':remaining,'cogs':cogs,'profit':revenue-cogs-d.rent-c.fee,'cash':cash,'debt':debt,'rep':rep,'repChange':rep-state.reputation};
    return TradeState(cash:cash,debt:debt,seed:state.seed,day:state.day+1,stock:remaining,inventoryCost:totalCost-cogs,reputation:rep,loanUsed:state.loanUsed||borrow,history:[...state.history,row]);
  }
  static int finalCash(TradeCampaign c,TradeState s)=>s.cash+s.stock*c.liquidation-s.debt;
  static String ending(TradeCampaign c,TradeState s){
    final cash=finalCash(c,s);
    if(s.insolvent||cash<0)return 'EL GREMIO CAE';
    if(cash>=c.targetCash&&s.reputation>=c.targetReputation)return 'LA CORONA DEL COMERCIO';
    if(cash>=c.targetCash)return 'EL MAGNATE SOLITARIO';
    if(s.reputation>=c.targetReputation)return 'EL PACTO DEL BARRIO';
    return 'UNA SEGUNDA OPORTUNIDAD';
  }
}

class TradeCampaignPage extends StatefulWidget {
  const TradeCampaignPage({super.key,required this.guide,required this.campaign,this.sceneBuilder,this.sideAdventure});
  final StudyGuide guide;
  final TradeCampaign campaign;
  final Widget Function(TradeDay)? sceneBuilder;
  final VoidCallback? sideAdventure;
  @override State<TradeCampaignPage> createState()=>_TradeCampaignPageState();
}
class _TradeCampaignPageState extends State<TradeCampaignPage> {
  TradeCampaign get c=>widget.campaign;
  late TradeState state;
  bool loading=true,busy=false,borrow=false;
  int choice=0,quantity=0,price=1;
  late final Map<int,TradeLesson> lessons;
  Set<int> mastered=<int>{};
  String? feedback;
  bool showingHint=false;
  final Set<int> chapterCases=<int>{};
  String? caseFeedback;
  int get xp=>mastered.length*100;
  TradeLesson? get pendingLesson=>state.day>0&&!mastered.contains(state.day)?lessons[state.day]:null;
  String get masteryKey=>'${key}_mastery';
  String get key=>'memora_trade_${widget.guide.id}_v${c.version}';
  TradeDay get d=>c.days[state.day];
  TradeChoice get action=>d.choices[choice];
  bool get done=>state.insolvent||state.day>=c.days.length;
  int get funds=>state.cash+(borrow?c.loanCash:0);
  int get maxBuy=>min(100,max(0,(funds-d.rent-action.fee)~/d.cost));
  int get outlay=>quantity*d.cost+d.rent+action.fee;
  @override void initState(){super.initState();lessons=TradeLesson.fromGuide(widget.guide,c.days.length);_load();}
  void _resetPlan(){choice=0;borrow=false;quantity=0;price=done?1:d.marketPrice;feedback=null;showingHint=false;caseFeedback=null;}
  Future<void> _load()async{
    final prefs=await SharedPreferences.getInstance();
    TradeState next=TradeEngine.start(c,Random.secure().nextInt(1<<30));
    try{
      final raw=prefs.getString(key);
      if(raw!=null){
        final loaded=TradeState.fromJson(jsonDecode(raw) as Map);
        if(loaded.day>=0&&loaded.day<=c.days.length&&loaded.cash>=0&&loaded.debt>=0&&loaded.stock>=0&&loaded.inventoryCost>=0&&loaded.reputation>=0&&loaded.reputation<=100&&loaded.history.length==loaded.day)next=loaded;
      }
    }catch(_){}
    final learned=(prefs.getStringList(masteryKey)??const <String>[]).map(int.tryParse).whereType<int>().where((n)=>n>0&&n<=next.day&&lessons.containsKey(n)).toSet();
    if(!mounted)return;
    setState((){state=next;mastered=learned;loading=false;_resetPlan();});
  }
  Future<void> _save(TradeState next)async{
    final prefs=await SharedPreferences.getInstance();
    if(!await prefs.setString(key,jsonEncode(next.toJson())))throw StateError('No se pudo guardar la partida.');
  }
  void _adjust(){quantity=min(quantity,maxBuy);}
  Future<void> _play()async{
    if(busy||done||pendingLesson!=null||outlay>funds)return;
    setState(()=>busy=true);
    try{
      final next=TradeEngine.turn(c,state,choice:choice,quantity:quantity,price:price,borrow:borrow);
      await _save(next);
      if(!mounted)return;
      HapticFeedback.mediumImpact();
      setState((){state=next;_resetPlan();});
      await _report(next.history.last);
    }catch(e){
      if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(e.toString())));
    }finally{if(mounted)setState(()=>busy=false);}
  }
  Future<void> _report(Map<String,dynamic> r)=>showDialog<void>(context:context,builder:(ctx)=>AlertDialog(
    title:Text((r['profit'] as int)>=0?'Jornada rentable':'La estrategia perdió dinero'),
    content:SingleChildScrollView(child:Column(crossAxisAlignment:CrossAxisAlignment.start,mainAxisSize:MainAxisSize.min,children:[
      Text(r['title'].toString(),style:const TextStyle(fontWeight:FontWeight.bold)),
      const SizedBox(height:8),
      Text('Compraste ${r['quantity']} · Vendiste ${r['sold']} de ${r['demand']} clientes potenciales.'),
      const Divider(),
      _line('Ingresos',r['revenue'] as int),
      _line('Costo de mercancía vendida',-(r['cogs'] as int)),
      _line('Alquiler y decisión',-(r['rent'] as int)-(r['fee'] as int)),
      _line('Beneficio operativo',r['profit'] as int),
      const Divider(),
      _line('Efectivo final',r['cash'] as int),
      Text('Inventario restante: ${r['remaining']} · Reputación: ${r['rep']}'),
      const SizedBox(height:10),
      const Text('El beneficio resta el costo de las unidades vendidas. La caja también paga compras que aún no vendiste. Un préstamo aumenta el efectivo, pero no es una ganancia.'),
    ])),
    actions:[FilledButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Continuar'))],
  ));
  Future<void> _restart()async{
    if(busy)return;
    final yes=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:const Text('¿Iniciar una nueva partida?'),content:const Text('Se reiniciará esta campaña. Tus guías y tarjetas de estudio permanecerán intactas.'),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Cancelar')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Reiniciar'))]));
    if(yes!=true||!mounted)return;
    setState(()=>busy=true);
    try{final next=TradeEngine.start(c,Random.secure().nextInt(1<<30));await _save(next);final prefs=await SharedPreferences.getInstance();await prefs.remove(masteryKey);if(mounted)setState((){state=next;mastered.clear();chapterCases.clear();_resetPlan();});}finally{if(mounted)setState(()=>busy=false);}
  }
  Future<void> _insolvent()async{
    if(busy||done)return;
    setState(()=>busy=true);
    try{
      final next=TradeState(cash:state.cash,debt:state.debt,seed:state.seed,day:state.day,stock:state.stock,inventoryCost:state.inventoryCost,reputation:state.reputation,loanUsed:state.loanUsed,insolvent:true,history:state.history);
      await _save(next);if(mounted)setState(()=>state=next);
    }finally{if(mounted)setState(()=>busy=false);}
  }

  String get arc {
    final n=min(c.days.length,max(1,state.day+(pendingLesson==null?1:0)));
    if(n<=6)return 'ARCO I · El aprendiz';
    if(n<=12)return 'ARCO II · La conspiración';
    if(n<=18)return 'ARCO III · La expansión';
    return 'ARCO IV · El juicio';
  }
  String get rank=>xp>=2400?'Maestro del gremio':xp>=1800?'Estratega':xp>=1200?'Comerciante':xp>=600?'Aprendiz avanzado':'Aprendiz';
  Future<void> _answerLesson(TradeLesson l,String answer)async{
    if(busy||mastered.contains(l.day)||l.day>state.day)return;
    if(l.day==state.day&&l.day%6==0&&!chapterCases.contains(l.day)){setState(()=>feedback='Resuelve primero el balance de tu propio arco.');return;}
    if(answer!=l.answer){
      HapticFeedback.lightImpact();
      setState((){feedback='Todavía no. Revisa la explicación y el ejemplo de ${l.mentor}; después vuelve a intentarlo.';showingHint=true;});
      return;
    }
    setState(()=>busy=true);
    try{
      final updated=<int>{...mastered,l.day};
      final prefs=await SharedPreferences.getInstance();
      if(!await prefs.setStringList(masteryKey,updated.map((n)=>n.toString()).toList()))throw StateError('No se pudo guardar el dominio.');
      if(!mounted)return;
      HapticFeedback.mediumImpact();
      setState((){mastered=updated;feedback=null;showingHint=false;});
      await showDialog<void>(context:context,builder:(ctx)=>AlertDialog(
        title:Text(l.day%6==0?'Arco superado · +100 XP':'Conocimiento adquirido · +100 XP'),
        content:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,crossAxisAlignment:CrossAxisAlignment.start,children:[
          const Icon(Icons.auto_awesome_rounded,size:42,color:Color(0xfff6ce85)),
          const SizedBox(height:12),Text(l.title,style:const TextStyle(fontWeight:FontWeight.w900,fontSize:20)),
          const SizedBox(height:10),Text(l.explanation),
          if(l.day%6==0)...[const Divider(),Text('Revisa las cuentas del arco: ${state.history.where((r)=>(r['day'] as int)>l.day-6&&(r['day'] as int)<=l.day).fold<int>(0,(sum,r)=>sum+(r['profit'] as int))} monedas de beneficio operativo acumulado. La caja puede diferir por el inventario y el crédito.')],
          const SizedBox(height:12),Text('Rango: $rank · $xp XP'),
        ])),
        actions:[FilledButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Continuar aventura'))],
      ));
    }catch(e){if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(e.toString())));}
    finally{if(mounted)setState(()=>busy=false);}
  }
  Widget _teach(TradeLesson l,{bool post=false})=>_panel([
    Row(children:[const Icon(Icons.auto_stories_rounded,color:Color(0xfff6ce85)),const SizedBox(width:10),Expanded(child:Text(post?'ENTRENAMIENTO · ${l.mentor.toUpperCase()}':'ANTES DE LA MISIÓN · ${l.mentor.toUpperCase()}',style:const TextStyle(color:Color(0xfff6ce85),fontWeight:FontWeight.w900,fontSize:12,letterSpacing:.6)))]),
    const SizedBox(height:12),Text(l.title,style:const TextStyle(fontSize:21,fontWeight:FontWeight.w900)),
    const SizedBox(height:8),Text(l.teach,style:const TextStyle(fontSize:16,height:1.5)),
    const SizedBox(height:12),Container(padding:const EdgeInsets.all(12),decoration:BoxDecoration(color:const Color(0xff243c50),borderRadius:BorderRadius.circular(12)),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('EJEMPLO RESUELTO',style:TextStyle(fontWeight:FontWeight.w900,color:Color(0xff94ddcf),fontSize:12)),const SizedBox(height:6),Text(l.example,style:const TextStyle(height:1.45))])),
    if(!post)...[const SizedBox(height:8),const Text('Utiliza este concepto en la decisión que viene. Al terminar la jornada, tu mentor comprobará que lo entendiste.',style:TextStyle(color:Color(0xffb6c6de),fontSize:12))],
  ]);

  Widget _chapterCase(TradeLesson l){
    final rows=state.history.where((r)=>(r['day'] as int)>l.day-6&&(r['day'] as int)<=l.day);
    int total(String k)=>rows.fold<int>(0,(sum,r)=>sum+(r[k] as int));
    final revenue=total('revenue'),cogs=total('cogs'),rent=total('rent'),fees=total('fee');
    final profit=revenue-cogs-rent-fees;
    final options=<int>{profit,revenue,profit+rent+fees,profit-50};
    if(options.length<4)options.add(profit+75);
    final ordered=options.toList()..shuffle(Random(state.seed+l.day*31));
    final passed=chapterCases.contains(l.day);
    return _panel([
      const Text('EXAMEN PRÁCTICO DEL ARCO',style:TextStyle(fontWeight:FontWeight.w900,color:Color(0xfff6ce85))),
      const SizedBox(height:8),
      const Text('Astra te entrega el balance de tus últimas seis jornadas. Calcula el beneficio operativo real antes de poder continuar.'),
      const Divider(),_line('Ingresos',revenue),_line('Costo de mercancía vendida',cogs),_line('Alquiler',rent),_line('Gastos de estrategia',fees),
      const SizedBox(height:8),
      if(passed)Text('Correcto: $revenue − $cogs − $rent − $fees = $profit monedas.',style:const TextStyle(color:Color(0xff94ddcf),fontWeight:FontWeight.bold))
      else for(final amount in ordered)Padding(padding:const EdgeInsets.only(bottom:8),child:OutlinedButton(onPressed:busy?null:()=>setState((){
        if(amount==profit){chapterCases.add(l.day);caseFeedback=null;feedback=null;HapticFeedback.mediumImpact();}
        else{caseFeedback='Recuerda: resta el costo de las unidades vendidas y todos los gastos operativos a los ingresos.';HapticFeedback.lightImpact();}
      }),child:Text('$amount monedas'))),
      if(caseFeedback!=null)Text(caseFeedback!,style:const TextStyle(color:Color(0xffffc0a0))),
    ]);
  }
  Widget _masteryScreen(TradeLesson l){
    final row=state.history.last;
    return Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
      if(widget.sceneBuilder!=null) ...[widget.sceneBuilder!(c.days[l.day-1]),const SizedBox(height:12)],
      _panel([
        Text('JORNADA ${l.day} COMPLETADA',style:const TextStyle(color:Color(0xff94ddcf),fontWeight:FontWeight.w900)),
        const SizedBox(height:6),Text('Tu resultado: ${row['sold']} ventas · ${row['profit']} de beneficio operativo · ${row['cash']} de caja.'),
        const SizedBox(height:8),Text((row['profit'] as int)<0?'Tu mentor quiere revisar por qué perdiste dinero antes de continuar.':'Tu mentor quiere que puedas explicar tu resultado, no solo conseguirlo.'),
        TextButton(onPressed:busy?null:()=>_report(row),child:const Text('Revisar las cuentas reales de mi jornada')),
      ]),
      const SizedBox(height:12),_teach(l,post:true),
      if(l.day%6==0)...[const SizedBox(height:12),_chapterCase(l)],
      const SizedBox(height:12),_panel([
        Text(l.day%6==0?'PRUEBA DEL ARCO':'PRUEBA DE DOMINIO',style:const TextStyle(color:Color(0xfff6ce85),fontWeight:FontWeight.w900)),
        const SizedBox(height:10),Text(l.question,style:const TextStyle(fontSize:19,fontWeight:FontWeight.bold)),
        const SizedBox(height:12),
        for(final option in l.choices)Padding(padding:const EdgeInsets.only(bottom:8),child:OutlinedButton(onPressed:busy?null:()=>_answerLesson(l,option),style:OutlinedButton.styleFrom(alignment:Alignment.centerLeft,padding:const EdgeInsets.all(14)),child:Text(option))),
        if(feedback!=null)...[const SizedBox(height:8),Text(feedback!,style:const TextStyle(color:Color(0xffffc0a0),height:1.4))],
        if(showingHint)TextButton(onPressed:()=>showDialog<void>(context:context,builder:(ctx)=>AlertDialog(title:const Text('Ayuda del mentor'),content:Text(l.explanation),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Entendido, volver a intentar'))])),child:const Text('Pedir ayuda al mentor')),
        const SizedBox(height:8),const Text('No pierdes dinero por equivocarte. Aprende del error y vuelve a intentarlo.',style:TextStyle(color:Color(0xffb6c6de),fontSize:12)),
      ]),
    ]);
  }
  Future<void> _academy()=>showDialog<void>(context:context,builder:(ctx)=>AlertDialog(
    title:Text('Academia del gremio · ${mastered.length}/${lessons.length}'),
    content:SizedBox(width:double.maxFinite,child:ListView(shrinkWrap:true,children:[
      for(final n in (lessons.keys.toList()..sort()))ListTile(
        contentPadding:EdgeInsets.zero,leading:Icon(mastered.contains(n)?Icons.check_circle_rounded:n<=state.day+1?Icons.menu_book_rounded:Icons.lock_outline),
        title:Text('$n. ${lessons[n]!.title}'),subtitle:Text(mastered.contains(n)?'Dominado':n<=state.day+1?'Disponible':'Desbloquea la jornada'),
        enabled:n<=state.day+1,onTap:n>state.day+1?null:(){Navigator.pop(ctx);final l=lessons[n]!;showDialog<void>(context:context,builder:(context)=>AlertDialog(title:Text(l.title),content:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,crossAxisAlignment:CrossAxisAlignment.start,children:[Text(l.teach),const Divider(),Text(l.example),if(n<=state.day&&!mastered.contains(n))...[
          const Divider(),Text(l.question),for(final opt in l.choices)TextButton(onPressed:(){Navigator.pop(context);_answerLesson(l,opt);},child:Text(opt)),
        ]else if(mastered.contains(n))...[const Divider(),Text(l.explanation)]])),actions:[TextButton(onPressed:()=>Navigator.pop(context),child:const Text('Cerrar'))]));}),
    ])),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Cerrar'))],
  ));
  Widget _line(String name,int value)=>Padding(padding:const EdgeInsets.symmetric(vertical:4),child:Row(children:[Expanded(child:Text(name)),Text('$value monedas',style:const TextStyle(fontWeight:FontWeight.w700))]));
  Widget _stat(String title,String value,IconData icon)=>Expanded(child:Container(padding:const EdgeInsets.symmetric(vertical:12,horizontal:8),decoration:BoxDecoration(color:const Color(0xff1c2940),borderRadius:BorderRadius.circular(12)),child:Column(children:[Icon(icon,color:const Color(0xfff6ce85),size:18),const SizedBox(height:5),Text(value,style:const TextStyle(fontSize:20,fontWeight:FontWeight.w900,color:Colors.white)),Text(title,style:const TextStyle(fontSize:11,color:Color(0xffb6c6de)))])));
  Widget _header()=>Column(children:[
    Row(children:[_stat('CAJA','${state.cash}',Icons.account_balance_wallet_outlined),const SizedBox(width:6),_stat('STOCK','${state.stock}',Icons.inventory_2_outlined),const SizedBox(width:6),_stat('DEUDA','${state.debt}',Icons.receipt_long),const SizedBox(width:6),_stat('PRESTIGIO','${state.reputation}',Icons.shield_outlined)]),
    const SizedBox(height:12),
    Text(arc,style:const TextStyle(color:Color(0xfff6ce85),fontWeight:FontWeight.w900,letterSpacing:1)),
    const SizedBox(height:6),
    Row(children:[Expanded(child:Text('$rank · $xp XP',style:const TextStyle(fontWeight:FontWeight.bold))),TextButton.icon(onPressed:busy?null:_academy,icon:const Icon(Icons.menu_book_rounded),label:Text('${mastered.length}/${lessons.length}'))]),
    LinearProgressIndicator(value:state.day/c.days.length,minHeight:7,borderRadius:BorderRadius.circular(5)),
    const SizedBox(height:6),
    Wrap(spacing:4,runSpacing:4,children:[for(var i=0;i<c.days.length;i++) Container(width:30,height:25,decoration:BoxDecoration(color:i<state.day?const Color(0xff426f62):i==state.day?const Color(0xfff6ce85):const Color(0xff28364c),borderRadius:BorderRadius.circular(5)),alignment:Alignment.center,child:Text('${i+1}',style:TextStyle(fontSize:11,color:i==state.day?const Color(0xff17263b):Colors.white,fontWeight:FontWeight.bold)))]),
    const SizedBox(height:6),
    Text('Jornadas completadas ${state.day}/${c.days.length} · Meta final: ${c.targetCash} monedas y ${c.targetReputation} de prestigio',style:const TextStyle(fontSize:12,color:Color(0xffbac9dc))),
  ]);
  Widget _panel(List<Widget> children)=>Container(padding:const EdgeInsets.all(16),decoration:BoxDecoration(color:const Color(0xff18243a),borderRadius:BorderRadius.circular(16),border:Border.all(color:const Color(0xff344360))),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:children));
  Widget _playScreen(){
    final day=d;
    final expected=TradeEngine.forecast(state,day,action,price);
    final predicted=min(state.stock+quantity,expected);
    final low=max(0,expected-4),high=expected+4;
    final tone=day.biome=='forja'?const Color(0xffa85235):day.biome=='torre'?const Color(0xff5753a2):const Color(0xff2c756e);
    final minPrice=max(1,day.marketPrice-8),maxPrice=day.marketPrice+12;
    return Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
      if(state.day==0)_panel([Text(c.subtitle,style:const TextStyle(color:Color(0xfff6ce85),fontWeight:FontWeight.bold)),const SizedBox(height:10),Text(c.intro,style:const TextStyle(height:1.45)),const SizedBox(height:10),const Text('Tu licencia se decide por el efectivo que conservas después de liquidar el inventario y pagar las deudas, no por la cantidad de ventas.',style:TextStyle(color:Color(0xffc0d0e5)))]),
      const SizedBox(height:12),
      if(widget.sceneBuilder!=null) ...[widget.sceneBuilder!(day),const SizedBox(height:10)],
      Container(padding:const EdgeInsets.all(20),decoration:BoxDecoration(gradient:LinearGradient(colors:[tone,const Color(0xff142139)],begin:Alignment.topLeft,end:Alignment.bottomRight),borderRadius:BorderRadius.circular(18)),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
        Row(children:[Icon(day.biome=='torre'?Icons.castle_outlined:day.biome=='forja'?Icons.local_fire_department_outlined:Icons.storefront_outlined,size:38,color:const Color(0xfff6ce85)),const SizedBox(width:12),Expanded(child:Text('JORNADA ${state.day+1} · ${day.place.toUpperCase()}',style:const TextStyle(fontSize:11,fontWeight:FontWeight.bold,letterSpacing:1)))]),
        const SizedBox(height:16),Text(day.title,style:const TextStyle(fontSize:27,fontWeight:FontWeight.w900)),const SizedBox(height:8),Text(day.speaker,style:const TextStyle(color:Color(0xfff6ce85),fontWeight:FontWeight.w800)),const SizedBox(height:8),Text(day.story,style:const TextStyle(fontSize:16,height:1.45)),
        if(state.history.isNotEmpty)...[const SizedBox(height:12),Text(state.reputation>=80?'Los vecinos te saludan al abrir el puesto. Tu reputación ya atrae compradores.':state.reputation<30?'Los clientes desconfían de tus promesas. La mala fama reduce tu demanda.':(state.history.last['profit'] as int)<0?'Mira señala las cuentas de ayer. Perdiste dinero; necesitas cambiar de estrategia.':'Mira revisa el libro de cuentas. Tu última jornada dejó beneficios.',style:const TextStyle(color:Color(0xfff6ce85),height:1.35))],
      ])),
      const SizedBox(height:12),
      if(lessons[state.day+1]!=null)...[_teach(lessons[state.day+1]!),const SizedBox(height:12)],
      _panel([const Text('01 · ELIGE TU ESTRATEGIA',style:TextStyle(fontWeight:FontWeight.w800,color:Color(0xfff6ce85))),const SizedBox(height:8),
        for(var i=0;i<day.choices.length;i++)Padding(padding:const EdgeInsets.only(bottom:8),child:InkWell(onTap:busy?null:()=>setState((){choice=i;_adjust();}),borderRadius:BorderRadius.circular(12),child:Container(padding:const EdgeInsets.all(12),decoration:BoxDecoration(color:choice==i?const Color(0xff30445b):const Color(0xff202e43),border:Border.all(color:choice==i?const Color(0xfff6ce85):Colors.transparent),borderRadius:BorderRadius.circular(12)),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(day.choices[i].name,style:const TextStyle(fontWeight:FontWeight.bold)),const SizedBox(height:5),Text(day.choices[i].note),Text('Costo: ${day.choices[i].fee} · Prestigio: ${day.choices[i].rep>=0?'+':''}${day.choices[i].rep}',style:const TextStyle(fontSize:12,color:Color(0xffbcd0e7)))])))),
      ]),
      const SizedBox(height:12),
      _panel([const Text('02 · ADMINISTRA TU NEGOCIO',style:TextStyle(fontWeight:FontWeight.w800,color:Color(0xfff6ce85))),const SizedBox(height:10),
        Text('Producto: ${c.product} · Costo unitario: ${day.cost} · Alquiler: ${day.rent}'),
        if(!state.loanUsed)SwitchListTile(contentPadding:EdgeInsets.zero,value:borrow,onChanged:busy?null:(v)=>setState((){borrow=v;_adjust();}),title:Text('Crédito de ${c.loanCash} monedas'),subtitle:Text('Devuelve ${c.loanDebt} al terminar. Solo una vez.')),
        Text('Comprar $quantity unidades · ${quantity*day.cost} monedas',style:const TextStyle(fontWeight:FontWeight.bold)),
        Slider(min:0,max:max(1,maxBuy).toDouble(),divisions:max(1,maxBuy),value:quantity.toDouble(),onChanged:busy||maxBuy==0?null:(v)=>setState(()=>quantity=v.round())),
        Text('Precio de venta: $price monedas · Mercado: ${day.marketPrice}',style:const TextStyle(fontWeight:FontWeight.bold)),
        Slider(min:minPrice.toDouble(),max:maxPrice.toDouble(),divisions:maxPrice-minPrice,value:price.toDouble(),onChanged:busy?null:(v)=>setState(()=>price=v.round())),
        const Divider(),
        _line('Efectivo disponible',funds),
        _line('Gasto antes de vender',outlay),
        Text('Demanda estimada: $low–$high clientes · Existencias disponibles: ${state.stock+quantity}'),
        const SizedBox(height:6),Text('Ventas estimadas: $predicted unidades · Caja estimada al cierre: ${funds-outlay+predicted*price} monedas',style:const TextStyle(color:Color(0xfff6ce85),fontWeight:FontWeight.bold)),
        const SizedBox(height:8),const Text('La demanda real puede variar. El inventario sobrante pasa a la siguiente jornada.',style:TextStyle(fontSize:12,color:Color(0xffb6c6de))),
      ]),
      const SizedBox(height:14),
      FilledButton.icon(onPressed:busy||outlay>funds?null:_play,icon:const Icon(Icons.play_arrow),label:const Text('ABRIR EL MERCADO Y EJECUTAR EL PLAN'),style:FilledButton.styleFrom(backgroundColor:const Color(0xfff6ce85),foregroundColor:const Color(0xff18243a),padding:const EdgeInsets.symmetric(vertical:18))),
      if(state.cash+(state.loanUsed?0:c.loanCash)<day.rent+day.choices.map((x)=>x.fee).reduce(min))OutlinedButton(onPressed:busy?null:_insolvent,child:const Text('Cerrar el gremio por falta de liquidez')),
      if(outlay>funds)const Padding(padding:EdgeInsets.all(8),child:Text('No tienes suficiente efectivo. Reduce gastos o activa el crédito.',style:TextStyle(color:Color(0xffffa6a2)))),
    ]);
  }
  Widget _ending(){
    final result=TradeEngine.ending(c,state),net=TradeEngine.finalCash(c,state);
    final text=state.insolvent?'No pudiste cubrir los gastos de la jornada. El consejo cierra el negocio.':net<0?'La deuda supera tus recursos. Astra rechaza la renovación.':result=='LA CORONA DEL COMERCIO'?'Astra aprueba tu licencia. Mira se une al gremio y los ciudadanos te nombran su representante. Rin pierde el monopolio.':result=='EL MAGNATE SOLITARIO'?'Pagaste la deuda y construiste riqueza, pero el consejo desconfía de tus métodos. Conservas tu taller sin el apoyo del barrio.':result=='EL PACTO DEL BARRIO'?'El barrio confía en ti y consigue una licencia provisional. Debes mejorar el margen y la caja.':'Pagaste la deuda, pero el taller sigue siendo frágil. El consejo te concede un nuevo intento.';
    return _panel([const Icon(Icons.emoji_events_outlined,color:Color(0xfff6ce85),size:70),const SizedBox(height:10),Text(result,textAlign:TextAlign.center,style:const TextStyle(fontSize:26,fontWeight:FontWeight.w900,color:Color(0xfff6ce85))),const SizedBox(height:10),Text(text,style:const TextStyle(height:1.5)),const Divider(),_line('Caja antes del cierre',state.cash),_line('Liquidación de inventario',state.stock*c.liquidation),_line('Deuda exigible',-state.debt),_line('Saldo final simulado',net),Text('Prestigio final: ${state.reputation}/100'),const SizedBox(height:16),FilledButton(onPressed:busy?null:_restart,child:const Text('Jugar otra estrategia'))]);
  }
  @override Widget build(BuildContext context)=>Theme(data:ThemeData.dark(useMaterial3:true),child:Scaffold(backgroundColor:const Color(0xff101a2b),appBar:AppBar(backgroundColor:const Color(0xff101a2b),title:Text(c.title,style:const TextStyle(fontSize:16)),actions:[if(widget.sideAdventure!=null)IconButton(tooltip:'Aventura paralela: La sombra del héroe',icon:const Icon(Icons.explore_outlined),onPressed:widget.sideAdventure),AdventureMusicButton(mood:loading?'silent':pendingLesson!=null?'study':done?(state.insolvent?'mystery':'victory'):adventureMood(d.music,d.biome,'')),IconButton(tooltip:'Personajes',icon:const Icon(Icons.groups_rounded),onPressed:()=>Navigator.of(context).push(MaterialPageRoute<void>(builder:(_)=>NebulaCastPage(guide:widget.guide)))),IconButton(tooltip:'Reiniciar partida',onPressed:loading||busy?null:_restart,icon:const Icon(Icons.restart_alt))]),body:loading?const Center(child:CircularProgressIndicator()):SafeArea(child:ListView(padding:const EdgeInsets.all(14),children:[
    _header(),const SizedBox(height:14),
    if(pendingLesson!=null)_masteryScreen(pendingLesson!)else if(done)_ending()else _playScreen(),
    if(state.history.isNotEmpty)...[
      const SizedBox(height:16),_panel([const Text('LIBRO DE CUENTAS',style:TextStyle(color:Color(0xfff6ce85),fontWeight:FontWeight.bold)),for(final row in state.history.reversed)ListTile(contentPadding:EdgeInsets.zero,title:Text('Día ${row['day']} · ${row['title']}'),subtitle:Text('Caja ${row['cash']} · Ventas ${row['sold']} · Beneficio ${row['profit']}'),trailing:const Icon(Icons.chevron_right),onTap:busy?null:()=>_report(row))]),
    ],
    const SizedBox(height:20),const Text('Simulación educativa. Las decisiones no involucran dinero real. El progreso de esta campaña se guarda en el dispositivo.',textAlign:TextAlign.center,style:TextStyle(fontSize:12,color:Color(0xff9aafcb))),
  ]))));
}
