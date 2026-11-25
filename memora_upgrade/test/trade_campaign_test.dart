import 'package:flutter_test/flutter_test.dart';
import 'package:memora/trade_campaign_page.dart';

const choice = TradeChoice('Open','Open the shop',5,3,0);
const day = TradeDay('Market','Kael','City','mercado','A new market day',6,20,15,10,[choice]);
const campaign = TradeCampaign('Test','Season','Intro','Crystal',1,300,100,350,65,4,150,180,[day,day]);

void main(){
  test('cash, inventory and accounting reconcile after trade',(){
    final first=TradeEngine.start(campaign,42);
    final next=TradeEngine.turn(campaign,first,choice:0,quantity:30,price:15,borrow:false);
    final row=next.history.single;
    final sold=row['sold'] as int;
    expect(next.cash,300-30*6-15+sold*15);
    expect(next.stock,30-sold);
    expect(next.inventoryCost,180-(row['cogs'] as int));
    expect(row['profit'],sold*15-(row['cogs'] as int)-15);
    expect(TradeState.fromJson(next.toJson()).cash,next.cash);
  });
  test('higher prices reduce demand; debt cannot be borrowed twice',(){
    final first=TradeEngine.start(campaign,42);
    expect(TradeEngine.forecast(first,day,choice,18),lessThan(TradeEngine.forecast(first,day,choice,15)));
    final next=TradeEngine.turn(campaign,first,choice:0,quantity:15,price:15,borrow:true);
    expect(next.debt,280);
    expect(next.loanUsed,isTrue);
    expect(()=>TradeEngine.turn(campaign,next,choice:0,quantity:1,price:15,borrow:true),throwsArgumentError);
    expect(()=>TradeEngine.turn(campaign,first,choice:0,quantity:100,price:15,borrow:false),throwsStateError);
  });
  test('liquidation repays debt and reputation affects ending',(){
    final rich=TradeState(cash:500,debt:100,seed:1,stock:10,reputation:80);
    expect(TradeEngine.finalCash(campaign,rich),440);
    expect(TradeEngine.ending(campaign,rich),'LA CORONA DEL COMERCIO');
    final lowRep=TradeState(cash:500,debt:100,seed:1,reputation:20);
    expect(TradeEngine.ending(campaign,lowRep),'EL MAGNATE SOLITARIO');
    expect(TradeEngine.ending(campaign,TradeState(cash:10,debt:100,seed:1)),'EL GREMIO CAE');
  });
}
