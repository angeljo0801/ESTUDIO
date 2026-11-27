import 'dart:math';

class LumenBusiness {
  LumenBusiness(this.sector);
  final String sector;
  int branches=1, staff=1, marketing=0, price=0, assets=0, reserve=0;
  Map<String,dynamic> toJson()=>{'sector':sector,'branches':branches,'staff':staff,'marketing':marketing,'price':price,'assets':assets,'reserve':reserve};
  factory LumenBusiness.fromJson(Map j){final b=LumenBusiness(j['sector'].toString());b.branches=j['branches'] as int;b.staff=j['staff'] as int;b.marketing=j['marketing'] as int;b.price=j['price'] as int;b.assets=j['assets'] as int;b.reserve=j['reserve'] as int;return b;}
}

class LumenEconomy {
  // All amounts are fictional game coins. A cycle is one commercial month.
  static const sectors=<String,Map<String,dynamic>>{
    'retail':{'name':'Tienda de suministros','startup':300,'unit':8,'price':16,'capacity':100,'demand':100,'rent':35,'wage':40,'expansion':450,'grade':0},
    'workshop':{'name':'Taller de fabricación','startup':2000,'unit':35,'price':75,'capacity':110,'demand':100,'rent':180,'wage':180,'expansion':3000,'grade':0},
    'transport':{'name':'Empresa de transporte','startup':8000,'unit':100,'price':210,'capacity':120,'demand':110,'rent':700,'wage':500,'expansion':10000,'grade':0},
    'wholesale':{'name':'Distribuidora mayorista','startup':25000,'unit':350,'price':680,'capacity':150,'demand':140,'rent':1800,'wage':1500,'expansion':30000,'grade':0},
    'factory':{'name':'Fábrica de equipamiento','startup':100000,'unit':1200,'price':2300,'capacity':180,'demand':160,'rent':7000,'wage':5000,'expansion':130000,'grade':0},
    'network':{'name':'Red comercial interregional','startup':350000,'unit':4000,'price':7400,'capacity':220,'demand':200,'rent':23000,'wage':16000,'expansion':450000,'grade':0},
  };
  static const starterJobs=<Map<String,dynamic>>[
    {'id':'margin','question':'Un proveedor cobra 60 monedas y vendes a 95. Pagas 10 de transporte. ¿Beneficio de la operación?','answer':25,'pay':350,'hint':'Calcula los ingresos menos el costo de compra y transporte.'},
    {'id':'cash','question':'Dispones de 200, cobras 150 y pagas 230. ¿Cuánto efectivo queda?','answer':120,'pay':450,'hint':'Caja inicial + cobros − pagos.'},
    {'id':'break_even','question':'Gastos fijos 240 y margen por unidad 12. ¿Cuántas unidades necesitas vender para cubrir gastos?','answer':20,'pay':700,'hint':'Gastos fijos divididos por margen de contribución.'},
  ];
  final Map<String,LumenBusiness> companies={};
  final Set<String> completedJobs={};
  final List<Map<String,dynamic>> history=[];
  int month=0, debt=0, installments=0, loanPayment=0, totalProfit=0, totalRevenue=0, totalInterest=0;
  int get assets=>companies.values.fold(0,(a,b)=>a+b.assets+b.reserve);
  int get netBusinessAssets=>assets-debt;
  int get totalBranches=>companies.values.fold(0,(a,b)=>a+b.branches);
  int number(String sector,String key)=>sectors[sector]![key] as int;
  String name(String sector)=>sectors[sector]!['name'] as String;
  int get loanLimit=>max(0,companies.values.fold<int>(0,(a,b)=>a+b.assets)~/2-debt);
  int? jobReward(String id,int answer){final jobs=starterJobs.where((j)=>j['id']==id);if(jobs.isEmpty||completedJobs.contains(id)||jobs.first['answer']!=answer)return null;completedJobs.add(id);return jobs.first['pay'] as int;}
  int? open(String sector,int cash){if(!sectors.containsKey(sector)||companies.containsKey(sector))return null;final cost=number(sector,'startup');if(cash<cost)return null;final b=LumenBusiness(sector)..assets=cost..price=number(sector,'price');companies[sector]=b;return cash-cost;}
  int? expand(String sector,int cash){final b=companies[sector];if(b==null||b.branches>=30)return null;final cost=number(sector,'expansion')*b.branches;if(cash<cost)return null;b.branches++;b.assets+=cost;return cash-cost;}
  bool configure(String sector,int price,int staff,int marketing){final b=companies[sector];if(b==null||staff<1||staff>b.branches*8||price<number(sector,'unit')~/2||price>number(sector,'price')*3||marketing<0||marketing>number(sector,'rent')*b.branches*4)return false;b.price=price;b.staff=staff;b.marketing=marketing;return true;}
  // Capacity is limited by both workers and branches. Units are produced/purchased to meet orders, not assumed sold from speculative stock.
  Map<String,int> forecast(String sector,{int? atMonth,bool estimate=false}){
    final b=companies[sector]!;final m=atMonth??month;
    final normal=number(sector,'price'),unit=number(sector,'unit'),rent=number(sector,'rent'),wage=number(sector,'wage');
    final totalCapacity=min(number(sector,'capacity')*b.branches,number(sector,'capacity')*b.staff);
    final capacity=max(0,totalCapacity-(contractedUnits['$m:$sector']??0));
    final cycle=estimate?100:85+((m*17+sector.codeUnits.fold<int>(0,(a,c)=>a+c))%31);
    final base=number(sector,'demand')*b.branches;
    final priceFactor=max(0,200-b.price*100~/normal);
    final ads=min(50,b.marketing*35~/max(1,rent*b.branches));
    final demand=base*cycle*(priceFactor+ads)~/10000;
    final sold=min(capacity,demand);
    final fixed=rent*b.branches+wage*b.staff+b.marketing;
    final variable=sold*unit;
    final revenue=sold*b.price;
    final pretax=revenue-variable-fixed,tax=max(0,pretax~/10);
    return {'capacity':capacity,'demand':demand,'sold':sold,'revenue':revenue,'variable':variable,'fixed':fixed,'tax':tax,'profit':pretax-tax,'workingCapital':variable+fixed,'breakEven':b.price>unit?(fixed+b.price-unit-1)~/(b.price-unit):-1,'marginPct':revenue==0?0:(pretax-tax)*100~/revenue};
  }
  int? borrow(int principal,int cash){if(principal<=0||principal>loanLimit||debt!=0)return null;debt=principal;installments=12;loanPayment=(principal+11)~/12;return cash+principal;}
  int get nextInterest=>debt==0?0:max(1,(debt*2+99)~/100);
  int get nextPrincipal=>min(debt,loanPayment);
  int? repayEarly(int amount,int cash){if(amount<=0||amount>debt||amount>cash)return null;debt-=amount;if(debt==0){installments=0;loanPayment=0;}return cash-amount;}
  // Contract sizes scale with invested capacity; require funding before delivery. Each unique contract can only be accepted once per month.
  final Set<String> contracts={};
  final Map<String,int> contractedUnits={};
  Map<String,int>? contractQuote(String sector){
    final b=companies[sector];if(b==null||contracts.contains('$month:$sector'))return null;
    final units=max(1,number(sector,'capacity')*min(b.branches,b.staff)~/2);
    final revenue=units*(number(sector,'price')*88~/100);
    final cost=units*number(sector,'unit');
    final profit=revenue-cost-max(0,(revenue-cost)~/10);
    return {'units':units,'revenue':revenue,'cost':cost,'profit':profit};
  }
  int? fulfill(String sector,int cash){final q=contractQuote(sector);if(q==null||cash<q['cost']!)return null;contracts.add('$month:$sector');contractedUnits['$month:$sector']=q['units']!;totalRevenue+=q['revenue']!;totalProfit+=q['profit']!;return cash+q['profit']!;}
  // Batch simulation: all companies settle one month together. No free overdraft; stop before an unfunded month.
  Map<String,int> advance(int cash,int requested){
    final count=requested.clamp(1,12).toInt();int completed=0,profit=0,revenue=0;
    if(companies.isEmpty)return {'cash':cash,'months':0,'profit':0,'revenue':0};
    for(var i=0;i<count;i++){
      final rows=companies.keys.map((k)=>forecast(k)).toList();
      final capital=rows.fold<int>(0,(a,b)=>a+b['workingCapital']!);
      final principal=nextPrincipal,interest=nextInterest;
      if(cash<capital+principal+interest)break;
      final earned=rows.fold<int>(0,(a,b)=>a+b['profit']!),sales=rows.fold<int>(0,(a,b)=>a+b['revenue']!);
      cash+=earned-principal-interest;debt-=principal;
      if(debt>0)installments=max(0,installments-1);else{installments=0;loanPayment=0;}
      month++;completed++;profit+=earned-interest;revenue+=sales;totalRevenue+=sales;totalProfit+=earned-interest;totalInterest+=interest;
      history.add({'month':month,'revenue':sales,'profit':earned-interest,'principal':principal,'interest':interest,'cash':cash,'debt':debt,'workingCapital':capital});
      if(history.length>60)history.removeAt(0);
    }
    return {'cash':cash,'months':completed,'profit':profit,'revenue':revenue};
  }
  Map<String,dynamic> toJson()=>{'companies':companies.map((k,v)=>MapEntry(k,v.toJson())),'jobs':completedJobs.toList(),'history':history,'month':month,'debt':debt,'installments':installments,'loanPayment':loanPayment,'totalProfit':totalProfit,'totalRevenue':totalRevenue,'totalInterest':totalInterest,'contracts':contracts.toList(),'contractedUnits':contractedUnits};
  factory LumenEconomy.fromJson(Map j){final s=LumenEconomy();if(j['companies'] is Map)for(final e in (j['companies'] as Map).entries){if(sectors.containsKey(e.key)&&e.value is Map)s.companies[e.key as String]=LumenBusiness.fromJson(e.value as Map);}int n(String k)=>j[k] is int?j[k] as int:0;s.month=n('month');s.debt=n('debt');s.installments=n('installments');s.loanPayment=n('loanPayment');s.totalProfit=n('totalProfit');s.totalRevenue=n('totalRevenue');s.totalInterest=n('totalInterest');if(j['jobs'] is List)s.completedJobs.addAll((j['jobs'] as List).whereType<String>());if(j['contracts'] is List)s.contracts.addAll((j['contracts'] as List).whereType<String>());if(j['contractedUnits'] is Map)for(final x in (j['contractedUnits'] as Map).entries){if(x.key is String&&x.value is int)s.contractedUnits[x.key as String]=x.value as int;}if(j['history'] is List)s.history.addAll((j['history'] as List).whereType<Map>().map((x)=>Map<String,dynamic>.from(x)));return s;}
  LumenEconomy();
}
