import 'package:flutter/material.dart';
import 'dual_world_engine.dart';
import 'lumen_economy.dart';

class LumenBusinessPanel extends StatefulWidget {
  const LumenBusinessPanel({super.key,required this.state,required this.act,required this.busy});
  final DualState state;
  final Future<void> Function(String Function()) act;
  final bool busy;
  @override State<LumenBusinessPanel> createState()=>_LumenBusinessPanelState();
}
class _LumenBusinessPanelState extends State<LumenBusinessPanel>{
  DualState get s=>widget.state;
  LumenEconomy get e=>s.economy;
  String coins(int n)=>n.toString()+' monedas';
  Widget button(String label,String Function() action)=>FilledButton(onPressed:widget.busy?null:()=>widget.act(action),child:Text(label));
  Widget block(String title,List<Widget> children)=>Card(child:Padding(padding:const EdgeInsets.all(12),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[Text(title,style:const TextStyle(fontSize:18,fontWeight:FontWeight.bold)),const SizedBox(height:8),...children])));
  String wallet(int? value,String success){if(value==null)return 'No reúnes los requisitos o no tienes suficiente capital.';s.cash=value;return success;}
  Future<void> job(Map j)async{final ctrl=TextEditingController();final answer=await showDialog<int>(context:context,builder:(ctx)=>AlertDialog(title:const Text('Encargo financiero'),content:Column(mainAxisSize:MainAxisSize.min,children:[Text(j['question'].toString()),Text(j['hint'].toString()),TextField(controller:ctrl,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'Respuesta'))]),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Cancelar')),FilledButton(onPressed:()=>Navigator.pop(ctx,int.tryParse(ctrl.text)),child:const Text('Entregar'))]));ctrl.dispose();if(answer!=null&&mounted)await widget.act((){final pay=e.jobReward(j['id'] as String,answer);if(pay==null)return 'Respuesta incorrecta o encargo ya cobrado. Revisa el método.';s.cash+=pay;return 'Encargo completado: +'+coins(pay);});}
  Future<void> edit(LumenBusiness b)async{
    final a=TextEditingController(text:b.price.toString()),c=TextEditingController(text:b.staff.toString()),d=TextEditingController(text:b.marketing.toString());
    final ok=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:Text(e.name(b.sector)),content:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[Text('Costo variable por unidad: '+e.number(b.sector,'unit').toString()+' · precio de referencia: '+e.number(b.sector,'price').toString()),TextField(controller:a,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'Precio de venta')),TextField(controller:c,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'Trabajadores')),TextField(controller:d,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'Publicidad mensual'))])),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Cancelar')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Guardar plan'))]));
    final price=int.tryParse(a.text),staff=int.tryParse(c.text),marketing=int.tryParse(d.text);a.dispose();c.dispose();d.dispose();if(ok==true&&mounted)await widget.act(()=>price!=null&&staff!=null&&marketing!=null&&e.configure(b.sector,price,staff,marketing)?'Plan operativo actualizado.':'Valores fuera del rango permitido.');
  }
  Future<void> advance(int months)async{
    final ok=await showDialog<bool>(context:context,builder:(ctx)=>AlertDialog(title:Text('Operar '+months.toString()+' mes(es)'),content:const Text('Se ejecutarán los planes de todas tus empresas, con cambios de demanda, salarios, alquiler, impuestos y deuda. Se detendrá antes de un mes que no puedas financiar. No avanzará el calendario académico.'),actions:[TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Cancelar')),FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('Operar'))]));
    if(ok==true&&mounted)await widget.act((){final r=e.advance(s.cash,months);s.cash=r['cash']!;return 'Meses operados: '+r['months'].toString()+'/'+months.toString()+' · beneficio después de intereses: '+coins(r['profit']!)+' · caja: '+coins(s.cash)+(r['months']!<months?' · Operación detenida por falta de capital.':'');});
  }
  @override Widget build(BuildContext context)=>Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
    block('Lumen · cartera empresarial',[Text('Mes comercial '+e.month.toString()+' · caja '+coins(s.cash)),Text('Patrimonio simplificado: '+coins(s.cash+s.inventoryCost+e.netBusinessAssets)),Text('Ventas acumuladas: '+coins(e.totalRevenue)+' · beneficio: '+coins(e.totalProfit)),Text('Deuda: '+coins(e.debt)+' · sucursales: '+e.totalBranches.toString()),const Text('La caja no equivale al beneficio. Conserva capital para pagar proveedores, empleados y deuda. Todas las cifras son monedas ficticias.')]),
    if(e.completedJobs.length<LumenEconomy.starterJobs.length)block('Encargos de iniciación',[const Text('Resuelve tres casos financieros para obtener hasta 1.500 monedas de capital inicial. Cada encargo se cobra una sola vez.'),for(final j in LumenEconomy.starterJobs.where((j)=>!e.completedJobs.contains(j['id'])))OutlinedButton(onPressed:widget.busy?null:()=>job(j),child:Text('Encargo · '+coins(j['pay'] as int)))]),
    block('Fundar una empresa',[for(final k in LumenEconomy.sectors.keys.where((k)=>!e.companies.containsKey(k)))...[
      Text(e.name(k)+' · inversión '+coins(e.number(k,'startup'))),button('Fundar',()=>wallet(e.open(k,s.cash),'Empresa fundada. Conserva capital operativo.'))]]),
    for(final b in e.companies.values)block(e.name(b.sector),[
      Text('Sucursales '+b.branches.toString()+' · trabajadores '+b.staff.toString()+' · precio '+coins(b.price)),
      ...forecast(b.sector),
      OutlinedButton(onPressed:widget.busy?null:()=>edit(b),child:const Text('Ajustar precios, empleados y publicidad')),
      button('Abrir sucursal · '+coins(e.number(b.sector,'expansion')*b.branches),()=>wallet(e.expand(b.sector,s.cash),'Sucursal abierta. Ajusta la plantilla si necesitas más capacidad.')),
      if(e.contractQuote(b.sector)!=null)...[
        const Text('Un contrato reserva parte de la capacidad del mes. Su beneficio se añade al acumulado al entregar; los salarios y alquiler se pagan al cerrar el mes.'),
        Text('Contrato mayorista: '+e.contractQuote(b.sector)!['units'].toString()+' unidades · capital '+coins(e.contractQuote(b.sector)!['cost']!)+' · beneficio '+coins(e.contractQuote(b.sector)!['profit']!)),
        button('Cumplir contrato',()=>wallet(e.fulfill(b.sector,s.cash),'Contrato entregado y cobrado.'))]]),
    if(e.companies.isNotEmpty)block('Operación delegada',[const Text('Opera todas tus empresas de una vez. El tiempo comercial no hace avanzar las clases ni los rescates de Asteria.'),for(final m in [1,3,12])OutlinedButton(onPressed:widget.busy?null:()=>advance(m),child:Text('Operar '+m.toString()+' mes(es)'))]),
    if(e.companies.isNotEmpty)block('Banco de Lumen',[Text('Préstamo disponible: '+coins(e.loanLimit)+' · interés 2% mensual sobre saldo · 12 cuotas de principal.'),if(e.debt==0&&e.loanLimit>0)button('Solicitar '+coins(e.loanLimit),()=>wallet(e.borrow(e.loanLimit,s.cash),'Préstamo recibido. No constituye beneficio.'))else if(e.debt>0)...[Text('Próxima cuota: '+coins(e.nextPrincipal+e.nextInterest)),button('Liquidar deuda',()=>wallet(e.repayEarly(e.debt,s.cash),'Deuda liquidada.'))]]),
    if(e.history.isNotEmpty)block('Resultados mensuales',[for(final r in e.history.reversed.take(12))Text('Mes '+r['month'].toString()+' · ventas '+r['revenue'].toString()+' · beneficio '+r['profit'].toString()+' · caja '+r['cash'].toString())])
  ]);
  List<Widget> forecast(String sector){final q=e.forecast(sector,estimate:true);return [Text('Pronóstico mensual · '+q['sold'].toString()+'/'+q['capacity'].toString()+' unidades'),Text('Ventas '+coins(q['revenue']!)+' · variables '+coins(q['variable']!)),Text('Fijos '+coins(q['fixed']!)+' · impuestos '+coins(q['tax']!)),Text('Beneficio estimado '+coins(q['profit']!)+' · capital operativo '+coins(q['workingCapital']!)),Text('Margen neto: '+q['marginPct'].toString()+'% · equilibrio: '+(q['breakEven']!<0?'No alcanzable con este precio':q['breakEven'].toString()+' unidades'))];}
}
