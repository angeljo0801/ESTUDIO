from pathlib import Path
import os

# Bring Agent chat response routing in line with the Tutor fast/normal/deep engine.
p = Path('lib/agent_page.dart')
s = p.read_text()
anchor = "  Future<void> _runAgent() async {\n"
helpers = r'''  bool _isQuickAgentGreeting(String value) {
    final text = value.toLowerCase().trim();
    if (text.isEmpty || text.length > 70) return false;
    return RegExp(r'^(?:hola|hello|hi|hey|buenas|buenos días|buenas tardes|buenas noches|qué tal|que tal)[!,.?\s]*$', caseSensitive: false).hasMatch(text);
  }

  bool _isSimpleAgentRequest(String value) {
    final text = value.toLowerCase().trim();
    if (text.isEmpty || text.length > 180 || AiService.looksLikeTask(text)) return false;
    if (RegExp(r'\b(step by step|in detail|deeply|compare and contrast|analyze|analysis|paso a paso|en detalle|profundamente|compara y contrasta|analiza|análisis)\b', caseSensitive: false).hasMatch(text)) return false;
    return RegExp(r"[A-Za-zÀ-ÿ0-9']+").allMatches(text).length <= 28;
  }

'''
if '_isQuickAgentGreeting(' not in s:
    if anchor not in s: raise RuntimeError('agent run anchor not found')
    s=s.replace(anchor,helpers+anchor,1)
start=s.find(anchor); end=s.find('\n  @override\n  Widget build',start)
if start < 0 or end < 0: raise RuntimeError('agent run block bounds not found')
new_run=r'''  Future<void> _runAgent() async {
    final agent = activeAgent;
    final request = input.text.trim();
    if (agent == null || request.isEmpty || busy) return;
    final isGreeting = _isQuickAgentGreeting(request);
    final simple = _isSimpleAgentRequest(request);
    input.clear();
    setState(() { busy = true; answer = isGreeting ? '' : 'Thinking…'; });
    try {
      if (isGreeting) {
        final spanish=RegExp(r'\b(hola|buenas|buenos|qué tal|que tal)\b',caseSensitive:false).hasMatch(request);
        if(mounted)setState(()=>answer=spanish?'¡Hola! Soy ${agent.name}. ¿En qué puedo ayudarte?':'Hi! I’m ${agent.name}. How can I help?');
        return;
      }
      final limits=_retrievalLimits();
      final contextChars=simple&&responseMode=='fast'?2400:limits.$1;
      final contextChunks=simple&&responseMode=='fast'?2:limits.$2;
      var context=KnowledgeRetriever.buildContext(guides:activeGuides,query:'${agent.prompt}\n$request',maxChars:contextChars,maxChunks:contextChunks,allowUnmatchedFallback:false);
      if(context.startsWith('(No matching evidence found'))context=KnowledgeRetriever.buildCoverageContext(guides:activeGuides,maxChars:simple&&responseMode=='fast'?3600:limits.$1,maxChunks:simple&&responseMode=='fast'?4:limits.$2);
      final answerStyle=responseMode=='fast'?'Answer directly and concisely. No preamble or unnecessary repetition.':responseMode=='deep'?'Give a thorough but focused answer, following the agent instructions carefully.':'Give a clear, focused answer with enough context to be useful.';
      final result=await AiService.askConfigured(providerOverride:agent.modelSource=='global'?'global':agent.modelSource,responseMode:simple&&responseMode=='fast'?'fast':responseMode,onPartial:(partial){if(mounted&&partial.isNotEmpty)setState(()=>answer=partial);},prompt:'''You are ${agent.name}, a custom Memora agent.

AGENT SYSTEM PROMPT:
${agent.prompt}

RELEVANT CONTENT FROM THE AGENT'S ASSIGNED KNOWLEDGE BASES:
$context

USER REQUEST:
$request

RESPONSE STYLE:
$answerStyle

Follow the agent system prompt. Use assigned knowledge when relevant. If information should come from the assigned knowledge bases but is not present, say so rather than inventing it.''');
      if(mounted)setState((){answer=result;accelerationLabel=AiService.localAccelerationLabel;});
    } catch(e){if(mounted)setState(()=>answer='El agente no pudo responder: ${AiService.userFacingError(e)}');}
    finally{if(mounted)setState(()=>busy=false);}
  }
'''
s=s[:start]+new_run+s[end:]
p.write_text(s)
print('Agent chat now shares Tutor-style response routing')

_v153=Path(os.environ['GITHUB_WORKSPACE'])/'memora_upgrade'/'v153_general_ai_chat_patch.py'
exec(compile(_v153.read_text(),str(_v153),'exec'))
