import 'package:flutter_test/flutter_test.dart';
import '../lib/dual_world_engine.dart';
void main(){
  test('elementos iguales y espíritu afín acumulan sinergia moderada',(){
    expect(DualState.synergy('fire','fire','fire'),2);
    expect(DualState.statusChance({'statusChance':20},2),36);
    expect(DualState.synergy('neutral','neutral','neutral'),0);
    expect(DualState.reaction('water','lightning'),true);
  });
  test('precisión favorece crítico y fallo base bajo',(){
    expect(DualState.baseMiss(0),2);
    expect(DualState.criticalChance({'precision':100}),greaterThan(DualState.criticalChance({'precision':80})));
  });
  test('resistencia espiritual pequeña y persistente',(){
    final s=DualState()..spirits.add('a');
    expect(s.bindCombatSpirit({'id':'a','element':'fire','damage':8},'fusion'),true);
    expect(s.resistanceTo('fire',{'fire':20}),23);
    expect(s.resistanceTo('water',{}),0);
    final copy=DualState.fromJson(s.toJson());
    expect(copy.spiritElement,'fire');
  });
  test('magia consume estamina y derrota por agotamiento',(){
    final s=DualState()..skills.add('x')..stamina=2..intelligence=10;
    s.startBattle(0,999);
    final result=s.action({'id':'x','type':'attack','magic':true,'cost':2,'damage':1,'minIntelligence':0},{'id':'enemy','hp':999,'attack':1,'defense':0});
    expect(s.energy,0);expect(s.inBattle,false);expect(result,contains('agotamiento'));
  });
}
