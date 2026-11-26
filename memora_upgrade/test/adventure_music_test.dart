import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:memora/adventure_music.dart';

void main(){
  test('remote music choices and fallback',(){
    expect(adventureMood('study','forja','boss'),'study');
    expect(adventureMood('invalid','mercado','boss'),'battle');
    expect(adventureMood(null,'torre','mentor'),'mystery');
    expect(adventureMood(null,'mercado','mentor'),'adventure');
  });
  test('original PCM loop has correct WAV header and nonzero audio',(){
    final bytes=synthesizeAdventureMusic('study');
    final data=ByteData.sublistView(bytes);
    expect(String.fromCharCodes(bytes.take(4)),'RIFF');
    expect(String.fromCharCodes(bytes.sublist(8,12)),'WAVE');
    expect(data.getUint32(24,Endian.little),22050);
    expect(data.getUint32(40,Endian.little),bytes.length-44);
    expect(bytes.skip(44).any((x)=>x!=0),isTrue);
  });
}
