import 'dart:convert';
import 'package:http/http.dart' as http;

class AiService {
  static Future<String> ask({required String apiKey, required String prompt}) async {
    final uri=Uri.parse('https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=$apiKey');
    final response=await http.post(uri,headers:{'Content-Type':'application/json'},body:jsonEncode({'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'temperature':0.25}}));
    if(response.statusCode!=200) throw Exception('Gemini respondió ${response.statusCode}');
    final data=jsonDecode(response.body);
    return data['candidates']?[0]?['content']?['parts']?[0]?['text'] ?? 'No pude generar una respuesta.';
  }
}
