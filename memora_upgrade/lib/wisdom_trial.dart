import 'dart:math';

class WisdomQuestion {
  const WisdomQuestion(this.prompt,this.answer,this.tolerance,this.explanation);
  final String prompt,explanation;
  final double answer,tolerance;
  bool accepts(String input){
    final value=double.tryParse(input.trim().replaceAll(',','.'));
    return value!=null&&value.isFinite&&(value-answer).abs()<=tolerance;
  }
}

class WisdomTrial {
  const WisdomTrial(this.tier,this.questions);
  final int tier;
  final List<WisdomQuestion> questions;
  static const names=['Fundamentos','Finanzas básicas','Análisis financiero','Finanzas empresariales','Valoración avanzada','Finanzas profesionales','Gestión de riesgo avanzada','Maestría financiera','Sabiduría divina'];
  String get name=>names[tier];
  bool passes(List<String> answers)=>answers.length==questions.length&&List.generate(questions.length,(i)=>questions[i].accepts(answers[i])).every((v)=>v);
  static int difficulty(Map enemy){
    final level=(enemy['level'] as num?)?.toInt()??1;
    final base=level<=3?0:level<=8?1:level<=15?2:level<=30?3:level<=55?4:level<=90?5:level<=140?6:level<=200?7:8;
    final rank=const {'E':0,'D':0,'C':1,'B':2,'B+':2,'A':3,'S':4,'SS':5,'SSS':6,'L':7,'Divino':7,'Divino+':8}[enemy['rank']]??0;
    return max(base,rank);
  }
  static double npv(double rate,List<double> flows){
    double value=0;
    for(var i=0;i<flows.length;i++){value+=flows[i]/pow(1+rate,i);}
    return value;
  }
  static double irr(List<double> flows){
    double lo=0,hi=1;
    for(var i=0;i<100;i++){final mid=(lo+hi)/2;if(npv(mid,flows)>0){lo=mid;}else{hi=mid;}}
    return (lo+hi)/2;
  }
  static WisdomTrial generate(Map enemy,int seed){
    final tier=difficulty(enemy),r=Random(seed);
    int n(int min,int max)=>min+r.nextInt(max-min+1);
    String f(num x)=>x.toStringAsFixed(x is int?0:2);
    WisdomQuestion q(String p,double v,String e,{double tol=0.015})=>WisdomQuestion(p,v,tol,e);
    final result=<WisdomQuestion>[];
    final units=n(80,240),price=n(18,45),cost=n(6,15),fixed=n(500,1100);
    final revenue=units*price,variable=units*cost,profit=revenue-variable-fixed;
    if(tier<=2){
      result.add(q('Una empresa vende $units unidades a \$$price cada una. Su coste variable es \$$cost por unidad y sus gastos fijos son \$$fixed. Calcula el beneficio operativo en dólares.',profit.toDouble(),'Beneficio = ventas - costes variables - gastos fijos.'));
      if(tier>=1)result.add(q('Con un precio de \$$price, coste variable unitario de \$$cost y costes fijos de \$$fixed, ¿cuántas unidades enteras como mínimo necesita vender para alcanzar el punto de equilibrio?',(fixed/(price-cost)).ceilToDouble(),'Punto de equilibrio = costes fijos / margen de contribución unitario, redondeado hacia arriba.',tol:0));
      if(tier>=2){final capital=n(100,300)*100,rate=n(4,12),years=n(3,7);result.add(q('Inviertes \$$capital al $rate% efectivo anual durante $years años, sin retiradas. ¿Cuál será el valor futuro en dólares?',capital*pow(1+rate/100,years).toDouble(),'VF = capital × (1 + tasa)^años.'));}
      return WisdomTrial(tier,result);
    }
    final investment=n(30,80)*1000,cf1=n(12,24)*1000,cf2=n(18,30)*1000,cf3=n(22,36)*1000,discount=n(8,15);
    final flows=[-investment.toDouble(),cf1.toDouble(),cf2.toDouble(),cf3.toDouble()];
    result.add(q('Proyecto: inversión inicial \$$investment; flujos al final de los años 1, 2 y 3: \$$cf1, \$$cf2 y \$$cf3. Tasa de descuento $discount% anual. Calcula el VAN en dólares.',npv(discount/100,flows),'VAN = -inversión + suma de flujos descontados por período.'));
    final ebit=n(80,180)*1000,dep=n(10,25)*1000,capex=n(20,40)*1000,nwc=n(5,15)*1000,tax=n(20,30);
    result.add(q('EBIT \$$ebit, depreciación \$$dep, CAPEX \$$capex, aumento de capital de trabajo \$$nwc, impuesto $tax%. Calcula el flujo libre para la empresa (FCFF).',ebit*(1-tax/100)+dep-capex-nwc,'FCFF = EBIT(1-t) + depreciación - CAPEX - aumento de capital de trabajo.'));
    final equity=n(45,75),rf=n(3,5),beta=n(90,160)/100,premium=n(5,8),debtRate=n(5,9);
    final wacc=equity/100*(rf/100+beta*premium/100)+(1-equity/100)*debtRate/100*(1-tax/100);
    result.add(q('La estructura de capital es $equity% patrimonio y el resto deuda. Tasa libre de riesgo $rf%, beta ${f(beta)}, prima de mercado $premium%, coste de deuda antes de impuestos $debtRate%, impuesto $tax%. Calcula el WACC en porcentaje (ejemplo 9.25).',wacc*100,'CAPM = Rf + beta × prima. WACC pondera patrimonio y deuda después de impuestos.'));
    if(tier>=4){
      final c1=n(30,50)*1000,c2=n(30,55)*1000,c3=n(45,70)*1000,outlay=n(50,70)*1000;
      result.add(q('Inversión inicial \$$outlay; flujos anuales \$$c1, \$$c2, \$$c3 al final de tres años. Calcula la TIR anual en porcentaje.',irr([-outlay.toDouble(),c1.toDouble(),c2.toDouble(),c3.toDouble()])*100,'La TIR es la tasa que hace VAN = 0; se puede hallar por iteración.',tol:0.025));
    }
    if(tier>=5){
      final annual=n(40,90)*1000,growth=n(2,4),fc1=annual.toDouble(),fc2=fc1*(1+growth/100),fc3=fc2*(1+growth/100),rate=(n(9,15))/100,g=growth/100,debt=n(60,150)*1000,cash=n(10,35)*1000;
      final terminal=fc3*(1+g)/(rate-g);
      final value=npv(rate,[0,fc1,fc2,fc3+terminal])-debt+cash;
      result.add(q('DCF: FCFF año 1 \$$annual, crecimiento anual $growth% en años 2 y 3 y a perpetuidad. WACC ${f(rate*100)}%. Deuda \$$debt, efectivo excedente \$$cash. Calcula el valor del patrimonio hoy en dólares. No redondees valores intermedios.',value,'Valor terminal = FCFF4/(WACC-g). Descontar FCFF y terminal; restar deuda y sumar efectivo.',tol:0.50));
      final p=n(20,40),qprob=n(20,35),a=n(-25,-5),b=n(5,15),c=n(20,40),mean=p/100*a+qprob/100*b+(100-p-qprob)/100*c;
      final sd=sqrt(p/100*pow(a-mean,2)+qprob/100*pow(b-mean,2)+(100-p-qprob)/100*pow(c-mean,2));
      result.add(q('Tres escenarios de rentabilidad: $a% con probabilidad $p%; $b% con $qprob%; $c% con la probabilidad restante. Calcula la desviación estándar de la rentabilidad en puntos porcentuales.',sd,'Media ponderada; varianza = suma de probabilidades por desviaciones cuadráticas; raíz cuadrada.'));
    }
    if(tier>=6){
      final face=n(8,15)*1000,coupon=n(4,8),yieldRate=n(8,12),years=n(4,8),yieldDecimal=yieldRate/100;
      final flows=[for(var i=1;i<=years;i++)face*coupon/100+(i==years?face:0)];
      double bond=0,weighted=0;
      for(var i=0;i<flows.length;i++){final pv=flows[i]/pow(1+yieldDecimal,i+1);bond+=pv;weighted+=(i+1)*pv;}
      result.add(q('Bono nominal \$$face, cupón anual $coupon%, rendimiento al vencimiento $yieldRate%, vencimiento $years años, pagos anuales. Calcula la duración modificada en años.',weighted/bond/(1+yieldDecimal),'Duración Macaulay = valor presente ponderado por tiempo / precio. Dividir por 1 + rendimiento.',tol:0.015));
    }
    if(tier>=7){
      final cf=n(70,120)*1000,unlevered=n(10,16)/100,perpetualDebt=n(120,220)*1000,issue=n(5,15)*1000;
      final apv=cf/unlevered+tax/100*perpetualDebt-issue;
      result.add(q('Una empresa genera FCFF constante de \$$cf a perpetuidad, comenzando en un año. Coste de capital sin deuda ${f(unlevered*100)}%, deuda perpetua fija \$$perpetualDebt, impuesto $tax%, costes de emisión iniciales \$$issue. Supón escudos fiscales descontados al coste de deuda. Calcula el valor presente ajustado (APV) en dólares.',apv,'APV = valor sin deuda + valor presente del escudo fiscal - costes de emisión.',tol:0.50));
      final cashAvailable=n(80,150)*1000,dscr=n(120,170)/100,interest=n(6,10)/100,term=n(5,10);
      final maxPayment=cashAvailable/dscr;
      final principal=maxPayment*(1-pow(1+interest,-term))/interest;
      result.add(q('Proyecto con CFADS anual constante de \$$cashAvailable, DSCR mínimo ${f(dscr)}x, préstamo totalmente amortizado con cuotas anuales iguales al ${f(interest*100)}% durante $term años. Calcula la deuda máxima admisible hoy.',principal,'Cuota máxima = CFADS/DSCR. Deuda = valor presente de las cuotas.',tol:0.50));
    }
    if(tier>=8){
      final s1=n(80,120)*1000,s2=n(130,200)*1000,s3=n(220,320)*1000,prob1=n(20,35),prob2=n(25,40),cap=n(120,180)*1000,k=n(10,16)/100;
      final p3=100-prob1-prob2;
      final expected=(prob1/100*max(0,s1-cap)+prob2/100*max(0,s2-cap)+p3/100*max(0,s3-cap))/(1+k);
      result.add(q('Opción de expansión: dentro de un año el valor del proyecto será \$$s1, \$$s2 o \$$s3, con probabilidades neutrales al riesgo $prob1%, $prob2% y $p3%. Puedes pagar \$$cap para adquirirlo en ese momento, o no ejercer. Tasa libre de riesgo ${f(k*100)}%. Calcula el valor actual de la opción.',expected,'Descontar el valor esperado neutral al riesgo de max(valor del proyecto - precio de ejercicio, 0).',tol:0.50));
      final pA=n(30,50)/100,volA=n(12,22)/100,volB=n(18,30)/100,corr=n(-30,65)/100;
      final vol=sqrt(pow(pA*volA,2)+pow((1-pA)*volB,2)+2*pA*(1-pA)*volA*volB*corr)*100;
      result.add(q('Cartera: peso A ${f(pA*100)}%, resto B; volatilidades anuales ${f(volA*100)}% y ${f(volB*100)}%; correlación ${f(corr)}. Calcula la volatilidad anual de la cartera en porcentaje.',vol,'Varianza de cartera = wA²σA² + wB²σB² + 2wAwBσAσBρ.',tol:0.015));
    }
    return WisdomTrial(tier,result);
  }
}
