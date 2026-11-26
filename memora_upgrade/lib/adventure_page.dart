import 'dart:math';
import 'dart:convert';
import 'package:flutter/services.dart';

import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'adventure_engine.dart';
import 'guide_store.dart';
import 'models.dart';
import 'trade_campaign_page.dart';
import 'nebula_art.dart';

/// A free, offline, animated interactive lesson - not an MP4 generator.
class AdventurePage extends StatefulWidget {
  const AdventurePage({super.key, required this.store, required this.guide});

  final GuideStore store;
  final StudyGuide guide;

  @override
  State<AdventurePage> createState() => _AdventurePageState();
}

class _AdventurePageState extends State<AdventurePage> {
  int _unlocked = 1;
  int _xp = 0;
  bool _loading = true;
  late final List<AdventureEpisode> _episodes;

  String get _key => 'memora_adventure_${widget.guide.id}';

  @override
  void initState() {
    super.initState();
    _episodes = AdventureEngine.episodesFor(widget.guide);
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() {
      _unlocked = max(1, prefs.getInt('${_key}_unlocked') ?? 1);
      _xp = prefs.getInt('${_key}_xp') ?? 0;
      _loading = false;
    });
  }

  Future<void> _open(AdventureEpisode episode) async {
    await Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => _EpisodePlayer(
        store: widget.store,
        guide: widget.guide,
        episode: episode,
        allCards: widget.guide.cards,
        progressKey: _key,
      ),
    ));
    if (mounted) await _load();
  }

  @override
  Widget build(BuildContext context) {
    final campaign = TradeCampaign.fromGuide(widget.guide);
    if (campaign != null) return TradeCampaignPage(guide: widget.guide, campaign: campaign, sceneBuilder: (day) => _TradeSceneArt(day: day));
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Memora Aventuras')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
              children: [
                Container(
                  padding: const EdgeInsets.all(22),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(colors: [cs.primaryContainer, cs.tertiaryContainer]),
                    borderRadius: BorderRadius.circular(25),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('🎬  TEMPORADA DE ESTUDIO', style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 1)),
                      const SizedBox(height: 10),
                      Text(widget.guide.title, style: const TextStyle(fontSize: 23, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 9),
                      const Text('Historias animadas, voz, preguntas y puntos. Todo basado en las tarjetas de tu guía.'),
                      const SizedBox(height: 15),
                      Wrap(spacing: 9, runSpacing: 8, children: [
                        Chip(avatar: const Icon(Icons.stars_rounded, size: 18), label: Text('$_xp XP')),
                        Chip(avatar: const Icon(Icons.movie_filter_rounded, size: 18), label: Text('${_episodes.length} episodios')),
                        Chip(avatar: const Icon(Icons.offline_bolt_rounded, size: 18), label: const Text('Sin API de pago')),
                      ]),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                const Text('Elige tu próximo episodio', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 19)),
                const SizedBox(height: 10),
                if (_episodes.isEmpty)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(18),
                      child: Text('Esta guía todavía no tiene preguntas utilizables. Crea o corrige sus tarjetas para comenzar la aventura.'),
                    ),
                  ),
                for (final episode in _episodes)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 9),
                    child: Card(
                      child: ListTile(
                        contentPadding: const EdgeInsets.fromLTRB(16, 10, 12, 10),
                        leading: CircleAvatar(
                          radius: 27,
                          backgroundColor: cs.primaryContainer,
                          child: Text(episode.number > _unlocked ? '🔒' : episode.icon,
                              style: const TextStyle(fontSize: 24)),
                        ),
                        title: Text('Episodio ${episode.number}',
                            style: const TextStyle(fontWeight: FontWeight.w800)),
                        subtitle: Text(_Scene.from(episode.cards.first).arc ?? episode.title,
                            maxLines: 2, overflow: TextOverflow.ellipsis),
                        trailing: Icon(episode.number > _unlocked
                            ? Icons.lock_outline_rounded
                            : episode.number < _unlocked
                                ? Icons.check_circle_outline_rounded
                                : Icons.play_circle_fill_rounded),
                        enabled: episode.number <= _unlocked,
                        onTap: episode.number <= _unlocked ? () => _open(episode) : null,
                      ),
                    ),
                  ),
                const SizedBox(height: 8),
                const Text(
                  'Cada episodio contiene hasta tres desafíos. Las respuestas se guardan en el repaso de Memora; lo que falles aparecerá antes para volver a practicar.',
                  style: TextStyle(height: 1.4),
                ),
              ],
            ),
    );
  }
}

class _EpisodePlayer extends StatefulWidget {
  const _EpisodePlayer({
    required this.store,
    required this.guide,
    required this.episode,
    required this.allCards,
    required this.progressKey,
  });

  final GuideStore store;
  final StudyGuide guide;
  final AdventureEpisode episode;
  final List<StudyCard> allCards;
  final String progressKey;

  @override
  State<_EpisodePlayer> createState() => _EpisodePlayerState();
}

class _EpisodePlayerState extends State<_EpisodePlayer> with SingleTickerProviderStateMixin {
  late final AnimationController _motion;
  int _dialogueIndex = 0;
  int _correctCount = 0;
  bool _completing = false;
  _Scene get _scene => _Scene.from(_card);
  List<String> get _dialogues => _scene.dialogue.isNotEmpty ? _scene.dialogue : [AdventureEngine.storyHook(_step), _card.answer];
  final FlutterTts _tts = FlutterTts();
  int _step = 0;
  int _earned = 0;
  bool _voiceOn = true;
  bool _finished = false;
  bool _rated = false;
  bool _needsSelfGrade = false;
  bool _saving = false;
  bool? _wasCorrect;
  String? _selected;
  String _stage = 'story';

  StudyCard get _card => widget.episode.cards[_step];

  @override
  void initState() {
    super.initState();
    _motion = AnimationController(vsync: this, duration: const Duration(seconds: 9))..repeat();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _say(_narrative());
    });
  }

  @override
  void dispose() {
    _motion.dispose();
    _tts.stop();
    super.dispose();
  }

  String _narrative() => _dialogues[_dialogueIndex.clamp(0, _dialogues.length - 1).toInt()];

  Future<void> _say(String text) async {
    if (!_voiceOn || !mounted) return;
    try {
      await _tts.stop();
      final english = RegExp(r'\b(the|what|which|with|from|this|that|how)\b', caseSensitive: false)
              .allMatches(text).length >= 2;
      await _tts.setLanguage(english ? 'en-US' : 'es-ES');
      await _tts.setSpeechRate(0.47);
      await _tts.setPitch(_scene.role == 'boss' ? .84 : _scene.role == 'rival' ? 1.17 : .98);
      if (_voiceOn && mounted) await _tts.speak(text);
    } catch (_) {
      // Device TTS voice packs can be missing; the lesson remains usable.
    }
  }

  void _changeStage(String next, {String? voiceText}) {
    setState(() => _stage = next);
    if (voiceText != null) _say(voiceText);
  }

  Future<void> _answer(bool correct, {String? selected}) async {
    if (_saving || _rated) return;
    setState(() {
      _saving = true;
      _rated = true;
      _needsSelfGrade = false;
      _wasCorrect = correct;
      _selected = selected;
      _stage = 'feedback';
      _earned += correct ? 100 : 20;
      if (correct) _correctCount++;
      HapticFeedback.mediumImpact();
    });
    _tts.stop();
    _card.rate(correct ? 2 : 0);
    widget.guide.lastStudiedAt = DateTime.now();
    try {
      await widget.store.update(widget.guide);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No pude guardar el repaso; revisa el almacenamiento.')),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
    if (mounted) _say(correct ? '¡Excelente! ${_card.answer}' : 'Seguimos aprendiendo. ${_card.answer}');
  }

  Future<void> _complete() async {
    if (_completing) return;
    _completing = true;
    _tts.stop();
    final prefs = await SharedPreferences.getInstance();
    final bestKey = '${widget.progressKey}_best_${widget.episode.number}';
    final previousBest = prefs.getInt(bestKey) ?? 0;
    final extra = max(0, _earned - previousBest);
    await prefs.setInt(bestKey, max(previousBest, _earned));
    await prefs.setInt(widget.progressKey + '_xp',
        (prefs.getInt(widget.progressKey + '_xp') ?? 0) + extra);
    final next = widget.episode.number + 1;
    final unlocked = prefs.getInt(widget.progressKey + '_unlocked') ?? 1;
    if (next > unlocked) {
      await prefs.setInt(widget.progressKey + '_unlocked', next);
    }
    if (mounted) setState(() => _finished = true);
  }

  void _next() {
    if (_step + 1 >= widget.episode.cards.length) {
      _complete();
      return;
    }
    setState(() {
      _step++;
      _dialogueIndex = 0;
      _stage = 'story';
      _rated = false;
      _wasCorrect = null;
      _needsSelfGrade = false;
      _selected = null;
    });
    _say(_narrative());
  }

  Widget _world(ColorScheme cs) {
    final scene = _scene;
    final palette = scene.biome == 'forja' ? const [Color(0xff411c31),Color(0xffe98443)] :
      scene.biome == 'torre' ? const [Color(0xff171f4b),Color(0xff9178ff)] :
      const [Color(0xff193447),Color(0xff62b7b5)];
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: SizedBox(height:244,child:Stack(fit:StackFit.expand,children:[
        AnimatedBuilder(animation:_motion,builder:(context,_)=>CustomPaint(
          painter:_WorldPainter(palette,scene.biome,scene.role,_motion.value))),
        Positioned(top:12,left:12,right:12,child:Row(children:[
          Container(padding:const EdgeInsets.symmetric(horizontal:10,vertical:6),
            decoration:BoxDecoration(color:const Color(0xdd0b1424),borderRadius:BorderRadius.circular(8)),
            child:Text(scene.role=='boss'?'JEFE DE ARCO':'MISIÓN ${_step+1}',
              style:const TextStyle(color:Colors.white,fontSize:11,fontWeight:FontWeight.w900,letterSpacing:1.1))),
          const Spacer(),const Icon(Icons.auto_awesome,color:Color(0xffffdf9b),size:19),
        ])),
        Positioned(bottom:0,left:0,right:0,child:Container(
          padding:const EdgeInsets.fromLTRB(14,22,14,12),
          decoration:const BoxDecoration(gradient:LinearGradient(begin:Alignment.topCenter,end:Alignment.bottomCenter,colors:[Colors.transparent,Color(0xf20b1424)])),
          child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
            Text(scene.location??'Santuario del conocimiento',style:const TextStyle(color:Colors.white,fontSize:18,fontWeight:FontWeight.w800)),
            Text(scene.speaker??'Kael',style:const TextStyle(color:Color(0xfff9d499),fontSize:13,fontWeight:FontWeight.w700)),
          ]),
        )),
      ])),
    );
  }

  Widget _story(ColorScheme cs) => Column(
    key: ValueKey('story-$_step-$_dialogueIndex'),
    crossAxisAlignment:CrossAxisAlignment.stretch,
    children:[
      Row(children:[
        Icon(_scene.role=='rival'?Icons.flash_on_rounded:Icons.chat_bubble_outline_rounded,color:cs.primary,size:19),
        const SizedBox(width:8),
        Expanded(child:Text(_scene.speaker??'Kael · Mentor',style:TextStyle(color:cs.primary,fontWeight:FontWeight.w900,letterSpacing:1))),
        Text('${_dialogueIndex+1}/${_dialogues.length}',style:TextStyle(color:cs.onSurfaceVariant)),
      ]),
      const SizedBox(height:12),
      Container(padding:const EdgeInsets.all(18),
        decoration:BoxDecoration(color:cs.surfaceContainerHigh,borderRadius:BorderRadius.circular(16),border:Border.all(color:cs.primary.withValues(alpha:.25))),
        child:TweenAnimationBuilder<double>(
          key:ValueKey('dialogue-$_step-$_dialogueIndex'),
          tween:Tween(begin:0.0,end:1.0),
          duration:Duration(milliseconds:min(2600,max(350,_narrative().length*13))),
          builder:(context,value,_)=>Text(_narrative().substring(0,(_narrative().length*value).floor().clamp(0,_narrative().length).toInt()),
            style:const TextStyle(fontSize:18,height:1.5,fontWeight:FontWeight.w500)),
        ),
      ),
      const SizedBox(height:16),
      FilledButton.icon(onPressed:(){
        if(_dialogueIndex+1<_dialogues.length){
          setState(()=>_dialogueIndex++);
          _say(_narrative());
        }else{
          _changeStage('challenge',voiceText:_card.question);
        }
      },icon:Icon(_dialogueIndex+1<_dialogues.length?Icons.arrow_forward_rounded:Icons.sports_esports_rounded),
        label:Text(_dialogueIndex+1<_dialogues.length?'Continuar diálogo':'Aceptar misión')),
      if(_dialogueIndex+1<_dialogues.length)
        TextButton(onPressed:()=>_changeStage('challenge',voiceText:_card.question),child:const Text('Ir al desafío')),
    ],
  );

  Widget _challenge(ColorScheme cs) {
    final choices = _scene.validChoices(_card) ?? AdventureEngine.choicesFor(_card, widget.allCards);
    return Column(
      key: const ValueKey('challenge'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(_scene.role=='boss'?'BATALLA CONTRA EL GUARDIÁN':'TU DECISIÓN',style:const TextStyle(fontWeight:FontWeight.w900,letterSpacing:1)),
        const SizedBox(height: 14),
        Text(_card.question, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
        const SizedBox(height: 18),
        if (choices.isNotEmpty)
          for (final choice in choices)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: OutlinedButton(
                onPressed: _saving ? null : () => _answer(choice == _card.answer.trim(), selected: choice),
                style: OutlinedButton.styleFrom(padding: const EdgeInsets.all(16),
                    alignment: Alignment.centerLeft),
                child: Row(children:[CircleAvatar(radius:15,backgroundColor:cs.primaryContainer,child:Text(String.fromCharCode(65+choices.indexOf(choice)),style:TextStyle(fontWeight:FontWeight.bold,color:cs.onPrimaryContainer))),const SizedBox(width:12),Expanded(child:Text(choice,style:const TextStyle(fontSize:16)))]),
              ),
            )
        else ...[
          const Text('Trata de responder en voz alta o mentalmente antes de revelar la respuesta.'),
          const SizedBox(height: 15),
          FilledButton.icon(
            onPressed: () {
              _tts.stop();
              setState(() {
                _stage = 'feedback';
                _needsSelfGrade = true;
              });
            },
            icon: const Icon(Icons.visibility_rounded),
            label: const Text('Ver la respuesta'),
          ),
        ],
      ],
    );
  }

  Widget _feedback(ColorScheme cs) => Column(
        key: const ValueKey('feedback'),
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(_needsSelfGrade
              ? '🎯 Comprueba tu respuesta'
              : _wasCorrect == true ? '¡MISIÓN SUPERADA! +100 XP' : '¡REAGRÚPATE! +20 XP',
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
          const SizedBox(height: 14),
          if (_selected != null && _wasCorrect == false)
            Text('Elegiste: $_selected', style: TextStyle(color: cs.error)),
          Card(
            color: cs.surfaceContainerHigh,
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('Respuesta de la guía', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 12),
                SelectableText(_scene.explanation ?? _card.answer,style:const TextStyle(fontSize:19,height:1.4)),
              ]),
            ),
          ),
          const SizedBox(height: 15),
          if (_needsSelfGrade) ...[
            FilledButton.icon(
              onPressed: _saving ? null : () => _answer(true),
              icon: const Icon(Icons.check_rounded),
              label: const Text('La recordé bien'),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _saving ? null : () => _answer(false),
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Necesito repasarla'),
            ),
          ] else
            FilledButton.icon(
              onPressed: _saving ? null : _next,
              icon: const Icon(Icons.arrow_forward_rounded),
              label: Text(_step + 1 == widget.episode.cards.length
                  ? 'Terminar episodio' : 'Siguiente escena'),
            ),
        ],
      );

  Widget _ending() => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('🏆', style: TextStyle(fontSize: 90)),
            const SizedBox(height: 12),
            const Text('¡Episodio completado!', textAlign: TextAlign.center,
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 24)),
            const SizedBox(height: 12),
            Text('Conseguiste $_earned XP en esta partida',
                textAlign: TextAlign.center, style: const TextStyle(fontSize: 18)),
            const SizedBox(height:12),
            Text('$_correctCount/${widget.episode.cards.length} misiones superadas · ${_correctCount == widget.episode.cards.length ? 'Rango S' : _correctCount > 0 ? 'Rango A' : 'En entrenamiento'}',textAlign:TextAlign.center,style:const TextStyle(fontWeight:FontWeight.w800)),
            const SizedBox(height: 15),
            const Text('Tus resultados se añadieron al repaso espaciado de Memora.',
                textAlign: TextAlign.center),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: () => Navigator.pop(context),
              icon: const Icon(Icons.list_rounded),
              label: const Text('Volver a episodios'),
            ),
          ],
        ),
      );

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: Text('Episodio ${widget.episode.number}'),
        actions: [
          IconButton(
            tooltip: _voiceOn ? 'Silenciar narración' : 'Activar narración',
            icon: Icon(_voiceOn ? Icons.volume_up_rounded : Icons.volume_off_rounded),
            onPressed: () {
              setState(() => _voiceOn = !_voiceOn);
              if (!_voiceOn) {
                _tts.stop();
              } else if (!_finished) {
                _say(_stage == 'story' ? _narrative()
                    : _stage == 'challenge' ? _card.question : _card.answer);
              }
            },
          ),
        ],
      ),
      body: SafeArea(
        child: _finished ? Padding(padding: const EdgeInsets.all(25), child: _ending()) :
          ListView(
            padding: const EdgeInsets.fromLTRB(18, 8, 18, 28),
            children: [
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                Text('Escena ${_step + 1} de ${widget.episode.cards.length}'),
                Text('⭐ $_earned XP', style: const TextStyle(fontWeight: FontWeight.bold)),
              ]),
              const SizedBox(height: 9),
              LinearProgressIndicator(
                value: (_step + (_stage == 'story' ? 0 : _stage == 'challenge' ? .5 : 1)) /
                    widget.episode.cards.length,
                minHeight: 8,
                borderRadius: BorderRadius.circular(8),
              ),
              const SizedBox(height: 23),
              _world(cs),
              const SizedBox(height: 24),
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 320),
                transitionBuilder:(child,animation)=>FadeTransition(opacity:animation,child:SlideTransition(position:Tween<Offset>(begin:const Offset(.04,.03),end:Offset.zero).animate(animation),child:child)),
                child: _stage == 'story' ? _story(cs)
                    : _stage == 'challenge' ? _challenge(cs) : _feedback(cs),
              ),
            ],
          ),
      ),
    );
  }
}


class _Scene {
  const _Scene({this.arc,this.location,this.speaker,this.biome='mercado',this.role='mentor',this.dialogue=const [],this.choices=const [],this.explanation});
  final String? arc,location,speaker,explanation;
  final String biome,role;
  final List<String> dialogue,choices;
  static _Scene from(StudyCard card){
    final raw=card.adventureStory.trim();
    if(raw.isEmpty)return const _Scene();
    try{
      final v=jsonDecode(raw);
      if(v is Map && v['kind']=='memora_scene_v1'){
        String? str(String k)=>v[k] is String?v[k] as String:null;
        List<String> list(String k)=>v[k] is List?(v[k] as List).whereType<String>().where((x)=>x.trim().isNotEmpty).take(8).toList():<String>[];
        return _Scene(arc:str('arc'),location:str('location'),speaker:str('speaker'),biome:str('biome')??'mercado',role:str('role')??'mentor',dialogue:list('dialogue'),choices:list('choices'),explanation:str('explanation'));
      }
    }catch(_){}
    return _Scene(dialogue:[raw,card.answer]);
  }
  List<String>? validChoices(StudyCard card){
    final clean=choices.map((x)=>x.trim()).toSet().toList();
    return clean.length>=2&&clean.length<=6&&clean.contains(card.answer.trim())?clean:null;
  }
}

/// Animated original vector scenery and portrait, rendered offline.
class _WorldPainter extends CustomPainter {
  _WorldPainter(this.colors,this.biome,this.role,this.phase,{this.duo=false});
  final bool duo;
  final List<Color> colors;
  final String biome,role;
  final double phase;
  @override
  void paint(Canvas canvas,Size size){
    final w=size.width,h=size.height,p=Paint();
    p.shader=LinearGradient(begin:Alignment.topCenter,end:Alignment.bottomCenter,colors:colors).createShader(Offset.zero&size);
    canvas.drawRect(Offset.zero&size,p);p.shader=null;
    p.color=const Color(0xfff7dca5).withValues(alpha:.8);canvas.drawCircle(Offset(w*.76,h*.22),h*.13,p);
    for(var i=0;i<13;i++){
      final x=i*w/12-w*.07,bh=h*(.14+((i*7)%5)*.045),bw=w*.09;
      p.color=Color.lerp(colors.first,const Color(0xff0d1528),.45)!;
      canvas.drawRect(Rect.fromLTWH(x,h*.66-bh,bw,bh),p);
      final roof=Path()..moveTo(x-bw*.1,h*.66-bh)..lineTo(x+bw*.5,h*.66-bh-bw*.46)..lineTo(x+bw*1.1,h*.66-bh)..close();
      canvas.drawPath(roof,p);
      p.color=colors.last.withValues(alpha:.48);canvas.drawRect(Rect.fromLTWH(x+bw*.35,h*.66-bh*.65,bw*.18,bh*.2),p);
    }
    p.color=const Color(0xff102237).withValues(alpha:.8);
    canvas.drawPath(Path()..moveTo(0,h*.73)..quadraticBezierTo(w*.47,h*.57,w,h*.73)..lineTo(w,h)..lineTo(0,h)..close(),p);
    for(var i=0;i<11;i++){
      final x=((i*.127+phase*.13)%1)*w,y=h*(.12+((i*17)%61)/100);
      p.color=const Color(0xfffbe6a8).withValues(alpha:.25+.5*(.5+.5*sin(phase*2*pi+i)));
      canvas.drawCircle(Offset(x,y),1.2+(i%3)*.6,p);
    }
    void portrait(String role,double x,double y,double scale){
    canvas.save();canvas.translate(x,y);canvas.scale(scale);
    final hair=role=='boss'?const Color(0xffd9d5ff):role=='rival'?const Color(0xffd88656):role=='hero'?const Color(0xff18223d):role=='ally'?const Color(0xffa75c37):const Color(0xff31455d);
    final cloak=role=='boss'?const Color(0xff563f85):role=='rival'?const Color(0xff913f48):role=='hero'?const Color(0xff224a91):role=='ally'?const Color(0xff557e60):const Color(0xff316b72);
    p.color=cloak;canvas.drawPath(Path()..moveTo(-22,25)..quadraticBezierTo(-65,32,-75,88)..lineTo(75,88)..quadraticBezierTo(61,32,22,25)..close(),p);
    p.color=const Color(0xffeac47d);p.strokeWidth=2.2;canvas.drawLine(const Offset(-39,38),const Offset(-62,82),p);canvas.drawLine(const Offset(39,38),const Offset(62,82),p);
    p.color=const Color(0xff17263b);canvas.drawPath(Path()..moveTo(-38,32)..lineTo(0,63)..lineTo(38,32)..lineTo(25,76)..lineTo(-25,76)..close(),p);
    p.color=const Color(0xffd2a381);canvas.drawRRect(RRect.fromRectAndRadius(const Rect.fromLTWH(-11,12,22,31),const Radius.circular(8)),p);
    p.color=hair;canvas.drawOval(const Rect.fromLTWH(-46,-73,92,91),p);
    p.color=const Color(0xfff0c5a2);
    canvas.drawPath(Path()..moveTo(-34,-39)..quadraticBezierTo(-36,1,-17,21)..lineTo(0,31)..lineTo(17,21)..quadraticBezierTo(36,1,34,-39)..close(),p);
    p.color=hair;canvas.drawPath(Path()..moveTo(-43,-44)..lineTo(-49,-72)..lineTo(-20,-69)..lineTo(-6,-85)..lineTo(13,-72)..lineTo(42,-76)..lineTo(49,-42)..lineTo(24,-19)..lineTo(27,-51)..lineTo(4,-25)..lineTo(0,-52)..lineTo(-24,-26)..lineTo(-18,-49)..lineTo(-40,-23)..close(),p);
    p.color=const Color(0xffcf956e).withValues(alpha:.7);canvas.drawPath(Path()..moveTo(0,-6)..lineTo(-3,5)..lineTo(3,5)..close(),p);
    if(role=='ally'||role=='boss'){p.color=hair;canvas.drawPath(Path()..moveTo(-38,-30)..quadraticBezierTo(-52,10,-48,44)..lineTo(-31,27)..lineTo(-29,-14)..close(),p);canvas.drawPath(Path()..moveTo(38,-30)..quadraticBezierTo(52,10,48,44)..lineTo(31,27)..lineTo(29,-14)..close(),p);}
    for(final x in [-17.0,17.0]){
      p.color=const Color(0xfffff6e9);canvas.drawOval(Rect.fromCenter(center:Offset(x,-9),width:18,height:10),p);
      p.color=role=='boss'?const Color(0xff8a62cc):const Color(0xff327687);canvas.drawOval(Rect.fromCenter(center:Offset(x,-9),width:8,height:9),p);
      p.color=const Color(0xff142031);canvas.drawCircle(Offset(x,-9),2.6,p);p.strokeWidth=1.6;canvas.drawLine(Offset(x-9,-15),Offset(x+8,-16),p);p.color=Colors.white;canvas.drawCircle(Offset(x-1.6,-11),1.3,p);
    }
    p.color=const Color(0xffa45f59);p.strokeWidth=1.5;p.style=PaintingStyle.stroke;canvas.drawArc(const Rect.fromLTWH(-7,8,14,8),.25,2.5,false,p);p.style=PaintingStyle.fill;
    p.color=const Color(0xffeac47d);canvas.drawCircle(const Offset(0,60),5,p);canvas.restore();
    }
    final scale=min(w/330,h/240);
    if(duo){portrait('hero',w*.27,h*.46+sin(phase*2*pi)*2,scale*.98);portrait(role,w*.73,h*.46+cos(phase*2*pi)*2,scale*.98);}
    else{portrait(role,w*.49,h*.45+sin(phase*2*pi)*3,scale);}
  }
  @override
  bool shouldRepaint(covariant _WorldPainter oldDelegate)=>oldDelegate.phase!=phase||oldDelegate.biome!=biome||oldDelegate.role!=role||oldDelegate.duo!=duo;
}



class _TradeSceneArt extends StatelessWidget {
  const _TradeSceneArt({required this.day});
  final TradeDay day;
  @override Widget build(BuildContext context){
    final id=day.speaker.toLowerCase().trim();
    return ClipRRect(borderRadius:BorderRadius.circular(16),child:Container(
      height:235,decoration:BoxDecoration(gradient:LinearGradient(colors:day.biome=='torre'?const [Color(0xff1b1837),Color(0xff51406b)]:day.biome=='forja'?const [Color(0xff281e30),Color(0xff78462d)]:const [Color(0xff101c31),Color(0xff28474f)])),
      child:Row(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
        Expanded(child:_portrait('hero','TÚ · Heredero')),
        const SizedBox(width:2),
        Expanded(child:_portrait(id,day.speaker)),
      ]),
    ));
  }
  Widget _portrait(String id,String label)=>Stack(fit:StackFit.expand,children:[
    AnimatedSwitcher(duration:const Duration(milliseconds:320),child:AnimePortrait(key:ValueKey(id),id:id)),
    Positioned(bottom:0,left:0,right:0,child:Container(padding:const EdgeInsets.symmetric(horizontal:8,vertical:10),decoration:const BoxDecoration(gradient:LinearGradient(begin:Alignment.topCenter,end:Alignment.bottomCenter,colors:[Colors.transparent,Color(0xf5101a2b)])),child:Text(label,textAlign:TextAlign.center,style:const TextStyle(color:Color(0xfff6ce85),fontWeight:FontWeight.w900)))),
  ]);
}
