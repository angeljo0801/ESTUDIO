import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'ai_service.dart';
import 'guide_store.dart';
import 'knowledge_retriever.dart';
import 'llm_settings_page.dart';
import 'models.dart';

const List<String> _generalModels = [
  'qwen2.5:3b — equilibrado y multilingüe',
  'llama3.2:3b — ligero y buen diálogo',
  'gemma3:4b — más contexto y 140+ idiomas',
];

const Set<String> _validSources = {
  'global', 'private', 'shared', 'gemini', 'openai', 'local',
};

class TutorProfile {
  const TutorProfile({
    required this.id,
    required this.name,
    required this.emoji,
    required this.description,
    required this.instructions,
    this.modelSource = 'global',
    this.recommendedModels = const [],
    this.guideIds = const [],
    this.isBuiltIn = false,
  });

  final String id;
  final String name;
  final String emoji;
  final String description;
  final String instructions;
  final String modelSource;
  final List<String> recommendedModels;
  final List<String> guideIds;
  final bool isBuiltIn;

  TutorProfile copyWith({
    String? name,
    String? emoji,
    String? description,
    String? instructions,
    String? modelSource,
    List<String>? recommendedModels,
    List<String>? guideIds,
    bool? isBuiltIn,
  }) => TutorProfile(
        id: id,
        name: name ?? this.name,
        emoji: emoji ?? this.emoji,
        description: description ?? this.description,
        instructions: instructions ?? this.instructions,
        modelSource: modelSource ?? this.modelSource,
        recommendedModels: recommendedModels ?? this.recommendedModels,
        guideIds: guideIds ?? this.guideIds,
        isBuiltIn: isBuiltIn ?? this.isBuiltIn,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'emoji': emoji,
        'description': description,
        'instructions': instructions,
        'modelSource': modelSource,
        'recommendedModels': recommendedModels,
        'guideIds': guideIds,
        'isBuiltIn': isBuiltIn,
      };

  factory TutorProfile.fromJson(Map<String, dynamic> json) {
    final source = json['modelSource']?.toString() ?? 'global';
    final models = json['recommendedModels'];
    final guides = json['guideIds'];
    return TutorProfile(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? 'Tutor',
      emoji: json['emoji']?.toString() ?? '🧠',
      description: json['description']?.toString() ?? '',
      instructions: json['instructions']?.toString() ?? '',
      modelSource: _validSources.contains(source) ? source : 'global',
      recommendedModels: models is List
          ? models.map((e) => e.toString()).where((e) => e.trim().isNotEmpty).toList()
          : const [],
      guideIds: guides is List
          ? guides.map((e) => e.toString()).where((e) => e.isNotEmpty).toList()
          : const [],
      isBuiltIn: json['isBuiltIn'] == true,
    );
  }
}

const List<TutorProfile> _defaultTutors = [
  TutorProfile(
    id: 'memora_general', name: 'Memora', emoji: '🧠',
    description: 'Tutor equilibrado para aprender y entender cualquier tema.',
    instructions: 'Explica con claridad, adapta la profundidad a la pregunta, divide los temas difíciles en pasos y comprueba que el estudiante entienda.',
    recommendedModels: _generalModels, isBuiltIn: true,
  ),
  TutorProfile(
    id: 'finanzas', name: 'Tutor de Finanzas', emoji: '💰',
    description: 'Enseña finanzas, contabilidad e inversiones con fórmulas, intuición y práctica.',
    instructions: 'Actúa como profesor de finanzas. Distingue conceptos contables, finanzas corporativas, mercados e inversiones. Explica intuición, definición formal y fórmula. Define variables y unidades. Muestra cálculos paso a paso, comprueba resultados, usa ejemplos numéricos y no inventes tasas ni datos que no estén en las bases asignadas.',
    recommendedModels: [
      'qwen2.5:3b — recomendado ligero para estudiar finanzas',
      'gemma3:4b — mejor razonamiento y contexto, multilingüe',
      'llama3.2:3b — rápido para explicaciones y repasos',
      'qwen2.5:7b — más potente si tienes suficiente RAM',
    ], isBuiltIn: true,
  ),
  TutorProfile(
    id: 'programacion', name: 'Tutor de Programación', emoji: '💻',
    description: 'Especialista en código, debugging, arquitectura y aprendizaje práctico.',
    instructions: 'Actúa como profesor y revisor de programación. Explica qué hace el código y por qué. Ante errores, identifica la causa raíz. Da código completo cuando haga falta y explica las líneas importantes. Prioriza seguridad, mantenibilidad y simplicidad. Compara alternativas y crea ejercicios progresivos.',
    recommendedModels: [
      'qwen2.5-coder:3b — recomendado para teléfono; código y debugging',
      'qwen2.5-coder:7b — mejor calidad, pero más pesado',
      'qwen2.5-coder:1.5b — opción muy ligera',
      'deepseek-coder:1.3b — ultraligero para tareas de código',
    ], isBuiltIn: true,
  ),
  TutorProfile(
    id: 'idiomas', name: 'Tutor de Idiomas', emoji: '🌍',
    description: 'Profesor multilingüe para vocabulario, gramática, conversación y corrección.',
    instructions: 'Actúa como profesor de idiomas. Detecta el idioma objetivo. Adapta el nivel, combina explicación en español con práctica en el idioma objetivo, corrige gramática, vocabulario y naturalidad, usa mini diálogos y permite inmersión cuando se pida.',
    recommendedModels: [
      'gemma3:4b — recomendado; soporte para 140+ idiomas',
      'qwen2.5:3b — multilingüe y relativamente ligero',
      'llama3.2:3b — diálogo multilingüe ligero',
      'aya-expanse:8b — especializado en 23 idiomas; más pesado',
    ], isBuiltIn: true,
  ),
  TutorProfile(
    id: 'paso_a_paso', name: 'Profesor Paso a Paso', emoji: '🪜',
    description: 'Descompone lo difícil en partes pequeñas y ordenadas.',
    instructions: 'Enseña paso a paso. No saltes operaciones ni conceptos intermedios. Usa ejemplos sencillos antes de aumentar la dificultad y resume la idea clave al final.',
    recommendedModels: _generalModels, isBuiltIn: true,
  ),
  TutorProfile(
    id: 'socratico', name: 'Tutor Socrático', emoji: '❓',
    description: 'Te guía con preguntas para que descubras la respuesta.',
    instructions: 'Usa el método socrático. Haz preguntas útiles antes de entregar una solución completa; si el estudiante está bloqueado, da pistas graduales.',
    recommendedModels: ['qwen2.5:7b — fuerte para razonamiento guiado','gemma3:4b — buen equilibrio de razonamiento y tamaño','llama3.2:3b — alternativa ligera'],
    isBuiltIn: true,
  ),
  TutorProfile(
    id: 'examinador', name: 'Examinador Estricto', emoji: '🎯',
    description: 'Busca errores, exige precisión y comprueba dominio real.',
    instructions: 'Actúa como examinador exigente pero respetuoso. Señala imprecisiones, pide definiciones exactas, formula preguntas de comprobación y explica por qué una respuesta está bien o mal.',
    recommendedModels: ['qwen2.5:7b — recomendado para evaluación más rigurosa','gemma3:4b — buena comprensión y contexto','llama3.2:3b — opción ligera'],
    isBuiltIn: true,
  ),
  TutorProfile(
    id: 'repaso_express', name: 'Repaso Express', emoji: '⚡',
    description: 'Respuestas breves, ideas clave y repasos rápidos.',
    instructions: 'Prioriza velocidad y retención. Da respuestas concisas, usa palabras clave, mini-resúmenes y reglas fáciles de recordar.',
    recommendedModels: ['qwen2.5:1.5b — rápido y pequeño','llama3.2:1b — muy ligero para repasos','gemma3:1b — alternativa compacta'],
    isBuiltIn: true,
  ),
  TutorProfile(
    id: 'ejemplos', name: 'Tutor de Ejemplos', emoji: '💡',
    description: 'Enseña principalmente mediante ejemplos y analogías.',
    instructions: 'Explica cada concepto con ejemplos concretos y analogías cotidianas. Conecta después el ejemplo con la definición formal.',
    recommendedModels: _generalModels, isBuiltIn: true,
  ),
];

class TutorPage extends StatefulWidget {
  const TutorPage({super.key, required this.store});
  final GuideStore store;
  @override
  State<TutorPage> createState() => _TutorPageState();
}

class _TutorPageState extends State<TutorPage> {
  static const _profilesKey = 'memora_tutor_profiles_v1';
  static const _activeTutorKey = 'memora_active_tutor_id';
  final q = TextEditingController();
  List<TutorProfile> tutors = List<TutorProfile>.from(_defaultTutors);
  String activeTutorId = _defaultTutors.first.id;
  String answer = 'Asigna una o varias guías a tu tutor y hazle una pregunta.';
  bool busy = false;
  bool loadingTutors = true;
  String globalLocalModel = '';

  TutorProfile get activeTutor => tutors.firstWhere((t) => t.id == activeTutorId, orElse: () => tutors.first);
  List<StudyGuide> get activeGuides => widget.store.guides.where((g) => activeTutor.guideIds.contains(g.id)).toList();

  @override
  void initState() { super.initState(); _loadTutors(); }
  @override
  void dispose() { q.dispose(); super.dispose(); }

  List<TutorProfile> _upgradeProfiles(List<TutorProfile> loaded) {
    final defaults = {for (final t in _defaultTutors) t.id: t};
    final upgraded = <TutorProfile>[];
    for (final tutor in loaded) {
      final builtIn = defaults[tutor.id];
      upgraded.add(tutor.copyWith(
        recommendedModels: tutor.recommendedModels.isEmpty ? List<String>.from(builtIn?.recommendedModels ?? _generalModels) : tutor.recommendedModels,
        guideIds: tutor.guideIds.where((id) => widget.store.guides.any((g) => g.id == id)).toList(),
      ));
    }
    final ids = upgraded.map((t) => t.id).toSet();
    for (final tutor in _defaultTutors) { if (!ids.contains(tutor.id)) upgraded.add(tutor); }
    return upgraded;
  }

  Future<void> _loadTutors() async {
    final prefs = await SharedPreferences.getInstance();
    globalLocalModel = prefs.getString('local_model') ?? '';
    final raw = prefs.getString(_profilesKey);
    if (raw != null && raw.isNotEmpty) {
      try {
        final decoded = jsonDecode(raw) as List<dynamic>;
        final loaded = decoded.whereType<Map>().map((e) => TutorProfile.fromJson(Map<String,dynamic>.from(e))).where((t) => t.id.isNotEmpty).toList();
        if (loaded.isNotEmpty) tutors = _upgradeProfiles(loaded);
      } catch (_) { tutors = List<TutorProfile>.from(_defaultTutors); }
    }
    final saved = prefs.getString(_activeTutorKey);
    if (saved != null && tutors.any((t) => t.id == saved)) activeTutorId = saved;
    await _saveTutors();
    if (mounted) setState(() { loadingTutors = false; answer = '${activeTutor.emoji} Soy ${activeTutor.name}. ${activeTutor.description}'; });
  }

  Future<void> _saveTutors() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_profilesKey, jsonEncode(tutors.map((t) => t.toJson()).toList()));
    await prefs.setString(_activeTutorKey, activeTutorId);
  }

  String _sourceLabel(String source) {
    switch (source) {
      case 'private': return 'GGUF privado de Memora';
      case 'shared': return 'GGUF compartido';
      case 'gemini': return 'Gemini configurado';
      case 'openai': return 'OpenAI / compatible configurado';
      case 'local': return 'Ollama / servidor local configurado';
      default: return 'Configuración general de IA';
    }
  }

  String _modelTag(String recommendation) => recommendation.split('—').first.trim();

  Future<void> _useRecommendedModel(String recommendation) async {
    final model = _modelTag(recommendation);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('local_model', model);
    await prefs.setString('llm_provider', 'local');
    if (mounted) {
      setState(() => globalLocalModel = model);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$model seleccionado como modelo general de Ollama.')));
    }
  }

  Future<void> _selectTutor(String? id) async {
    if (id == null || !tutors.any((t) => t.id == id)) return;
    setState(() { activeTutorId = id; answer = '${activeTutor.emoji} Soy ${activeTutor.name}. ${activeTutor.description}'; });
    await _saveTutors();
  }

  Future<void> _assignGuides() async {
    final working = activeTutor.guideIds.toSet();
    final result = await showModalBottomSheet<Set<String>>(
      context: context, isScrollControlled: true,
      builder: (sheetContext) => StatefulBuilder(
        builder: (context, setSheetState) => SafeArea(child: SizedBox(
          height: MediaQuery.of(context).size.height * .8,
          child: Column(children: [
            const Padding(padding: EdgeInsets.all(16), child: Text('Asignar guías a este tutor', style: TextStyle(fontSize:20,fontWeight:FontWeight.bold))),
            Expanded(child: widget.store.guides.isEmpty
              ? const Center(child: Text('Primero añade o crea guías en Biblioteca.'))
              : ListView(children: [for (final guide in widget.store.guides) CheckboxListTile(
                  value: working.contains(guide.id), title: Text(guide.title), subtitle: Text('${guide.sourceType.toUpperCase()} • ${guide.sourceName}'),
                  onChanged: (value) => setSheetState(() { if (value == true) working.add(guide.id); else working.remove(guide.id); }),
                )])),
            Padding(padding: const EdgeInsets.all(16), child: FilledButton(onPressed: () => Navigator.pop(sheetContext, working), child: Text('Guardar ${working.length} guía(s)'))),
          ]),
        )),
      ),
    );
    if (result == null) return;
    final index = tutors.indexWhere((t) => t.id == activeTutorId);
    if (index < 0) return;
    final updated = List<TutorProfile>.from(tutors);
    updated[index] = updated[index].copyWith(guideIds: result.toList());
    setState(() => tutors = updated);
    await _saveTutors();
  }

  Future<void> _ask() async {
    final question = q.text.trim();
    final guides = activeGuides;
    if (question.isEmpty || busy) return;
    if (guides.isEmpty) { setState(() => answer = 'Asigna al menos una guía a ${activeTutor.name} antes de preguntar.'); return; }
    setState(() => busy = true);
    try {
      final tutor = activeTutor;
      final context = KnowledgeRetriever.buildContext(guides: guides, query: question, maxChars: 11000, maxChunks: 8);
      final result = await AiService.askConfigured(
        providerOverride: tutor.modelSource,
        prompt: '''Eres ${tutor.name}, uno de los tutores de Memora.
TU ESTILO: ${tutor.description}
INSTRUCCIONES: ${tutor.instructions}

REGLAS:
- Por defecto responde en español, excepto si el tutor requiere practicar otro idioma.
- Usa prioritariamente los fragmentos relevantes de las bases asignadas.
- Si la respuesta no está en ellas, dilo claramente y no inventes datos.
- Sé conciso salvo que el usuario pida detalle.

FRAGMENTOS RELEVANTES:
$context

PREGUNTA: $question''',
      );
      if (mounted) setState(() => answer = result);
    } catch (e) {
      if (mounted) setState(() => answer = 'No pude consultar ${_sourceLabel(activeTutor.modelSource)}: ${AiService.userFacingError(e)}');
    } finally { if (mounted) setState(() => busy = false); }
  }

  Future<TutorProfile?> _editTutorDialog({TutorProfile? existing}) async {
    final name = TextEditingController(text: existing?.name ?? '');
    final emoji = TextEditingController(text: existing?.emoji ?? '🧑‍🏫');
    final description = TextEditingController(text: existing?.description ?? '');
    final instructions = TextEditingController(text: existing?.instructions ?? '');
    final models = TextEditingController(text: (existing?.recommendedModels ?? _generalModels).join('\n'));
    var source = existing?.modelSource ?? 'global';
    final result = await showDialog<TutorProfile>(context: context, builder: (dialogContext) => StatefulBuilder(
      builder: (context, setDialogState) => AlertDialog(
        title: Text(existing == null ? 'Crear tutor' : 'Editar tutor'),
        content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller:name, decoration: const InputDecoration(labelText:'Nombre')),
          const SizedBox(height:10), TextField(controller:emoji, decoration: const InputDecoration(labelText:'Emoji')),
          const SizedBox(height:10), TextField(controller:description,minLines:2,maxLines:3,decoration: const InputDecoration(labelText:'Descripción / estilo')),
          const SizedBox(height:10), TextField(controller:instructions,minLines:3,maxLines:7,decoration: const InputDecoration(labelText:'Prompt / instrucciones del tutor')),
          const SizedBox(height:12), DropdownButtonFormField<String>(
            initialValue: source, decoration: const InputDecoration(labelText:'Fuente de IA de este tutor'),
            items: const [
              DropdownMenuItem(value:'global',child:Text('Configuración general')),
              DropdownMenuItem(value:'private',child:Text('GGUF privado')),
              DropdownMenuItem(value:'shared',child:Text('GGUF compartido')),
              DropdownMenuItem(value:'gemini',child:Text('Gemini configurado')),
              DropdownMenuItem(value:'openai',child:Text('OpenAI / compatible configurado')),
              DropdownMenuItem(value:'local',child:Text('Ollama / servidor local configurado')),
            ], onChanged:(value)=>setDialogState(()=>source=value??'global'),
          ),
          const SizedBox(height:12), TextField(controller:models,minLines:4,maxLines:8,decoration: const InputDecoration(labelText:'Modelos recomendados (uno por línea)',helperText:'La lista sirve también como selector rápido del modelo general Ollama.')),
        ])),
        actions:[
          TextButton(onPressed:()=>Navigator.pop(dialogContext),child:const Text('Cancelar')),
          FilledButton(onPressed:(){
            if(name.text.trim().isEmpty)return;
            Navigator.pop(dialogContext,TutorProfile(
              id:existing?.id??'custom_${DateTime.now().microsecondsSinceEpoch}',
              name:name.text.trim(),emoji:emoji.text.trim().isEmpty?'🧑‍🏫':emoji.text.trim(),
              description:description.text.trim().isEmpty?'Tutor personalizado de Memora.':description.text.trim(),
              instructions:instructions.text.trim().isEmpty?'Explica con claridad y adapta la enseñanza.':instructions.text.trim(),
              modelSource:source,recommendedModels:models.text.split('\n').map((e)=>e.trim()).where((e)=>e.isNotEmpty).toSet().toList(),
              guideIds:existing?.guideIds??const[],isBuiltIn:existing?.isBuiltIn??false,
            ));
          },child:const Text('Guardar')),
        ],
      ),
    ));
    name.dispose(); emoji.dispose(); description.dispose(); instructions.dispose(); models.dispose();
    return result;
  }

  Future<void> _addTutor() async { final created=await _editTutorDialog(); if(created==null)return; setState((){tutors=[...tutors,created];activeTutorId=created.id;}); await _saveTutors(); }
  Future<void> _editActiveTutor() async { final edited=await _editTutorDialog(existing:activeTutor); if(edited==null)return; final i=tutors.indexWhere((t)=>t.id==activeTutorId); if(i<0)return; final u=List<TutorProfile>.from(tutors);u[i]=edited;setState(()=>tutors=u);await _saveTutors(); }
  Future<void> _deleteActiveTutor() async {
    if(tutors.length<=1)return;
    final yes=await showDialog<bool>(context:context,builder:(context)=>AlertDialog(title:const Text('Eliminar tutor'),content:Text('¿Eliminar a ${activeTutor.name}?'),actions:[TextButton(onPressed:()=>Navigator.pop(context,false),child:const Text('Cancelar')),FilledButton(onPressed:()=>Navigator.pop(context,true),child:const Text('Eliminar'))]));
    if(yes!=true)return; setState((){tutors=tutors.where((t)=>t.id!=activeTutorId).toList();activeTutorId=tutors.first.id;});await _saveTutors();
  }

  Future<void> _openManager() async {
    final action=await showModalBottomSheet<String>(context:context,isScrollControlled:true,builder:(sheetContext)=>SafeArea(child:SizedBox(
      height:MediaQuery.of(sheetContext).size.height*.82,
      child:Column(children:[
        Padding(padding:const EdgeInsets.fromLTRB(16,16,8,8),child:Row(children:[const Expanded(child:Text('Mis tutores',style:TextStyle(fontSize:22,fontWeight:FontWeight.bold))),IconButton(onPressed:()=>Navigator.pop(sheetContext,'add'),icon:const Icon(Icons.person_add_alt_1))])),
        Expanded(child:ListView(children:[for(final tutor in tutors)ListTile(leading:Text(tutor.emoji,style:const TextStyle(fontSize:26)),title:Text(tutor.name),subtitle:Text('${_sourceLabel(tutor.modelSource)} • ${tutor.guideIds.length} guía(s)'),trailing:tutor.id==activeTutorId?const Icon(Icons.check_circle):null,onTap:(){_selectTutor(tutor.id);Navigator.pop(sheetContext);})])),
        Padding(padding:const EdgeInsets.all(12),child:Row(children:[Expanded(child:OutlinedButton.icon(onPressed:()=>Navigator.pop(sheetContext,'edit'),icon:const Icon(Icons.edit),label:const Text('Editar activo'))),const SizedBox(width:8),Expanded(child:OutlinedButton.icon(onPressed:()=>Navigator.pop(sheetContext,'delete'),icon:const Icon(Icons.delete_outline),label:const Text('Eliminar')))])),
      ]),
    )));
    if(!mounted)return; if(action=='add')await _addTutor(); if(action=='edit')await _editActiveTutor(); if(action=='delete')await _deleteActiveTutor();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar:AppBar(title:const Text('Tutores con IA'),actions:[IconButton(onPressed:_openManager,tooltip:'Administrar tutores',icon:const Icon(Icons.groups_2_outlined)),IconButton(onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const LlmSettingsPage())),icon:const Icon(Icons.tune))]),
    body:loadingTutors?const Center(child:CircularProgressIndicator()):ListView(padding:const EdgeInsets.all(16),children:[
      DropdownButtonFormField<String>(initialValue:activeTutorId,decoration:const InputDecoration(labelText:'Tutor activo',prefixIcon:Icon(Icons.school_outlined)),items:[for(final tutor in tutors)DropdownMenuItem(value:tutor.id,child:Text('${tutor.emoji} ${tutor.name}',overflow:TextOverflow.ellipsis))],onChanged:_selectTutor),
      const SizedBox(height:10),
      Card(child:ExpansionTile(
        leading:const Icon(Icons.memory_outlined),title:const Text('Modelos recomendados'),
        subtitle:Text(globalLocalModel.isEmpty?'Toca uno para usarlo como modelo general Ollama':'Modelo general Ollama: $globalLocalModel'),
        childrenPadding:const EdgeInsets.fromLTRB(12,0,12,14),
        children:[
          for(final model in activeTutor.recommendedModels) ListTile(
            dense:true,contentPadding:EdgeInsets.zero,title:Text(model),
            trailing:_modelTag(model)==globalLocalModel?const Icon(Icons.check_circle):const Icon(Icons.touch_app_outlined),
            onTap:()=>_useRecommendedModel(model),
          ),
          const Align(alignment:Alignment.centerLeft,child:Padding(padding:EdgeInsets.only(bottom:8),child:Text('El selector cambia el modelo general de Ollama; no descarga el modelo automáticamente.'))),
          OutlinedButton.icon(onPressed:_editActiveTutor,icon:const Icon(Icons.tune),label:const Text('Editar tutor / recomendaciones')),
        ],
      )),
      const SizedBox(height:10),
      Card(child:ExpansionTile(leading:const Icon(Icons.library_books_outlined),title:const Text('Biblioteca de este tutor'),subtitle:Text('${activeGuides.length} guía(s) asignada(s)'),childrenPadding:const EdgeInsets.fromLTRB(16,0,16,14),children:[
        if(activeGuides.isEmpty)const Align(alignment:Alignment.centerLeft,child:Text('Todavía no tiene guías asignadas.')),
        for(final guide in activeGuides)ListTile(dense:true,contentPadding:EdgeInsets.zero,leading:Icon(guide.sourceType=='xlsx'?Icons.table_chart:Icons.description_outlined),title:Text(guide.title),subtitle:Text(guide.sourceType.toUpperCase())),
        OutlinedButton.icon(onPressed:_assignGuides,icon:const Icon(Icons.library_add_check),label:const Text('Asignar / quitar guías')),
      ])),
      const SizedBox(height:12),
      Card(child:Padding(padding:const EdgeInsets.all(18),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Row(children:[Text(activeTutor.emoji,style:const TextStyle(fontSize:26)),const SizedBox(width:8),Expanded(child:Text(activeTutor.name,style:const TextStyle(fontWeight:FontWeight.bold)))]),const Divider(),SelectableText(answer)]))),
      const SizedBox(height:12),
      TextField(controller:q,minLines:2,maxLines:5,decoration:InputDecoration(hintText:'Pregunta a ${activeTutor.name}…',suffixIcon:IconButton(onPressed:busy?null:_ask,icon:busy?const Padding(padding:EdgeInsets.all(12),child:CircularProgressIndicator()):const Icon(Icons.send))),onSubmitted:(_)=>_ask()),
    ]),
  );
}
