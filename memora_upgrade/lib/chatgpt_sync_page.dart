import 'dart:convert';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'guide_store.dart';
import 'models.dart';
import 'study_engine.dart';

class ChatgptSyncPage extends StatefulWidget {
  const ChatgptSyncPage({super.key, required this.store});
  final GuideStore store;
  @override
  State<ChatgptSyncPage> createState() => _ChatgptSyncPageState();
}
class _ChatgptSyncPageState extends State<ChatgptSyncPage> {
  static const vault = FlutterSecureStorage();
  static const tokenKey = 'memora_sync_token_v1';
  static const repoKey = 'memora_sync_repo_v1';
  final repo = TextEditingController(text: 'angeljo0801/Memora-Sync');
  final token = TextEditingController();
  final prompt = TextEditingController();
  bool busy = true, saved = false;
  String type = 'adventure', status = 'Configura tu conexión privada.';
  @override
  void initState() { super.initState(); load(); }
  Future<void> load() async {
    try {
      final p = await SharedPreferences.getInstance();
      final t = await vault.read(key: tokenKey);
      if (!mounted) return;
      repo.text = p.getString(repoKey) ?? repo.text;
      saved = t != null && t.isNotEmpty;
      if (saved) status = 'Conexión guardada.';
    } catch (_) { status = 'No se pudo leer la configuración segura.'; }
    finally { if (mounted) setState(() => busy = false); }
  }
  @override
  void dispose() { repo.dispose(); token.dispose(); prompt.dispose(); super.dispose(); }
  Future<void> run(Future<String> Function() action) async {
    if (busy) return;
    setState(() { busy = true; status = 'Sincronizando…'; });
    try {
      final result = await action();
      if (mounted) setState(() => status = result);
    } catch (e) {
      if (mounted) setState(() => status = e is FormatException ? e.message : 'Error de conexión o almacenamiento.');
    } finally { if (mounted) setState(() => busy = false); }
  }
  Future<_Api> connection() async {
    final p = await SharedPreferences.getInstance();
    final r = p.getString(repoKey);
    final t = await vault.read(key: tokenKey);
    if (r == null || t == null || t.isEmpty) throw const FormatException('Guarda primero la conexión.');
    final a = _Api(r,t);
    await a.verify();
    return a;
  }
  Future<String> configure() async {
    final p = await SharedPreferences.getInstance();
    final r = repo.text.trim();
    final t = token.text.trim().isNotEmpty ? token.text.trim() : (p.getString(repoKey) == r ? await vault.read(key: tokenKey) : null);
    if (t == null || t.isEmpty) throw const FormatException('Introduce el token.');
    await _Api(r,t).verify();
    await vault.write(key: tokenKey,value:t);
    await p.setString(repoKey,r);
    saved = true;
    if (mounted) token.clear();
    return 'Repositorio privado verificado.';
  }
  Future<String> disconnect() async {
    await vault.delete(key: tokenKey);
    final p = await SharedPreferences.getInstance();
    await p.remove(repoKey);
    saved = false;
    if (mounted) token.clear();
    return 'Desvinculado. Tus guías permanecen en el teléfono.';
  }
  Future<String> download() async {
    final a = await connection();
    final file = await a.read('memora-guides.json');
    if (file == null) return 'Todavía no hay guías remotas.';
    final root = file.data;
    if (root['schema'] != 1 || root['guides'] is! List) throw const FormatException('Formato de catálogo incompatible.');
    final rows = root['guides'] as List;
    if (rows.length > 100) throw const FormatException('Demasiadas guías.');
    final p = await SharedPreferences.getInstance();
    final pending = <StudyGuide>[];
    final revisions = <String,int>{};
    final seen = <String>{};
    for (final raw in rows) {
      final row = obj(raw);
      final id = a.prefix + identifier(row['id']);
      if (!seen.add(id)) throw const FormatException('Guía duplicada.');
      final rev = row['revision'];
      if (rev is! int || rev < 1) throw const FormatException('Revisión inválida.');
      final old = widget.store.findById(id);
      if (old != null && old.sourceType != 'chatgpt') throw const FormatException('Conflicto con guía local.');
      if (rev <= (p.getInt('sync_revision_'+id) ?? 0)) continue;
      final title = str(row['title'],180);
      final summary = str(row['summary'],20000);
      final body = str(row['text'],250000);
      final list = row['cards'];
      if (list is! List || list.isEmpty || list.length > 300) throw const FormatException('Se requieren entre 1 y 300 tarjetas.');
      final existing = {for (final c in old?.cards ?? <StudyCard>[]) c.id:c};
      final cards = <StudyCard>[];
      final cardIds = <String>{};
      for (final rawCard in list) {
        final c = obj(rawCard);
        final cid = id+'_'+identifier(c['id']);
        if (!cardIds.add(cid)) throw const FormatException('Tarjeta duplicada.');
        final q = str(c['question'],4000), ans = str(c['answer'],12000);
        final before = existing[cid];
        final card = StudyCard.fromJson({
          if (before != null && before.question == q && before.answer == ans) ...before.toJson(),
          'id':cid,'question':q,'answer':ans,
          'source':str(c['source'] ?? '',2000,empty:true),
          'adventureStory':str(c['story'] ?? '',16000,empty:true),
        });
        if (!StudyEngine.isCardUsable(card)) throw FormatException('Tarjeta no válida: '+q);
        cards.add(card);
      }
      cards.addAll(existing.values.where((c) => !cardIds.contains(c.id)));
      pending.add(StudyGuide(id:id,title:title,sourceType:'chatgpt',sourceName:'ChatGPT · Memora Sync',text:body,summary:summary,cards:cards,createdAt:old?.createdAt ?? DateTime.now(),lastStudiedAt:old?.lastStudiedAt,filePath:old?.filePath));
      revisions[id] = rev;
    }
    for (final g in pending) {
      if (widget.store.findById(g.id) == null) { await widget.store.add(g); }
      else { await widget.store.update(g); }
      await p.setInt('sync_revision_'+g.id,revisions[g.id]!);
    }
    return pending.isEmpty ? 'No hay revisiones nuevas.' : 'Guías recibidas: '+pending.length.toString()+'. Ábrelas en Biblioteca.';
  }
  Future<String> sendRequest() async {
    final message = str(prompt.text,12000);
    final a = await connection();
    final file = await a.read('memora-requests.json');
    final root = file?.data ?? <String,dynamic>{'schema':1,'requests':[]};
    if (root['schema'] != 1 || root['requests'] is! List) throw const FormatException('Solicitudes incompatibles.');
    final requests = List<dynamic>.from(root['requests'] as List);
    if (requests.length >= 200) throw const FormatException('Archiva las solicitudes antiguas.');
    requests.add({'id':DateTime.now().microsecondsSinceEpoch.toString()+'-'+Random.secure().nextInt(1<<30).toString(),'type':type,'prompt':message,'createdAt':DateTime.now().toUtc().toIso8601String()});
    await a.write('memora-requests.json',{'schema':1,'requests':requests},file?.sha);
    if (mounted) prompt.clear();
    return 'Solicitud enviada. Pide a ChatGPT que revise Memora-Sync.';
  }
  Future<void> chooseCardsGuide() async {
    if(busy || !saved) return;
    final eligible=widget.store.guides.where((g)=>g.text.trim().length>=40).toList();
    if(eligible.isEmpty) {
      setState(()=>status='No hay guías con texto suficiente.');
      return;
    }
    final choice=await showDialog<StudyGuide>(
      context:context,
      builder:(ctx)=>SimpleDialog(
        title:const Text('Crear tarjetas con ChatGPT'),
        children:[
          const Padding(padding:EdgeInsets.all(16),child:Text('Se enviará el texto extraído de la guía seleccionada al repositorio privado Memora-Sync. Se crearán hasta 50 tarjetas; no se eliminarán las existentes.')),
          for(final g in eligible) SimpleDialogOption(
            onPressed:()=>Navigator.pop(ctx,g),
            child:Text(g.title),
          ),
          SimpleDialogOption(onPressed:()=>Navigator.pop(ctx),child:const Text('Cancelar')),
        ],
      ),
    );
    if(choice!=null && mounted) await run(()=>createCards(choice));
  }
  Future<String> createCards(StudyGuide guide) async {
    final original=guide.text.trim();
    final material=original.length>60000 ? original.substring(0,60000) : original;
    final task='Crea hasta 50 tarjetas de estudio precisas y variadas basadas exclusivamente en el MATERIAL. '
      'Cubre los conceptos más importantes, evita repeticiones y preguntas ambiguas. '
      'Devuelve únicamente un objeto JSON con una propiedad cards, que sea una lista de objetos con question, answer y evidence. '
      'Cada evidence debe ser una cita literal no vacía del material, de 12 a 600 caracteres, que respalde la respuesta. '
      'No inventes datos. Si hay menos de 50 conceptos válidos, devuelve menos. '
      'Responde en el idioma del material.\nMATERIAL:\n'+material;
    final response=await MemoraSyncModel.ask(prompt:task,mode:'deep',cancelled:()=>!mounted);
    if(!mounted) throw Exception('Generación cancelada.');
    var jsonText=response.trim();
    if(jsonText.startsWith('~~~') || jsonText.startsWith('\u0060\u0060\u0060')) {
      final first=jsonText.indexOf('\n');
      final last=jsonText.lastIndexOf('\n');
      if(first>=0 && last>first) jsonText=jsonText.substring(first+1,last).trim();
    }
    final decoded=obj(jsonDecode(jsonText));
    if(decoded['cards'] is! List) throw const FormatException('La respuesta no contiene tarjetas.');
    final current=widget.store.findById(guide.id);
    if(current==null) throw const FormatException('La guía ya no existe.');
    if(current.text.trim()!=original) throw const FormatException('El texto de la guía cambió. Vuelve a iniciar la tarea.');
    final existing=List<StudyCard>.of(current.cards);
    final seen=existing.map((c)=>c.question.trim().toLowerCase()).toSet();
    final generated=<StudyCard>[];
    final now=DateTime.now();
    for(final item in (decoded['cards'] as List).take(50)) {
      try {
        final row=obj(item);
        final q=str(row['question'],4000), a=str(row['answer'],12000), evidence=str(row['evidence'],600);
        if(evidence.length<12 || !material.contains(evidence) || seen.contains(q.toLowerCase())) continue;
        final card=StudyCard.fromJson({'id':'sync-card-'+now.microsecondsSinceEpoch.toString()+'-'+generated.length.toString(),'question':q,'answer':a,'source':guide.title,'sourceExcerpt':evidence,'dueAt':now.toIso8601String()});
        if(!StudyEngine.isCardUsable(card)) continue;
        generated.add(card);
        seen.add(q.toLowerCase());
      } catch(_) {
        // Reject individual malformed cards without losing the existing library.
      }
    }
    if(generated.isEmpty) return 'No se encontraron tarjetas nuevas con evidencia literal válida. Tus tarjetas siguen intactas.';
    current.cards=[...existing,...generated];
    try {
      await widget.store.update(current);
    } catch(_) {
      current.cards=existing;
      rethrow;
    }
    return 'Tarjetas nuevas: '+generated.length.toString()+'. Se conservaron las existentes y su progreso.'+(original.length>material.length?' Se usaron los primeros 60 000 caracteres del documento.':'');
  }

  Future<String> sendProgress() async {
    final a = await connection();
    final old = await a.read('memora-progress.json');
    final rows = [
      for (final g in widget.store.guides.where((g) => g.id.startsWith(a.prefix) && g.sourceType == 'chatgpt'))
        {'id':g.id.substring(a.prefix.length),'title':g.title,'cards':g.cards.length,'mastered':g.masteredCount,'correct':g.totalCorrect,'wrong':g.totalWrong,
        'lastStudiedAt':g.lastStudiedAt?.toUtc().toIso8601String(),
        'cardResults':[for (final c in g.cards) {'id':c.id,'correct':c.correct,'wrong':c.wrong,'streak':c.streak}]}
    ];
    await a.write('memora-progress.json',{'schema':1,'updatedAt':DateTime.now().toUtc().toIso8601String(),'guides':rows},old?.sha);
    return 'Progreso enviado. No se compartió la biblioteca local.';
  }
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar:AppBar(title:const Text('Memora ↔ ChatGPT')),
    body:ListView(padding:const EdgeInsets.all(18),children:[
      const Text('Recibe guías y aventuras. Envía solicitudes y progreso de las guías sincronizadas. Tu biblioteca local no se comparte.'),
      const SizedBox(height:16),
      TextField(controller:repo,enabled:!busy,decoration:const InputDecoration(labelText:'Repositorio privado (owner/name)')),
      const SizedBox(height:10),
      TextField(controller:token,enabled:!busy,obscureText:true,autocorrect:false,enableSuggestions:false,decoration:InputDecoration(labelText:saved?'Token guardado (opcional reemplazar)':'Token GitHub · Contents lectura/escritura')),
      const Text('Usa un token fine-grained limitado a Memora-Sync. No lo compartas por chat.'),
      FilledButton.icon(onPressed:busy?null:()=>run(configure),icon:const Icon(Icons.lock_outline),label:const Text('Guardar y verificar conexión')),
      if(saved) TextButton(onPressed:busy?null:()=>run(disconnect),child:const Text('Desvincular')),
      const Divider(height:32),
      FilledButton.icon(onPressed:busy||!saved?null:()=>run(download),icon:const Icon(Icons.cloud_download_outlined),label:const Text('Recibir / actualizar guías')),
      const SizedBox(height:10),
      FilledButton.icon(onPressed:busy||!saved?null:chooseCardsGuide,icon:const Icon(Icons.style_outlined),label:const Text('Crear tarjetas con ChatGPT')),
      const SizedBox(height:20),
      const Text('Solicitar una guía',style:TextStyle(fontSize:20,fontWeight:FontWeight.bold)),
      DropdownButton<String>(value:type,isExpanded:true,onChanged:busy?null:(v){if(v!=null)setState(()=>type=v);},items:const [
        DropdownMenuItem(value:'adventure',child:Text('Aventura educativa')),
        DropdownMenuItem(value:'traditional',child:Text('Guía tradicional')),
        DropdownMenuItem(value:'simulation',child:Text('Simulador (solicitud de diseño)')),
      ]),
      TextField(controller:prompt,enabled:!busy,minLines:3,maxLines:8,decoration:const InputDecoration(hintText:'Tema, nivel y objetivos')),
      FilledButton.icon(onPressed:busy||!saved?null:()=>run(sendRequest),icon:const Icon(Icons.send_outlined),label:const Text('Enviar solicitud a ChatGPT')),
      const Text('Después pide a ChatGPT revisar Memora-Sync; no se inicia un chat automáticamente.'),
      const Divider(height:32),
      OutlinedButton.icon(onPressed:busy||!saved?null:()=>run(sendProgress),icon:const Icon(Icons.upload_outlined),label:const Text('Compartir progreso de guías sincronizadas')),
      if(busy) const LinearProgressIndicator(),
      const SizedBox(height:12),Text(status),
    ]),
  );
}
Map<String,dynamic> obj(dynamic v) {
  if(v is! Map) throw const FormatException('JSON inválido.');
  return Map<String,dynamic>.from(v);
}
String str(dynamic v,int max,{bool empty=false}) {
  if(v is! String || v.length>max || (!empty&&v.trim().isEmpty)) throw const FormatException('Texto inválido.');
  return v.trim();
}
String identifier(dynamic v) {
  if(v is! String || !RegExp(r'^[a-zA-Z0-9_-]{1,80}$').hasMatch(v)) throw const FormatException('Identificador inválido.');
  return v;
}
class _Remote {
  const _Remote(this.sha,this.data);
  final String sha;
  final Map<String,dynamic> data;
}
class _Api {
  _Api(this.repo,this.token) {
    if(!RegExp(r'^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$').hasMatch(repo)) throw const FormatException('Usa owner/name.');
  }
  final String repo,token;
  String get prefix=>'chatgpt_'+base64Url.encode(utf8.encode(repo)).replaceAll('=','')+'_';
  Future<http.Response> request(String method,String path,[Map<String,dynamic>? body]) async {
    final client=http.Client();
    try {
      final req=http.Request(method,Uri.https('api.github.com','/repos/'+repo+path));
      req.followRedirects=false;
      req.headers.addAll({'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'});
      if(body!=null){req.headers['Content-Type']='application/json';req.body=jsonEncode(body);}
      return await http.Response.fromStream(await client.send(req).timeout(const Duration(seconds:20))).timeout(const Duration(seconds:30));
    } finally {client.close();}
  }
  Future<void> verify() async {
    final r=await request('GET','');
    if(r.statusCode!=200) throw FormatException('No se pudo verificar el repositorio: '+r.statusCode.toString());
    final info=obj(jsonDecode(r.body));
    if(info['private']!=true || info['visibility']!='private') throw const FormatException('Solo se permiten repositorios privados.');
  }
  Future<_Remote?> read(String path) async {
    final r=await request('GET','/contents/'+path);
    if(r.statusCode==404)return null;
    if(r.statusCode!=200)throw FormatException('Error al leer '+path+': '+r.statusCode.toString());
    final info=obj(jsonDecode(r.body));
    if(info['encoding']!='base64'||info['size'] is! int||(info['size'] as int)>900000)throw const FormatException('Archivo remoto demasiado grande o incompatible.');
    final bytes=base64Decode((info['content'] as String).replaceAll(RegExp(r'\s'),''));
    return _Remote(info['sha'] as String,obj(jsonDecode(utf8.decode(bytes))));
  }
  Future<void> write(String path,Map<String,dynamic> data,String? sha) async {
    final bytes=utf8.encode(jsonEncode(data));
    if(bytes.length>900000)throw const FormatException('Envío demasiado grande.');
    await verify();
    final r=await request('PUT','/contents/'+path,{'message':'Memora: '+path,'content':base64Encode(bytes),if(sha!=null)'sha':sha});
    if(r.statusCode!=200&&r.statusCode!=201)throw FormatException('No se pudo enviar: '+r.statusCode.toString()+'. Si hubo un conflicto, reintenta.');
  }
}


/// A queued model provider, not a live OpenAI API. The authorized ChatGPT
/// conversation reads pending jobs and writes responses to the private repo.
class MemoraSyncModel {
  static const vault = FlutterSecureStorage();
  static Future<bool> configured() async {
    final p = await SharedPreferences.getInstance();
    return (p.getString('memora_sync_repo_v1') ?? '').isNotEmpty &&
        (await vault.read(key:'memora_sync_token_v1') ?? '').isNotEmpty;
  }

  static Future<String> ask({
    required String prompt,
    required String mode,
    required bool Function() cancelled,
  }) async {
    if (prompt.trim().isEmpty || utf8.encode(prompt).length > 180000) {
      throw const FormatException('La solicitud Memora-Sync está vacía o es demasiado grande.');
    }
    final p = await SharedPreferences.getInstance();
    final repo = p.getString('memora_sync_repo_v1');
    final token = await vault.read(key:'memora_sync_token_v1');
    if(repo == null || token == null || token.isEmpty) {
      throw const FormatException('Configura Memora-Sync desde Biblioteca → sincronización.');
    }
    final api = _Api(repo,token);
    await api.verify();
    const path = 'memora-model-queue.json';
    String? id;
    final now = DateTime.now().toUtc();
    for(var attempt=0;attempt<3;attempt++) {
      if(cancelled()) throw Exception('Generación cancelada.');
      final old = await api.read(path);
      final root = old?.data ?? <String,dynamic>{'schema':1,'jobs':[]};
      if(root['schema']!=1 || root['jobs'] is! List) throw const FormatException('Cola Memora-Sync incompatible.');
      final jobs=List<dynamic>.from(root['jobs'] as List);
      // Reuse a recent identical job, so retrying after a timeout does not
      // create duplicates or discard a response that arrived late.
      for(final raw in jobs.reversed) {
        final job=obj(raw);
        final created=DateTime.tryParse(job['createdAt']?.toString() ?? '');
        if(created!=null && now.difference(created).inHours<24 &&
            job['prompt']==prompt && job['mode']==mode &&
            job['id'] is String && (job['status']=='pending'||job['status']=='done')) {
          id=job['id'] as String;
          break;
        }
      }
      if(id!=null) break;
      if(jobs.length>=50) throw const FormatException('La cola tiene 50 tareas. Archiva las terminadas en el repositorio privado.');
      final next=now.microsecondsSinceEpoch.toString()+'-'+Random.secure().nextInt(1<<30).toString();
      jobs.add({'id':next,'status':'pending','mode':mode,'prompt':prompt,'createdAt':now.toIso8601String()});
      try {
        await api.write(path,{'schema':1,'jobs':jobs},old?.sha);
        id=next;
        break;
      } on FormatException {
        if(attempt==2) rethrow;
        await Future<void>.delayed(const Duration(seconds:2));
      }
    }
    if(id==null) throw const FormatException('No se pudo registrar la tarea.');
    final deadline=DateTime.now().add(const Duration(seconds:90));
    do {
      if(cancelled()) throw Exception('Generación cancelada.');
      final remote=await api.read(path);
      if(remote!=null && remote.data['jobs'] is List) {
        for(final raw in remote.data['jobs'] as List) {
          final job=obj(raw);
          if(job['id']!=id) continue;
          if(job['status']=='done') {
            final answer=job['response'];
            if(answer is String && answer.trim().isNotEmpty) return answer;
            throw const FormatException('Respuesta Memora-Sync vacía.');
          }
          if(job['status']=='error') throw FormatException(job['error']?.toString() ?? 'No se pudo procesar la solicitud.');
        }
      }
      await Future<void>.delayed(const Duration(seconds:5));
    } while(DateTime.now().isBefore(deadline));
    throw FormatException('Solicitud guardada en Memora-Sync ('+id+'). Pide a ChatGPT revisar la cola y vuelve a intentar la misma tarea para recoger la respuesta.');
  }
}
