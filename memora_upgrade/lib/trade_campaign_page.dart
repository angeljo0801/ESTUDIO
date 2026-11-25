import 'dart:convert';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'models.dart';

class TradeChoice {
  const TradeChoice(this.name,this.note,this.fee,this.rep,this.boost);
  final String name,note;
  final int fee,rep,boost;
}
class TradeDay {
  const TradeDay(this.title,this.speaker,this.place,this.biome,this.story,this.cost,this.demand,this.marketPrice,this.rent,this.choices);
  final String title,speaker,place,biome,story;
  final int cost,demand,marketPrice,rent;
  final List<TradeChoice> choices;
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
          days.add(TradeDay(str(d,'title'),str(d,'speaker'),str(d,'place'),str(d,'biome'),str(d,'story'),num(d,'cost',1,100),num(d,'demand',0,100),num(d,'marketPrice',1,100),num(d,'rent',0,300),choices));
        }
        return TradeCampaign(str(v,'title'),str(v,'subtitle'),str(v,'intro'),str(v,'product'),num(v,'version',1,100000),num(v,'initialCash',1,10000),num(v,'initialDebt',0,10000),num(v,'targetCash',0,100000),num(v,'targetReputation',0,100),num(v,'liquidation',0,100),num(v,'loanCash',0,1000),num(v,'loanDebt',0,2000),days);
      }catch(_){}
    }
    return null;
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
  const TradeCampaignPage({super.key,required this.guide,required this.campaign});
  final StudyGuide guide;
  final TradeCampaign campaign;
  @override State<TradeCampaignPage> createState()=>_TradeCampaignPageState();
}
class _TradeCampaignPageState extends State<TradeCampaignPage> {
  TradeCampaign get c=>widget.campaign;
  late TradeState state;
  bool loading=true,busy=false,borrow=false;
  int choice=0,quantity=0,price=1;
  String get key=>'memora_trade_${widget.guide.id}_v${c.version}';
  TradeDay get d=>c.days[state.day];
  TradeChoice get action=>d.choices[choice];
  bool get done=>state.insolvent||state.day>=c.days.length;
  int get funds=>state.cash+(borrow?c.loanCash:0);
  int get maxBuy=>min(100,max(0,(funds-d.rent-action.fee)~/d.cost));
  int get outlay=>quantity*d.cost+d.rent+action.fee;
  @override void initState(){super.initState();_load();}
  void _resetPlan(){choice=0;borrow=false;quantity=0;price=done?1:d.marketPrice;}
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
    if(!mounted)return;
    setState((){state=next;loading=false;_resetPlan();});
  }
  Future<void> _save(TradeState next)async{
    final prefs=await SharedPreferences.getInstance();
    if(!await prefs.setString(key,jsonEncode(next.toJson())))throw StateError('No se pudo guardar la partida.');
  }
  void _adjust(){quantity=min(quantity,maxBuy);}
  Future<void> _play()async{
    if(busy||done||outlay>funds)return;
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
    try{final next=TradeEngine.start(c,Random.secure().nextInt(1<<30));await _save(next);if(mounted)setState((){state=next;_resetPlan();});}finally{if(mounted)setState(()=>busy=false);}
  }
  Future<void> _insolvent()async{
    if(busy||done)return;
    setState(()=>busy=true);
    try{
      final next=TradeState(cash:state.cash,debt:state.debt,seed:state.seed,day:state.day,stock:state.stock,inventoryCost:state.inventoryCost,reputation:state.reputation,loanUsed:state.loanUsed,insolvent:true,history:state.history);
      await _save(next);if(mounted)setState(()=>state=next);
    }finally{if(mounted)setState(()=>busy=false);}
  }
  Widget _line(String name,int value)=>Padding(padding:const EdgeInsets.symmetric(vertical:4),child:Row(children:[Expanded(child:Text(name)),Text('$value monedas',style:const TextStyle(fontWeight:FontWeight.w700))]));
  Widget _stat(String title,String value,IconData icon)=>Expanded(child:Container(padding:const EdgeInsets.symmetric(vertical:12,horizontal:8),decoration:BoxDecoration(color:const Color(0xff1c2940),borderRadius:BorderRadius.circular(12)),child:Column(children:[Icon(icon,color:const Color(0xfff6ce85),size:18),const SizedBox(height:5),Text(value,style:const TextStyle(fontSize:20,fontWeight:FontWeight.w900,color:Colors.white)),Text(title,style:const TextStyle(fontSize:11,color:Color(0xffb6c6de)))])));
  Widget _header()=>Column(children:[
    Row(children:[_stat('CAJA','${state.cash}',Icons.account_balance_wallet_outlined),const SizedBox(width:6),_stat('STOCK','${state.stock}',Icons.inventory_2_outlined),const SizedBox(width:6),_stat('DEUDA','${state.debt}',Icons.receipt_long),const SizedBox(width:6),_stat('PRESTIGIO','${state.reputation}',Icons.shield_outlined)]),
    const SizedBox(height:12),
    LinearProgressIndicator(value:state.day/c.days.length,minHeight:7,borderRadius:BorderRadius.circular(5)),
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
      Container(padding:const EdgeInsets.all(20),decoration:BoxDecoration(gradient:LinearGradient(colors:[tone,const Color(0xff142139)],begin:Alignment.topLeft,end:Alignment.bottomRight),borderRadius:BorderRadius.circular(18)),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
        Row(children:[Icon(day.biome=='torre'?Icons.castle_outlined:day.biome=='forja'?Icons.local_fire_department_outlined:Icons.storefront_outlined,size:38,color:const Color(0xfff6ce85)),const SizedBox(width:12),Expanded(child:Text('JORNADA ${state.day+1} · ${day.place.toUpperCase()}',style:const TextStyle(fontSize:11,fontWeight:FontWeight.bold,letterSpacing:1)))]),
        const SizedBox(height:16),Text(day.title,style:const TextStyle(fontSize:27,fontWeight:FontWeight.w900)),const SizedBox(height:8),Text(day.speaker,style:const TextStyle(color:Color(0xfff6ce85),fontWeight:FontWeight.w800)),const SizedBox(height:8),Text(day.story,style:const TextStyle(fontSize:16,height:1.45)),
      ])),
      const SizedBox(height:12),
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
  @override Widget build(BuildContext context)=>Theme(data:ThemeData.dark(useMaterial3:true),child:Scaffold(backgroundColor:const Color(0xff101a2b),appBar:AppBar(backgroundColor:const Color(0xff101a2b),title:Text(c.title,style:const TextStyle(fontSize:16)),actions:[IconButton(tooltip:'Reiniciar partida',onPressed:loading||busy?null:_restart,icon:const Icon(Icons.restart_alt))]),body:loading?const Center(child:CircularProgressIndicator()):SafeArea(child:ListView(padding:const EdgeInsets.all(14),children:[
    _header(),const SizedBox(height:14),
    if(done)_ending()else _playScreen(),
    if(state.history.isNotEmpty)...[
      const SizedBox(height:16),_panel([const Text('LIBRO DE CUENTAS',style:TextStyle(color:Color(0xfff6ce85),fontWeight:FontWeight.bold)),for(final row in state.history.reversed)ListTile(contentPadding:EdgeInsets.zero,title:Text('Día ${row['day']} · ${row['title']}'),subtitle:Text('Caja ${row['cash']} · Ventas ${row['sold']} · Beneficio ${row['profit']}'),trailing:const Icon(Icons.chevron_right),onTap:busy?null:()=>_report(row))]),
    ],
    const SizedBox(height:20),const Text('Simulación educativa. Las decisiones no involucran dinero real. El progreso de esta campaña se guarda en el dispositivo.',textAlign:TextAlign.center,style:TextStyle(fontSize:12,color:Color(0xff9aafcb))),
  ]))));
}
