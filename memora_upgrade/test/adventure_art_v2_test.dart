import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:memora/nebula_art.dart';
void main(){
  final webp=base64Encode([82,73,70,70,4,0,0,0,87,69,66,80]);
  Map<String,dynamic> part(String adventure,String id)=>{'schema':2,'kind':'memora_adventure_art_v2','adventure':adventure,'assets':{id:webp}};
  test('combine independent art parts',(){
    expect(AdventureArtStore.mergeParts([part('marketing','city'),part('marketing','mentor')],'marketing').keys.toSet(),{'city','mentor'});
  });
  test('reject foreign and duplicate assets',(){
    expect(()=>AdventureArtStore.mergeParts([part('finance','city')],'marketing'),throwsFormatException);
    expect(()=>AdventureArtStore.mergeParts([part('marketing','city'),part('marketing','city')],'marketing'),throwsFormatException);
  });
  test('generic scene positions are bounded',(){
    final v=AdventureVisualSpec.parse({'background':'future_city','actors':[{'id':'mentor','expression':'happy','position':5,'scale':8}],'height':900})!;
    expect(v.background,'future_city');expect(v.actors.single.position,1);expect(v.actors.single.scale,1.5);expect(v.height,420);
  });
  test('legacy Nébula remains isolated',(){
    expect(AdventureArtStore.isNebula('chatgpt_example_nebula-finanzas-rpg'),isTrue);
    expect(AdventureArtStore.isNebula('chatgpt_example_marketing'),isFalse);
  });
}
