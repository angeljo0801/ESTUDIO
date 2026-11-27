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
 test('numeric cases accept decimals and negative results without guessing',(){
  final s=ScenePath.parse({'numericAnswer':-54,'numericTolerance':0.001});
  expect(s.acceptsNumber('-54'),isTrue);expect(s.acceptsNumber('54'),isFalse);expect(s.acceptsNumber('NaN'),isFalse);
  final d=ScenePath.parse({'numericAnswer':63.33,'numericTolerance':0.01});
  expect(d.acceptsNumber('63,33'),isTrue);expect(d.acceptsNumber('63.33'),isTrue);expect(d.acceptsNumber('64'),isFalse);
 });
 test('mastery gating is opt in',(){expect(ScenePath.parse({'requireMastery':true}).requireMastery,isTrue);expect(ScenePath.parse({}).requireMastery,isFalse);});
 test('no resource deadlock',(){expect(ScenePath.parse({'decisions':[{'label':'A','outcome':'A','resources':-5},{'label':'B','outcome':'B','resources':-5}]}).decisions,ScenePath.defaults);});
}
