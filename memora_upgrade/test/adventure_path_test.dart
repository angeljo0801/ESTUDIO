import 'package:flutter_test/flutter_test.dart';
import 'package:memora/adventure_path.dart';
void main(){
 test('choices affect later scenes and persisted state',(){
  final s=ScenePath.parse({'decisions':[{'label':'A','outcome':'Pista','evidence':4,'flag':'clue'},{'label':'B','outcome':'Aliado','trust':3}],'reactions':{'clue':'Archivo descubierto'}});
  final a=const AdventurePath().apply(s.decisions.first), b=const AdventurePath().apply(s.decisions.last);
  expect(a.evidence,4);expect(b.trust,8);expect(a.endingTitle,isNot(b.endingTitle));expect(s.reaction(a),'Archivo descubierto');expect(AdventurePath.fromJson(a.toJson()).flags,['clue']);expect(a.resolve(false).resources,4);
 });
 test('finale distinguishes alliances, evidence and reserves',(){
  expect(const AdventurePath(trust:20,evidence:21,resources:5).finaleTitle,'El aliado legendario');
  expect(const AdventurePath(trust:8,evidence:21,resources:5).finaleTitle,'La verdad sin aplausos');
  expect(const AdventurePath(trust:20,evidence:10,resources:5).finaleTitle,'El protector de Nébula');
 });
 test('no resource deadlock',(){expect(ScenePath.parse({'decisions':[{'label':'A','outcome':'A','resources':-5},{'label':'B','outcome':'B','resources':-5}]}).decisions,ScenePath.defaults);});
}
