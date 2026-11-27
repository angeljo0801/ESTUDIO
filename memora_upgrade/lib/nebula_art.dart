import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'models.dart';

class MemoraArtStore {
  static final ValueNotifier<int> revision=ValueNotifier<int>(0);
  static Future<Map<String,Uint8List>>? _cached;
  static Future<File> _file() async => File('${(await getApplicationSupportDirectory()).path}/nebula-art-v1.json');
  static Map<String,Uint8List> decode(dynamic raw) {
    if(raw is! Map||raw['schema']!=1||raw['kind']!='memora_art_v1'||raw['campaign']!='nebula-finanzas-rpg'||raw['portraits'] is! Map)throw const FormatException('Paquete de arte incompatible.');
    final items=raw['portraits'] as Map;
    if(items.isEmpty||items.length>80)throw const FormatException('Cantidad de retratos inválida.');
    final out=<String,Uint8List>{};
    var size=0;
    for(final e in items.entries){
      final id=e.key,value=e.value;
      if(id is! String||!RegExp(r'^[a-z0-9_]{1,48}$').hasMatch(id)||value is! String||value.length>180000)throw const FormatException('Retrato inválido.');
      size+=value.length;
      if(size>2450000)throw const FormatException('Paquete demasiado grande.');
      final bytes=base64Decode(value);
      if(bytes.length<12||ascii.decode(bytes.sublist(0,4),allowInvalid:true)!='RIFF'||ascii.decode(bytes.sublist(8,12),allowInvalid:true)!='WEBP')throw const FormatException('El retrato debe estar en formato WebP.');
      out[id]=bytes;
    }
    return out;
  }
  static Future<Map<String,Uint8List>> load()=>_cached??=_load();
  static Future<Map<String,Uint8List>> _load()async{
    try{final f=await _file();if(await f.exists()&&await f.length()<=2500000)return decode(jsonDecode(await f.readAsString()));}catch(_){}
    return {};
  }
  static Future<int> save(dynamic root)async{
    final images=decode(root),encoded=jsonEncode(root);
    if(utf8.encode(encoded).length>2500000)throw const FormatException('Paquete demasiado grande.');
    final f=await _file(),tmp=File(f.path+'.tmp');
    await tmp.writeAsString(encoded,flush:true);
    await tmp.rename(f.path);
    _cached=Future.value(images);
    AdventureArtStore.invalidateLegacy();
    revision.value++;
    return images.length;
  }
  static Future<int?> importLocal()async{
    final f=await FilePicker.pickFile(type:FileType.custom,allowedExtensions:['json'],dialogTitle:'Selecciona memora-art.json');
    if(f==null)return null;
    final b=await f.readAsBytes();
    if(b.length>2500000)throw const FormatException('Paquete demasiado grande.');
    return save(jsonDecode(utf8.decode(b)));
  }
}
class NebulaCharacter {
  const NebulaCharacter(this.id,this.name,this.role,this.bio);
  final String id,name,role,bio;
  static List<NebulaCharacter> fromGuide(StudyGuide guide){
    for(final card in guide.cards){
      try{
        final r=jsonDecode(card.adventureStory);
        if(r is! Map||!const ['memora_trade_cast_v1','memora_cast_v2'].contains(r['kind'])||r['characters'] is! List)continue;
        final result=<NebulaCharacter>[],seen=<String>{};
        for(final item in (r['characters'] as List).take(80)){
          if(item is! Map)continue;
          final id=item['id'],name=item['name'],role=item['role'],bio=item['bio'];
          if(id is! String||!RegExp(r'^[a-z0-9_]{1,48}$').hasMatch(id)||!seen.add(id)||name is! String||role is! String||bio is! String)continue;
          result.add(NebulaCharacter(id,name,role,bio));
        }
        return result;
      }catch(_){}
    }
    return [];
  }
}
class AnimePortrait extends StatelessWidget {
  const AnimePortrait({super.key,required this.id,this.expression='',this.fit=BoxFit.cover,this.transparentBackground=false,this.guide});
  final String id,expression;
  final BoxFit fit;
  final bool transparentBackground;
  final StudyGuide? guide;
  @override Widget build(BuildContext context)=>ValueListenableBuilder<int>(valueListenable:MemoraArtStore.revision,builder:(context,_,child)=>FutureBuilder<Map<String,Uint8List>>(future:guide==null?MemoraArtStore.load():AdventureArtStore.load(guide!.id),builder:(context,snapshot){
    final all=snapshot.data??const <String,Uint8List>{};
    final data=all[expression.isEmpty?id:id+'_'+expression]??all[id];
    return data==null?ColoredBox(color:transparentBackground?Colors.transparent:const Color(0xff131b2e),child:const Center(child:Icon(Icons.person_outline_rounded,size:48,color:Color(0xff91a4c7)))):Image.memory(data,fit:fit,width:double.infinity,height:double.infinity,gaplessPlayback:true,errorBuilder:(context,error,stack)=>const Center(child:Icon(Icons.image_not_supported_outlined)));
  }));
}
class NebulaCastPage extends StatefulWidget {
  const NebulaCastPage({super.key,required this.guide});
  final StudyGuide guide;
  @override State<NebulaCastPage> createState()=>_NebulaCastPageState();
}
class _NebulaCastPageState extends State<NebulaCastPage>{
  bool busy=false;
  Future<void> _import()async{
    if(busy)return;
    setState(()=>busy=true);
    try{final n=await AdventureArtStore.importLocal(widget.guide);if(n!=null&&mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('Arte instalado: $n recursos gráficos.')));}
    catch(e){if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(e.toString())));}
    finally{if(mounted)setState(()=>busy=false);}
  }
  @override Widget build(BuildContext context){
    final cast=NebulaCharacter.fromGuide(widget.guide);
    return Scaffold(appBar:AppBar(title:Text('Personajes · ${cast.length}'),actions:[IconButton(tooltip:'Importar arte anime',onPressed:busy?null:_import,icon:const Icon(Icons.file_download_outlined))]),body:Column(children:[
      Padding(padding:const EdgeInsets.all(12),child:OutlinedButton.icon(onPressed:busy?null:_import,icon:const Icon(Icons.image_outlined),label:const Text('Importar personajes y paisajes'))),
      if(busy)const LinearProgressIndicator(),
      Expanded(child:cast.isEmpty?const Center(child:Text('Sincroniza la guía para recibir el reparto.')):GridView.builder(padding:const EdgeInsets.all(12),gridDelegate:const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount:2,crossAxisSpacing:12,mainAxisSpacing:12,childAspectRatio:.72),itemCount:cast.length,itemBuilder:(context,i){
        final p=cast[i];return Card(clipBehavior:Clip.antiAlias,child:InkWell(onTap:()=>showDialog<void>(context:context,builder:(ctx)=>AlertDialog(title:Text(p.name),content:Column(mainAxisSize:MainAxisSize.min,children:[SizedBox(height:190,width:190,child:AnimePortrait(id:p.id,guide:widget.guide)),const SizedBox(height:12),Text(p.role,style:const TextStyle(fontWeight:FontWeight.bold)),Text(p.bio)]),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Cerrar'))])),child:Column(children:[Expanded(child:AnimePortrait(id:p.id,guide:widget.guide)),Padding(padding:const EdgeInsets.all(8),child:Column(children:[Text(p.name,style:const TextStyle(fontWeight:FontWeight.bold)),Text(p.role,maxLines:1,overflow:TextOverflow.ellipsis)]) )])));
      })),
    ]));
  }
}

/// Select a landscape by exact story location; biome is a safe default for new chapters.
String nebulaLandscapeKey(String place,String biome){
  const locations=<String,String>{
    'distrito de los puentes':'puentes',
    'almacén de la luna':'almacen',
    'plaza del reloj':'plaza',
    'barrio de los refugiados':'barrio',
    'puerta de hierro':'forja',
    'taller secreto':'forja',
    'avenida de los gremios':'mercado',
    'torre del consejo':'tribunal',
    'archivo de la luna':'archivo',
    'muelles del norte':'puerto',
    'salón de subastas':'subastas',
    'tribunal de comerciantes':'tribunal',
    'callejón de obsidiana':'barrio',
    'puerto de la aurora':'puerto',
    'taller del reloj':'forja',
    'casa de los gremios':'tribunal',
    'muralla del oeste':'muralla',
    'palacio de cristal':'tesoreria',
    'mercado de espejos':'mercado',
    'archivo prohibido':'archivo',
    'avenida del eclipse':'mercado',
    'puerto imperial':'puerto',
    'tesorería real':'tesoreria',
    'tribunal del eclipse':'tribunal',
  };
  return 'scene_'+(locations[place.trim().toLowerCase()]??(biome=='torre'?'tribunal':biome=='forja'?'forja':'mercado'));
}
class NebulaLandscape extends StatelessWidget {
  const NebulaLandscape({super.key,required this.place,required this.biome});
  final String place,biome;
  @override Widget build(BuildContext context)=>ValueListenableBuilder<int>(
    valueListenable:MemoraArtStore.revision,
    builder:(context,_,child)=>FutureBuilder<Map<String,Uint8List>>(
      future:MemoraArtStore.load(),
      builder:(context,snapshot){
        final bytes=snapshot.data?[nebulaLandscapeKey(place,biome)];
        if(bytes==null)return const SizedBox.expand();
        return Image.memory(bytes,fit:BoxFit.cover,width:double.infinity,height:double.infinity,gaplessPlayback:true,errorBuilder:(context,error,stack)=>const SizedBox.expand());
      },
    ),
  );
}

class AdventureArtStore {
  static const maxBytes=32*1024*1024;
  static const maxAssets=512;
  static final _cache=<String,Future<Map<String,Uint8List>>>{};
  static bool isNebula(String id)=>id=='nebula-finanzas-rpg'||id.endsWith('_nebula-finanzas-rpg');
  static bool validId(dynamic id)=>id is String&&RegExp(r'^[a-z0-9_]{1,80}$').hasMatch(id);
  static void invalidateLegacy()=>_cache.removeWhere((id,_)=>isNebula(id));
  static Future<File> _file(String guideId)async{
    final dir=Directory('${(await getApplicationSupportDirectory()).path}/adventure-art-v2');
    await dir.create(recursive:true);
    final key=base64Url.encode(utf8.encode(guideId)).replaceAll('=','');
    if(key.length>220)throw const FormatException('Identificador demasiado largo.');
    return File('${dir.path}/$key.json');
  }
  static Map<String,String> validatePart(dynamic root,{String? expected}){
    if(root is! Map||root['schema']!=2||root['kind']!='memora_adventure_art_v2'||root['adventure'] is! String||(expected!=null&&root['adventure']!=expected)||root['assets'] is! Map)throw const FormatException('Paquete de arte incompatible.');
    final entries=root['assets'] as Map;
    if(entries.isEmpty||entries.length>maxAssets)throw const FormatException('Cantidad de imágenes inválida.');
    final out=<String,String>{};
    var total=0;
    for(final e in entries.entries){
      final id=e.key,encoded=e.value;
      if(!validId(id)||encoded is! String||encoded.length>1200000)throw const FormatException('Imagen inválida.');
      total+=encoded.length;
      if(total>maxBytes)throw const FormatException('Paquete demasiado grande.');
      final b=base64Decode(encoded);
      if(b.length<12||ascii.decode(b.sublist(0,4),allowInvalid:true)!='RIFF'||ascii.decode(b.sublist(8,12),allowInvalid:true)!='WEBP')throw const FormatException('Se requiere WebP.');
      out[id as String]=encoded;
    }
    return out;
  }
  static Map<String,String> mergeParts(List<dynamic> parts,String adventure){
    final all=<String,String>{};
    var size=0;
    for(final p in parts){
      for(final e in validatePart(p,expected:adventure).entries){
        if(all.containsKey(e.key))throw const FormatException('Imagen duplicada.');
        size+=e.value.length;
        if(size>maxBytes||all.length>=maxAssets)throw const FormatException('Paquete demasiado grande.');
        all[e.key]=e.value;
      }
    }
    if(all.isEmpty)throw const FormatException('Paquete vacío.');
    return all;
  }
  static Future<int> saveParts(String guideId,String adventure,List<dynamic> parts)async{
    final all=mergeParts(parts,adventure);
    final encoded=jsonEncode({'schema':2,'kind':'memora_adventure_art_v2','adventure':adventure,'assets':all});
    if(utf8.encode(encoded).length>maxBytes)throw const FormatException('Paquete demasiado grande.');
    final f=await _file(guideId),tmp=File(f.path+'.tmp');
    await tmp.writeAsString(encoded,flush:true);await tmp.rename(f.path);
    _cache.remove(guideId);MemoraArtStore.revision.value++;
    return all.length;
  }
  static Future<Map<String,Uint8List>> load(String guideId)=>_cache.putIfAbsent(guideId,()=>_load(guideId));
  static Future<Map<String,Uint8List>> _load(String guideId)async{
    final legacy=isNebula(guideId)?await MemoraArtStore.load():<String,Uint8List>{};
    try{
      final f=await _file(guideId);
      if(await f.exists()&&await f.length()<=maxBytes){
        final all=validatePart(jsonDecode(await f.readAsString()));
        return {...legacy,for(final e in all.entries)e.key:base64Decode(e.value)};
      }
    }catch(_){}
    return legacy;
  }
  static Future<int?> importLocal(StudyGuide guide)async{
    final selected=await FilePicker.pickFile(type:FileType.custom,allowedExtensions:['json'],dialogTitle:'Arte de esta aventura');
    if(selected==null)return null;
    final b=await selected.readAsBytes();
    if(b.length>maxBytes)throw const FormatException('Paquete demasiado grande.');
    final raw=jsonDecode(utf8.decode(b));
    if(raw is Map&&raw['schema']==1){
      if(!isNebula(guide.id))throw const FormatException('Este paquete pertenece a Nébula.');
      return MemoraArtStore.save(raw);
    }
    if(raw is! Map||raw['adventure'] is! String)throw const FormatException('Paquete incompatible.');
    final id=raw['adventure'] as String;
    if(guide.id!=id&&!guide.id.endsWith('_$id'))throw const FormatException('El paquete pertenece a otra aventura.');
    if(id=='entre-dos-mundos-academia'){
      final additions=validatePart(raw,expected:id);
      final current=await load(guide.id);
      return saveParts(guide.id,id,[{'schema':2,'kind':'memora_adventure_art_v2','adventure':id,'assets':{for(final e in current.entries)e.key:base64Encode(e.value),...additions}}]);
    }
    return saveParts(guide.id,id,[raw]);
  }
}
class AdventureActor {
  const AdventureActor(this.id,{this.expression='',this.label='',this.position=0,this.scale=1});
  final String id,expression,label;
  final double position,scale;
}
class AdventureVisualSpec {
  const AdventureVisualSpec({this.background,this.actors=const [],this.height=300});
  final String? background;
  final List<AdventureActor> actors;
  final double height;
  static AdventureVisualSpec? parse(dynamic raw){
    if(raw is! Map)return null;
    final bg=AdventureArtStore.validId(raw['background'])?raw['background'] as String:null;
    final actors=<AdventureActor>[];
    final list=raw['actors'];
    double bound(dynamic n,double fallback,double lo,double hi)=>n is num&&n.isFinite?n.toDouble().clamp(lo,hi).toDouble():fallback;
    if(list is List){
      for(final item in list.take(4)){
        if(item is! Map||!AdventureArtStore.validId(item['id']))continue;
        final expression=AdventureArtStore.validId(item['expression'])?item['expression'] as String:'';
        final label=item['label'] is String?item['label'] as String:'';
        actors.add(AdventureActor(item['id'] as String,expression:expression,label:label.length>80?label.substring(0,80):label,position:bound(item['position'],0,-1,1),scale:bound(item['scale'],1,.35,1.5)));
      }
    }
    if(bg==null&&actors.isEmpty)return null;
    return AdventureVisualSpec(background:bg,actors:actors,height:bound(raw['height'],300,200,420));
  }
}
class AdventureSceneView extends StatelessWidget {
  const AdventureSceneView({super.key,required this.guide,required this.visual,this.location=''});
  final StudyGuide guide;
  final AdventureVisualSpec visual;
  final String location;
  @override Widget build(BuildContext context)=>ClipRRect(
    borderRadius:BorderRadius.circular(16),
    child:SizedBox(height:visual.height,child:ValueListenableBuilder<int>(
      valueListenable:MemoraArtStore.revision,
      builder:(context,_,child)=>FutureBuilder<Map<String,Uint8List>>(
        future:AdventureArtStore.load(guide.id),
        builder:(context,snapshot){
          final assets=snapshot.data??const <String,Uint8List>{};
          final bg=assets[visual.background];
          return LayoutBuilder(builder:(context,box)=>Stack(fit:StackFit.expand,children:[
            const DecoratedBox(decoration:BoxDecoration(gradient:LinearGradient(colors:[Color(0xff101c31),Color(0xff28474f)]))),
            if(bg!=null)Image.memory(bg,fit:BoxFit.cover,gaplessPlayback:true,errorBuilder:(context,error,stack)=>const SizedBox.expand()),
            if(bg==null&&visual.background!=null&&snapshot.connectionState==ConnectionState.done)
              const Align(alignment:Alignment.topCenter,child:Padding(padding:EdgeInsets.all(8),child:Text('Paisaje pendiente de sincronizar',style:TextStyle(color:Colors.white70,fontSize:12)))),
            for(final actor in visual.actors)
              Align(alignment:Alignment(actor.position,1),child:SizedBox(
                width:box.maxWidth*(visual.actors.length==1 ? .8 : .46),
                height:(box.maxHeight*.70*actor.scale).clamp(80.0,box.maxHeight).toDouble(),
                child:Stack(fit:StackFit.expand,children:[
                  Positioned.fill(bottom:actor.label.isEmpty?0:24,child:AnimePortrait(id:actor.id,expression:actor.expression,guide:guide,fit:BoxFit.contain,transparentBackground:true)),
                  if(actor.label.isNotEmpty)Positioned(bottom:0,left:0,right:0,child:Container(color:const Color(0xb0101a2b),padding:const EdgeInsets.all(5),child:Text(actor.label,textAlign:TextAlign.center,maxLines:1,overflow:TextOverflow.ellipsis,style:const TextStyle(color:Color(0xfff6ce85),fontWeight:FontWeight.bold)))),
                ]),
              )),
            if(location.isNotEmpty)Positioned(left:10,top:10,right:10,child:Align(alignment:Alignment.topLeft,child:Container(padding:const EdgeInsets.symmetric(horizontal:10,vertical:6),decoration:BoxDecoration(color:const Color(0xbf101a2b),borderRadius:BorderRadius.circular(10)),child:Text(location,style:const TextStyle(color:Color(0xfff6ce85),fontWeight:FontWeight.bold))))),
          ]));
        },
      ),
    )),
  );
}
