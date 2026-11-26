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
        if(r is! Map||r['kind']!='memora_trade_cast_v1'||r['characters'] is! List)continue;
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
  const AnimePortrait({super.key,required this.id,this.expression='',this.fit=BoxFit.cover,this.transparentBackground=false});
  final String id,expression;
  final BoxFit fit;
  final bool transparentBackground;
  @override Widget build(BuildContext context)=>ValueListenableBuilder<int>(valueListenable:MemoraArtStore.revision,builder:(context,_,child)=>FutureBuilder<Map<String,Uint8List>>(future:MemoraArtStore.load(),builder:(context,snapshot){
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
    try{final n=await MemoraArtStore.importLocal();if(n!=null&&mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('Arte instalado: $n recursos gráficos.')));}
    catch(e){if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(e.toString())));}
    finally{if(mounted)setState(()=>busy=false);}
  }
  @override Widget build(BuildContext context){
    final cast=NebulaCharacter.fromGuide(widget.guide);
    return Scaffold(appBar:AppBar(title:Text('Personajes · ${cast.length}'),actions:[IconButton(tooltip:'Importar arte anime',onPressed:busy?null:_import,icon:const Icon(Icons.file_download_outlined))]),body:Column(children:[
      Padding(padding:const EdgeInsets.all(12),child:OutlinedButton.icon(onPressed:busy?null:_import,icon:const Icon(Icons.image_outlined),label:const Text('Importar personajes y paisajes'))),
      if(busy)const LinearProgressIndicator(),
      Expanded(child:cast.isEmpty?const Center(child:Text('Sincroniza la guía para recibir el reparto.')):GridView.builder(padding:const EdgeInsets.all(12),gridDelegate:const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount:2,crossAxisSpacing:12,mainAxisSpacing:12,childAspectRatio:.72),itemCount:cast.length,itemBuilder:(context,i){
        final p=cast[i];return Card(clipBehavior:Clip.antiAlias,child:InkWell(onTap:()=>showDialog<void>(context:context,builder:(ctx)=>AlertDialog(title:Text(p.name),content:Column(mainAxisSize:MainAxisSize.min,children:[SizedBox(height:190,width:190,child:AnimePortrait(id:p.id)),const SizedBox(height:12),Text(p.role,style:const TextStyle(fontWeight:FontWeight.bold)),Text(p.bio)]),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Cerrar'))])),child:Column(children:[Expanded(child:AnimePortrait(id:p.id)),Padding(padding:const EdgeInsets.all(8),child:Column(children:[Text(p.name,style:const TextStyle(fontWeight:FontWeight.bold)),Text(p.role,maxLines:1,overflow:TextOverflow.ellipsis)]) )])));
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
