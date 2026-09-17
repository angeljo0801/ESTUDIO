import 'dart:convert';
import 'dart:io';

import 'package:flutter_file_dialog/flutter_file_dialog.dart';
import 'package:path_provider/path_provider.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

class ChatMessage {
  const ChatMessage({required this.role,required this.text,required this.createdAt,this.attachments=const [],this.responseSeconds});
  final String role;
  final String text;
  final DateTime createdAt;
  final List<String> attachments;
  final double? responseSeconds;
  ChatMessage copyWith({String? text,List<String>? attachments,double? responseSeconds})=>ChatMessage(role:role,text:text??this.text,createdAt:createdAt,attachments:attachments??this.attachments,responseSeconds:responseSeconds??this.responseSeconds);
  Map<String,dynamic> toJson()=>{'role':role,'text':text,'createdAt':createdAt.toIso8601String(),'attachments':attachments,if(responseSeconds!=null)'responseSeconds':responseSeconds};
  factory ChatMessage.fromJson(Map<String,dynamic> json)=>ChatMessage(role:json['role']?.toString()=='assistant'?'assistant':'user',text:json['text']?.toString()??'',createdAt:DateTime.tryParse(json['createdAt']?.toString()??'')??DateTime.now(),attachments:(json['attachments'] is List)?(json['attachments'] as List).map((e)=>e.toString()).toList():const [],responseSeconds:(json['responseSeconds'] as num?)?.toDouble());
}

class ChatSession {
  const ChatSession({required this.id,required this.ownerType,required this.ownerId,required this.title,required this.createdAt,required this.updatedAt,required this.messages});
  final String id; final String ownerType; final String ownerId; final String title; final DateTime createdAt; final DateTime updatedAt; final List<ChatMessage> messages;
  factory ChatSession.empty({required String ownerType,required String ownerId}){final now=DateTime.now();return ChatSession(id:'chat_${now.microsecondsSinceEpoch}',ownerType:ownerType,ownerId:ownerId,title:'Nuevo chat',createdAt:now,updatedAt:now,messages:const []);}
  ChatSession copyWith({String? title,DateTime? updatedAt,List<ChatMessage>? messages})=>ChatSession(id:id,ownerType:ownerType,ownerId:ownerId,title:title??this.title,createdAt:createdAt,updatedAt:updatedAt??this.updatedAt,messages:messages??this.messages);
  String conversationContext({int maxChars=6000,int maxMessages=12}){if(messages.isEmpty)return '(Sin mensajes anteriores)';final selected=messages.length>maxMessages?messages.sublist(messages.length-maxMessages):messages;final chunks=<String>[];var used=0;for(final message in selected.reversed){if(message.text.trim().isEmpty)continue;final label=message.role=='assistant'?'ASISTENTE':'USUARIO';final line='$label: ${message.text.trim()}';final remaining=maxChars-used;if(remaining<=80)break;final clipped=line.length>remaining?line.substring(0,remaining):line;chunks.add(clipped);used+=clipped.length+1;}return chunks.reversed.join('\n');}
  Map<String,dynamic> toJson()=>{'id':id,'ownerType':ownerType,'ownerId':ownerId,'title':title,'createdAt':createdAt.toIso8601String(),'updatedAt':updatedAt.toIso8601String(),'messages':messages.map((m)=>m.toJson()).toList()};
  factory ChatSession.fromJson(Map<String,dynamic> json)=>ChatSession(id:json['id']?.toString()??'',ownerType:json['ownerType']?.toString()??'',ownerId:json['ownerId']?.toString()??'',title:json['title']?.toString()??'Chat',createdAt:DateTime.tryParse(json['createdAt']?.toString()??'')??DateTime.now(),updatedAt:DateTime.tryParse(json['updatedAt']?.toString()??'')??DateTime.now(),messages:(json['messages'] is List)?(json['messages'] as List).whereType<Map>().map((e)=>ChatMessage.fromJson(Map<String,dynamic>.from(e))).toList():const []);
  static String titleFrom(String text,{String fallback='Nuevo chat'}){final clean=text.replaceAll(RegExp(r'\s+'),' ').trim();if(clean.isEmpty)return fallback;return clean.length<=46?clean:'${clean.substring(0,46).trim()}…';}
}

class ChatStore {
  static Future<File> _file() async {final root=await getApplicationDocumentsDirectory();final dir=Directory('${root.path}/chat_history');await dir.create(recursive:true);return File('${dir.path}/sessions.json');}
  static Future<List<ChatSession>> loadAll() async {try{final file=await _file();if(!await file.exists())return [];final decoded=jsonDecode(await file.readAsString());if(decoded is! List)return [];return decoded.whereType<Map>().map((e)=>ChatSession.fromJson(Map<String,dynamic>.from(e))).toList();}catch(_){return [];}}
  static Future<List<ChatSession>> forOwner({required String ownerType,required String ownerId}) async {final all=await loadAll();final result=all.where((s)=>s.ownerType==ownerType&&s.ownerId==ownerId).toList();result.sort((a,b)=>b.updatedAt.compareTo(a.updatedAt));return result;}
  static Future<void> save(ChatSession session) async {final all=await loadAll();final i=all.indexWhere((s)=>s.id==session.id);if(i>=0)all[i]=session;else all.add(session);await (await _file()).writeAsString(jsonEncode(all.map((s)=>s.toJson()).toList()),flush:true);}
  static Future<void> delete(String sessionId) async {final all=await loadAll();all.removeWhere((s)=>s.id==sessionId);await (await _file()).writeAsString(jsonEncode(all.map((s)=>s.toJson()).toList()),flush:true);}
  static Future<String?> exportPdf(ChatSession session,{required String participantName}) async {final doc=pw.Document();doc.addPage(pw.MultiPage(pageFormat:PdfPageFormat.a4,margin:const pw.EdgeInsets.all(36),build:(_)=>[pw.Text(session.title,style:pw.TextStyle(fontSize:20,fontWeight:pw.FontWeight.bold)),pw.SizedBox(height:8),pw.Text('Memora chat • $participantName'),pw.SizedBox(height:18),...session.messages.where((m)=>m.text.trim().isNotEmpty).map((m)=>pw.Padding(padding:const pw.EdgeInsets.only(bottom:12),child:pw.Column(crossAxisAlignment:pw.CrossAxisAlignment.start,children:[pw.Text(m.role=='user'?'You':participantName,style:pw.TextStyle(fontWeight:pw.FontWeight.bold)),pw.SizedBox(height:3),pw.Text(m.text),if(m.attachments.isNotEmpty)pw.Text('Attachments: ${m.attachments.join(', ')}',style:const pw.TextStyle(fontSize:9)),if(m.responseSeconds!=null&&m.role=='assistant')pw.Text('${m.responseSeconds!.toStringAsFixed(1)} s',style:const pw.TextStyle(fontSize:9))])))]));final root=await getTemporaryDirectory();final file=File('${root.path}/memora_chat_${DateTime.now().millisecondsSinceEpoch}.pdf');await file.writeAsBytes(await doc.save(),flush:true);final path=await FlutterFileDialog.saveFile(params:SaveFileDialogParams(sourceFilePath:file.path,fileName:'Memora_${session.title.replaceAll(RegExp(r'[^A-Za-z0-9_-]+'),'_')}.pdf'));return path;}
}
