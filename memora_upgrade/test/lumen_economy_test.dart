import 'package:flutter_test/flutter_test.dart';
import 'package:memora/lumen_economy.dart';
import 'package:memora/dual_world_engine.dart';
void main(){
 test('starter capital is earned only once',(){final e=LumenEconomy();expect(e.jobReward('margin',0),isNull);expect(e.jobReward('margin',25),120);expect(e.jobReward('margin',25),isNull);});
 test('formation, batch operations and no overdraft',(){final e=LumenEconomy();expect(e.open('retail',299),isNull);expect(e.open('retail',1500),1200);final q=e.forecast('retail');expect(q['profit'],greaterThan(0));expect(e.advance(0,12)['months'],0);final result=e.advance(1200,12);expect(result['months'],12);expect(result['cash'],greaterThan(1200));expect(LumenEconomy.fromJson(e.toJson()).month,12);});
 test('loan principal is not profit and company capacity increases with branches and staffing',(){final e=LumenEconomy();expect(e.open('retail',2000),1700);expect(e.borrow(150,1700),1850);expect(e.totalProfit,0);expect(e.advance(1850,12)['months'],12);expect(e.debt,0);expect(e.expand('retail',2000),1550);expect(e.configure('retail',16,2,0),true);expect(e.forecast('retail')['capacity'],200);});
 test('contract pays once per month, and requires working capital',(){final e=LumenEconomy();e.open('retail',1000);expect(e.fulfill('retail',0),isNull);expect(e.fulfill('retail',3000),greaterThan(3000));expect(e.fulfill('retail',3000),isNull);});
 test('return resets businesses and debt but retains intelligence',(){final s=DualState();s.intelligence=25;s.economy.open('retail',1000);s.economy.borrow(150,0);expect(DualState.fromJson(s.toJson()).economy.companies.length,1);final r=s.returnToBeginning();expect(r.economy.companies,isEmpty);expect(r.economy.debt,0);expect(r.intelligence,25);});
}
