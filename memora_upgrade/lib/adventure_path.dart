class StoryDecision {
  const StoryDecision(this.label,this.outcome,{this.trust=0,this.resources=0,this.evidence=0,this.flag=''});
  final String label,outcome,flag;
  final int trust,resources,evidence;
  static String signed(int n)=>n>=0?'+'+n.toString():n.toString();
  String get effectSummary=>'Confianza '+signed(trust)+' · Recursos '+signed(resources)+' · Pruebas '+signed(evidence);
  static StoryDecision? parse(dynamic v){
    if(v is! Map||v['label'] is! String||v['outcome'] is! String)return null;
    int n(String k)=>v[k] is int?(v[k] as int).clamp(-5,5).toInt():0;
    final label=(v['label'] as String).trim(),outcome=(v['outcome'] as String).trim();
    if(label.isEmpty||outcome.isEmpty)return null;
    return StoryDecision(label,outcome,trust:n('trust'),resources:n('resources'),evidence:n('evidence'),flag:v['flag'] is String?v['flag'] as String:'');
  }
}
class AdventurePath {
  const AdventurePath({this.trust=5,this.resources=5,this.evidence=0,this.flags=const []});
  final int trust,resources,evidence;
  final List<String> flags;
  static int bound(int n)=>n.clamp(0,100).toInt();
  AdventurePath apply(StoryDecision d)=>AdventurePath(trust:bound(trust+d.trust),resources:bound(resources+d.resources),evidence:bound(evidence+d.evidence),flags:[...flags,if(d.flag.isNotEmpty)d.flag]);
  AdventurePath resolve(bool correct)=>AdventurePath(trust:bound(trust+(correct?1:-1)),resources:bound(resources+(correct?0:-1)),evidence:bound(evidence+(correct?1:0)),flags:flags);
  Map<String,dynamic> toJson()=>{'trust':trust,'resources':resources,'evidence':evidence,'flags':flags};
  factory AdventurePath.fromJson(dynamic v){
    if(v is! Map)return const AdventurePath();
    int n(String k,int fallback)=>v[k] is int?bound(v[k] as int):fallback;
    return AdventurePath(trust:n('trust',5),resources:n('resources',5),evidence:n('evidence',0),flags:v['flags'] is List?(v['flags'] as List).whereType<String>().take(300).toList():const []);
  }
  // Scale the finale to a nine-mission campaign. Decisions remain meaningful
  // even if the player answers every educational question correctly.
  String get finaleTitle=>trust>=19&&evidence>=20&&resources>=4?'El aliado legendario':evidence>=20?'La verdad sin aplausos':trust>=19?'El protector de Nébula':resources>=12?'El estratega de la reconstrucción':'El gremio en recuperación';
  String get finaleText=>trust>=19&&evidence>=20&&resources>=4?'El consejo acepta las pruebas, los héroes conservan sus aliados y el gremio dispone de reservas para reconstruirse. Mira revela que fuiste tú quien mantuvo al equipo unido.':evidence>=20?'Los documentos desmontan el fraude, pero las relaciones o las reservas del grupo son demasiado frágiles para una recuperación inmediata.':trust>=19?'La comunidad protege a los héroes y obtiene una nueva audiencia, aunque todavía faltan documentos concluyentes.':resources>=12?'Has salvado las reservas del gremio; los héroes deberán reunir más pruebas y apoyo antes de recuperar su nombre.':'El equipo conserva una oportunidad para reconstruirse. Revisa tus decisiones y vuelve a jugar con otra estrategia.';
  String get endingTitle=>trust>=7&&evidence>=4?'Victoria con aliados':evidence>=4?'La verdad sale a la luz':resources==0||trust<3?'Retirada estratégica':'Misión incompleta: el camino continúa';
  String get endingText=>trust>=7&&evidence>=4?'El equipo conserva la confianza en ti y tiene pruebas para avanzar.':evidence>=4?'Conseguiste información valiosa, pero tus relaciones necesitan recuperarse.':resources==0||trust<3?'El equipo debe reagruparse y reconstruir sus recursos.':'Has avanzado, pero aún quedan pruebas por descubrir. Tus decisiones se conservan para el próximo capítulo.';
}
class ScenePath {
  const ScenePath({this.prompt='El grupo necesita decidir cómo abordar la misión.',this.decisions=defaults,this.reactions=const {},this.teach,this.success,this.failure,this.numericAnswer,this.numericTolerance=.001});
  final String prompt;
  final List<StoryDecision> decisions;
  final Map<String,String> reactions;
  final String? teach,success,failure;
  final double? numericAnswer;
  final double numericTolerance;
  static double? parseNumber(String raw){final n=double.tryParse(raw.trim().replaceAll(',', '.'));return n!=null&&n.isFinite?n:null;}
  bool acceptsNumber(String raw){final n=parseNumber(raw);return n!=null&&numericAnswer!=null&&(n-numericAnswer!).abs()<=numericTolerance+1e-9;}
  static const defaults=[
    StoryDecision('Ayudar a los aliados','Compartes tus provisiones. El grupo confía más en ti.',trust:2,resources:-1,flag:'help'),
    StoryDecision('Investigar por tu cuenta','Consigues una pista, pero el grupo se queda sin tu ayuda.',trust:-1,evidence:2,flag:'investigate'),
    StoryDecision('Reagrupar y preparar suministros','Aplazas el avance para conseguir recursos.',resources:2,flag:'prepare'),
  ];
  static ScenePath parse(dynamic v){
    if(v is! Map)return const ScenePath();
    String? s(String k)=>v[k] is String&&(v[k] as String).trim().isNotEmpty?v[k] as String:null;
    final list=v['decisions'] is List?(v['decisions'] as List).map(StoryDecision.parse).whereType<StoryDecision>().take(4).toList():<StoryDecision>[];
    final decisions=list.length>=2&&list.any((d)=>d.resources>=0)?list:defaults;
    final reactions=<String,String>{};
    if(v['reactions'] is Map){for(final e in (v['reactions'] as Map).entries.take(24)){if(e.key is String&&e.value is String)reactions[e.key as String]=e.value as String;}}
    return ScenePath(prompt:s('prompt')??'El grupo necesita decidir cómo abordar la misión.',decisions:decisions,reactions:reactions,teach:s('teach'),success:s('success'),failure:s('failure'),numericAnswer:v['numericAnswer'] is num&&(v['numericAnswer'] as num).isFinite?(v['numericAnswer'] as num).toDouble():null,numericTolerance:v['numericTolerance'] is num&&(v['numericTolerance'] as num).isFinite?(v['numericTolerance'] as num).toDouble().clamp(0.000001,1).toDouble():.001);
  }
  String? reaction(AdventurePath path){
    for(final flag in path.flags.reversed){if(reactions.containsKey(flag))return reactions[flag];}
    if(path.flags.isEmpty)return null;
    if(path.trust<3)return 'Los aliados dudan de tu plan. Tendrás que recuperar su confianza.';
    if(path.resources==0)return 'El grupo avanza sin reservas.';
    if(path.evidence>=4)return 'Las pistas que reuniste empiezan a encajar.';
    return null;
  }
}
