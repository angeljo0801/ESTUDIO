import 'package:flutter_test/flutter_test.dart';
import 'package:memora/dual_world_engine.dart';
void main(){
 test('world travel, reading once and exercise cap',(){final s=DualState();expect(s.travel(),true);expect(s.world,'trade');s.place='Mercado';expect(s.travel(),false);expect(s.read('book',0,5),true);expect(s.read('book',0,5),false);for(var i=1;i<5;i++){s.read('book',i,5);}expect(s.intelligence,10);expect(s.workout('2026-11-27'),true);expect(s.workout('2026-11-27'),false);expect(s.workout('2026-11-26'),false);expect(s.strength,6);});
 test('cash is conserved and skills cannot be purchased twice',(){final s=DualState();s.commission();final r=s.trade(3,12,2,5,2)!;expect(r['profit'],12);expect(s.cash,37);expect(s.stock,1);s.appraised.add('shield');expect(s.buySkill('shield',30),true);expect(s.buySkill('shield',30),false);expect(s.cash,7);});
 test('exams unlock rewards once and persisted state survives',(){final s=DualState();expect(s.rewardExam('a',false),0);expect(s.rewardExam('a',true),90);expect(s.rewardExam('a',true),90);expect(s.cash,0);expect(s.claimGuild('a'),90);expect(s.claimGuild('a'),0);final copy=DualState.fromJson(s.toJson());expect(copy.grades['a'],90);expect(copy.cash,90);});
}
