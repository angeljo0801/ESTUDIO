import 'dart:math';
import 'dart:typed_data';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

const adventureMusicMoods = {'adventure','study','mystery','battle','victory','silent'};

String adventureMood(String? requested, String biome, String role) {
  final mood = requested?.trim().toLowerCase();
  if (mood != null && adventureMusicMoods.contains(mood)) return mood;
  if (role == 'boss') return 'battle';
  if (role == 'rival' || biome == 'forja' || biome == 'torre') return 'mystery';
  return 'adventure';
}

/// Original instrumental loops, synthesized offline in an isolate.
/// WAV: mono, signed 16-bit PCM, 22050 Hz.
Uint8List synthesizeAdventureMusic(String mood) {
  const rate = 22050;
  final tempo = mood == 'battle' ? 112 : mood == 'victory' ? 96 : mood == 'study' ? 66 : mood == 'mystery' ? 72 : 84;
  final beat = 60.0 / tempo;
  final length = (32 * beat * rate).round();
  final out = ByteData(44 + length * 2);
  void ascii(int offset, String s) {
    for (var i = 0; i < s.length; i++) { out.setUint8(offset+i, s.codeUnitAt(i)); }
  }
  ascii(0,'RIFF'); out.setUint32(4,36+length*2,Endian.little);
  ascii(8,'WAVE'); ascii(12,'fmt '); out.setUint32(16,16,Endian.little);
  out.setUint16(20,1,Endian.little); out.setUint16(22,1,Endian.little);
  out.setUint32(24,rate,Endian.little); out.setUint32(28,rate*2,Endian.little);
  out.setUint16(32,2,Endian.little); out.setUint16(34,16,Endian.little);
  ascii(36,'data'); out.setUint32(40,length*2,Endian.little);
  final chords = mood == 'mystery' || mood == 'battle'
      ? const [[45,48,52],[41,45,48],[38,41,45],[43,46,50]]
      : mood == 'victory'
          ? const [[48,52,55],[43,47,50],[45,48,52],[41,45,48]]
          : const [[48,52,55],[45,48,52],[41,45,48],[43,47,50]];
  const pattern = [0,1,2,1,0,2,1,2];
  double hz(int midi) => 440 * pow(2,(midi-69)/12).toDouble();
  double env(double t,double duration) => min(1.0,min(t/.08,(duration-t)/.14)).clamp(0.0,1.0).toDouble();
  double tone(double f,double t) => sin(2*pi*f*t) + .18*sin(4*pi*f*t);
  final freq = chords.map((c)=>c.map(hz).toList()).toList();
  for (var i=0;i<length;i++) {
    final t=i/rate;
    final bar=(t/(4*beat)).floor().clamp(0,7).toInt();
    final local=t-bar*4*beat;
    final chord=freq[bar%4];
    final pad=env(local,4*beat);
    final noteDuration=beat/2;
    final step=(local/noteDuration).floor().clamp(0,7).toInt();
    final nt=local-step*noteDuration;
    final melody=chord[pattern[step]]*2;
    final pulse=env(nt,noteDuration)*exp(-nt*3);
    var sample=0.0;
    if(mood!='silent') {
      for(final f in chord) { sample+=.085*pad*tone(f,local); }
      sample+=.15*pad*sin(2*pi*chord.first*.5*local);
      sample+=(mood=='study'?.065:.15)*pulse*tone(melody,nt);
      if(mood=='battle') {
        final kickT=local%beat;
        sample+=.16*exp(-kickT*18)*sin(2*pi*(48*kickT+2*(1-exp(-kickT*24))));
      }
      final edge=min(1.0,min(t/.1,(length/rate-t)/.1));
      sample*=edge;
    }
    out.setInt16(44+i*2,(sample.clamp(-1.0,1.0)*32767).round(),Endian.little);
  }
  return out.buffer.asUint8List();
}

class AdventureMusicButton extends StatefulWidget {
  const AdventureMusicButton({super.key,required this.mood});
  final String mood;
  @override State<AdventureMusicButton> createState()=>_AdventureMusicButtonState();
}

class _AdventureMusicButtonState extends State<AdventureMusicButton> with WidgetsBindingObserver {
  final _player=AudioPlayer();
  final _tracks=<String,Uint8List>{};
  Future<void> _queue=Future<void>.value();
  double _volume=.18;
  bool _ready=false,_visible=false,_active=true,_disposed=false;
  String? _playing;
  int _revision=0;
  static const _pref='memora_adventure_music_volume';

  @override void initState(){
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    final lifecycle=WidgetsBinding.instance.lifecycleState;
    _active=lifecycle==null||lifecycle==AppLifecycleState.resumed;
    _load();
  }
  Future<void> _load() async {
    try {
      final prefs=await SharedPreferences.getInstance();
      if(!mounted)return;
      _volume=(prefs.getDouble(_pref)??.18).clamp(0.0,.5).toDouble();
    } catch (_) {}
    if(!mounted)return;
    setState(()=>_ready=true);
    _sync();
  }
  @override void didChangeDependencies(){
    super.didChangeDependencies();
    _visible=ModalRoute.isCurrentOf(context)??true;
    _sync();
  }
  @override void didUpdateWidget(covariant AdventureMusicButton oldWidget){
    super.didUpdateWidget(oldWidget);
    if(widget.mood!=oldWidget.mood)_sync();
  }
  @override void didChangeAppLifecycleState(AppLifecycleState state){
    _active=state==AppLifecycleState.resumed;
    _sync();
  }
  void _sync(){
    final rev=++_revision;
    _queue=_queue.then((_) async {
      if(_disposed||rev!=_revision)return;
      final mood=widget.mood;
      if(!_ready||!_visible||!_active||_volume==0||mood=='silent'){
        await _player.stop();_playing=null;return;
      }
      if(_playing==mood){await _player.setVolume(_volume);return;}
      await _player.stop();_playing=null;
      final bytes=_tracks[mood]??=await compute(synthesizeAdventureMusic,mood);
      if(_disposed||rev!=_revision)return;
      await _player.setAudioContext(AudioContext(android: const AudioContextAndroid(audioFocus: AndroidAudioFocus.none)));
      await _player.setReleaseMode(ReleaseMode.loop);
      await _player.play(BytesSource(bytes,mimeType:'audio/wav'),volume:_volume);
      _playing=mood;
    }).catchError((Object error,StackTrace stack){
      _playing=null;
      debugPrint('Memora music unavailable: $error');
    });
  }
  Future<void> _select(double value) async {
    if(!mounted)return;
    setState(()=>_volume=value);
    _sync();
    try{final prefs=await SharedPreferences.getInstance();await prefs.setDouble(_pref,value);}catch(_){}
  }
  @override void dispose(){
    _disposed=true;_revision++;
    WidgetsBinding.instance.removeObserver(this);
    _queue.whenComplete(()=>_player.dispose());
    super.dispose();
  }
  @override Widget build(BuildContext context)=>PopupMenuButton<double>(
    tooltip:'Música ambiental',
    icon:Icon(_volume==0?Icons.music_off:Icons.music_note),
    initialValue:_volume,
    onSelected:_select,
    itemBuilder:(_)=>const [
      PopupMenuItem(value:0.0,child:Text('Música desactivada')),
      PopupMenuItem(value:.08,child:Text('Música suave')),
      PopupMenuItem(value:.18,child:Text('Música normal')),
      PopupMenuItem(value:.35,child:Text('Música alta')),
    ],
  );
}
