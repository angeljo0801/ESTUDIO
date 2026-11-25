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
