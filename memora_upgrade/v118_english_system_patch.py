from pathlib import Path

# Memora v1.18
# English-only system/UI pass. This patch runs last so it also translates text
# introduced by previous patches. It also migrates saved built-in tutor wording
# and invalidates old Spanish exam sessions while preserving guide progress.


def replace_many(path, pairs):
    p = Path(path)
    s = p.read_text()
    for old, new in pairs:
        s = s.replace(old, new)
    p.write_text(s)

# -----------------------------------------------------------------------------
# Navigation + library
# -----------------------------------------------------------------------------
replace_many('lib/app_shell.dart', [
    ("label: 'Biblioteca'", "label: 'Library'"),
    ("label: 'Agentes'", "label: 'Agents'"),
    ("label: 'Crear'", "label: 'Create'"),
    ("label: 'Examen'", "label: 'Exam'"),
])

replace_many('lib/home_page.dart', [
    ("'Listo: ${guide.cards.length} repasos creados.'", "'Done: ${guide.cards.length} review cards created.'"),
    ("'No pude importar la guía: $e'", "'I could not import the guide: $e'"),
    ("'Pegar una guía'", "'Paste a guide'"),
    ("'Título'", "'Title'"),
    ("'Contenido de la guía'", "'Guide content'"),
    ("'Cancelar'", "'Cancel'"),
    ("'Crear'", "'Create'"),
    ("'Guía pegada'", "'Pasted guide'"),
    ("sourceType: 'texto'", "sourceType: 'text'"),
    ("sourceName: 'Texto pegado'", "sourceName: 'Pasted text'"),
    ("'Necesitas al menos dos guías para fusionar.'", "'You need at least two guides to merge.'"),
    ("'Fusionar guías'", "'Merge guides'"),
    ("'Selecciona dos o más. Se creará una nueva guía sin borrar las originales.'", "'Select two or more. A new guide will be created without deleting the originals.'"),
    ("'Fusionar ${selected.length} guía(s)'", "'Merge ${selected.length} guide(s)'"),
    ("'Guía fusionada'", "'Merged guide'"),
    ("'Nombre de la guía fusionada'", "'Merged guide name'"),
    ("sourceName: '${sources.length} guías fusionadas'", "sourceName: '${sources.length} merged guides'"),
    ("'Guía fusionada creada con ${sources.length} fuentes.'", "'Merged guide created from ${sources.length} sources.'"),
    ("'Importar archivo'", "'Import file'"),
    ("'Crear PDF o Excel con IA'", "'Create PDF or Excel with AI'"),
    ("'Escoge la IA y usa otras guías como fuentes si quieres'", "'Choose the AI and optionally use other guides as sources'"),
    ("'Combina varias guías en una nueva'", "'Combine several guides into a new one'"),
    ("'Pegar texto'", "'Paste text'"),
    ("'Copia una guía desde cualquier app'", "'Paste a guide from any app'"),
    ("'Biblioteca, tutores y agentes'", "'Library, tutors and agents'"),
    ("'Procesando…'", "'Processing…'"),
    ("'Añadir / crear'", "'Add / create'"),
    ("' tarjetas'", "' cards'"),
    ("' • exportable'", "' • exportable'"),
    ("' por repasar'", "' due'"),
    ("' dominadas'", "' mastered'"),
    ("'guía disponible'", "'guide available'"),
    ("'guías disponibles'", "'guides available'"),
    ("' para estudiar o usar como conocimiento.'", "' to study or use as knowledge.'"),
    ("'Crea o importa tu primera guía'", "'Create or import your first guide'"),
    ("'Importa PDF, Excel, DOCX, TXT o Markdown; o deja que una IA cree un PDF/Excel por ti.'", "'Import PDF, Excel, DOCX, TXT or Markdown, or let an AI create a PDF/Excel for you.'"),
    ("'Añadir mi primera guía'", "'Add my first guide'"),
])

# -----------------------------------------------------------------------------
# Card/question language and one-time in-place migration of old generated labels
# -----------------------------------------------------------------------------
replace_many('lib/study_engine.dart', [
    ("'Guía sin título'", "'Untitled guide'"),
    ("'¿Cuál es la fórmula o relación de $left?'", "'What is the formula or relationship for $left?'"),
    ("'¿Qué significa o cómo se explica “$term”?'", "'What does “$term” mean?'"),
    ("'¿Qué es o qué significa $term?'", "'What is or what does $term mean?'"),
    ("'Completa la idea:\\n$blanked'", "'Complete the idea:\\n$blanked'"),
    ("'Explica esta idea: $cue…'", "'Explain this idea: $cue…'"),
    ("r'^¿?(?:qué es o qué significa|qué significa o cómo se explica)\\s+[“\"]?(.+?)[”\"]?\\?$'", "r'^(?:what is or what does|what does)\\s+[“\"]?(.+?)[”\"]?(?:\\s+mean)?\\?$'"),
    ("q.startsWith('Completa la idea:')", "q.startsWith('Complete the idea:')"),
])

# Preserve spaced-repetition statistics while translating cards already stored
# on the phone from earlier versions.
p = Path('lib/guide_store.dart')
s = p.read_text()
anchor = "      var repaired = false;\n"
helper = r'''      String englishQuestion(String question) {
        var q = question;
        q = q.replaceFirst(RegExp(r'^¿Cuál es la fórmula o relación de (.+)\?$'), 'What is the formula or relationship for \$1?');
        q = q.replaceFirst(RegExp(r'^¿Qué significa o cómo se explica [“"](.+)[”"]\?$'), 'What does “\$1” mean?');
        q = q.replaceFirst(RegExp(r'^¿Qué es o qué significa (.+)\?$'), 'What is or what does \$1 mean?');
        q = q.replaceFirst('Completa la idea:', 'Complete the idea:');
        q = q.replaceFirst('Explica esta idea:', 'Explain this idea:');
        return q;
      }

'''
if anchor not in s:
    raise RuntimeError('GuideStore repair anchor not found')
s = s.replace(anchor, helper + anchor, 1)
old = """      for (final guide in guides) {
        final cleaned = guide.cards.where(StudyEngine.isCardUsable).toList();
"""
new = """      for (final guide in guides) {
        final translated = guide.cards.map((card) {
          final question = englishQuestion(card.question);
          if (question == card.question) return card;
          repaired = true;
          return StudyCard(
            id: card.id,
            question: question,
            answer: card.answer,
            source: card.source,
            dueAt: card.dueAt,
            intervalDays: card.intervalDays,
            ease: card.ease,
            correct: card.correct,
            wrong: card.wrong,
            streak: card.streak,
          );
        }).toList();
        guide.cards = translated;
        final cleaned = guide.cards.where(StudyEngine.isCardUsable).toList();
"""
if old not in s:
    raise RuntimeError('GuideStore card migration anchor not found')
s = s.replace(old, new, 1)
s = s.replace('// La guía ya fue retirada de la biblioteca; un fallo al limpiar el archivo no debe bloquear la app.', '// The guide is already removed from the library; file cleanup must not block the app.')
p.write_text(s)

# -----------------------------------------------------------------------------
# Review + quiz + guide details
# -----------------------------------------------------------------------------
replace_many('lib/review_page.dart', [
    ("'Repaso terminado'", "'Review complete'"),
    ("'No hay tarjetas válidas para repasar'", "'There are no valid cards to review'"),
    ("'Sesión completada'", "'Session complete'"),
    ("'Memora descartó tarjetas incompletas o fragmentadas de esta guía.'", "'Memora discarded incomplete or fragmented cards from this guide.'"),
    ("'$_good bien • $_again para reforzar'", "'$_good correct • $_again to reinforce'"),
    ("'Terminar'", "'Finish'"),
    ("'PREGUNTA'", "'QUESTION'"),
    ("'RESPUESTA'", "'ANSWER'"),
    ("'Toca la tarjeta para ver la respuesta'", "'Tap the card to reveal the answer'"),
    ("'Mostrar respuesta'", "'Show answer'"),
    ("'No lo sé'", "'I do not know'"),
    ("'Difícil'", "'Hard'"),
    ("'Bien'", "'Good'"),
    ("'Fácil'", "'Easy'"),
])

replace_many('lib/quiz_page.dart', [
    ("'Resultado'", "'Result'"),
    ("'No hay preguntas válidas'", "'There are no valid questions'"),
    ("'Memora descartó tarjetas incompletas o fragmentadas de esta guía.'", "'Memora discarded incomplete or fragmented cards from this guide.'"),
    ("'$_score de ${_questions.length} correctas'", "'$_score of ${_questions.length} correct'"),
    ("'Terminar'", "'Finish'"),
    ("'Examen ${_index + 1}/${_questions.length}'", "'Exam ${_index + 1}/${_questions.length}'"),
    ("'PREGUNTA'", "'QUESTION'"),
    ("'Correcto.'", "'Correct.'"),
    ("'Respuesta correcta: ${_card.answer}'", "'Correct answer: ${_card.answer}'"),
    ("'Ver resultado'", "'See result'"),
    ("'Siguiente'", "'Next'"),
])

replace_many('lib/guide_detail_page.dart', [
    ("'Necesito al menos 2 tarjetas para crear un examen.'", "'I need at least 2 cards to create an exam.'"),
    ("'${regenerated.length} tarjetas regeneradas.'", "'${regenerated.length} cards regenerated.'"),
    ("'Archivo exportado al teléfono.'", "'File exported to the phone.'"),
    ("'No pude exportar esta guía: $e'", "'I could not export this guide: $e'"),
    ("'Eliminar guía'", "'Delete guide'"),
    ("'¿Eliminar “${widget.guide.title}” y su progreso?'", "'Delete “${widget.guide.title}” and its progress?'"),
    ("'Cancelar'", "'Cancel'"),
    ("'Eliminar'", "'Delete'"),
    ("'Ver contenido extraído'", "'View extracted content'"),
    ("'Exportar archivo al móvil'", "'Export file to phone'"),
    ("'Sin archivo exportable'", "'No exportable file'"),
    ("'Regenerar preguntas'", "'Regenerate questions'"),
    ("'Exportar $fileType al teléfono'", "'Export $fileType to phone'"),
    ("'Resumen automático'", "'Automatic summary'"),
    ("label: 'Tarjetas'", "label: 'Cards'"),
    ("label: 'Pendientes'", "label: 'Due'"),
    ("label: 'Dominadas'", "label: 'Mastered'"),
    ("label: 'Precisión'", "label: 'Accuracy'"),
    ("'Repasar ${guide.dueCount} ahora'", "'Review ${guide.dueCount} now'"),
    ("'Repaso libre'", "'Free review'"),
    ("'Hacer examen'", "'Take exam'"),
    ("'Cómo funciona el repaso'", "'How review works'"),
    ("'Memora vuelve a mostrar antes lo que fallas y separa por más días lo que ya dominas. Los tutores y agentes pueden usar esta guía como base de conocimiento.'", "'Memora shows missed material sooner and spaces mastered material farther apart. Tutors and agents can use this guide as a knowledge base.'"),
])

# -----------------------------------------------------------------------------
# Imports, attachments and voice
# -----------------------------------------------------------------------------
replace_many('lib/guide_importer.dart', [
    ("'Escoge una guía o base de conocimiento'", "'Choose a guide or knowledge base'"),
    ("'El archivo está vacío.'", "'The file is empty.'"),
    ("'No pude extraer suficiente contenido. Si es un PDF escaneado como imagen, necesitará OCR.'", "'I could not extract enough content. If this is an image-scanned PDF, OCR will be required.'"),
    ("'Formato .$extension no compatible todavía.'", "'Format .$extension is not supported yet.'"),
    ("buffer.writeln('HOJA: $sheetName')", "buffer.writeln('SHEET: $sheetName')"),
    ("'El DOCX no contiene un documento de Word válido.'", "'The DOCX does not contain a valid Word document.'"),
])

replace_many('lib/query_extras_bar.dart', [
    ("'No pude adjuntar el archivo: $e'", "'I could not attach the file: $e'"),
    ("'No pude escuchar el audio: ${error.errorMsg}'", "'I could not capture the audio: ${error.errorMsg}'"),
    ("'El reconocimiento de voz no está disponible en este dispositivo.'", "'Speech recognition is not available on this device.'"),
    ("tooltip: 'Adjuntar'", "tooltip: 'Attach'"),
    ("'Tomar foto'", "'Take photo'"),
    ("'Galería / screenshot'", "'Gallery / screenshot'"),
    ("'Detener dictado'", "'Stop dictation'"),
    ("'Preguntar por voz'", "'Ask by voice'"),
    ("'Escuchando… habla tu pregunta'", "'Listening… speak your question'"),
    ("'Adjunta PDF, foto o screenshot • o dicta la pregunta'", "'Attach a PDF, photo or screenshot • or dictate your question'"),
])

replace_many('lib/query_attachment_service.dart', [
    ("'Adjuntar PDF'", "'Attach PDF'"),
    ("'El PDF está vacío.'", "'The PDF is empty.'"),
    ("'[PDF ${picked.name}: no se pudo extraer texto; podría ser un PDF escaneado.]'", "'[PDF ${picked.name}: text could not be extracted; it may be a scanned PDF.]'"),
    ("'imagen_${DateTime.now().millisecondsSinceEpoch}.jpg'", "'image_${DateTime.now().millisecondsSinceEpoch}.jpg'"),
    ("'[Imagen $name: OCR no detectó texto. Usa análisis visual si el modelo lo admite.]'", "'[Image $name: OCR did not detect text. Use visual analysis if the model supports it.]'"),
    ("'=== ADJUNTO: ${item.name} (${item.kind.toUpperCase()}) ==='", "'=== ATTACHMENT: ${item.name} (${item.kind.toUpperCase()}) ==='"),
    ("'El adjunto no es una imagen.'", "'The attachment is not an image.'"),
    ("'La imagen ya no existe.'", "'The image no longer exists.'"),
    ("'Imagen guardada en Memora. No se detectó texto mediante OCR.'", "'Image saved in Memora. OCR did not detect any text.'"),
    ("title: title.isEmpty ? 'Imagen' : title", "title: title.isEmpty ? 'Image' : title"),
])

replace_many('lib/chat_widgets.dart', [
    ("this.emptyText = 'Empieza una conversación.'", "this.emptyText = 'Start a conversation.'"),
    ("mine ? 'Tú' : participantName", "mine ? 'You' : participantName"),
])

# -----------------------------------------------------------------------------
# AI settings + transport/system language
# -----------------------------------------------------------------------------
replace_many('lib/llm_settings_page.dart', [
    ("'Modelo privado de Memora importado correctamente.'", "'Memora private model imported successfully.'"),
    ("'No pude importar el modelo privado: $e'", "'I could not import the private model: $e'"),
    ("'Android no devolvió una ubicación persistente para el archivo.'", "'Android did not return a persistent file location.'"),
    ("'Modelo compartido seleccionado. Memora no creó otra copia.'", "'Shared model selected. Memora did not create another copy.'"),
    ("'No pude seleccionar el modelo compartido: $e'", "'I could not select the shared model: $e'"),
    ("'Primero importa un modelo privado para Memora.'", "'Import a private model for Memora first.'"),
    ("'El modelo privado ya no existe en el almacenamiento de Memora.'", "'The private model no longer exists in Memora storage.'"),
    ("'Modelo privado exportado correctamente.'", "'Private model exported successfully.'"),
    ("'No pude exportar el modelo: $e'", "'I could not export the model: $e'"),
    ("'Configuración de IA guardada'", "'AI settings saved'"),
    ("'Ajustes de IA'", "'AI Settings'"),
    ("'Elige qué cerebro usará Memora'", "'Choose which AI brain Memora will use'"),
    ("'Rápido y sencillo con una clave de Google AI Studio.'", "'Fast and simple with a Google AI Studio key.'"),
    ("'LLM online compatible'", "'Compatible online LLM'"),
    ("'OpenAI o cualquier API compatible con /chat/completions.'", "'OpenAI or any API compatible with /chat/completions.'"),
    ("'LLM local'", "'Local LLM'"),
    ("'Ollama, LM Studio u otro servidor compatible, sin nube.'", "'Ollama, LM Studio or another compatible server, without the cloud.'"),
    ("'GGUF en este teléfono'", "'GGUF on this phone'"),
    ("'Memora puede usar su modelo privado o un modelo compartido con otras APK.'", "'Memora can use its private model or a model shared with other apps.'"),
    ("'Clave de Gemini'", "'Gemini key'"),
    ("'URL del LLM local'", "'Local LLM URL'"),
    ("'Nombre del modelo'", "'Model name'"),
    ("'Clave opcional'", "'Optional key'"),
    ("'El servidor debe exponer una API compatible con OpenAI. Si corre en otro equipo, usa su IP local; 127.0.0.1 solo sirve si el servidor corre en el propio teléfono.'", "'The server must expose an OpenAI-compatible API. If it runs on another device, use that device local IP; 127.0.0.1 only works when the server runs on this phone.'"),
    ("'Modelo de Memora'", "'Memora model'"),
    ("'Modelo privado de Memora'", "'Memora private model'"),
    ("'Memora guarda su propia copia. Es la opción principal y más estable.'", "'Memora stores its own copy. This is the primary and most stable option.'"),
    ("'Modelo compartido'", "'Shared model'"),
    ("'Usa un GGUF externo sin copiarlo dentro de Memora. Puede ser el mismo que usan otras APK.'", "'Use an external GGUF without copying it into Memora. It can be the same model used by other apps.'"),
    ("'Copiando modelo…'", "'Copying model…'"),
    ("'Dar modelo privado a Memora'", "'Give Memora a private model'"),
    ("'Cambiar modelo privado de Memora'", "'Change Memora private model'"),
    ("'Exportando modelo…'", "'Exporting model…'"),
    ("'Exportar modelo privado'", "'Export private model'"),
    ("'Memora todavía no tiene un modelo privado.'", "'Memora does not have a private model yet.'"),
    ("'Privado: ${deviceModelPath.split('/').last}'", "'Private: ${deviceModelPath.split('/').last}'"),
    ("'Seleccionando…'", "'Selecting…'"),
    ("'Elegir modelo compartido .gguf'", "'Choose shared .gguf model'"),
    ("'Cambiar modelo compartido'", "'Change shared model'"),
    ("'No hay un modelo compartido seleccionado.'", "'No shared model is selected.'"),
    ("'Compartido: ${sharedModelName.isEmpty ? 'modelo.gguf' : sharedModelName}'", "'Shared: ${sharedModelName.isEmpty ? 'model.gguf' : sharedModelName}'"),
    ("'Memora conserva ambos ajustes. Cambiar entre Privado y Compartido no borra el otro modelo. Así puedes dejar un modelo dedicado para Memora y otro único para el resto de tus aplicaciones.'", "'Memora keeps both settings. Switching between Private and Shared does not delete the other model, so you can keep one dedicated to Memora and another shared by your other apps.'"),
    ("'Recomendado: modelo instruct de 1B a 4B, cuantización Q4. Los modelos grandes ocupan varios GB y consumen más RAM.'", "'Recommended: a 1B to 4B instruct model with Q4 quantization. Larger models use several GB and require more RAM.'"),
    ("'Guardar y usar esta opción'", "'Save and use this option'"),
])

replace_many('lib/ai_service.dart', [
    ("'Configura la clave de Gemini en Ajustes de IA.'", "'Configure the Gemini key in AI Settings.'"),
    ("'Configura la clave y el modelo online en Ajustes de IA.'", "'Configure the online key and model in AI Settings.'"),
    ("'Indica el nombre del modelo local/Ollama en Ajustes de IA.'", "'Enter the local/Ollama model name in AI Settings.'"),
    ("'Fuente de IA no reconocida: $provider'", "'Unknown AI source: $provider'"),
    ("'No pude generar una respuesta.'", "'I could not generate a response.'"),
    ("'Eres la inteligencia de Memora. Sigue cuidadosamente las instrucciones específicas incluidas en la solicitud.'", "'You are Memora intelligence. Follow the specific instructions in the request carefully. Always answer in English unless the user explicitly asks for another language.'"),
    ("'Generación cancelada.'", "'Generation cancelled.'"),
    ("'El modelo local está ocupado con otra tarea. Espera unos segundos y vuelve a intentarlo.'", "'The local model is busy with another task. Wait a few seconds and try again.'"),
    ("'La IA encontró un error interno. Inténtalo nuevamente.'", "'The AI encountered an internal error. Try again.'"),
    ("'La IA no pudo completar la solicitud.'", "'The AI could not complete the request.'"),
])

replace_many('lib/device_llm_service.dart', [
    ("'Sin cargar'", "'Not loaded'"),
    ("'Memora no tiene un modelo privado. Ve a Ajustes de IA y dale un archivo GGUF.'", "'Memora does not have a private model. Open AI Settings and select a GGUF file.'"),
    ("'No hay un modelo compartido seleccionado. Ve a Ajustes de IA y elige un GGUF compartido.'", "'No shared model is selected. Open AI Settings and choose a shared GGUF.'"),
    ("'La ubicación del modelo compartido no es válida.'", "'The shared model location is invalid.'"),
    ("'El modelo compartido ya no existe en esa ubicación.'", "'The shared model no longer exists at that location.'"),
    ("'Android no pudo abrir el modelo compartido.'", "'Android could not open the shared model.'"),
    ("'GPU Vulkan${gpuName.isEmpty ? '' : ' • $gpuName'}'", "'Vulkan GPU${gpuName.isEmpty ? '' : ' • $gpuName'}'"),
    ("'CPU • $threads hilos'", "'CPU • $threads threads'"),
    ("'CPU • $threads hilos (GPU no compatible con este modelo)'", "'CPU • $threads threads (GPU is not compatible with this model)'"),
    ("'Generación cancelada.'", "'Generation cancelled.'"),
    ("'No se pudo iniciar el modelo GGUF.'", "'The GGUF model could not be started.'"),
    ("'Eres la inteligencia local de Memora. Sigue cuidadosamente las instrucciones del tutor o agente, responde con claridad y no inventes información.'", "'You are Memora local intelligence. Follow the tutor or agent instructions carefully, answer clearly, do not invent information, and answer in English unless the user explicitly requests another language.'"),
    ("'El modelo local no generó una respuesta.'", "'The local model did not generate a response.'"),
])

# -----------------------------------------------------------------------------
# Guide creation and AI study-guide prompts
# -----------------------------------------------------------------------------
replace_many('lib/guide_creator_page.dart', [
    ("'GGUF privado de Memora'", "'Memora private GGUF'"),
    ("'GGUF compartido'", "'Shared GGUF'"),
    ("'Gemini configurado'", "'Configured Gemini'"),
    ("'OpenAI / compatible configurado'", "'Configured OpenAI / compatible'"),
    ("'Ollama / servidor local configurado'", "'Configured Ollama / local server'"),
    ("'Configuración general de Memora'", "'Memora general settings'"),
    ("'Fuentes para crear la nueva guía'", "'Sources for the new guide'"),
    ("'No hay guías todavía. Puedes crear desde un prompt.'", "'There are no guides yet. You can create one from a prompt.'"),
    ("'Usar estas fuentes'", "'Use these sources'"),
    ("'Generando contenido con ${_sourceLabel(aiSource)}…'", "'Generating content with ${_sourceLabel(aiSource)}…'"),
    ("'Creado: $filename. Ya está en tu biblioteca.'", "'Created: $filename. It is now in your library.'"),
    ("'${format.toUpperCase()} creado y añadido a Biblioteca.'", "'${format.toUpperCase()} created and added to Library.'"),
    ("'No pude crear el archivo: $e'", "'I could not create the file: $e'"),
    ("'Crear guía con IA'", "'Create guide with AI'"),
    ("'Nombre de la guía'", "'Guide name'"),
    ("'Ej. Finanzas corporativas - Capítulo 4'", "'E.g. Corporate Finance - Chapter 4'"),
    ("'IA / modelo que creará el archivo'", "'AI / model that will create the file'"),
    ("'Usar guías existentes como fuentes (opcional)'", "'Use existing guides as sources (optional)'"),
    ("'${selectedGuideIds.length} fuente(s) seleccionada(s)'", "'${selectedGuideIds.length} source(s) selected'"),
    ("'Qué quieres que contenga'", "'What you want it to contain'"),
    ("'Describe la guía, tabla o base de datos que quieres crear…'", "'Describe the guide, table, or database you want to create…'"),
    ("'Creando archivo…'", "'Creating file…'"),
    ("'Crear y guardar en Biblioteca'", "'Create and save to Library'"),
])

# Replace the Spanish generation instructions with explicit English output.
p = Path('lib/guide_creator_page.dart')
s = p.read_text()
s = s.replace("'''Crea una guía profesional lista para guardar como PDF.", "'''Create a professional guide ready to save as PDF. Write the entire output in English.")
s = s.replace('TÍTULO: $title', 'TITLE: $title')
s = s.replace('PETICIÓN DEL USUARIO: $request', 'USER REQUEST: $request')
s = s.replace("'BASES DE CONOCIMIENTO:\\n$knowledge'", "'KNOWLEDGE BASES:\\n$knowledge'")
s = s.replace('REQUISITOS:', 'REQUIREMENTS:')
s = s.replace('- Escribe contenido claro, completo y bien organizado.', '- Write clear, complete, well-organized content.')
s = s.replace('- Usa títulos y subtítulos en texto plano.', '- Use plain-text headings and subheadings.')
s = s.replace('- Incluye explicaciones, ejemplos, conceptos clave y una sección final de repaso cuando aplique.', '- Include explanations, examples, key concepts, and a final review section when appropriate.')
s = s.replace('- Si se proporcionaron bases de conocimiento, no inventes datos que las contradigan y priorízalas.', '- If knowledge bases were provided, prioritize them and do not invent conflicting facts.')
s = s.replace('- Devuelve solamente el contenido de la guía, sin comentarios sobre el proceso.', '- Return only the guide content, with no comments about the process.')
s = s.replace("'''Crea una guía estructurada para convertirla directamente en un archivo Excel.", "'''Create a structured guide that can be converted directly into an Excel file. Write all content in English.")
s = s.replace('DEVUELVE EXCLUSIVAMENTE una tabla TSV (valores separados por TABULADORES), sin bloque de código ni explicaciones externas.', 'RETURN ONLY a TSV table (TAB-separated values), with no code block or external explanation.')
s = s.replace('La primera fila debe ser: Tema<TAB>Concepto<TAB>Explicación<TAB>Ejemplo/Nota', 'The first row must be: Topic<TAB>Concept<TAB>Explanation<TAB>Example/Note')
s = s.replace('Luego crea filas útiles y completas. No uses tabuladores dentro de una celda. Si se proporcionaron bases de conocimiento, prioriza esa información.', 'Then create useful, complete rows. Do not use tab characters inside a cell. If knowledge bases were provided, prioritize that information.')
p.write_text(s)

replace_many('lib/ai_study_guide_page.dart', [
    ("'No pude generar la guía: $e'", "'I could not generate the study guide: $e'"),
    ("'Guía de estudio'", "'Study Guide'"),
    ("'Añade primero un documento.'", "'Add a document first.'"),
    ("'Contenido para la guía'", "'Content for the guide'"),
    ("'Creando guía…'", "'Creating guide…'"),
    ("'Crear guía de estudio'", "'Create study guide'"),
    ("'Crea una guía de estudio completa en español usando SOLAMENTE este contenido. Organízala con: 1) objetivos de aprendizaje, 2) índice de temas, 3) conceptos esenciales explicados sencillamente, 4) ejemplos presentes o derivados directamente del texto, 5) vocabulario clave, 6) errores o confusiones frecuentes, 7) preguntas de práctica, 8) lista final de lo que el estudiante debe dominar. No inventes datos externos. Título: ${g.title}\\nCONTENIDO:\\n$text'", "'Create a complete study guide in English using ONLY this content. Organize it with: 1) learning objectives, 2) topic outline, 3) essential concepts explained simply, 4) examples present in or directly derived from the text, 5) key vocabulary, 6) common mistakes or confusions, 7) practice questions, 8) a final mastery checklist. Do not invent external facts. Title: ${g.title}\\nCONTENT:\\n$text'"),
])

# -----------------------------------------------------------------------------
# Study plan: all-English UI/output. Keep v1.17 local-context protections.
# -----------------------------------------------------------------------------
replace_many('lib/study_plan_page.dart', [
    ("'Añade al menos una guía a Biblioteca.'", "'Add at least one guide to Library.'"),
    ("'${ownerTutor.name} todavía no tiene guías asignadas.'", "'${ownerTutor.name} does not have any assigned guides yet.'"),
    ("'No encontré una IA disponible. Configura Gemini/OpenAI, importa un GGUF o inicia tu servidor Ollama.'", "'No AI is available. Configure Gemini/OpenAI, import a GGUF, or start your Ollama server.'"),
    ("'Mejor IA disponible'", "'Best available AI'"),
    ("'Buscando una IA disponible…'", "'Looking for an available AI…'"),
    ("'Crea el mejor plan posible, práctico, claro y sostenible.'", "'Create the best possible plan: practical, clear, and sustainable. Write everything in English.'"),
    ("'No pude crear el plan: ${AiService.userFacingError(e)}'", "'I could not create the plan: ${AiService.userFacingError(e)}'"),
    ("'Plan copiado al portapapeles.'", "'Plan copied to the clipboard.'"),
    ("'Primero crea un plan para poder exportarlo.'", "'Create a plan before exporting it.'"),
    ("'Plan de aprendizaje'", "'Learning plan'"),
    ("'Plan exportado como PDF.'", "'Plan exported as PDF.'"),
    ("'No pude exportar el plan: $e'", "'I could not export the plan: $e'"),
    ("'Mi plan de aprendizaje'", "'My Learning Plan'"),
    ("'Quién aporta el contenido'", "'Who provides the content'"),
    ("'Contenido del plan'", "'Plan content'"),
    ("'Toda mi Biblioteca'", "'My entire Library'"),
    ("'Quién crea el plan'", "'Who creates the plan'"),
    ("'Generador del plan'", "'Plan generator'"),
    ("'✨ Mejor IA disponible'", "'✨ Best available AI'"),
    ("'Memora prueba las IA configuradas y cambia automáticamente a otra si una falla. Ollama solo se usa si el servidor está accesible.'", "'Memora tries configured AIs and automatically switches if one fails. Ollama is used only when its server is reachable.'"),
    ("'Se usarán el estilo y la fuente de IA configurada para ese tutor.'", "'The style and AI source configured for that tutor will be used.'"),
    ("'¿Qué quieres llegar a dominar?'", "'What do you want to master?'"),
    ("'Minutos disponibles por día'", "'Minutes available per day'"),
    ("'Tengo una fecha objetivo'", "'I have a target date'"),
    ("'Aprendizaje continuo'", "'Continuous learning'"),
    ("'Tranquila'", "'Light'"),
    ("'Normal'", "'Normal'"),
    ("'Intensiva'", "'Intensive'"),
    ("'Intensidad'", "'Intensity'"),
    ("'Creando plan…'", "'Creating plan…'"),
    ("'Crear mi plan'", "'Create my plan'"),
    ("'Creado por: $createdBy'", "'Created by: $createdBy'"),
    ("'Fuente de IA: $usedSource'", "'AI source: $usedSource'"),
    ("'Exportar plan a PDF'", "'Export plan to PDF'"),
    ("'Copiar plan'", "'Copy plan'"),
    ("'Probando ${TutorContextService.sourceLabel(candidate)}…'", "'Trying ${TutorContextService.sourceLabel(candidate)}…'"),
])

p = Path('lib/study_plan_page.dart')
s = p.read_text()
s = s.replace('Crea en español un plan para aprender y dominar exclusivamente el contenido proporcionado.', 'Create an English-language plan to learn and master exclusively the provided content.')
s = s.replace('Objetivo del estudiante:', 'Student goal:')
s = s.replace("'Dominar progresivamente el contenido'", "'Progressively master the content'")
s = s.replace('Minutos diarios:', 'Daily minutes:')
s = s.replace('Intensidad:', 'Intensity:')
s = s.replace("'preparación con fecha objetivo'", "'preparation with a target date'")
s = s.replace("'aprendizaje continuo para la vida'", "'continuous lifelong learning'")
s = s.replace('Incluye:', 'Include:')
s = s.replace('- acciones diarias concretas;', '- concrete daily actions;')
s = s.replace('- qué estudiar primero y por qué;', '- what to study first and why;')
s = s.replace('- práctica y recuperación activa;', '- practice and active recall;')
s = s.replace('- repetición espaciada;', '- spaced repetition;')
s = s.replace('- exámenes periódicos;', '- periodic exams;')
s = s.replace('- revisión semanal;', '- weekly review;')
s = s.replace('- metas mensuales y, cuando tenga sentido, trimestrales;', '- monthly goals and, when useful, quarterly goals;')
s = s.replace('- criterios claros para saber cuándo avanzar.', '- clear criteria for when to advance.')
s = s.replace('No mezcles temas que no estén en las fuentes. Si el material es demasiado amplio, prioriza y divide por etapas.', 'Do not mix in topics that are not in the sources. If the material is too broad, prioritize it and divide it into stages.')
s = s.replace('FUENTES DEL PLAN:', 'PLAN SOURCES:')
s = s.replace('Objetivo: $objective', 'Goal: $objective')
s = s.replace('Modalidad:', 'Mode:')
s = s.replace("'Fecha objetivo'", "'Target date'")
s = s.replace('Creado por:', 'Created by:')
s = s.replace('Fuente de IA:', 'AI source:')
s = s.replace("'No indicada'", "'Not specified'")
p.write_text(s)

# -----------------------------------------------------------------------------
# Exams: English generation, UI, and a new storage key so old Spanish sessions
# cannot reappear after this upgrade.
# -----------------------------------------------------------------------------
replace_many('lib/daily_exam_page.dart', [
    ("'memora_tutor_exams_v1'", "'memora_tutor_exams_v2_en'"),
    ("'Media'", "'Medium'"),
    ("'Adaptativa'", "'Adaptive'"),
    ("'Contenido del tutor'", "'Tutor content'"),
    ("'${tutor.name} todavía no tiene material asignado para examinarte.'", "'${tutor.name} does not have assigned material for an exam yet.'"),
    ("'Instantáneo • contenido indexado'", "'Instant • indexed content'"),
    ("'Mejor IA disponible • ${TutorContextService.sourceLabel(provider ?? 'global')}'", "'Best available AI • ${TutorContextService.sourceLabel(provider ?? 'global')}'"),
    ("'No pude crear preguntas con el contenido asignado a ${tutor.name}.'", "'I could not create questions from the content assigned to ${tutor.name}.'"),
    ("'${tutor.name} todavía no tiene material para examinarte.'", "'${tutor.name} does not have material for an exam yet.'"),
    ("'Cómo redactar las preguntas'", "'How to generate the questions'"),
    ("'Instantáneo (sin IA)'", "'Instant (no AI)'"),
    ("'Mejor IA disponible'", "'Best available AI'"),
    ("'Tutor seleccionado'", "'Selected tutor'"),
    ("'Más rápido: usa las preguntas ya creadas a partir de las guías del tutor.'", "'Fastest: uses questions already created from the tutor guides.'"),
    ("'La IA redacta nuevas preguntas, pero solo recibe el material de este tutor. Para exámenes grandes, Memora completa con preguntas indexadas si hace falta.'", "'The AI writes new questions but only receives this tutor material. For large exams, Memora fills the remainder with indexed questions when needed.'"),
    ("'Examen diario'", "'Daily exam'"),
    ("'Crear examen'", "'Create exam'"),
    ("'Dificultad'", "'Difficulty'"),
    ("'Fácil'", "'Easy'"),
    ("'Difícil'", "'Hard'"),
    ("'Preguntas'", "'Questions'"),
    ("'Crear nuevo examen'", "'Create new exam'"),
    ("'Generando…'", "'Generating…'"),
    ("'Mostrar respuesta'", "'Show answer'"),
    ("'No la sabía'", "'I did not know it'"),
    ("'La sabía'", "'I knew it'"),
    ("'Pregunta ${index + 1} de ${exam.questions.length} • Puntos: $correct'", "'Question ${index + 1} of ${exam.questions.length} • Points: $correct'"),
    ("'Respuesta'", "'Answer'"),
    ("'Examen completado'", "'Exam completed'"),
    ("'Puntuación'", "'Score'"),
    ("'Cerrar'", "'Close'"),
])

p = Path('lib/daily_exam_page.dart')
s = p.read_text()
s = s.replace("'''Crea un examen de $aiCount preguntas basado EXCLUSIVAMENTE en el contenido del tutor ${tutor.name}.", "'''Create an exam with $aiCount questions in English based EXCLUSIVELY on the content of tutor ${tutor.name}.")
s = s.replace('Dificultad: $difficulty.', 'Difficulty: $difficulty.')
s = s.replace('REGLAS:', 'RULES:')
s = s.replace('- Evalúa comprensión real, no solo memorización literal.', '- Test real understanding, not just literal memorization.')
s = s.replace('- No uses información de otros tutores ni conocimiento externo.', '- Do not use information from other tutors or external knowledge.')
s = s.replace('- Distribuye las preguntas entre los temas disponibles.', '- Distribute questions across the available topics.')
s = s.replace('- La respuesta debe ser breve pero suficiente para corregir.', '- The answer must be brief but sufficient for grading.')
s = s.replace('- Devuelve SOLO un arreglo JSON válido, sin Markdown y sin explicaciones adicionales.', '- Return ONLY a valid JSON array, with no Markdown or extra explanation.')
s = s.replace('- Formato exacto de cada elemento: {"question":"...","answer":"...","source":"nombre o tema de la fuente"}.', '- Exact item format: {"question":"...","answer":"...","source":"source name or topic"}.')
s = s.replace('CONTENIDO DEL TUTOR:', 'TUTOR CONTENT:')
p.write_text(s)

# -----------------------------------------------------------------------------
# Tutors: English built-ins and English-only chat/system wording.
# -----------------------------------------------------------------------------
replace_many('lib/tutor_page.dart', [
    ("'qwen2.5:3b — equilibrado y multilingüe'", "'qwen2.5:3b — balanced and multilingual'"),
    ("'llama3.2:3b — ligero y buen diálogo'", "'llama3.2:3b — lightweight with good dialogue'"),
    ("'gemma3:4b — más contexto y 140+ idiomas'", "'gemma3:4b — more context and 140+ languages'"),
    ("'Tutor equilibrado para aprender y entender cualquier tema.'", "'Balanced tutor for learning and understanding any subject.'"),
    ("'Tutor de Finanzas'", "'Finance Tutor'"),
    ("'Tutor de Programación'", "'Programming Tutor'"),
    ("'Tutor de Idiomas'", "'Language Tutor'"),
    ("'Profesor Paso a Paso'", "'Step-by-Step Teacher'"),
    ("'Tutor Socrático'", "'Socratic Tutor'"),
    ("'Examinador Estricto'", "'Strict Examiner'"),
    ("'Repaso Express'", "'Quick Review'"),
    ("'Tutor de Ejemplos'", "'Examples Tutor'"),
    ("'Asigna una o varias guías a tu tutor y hazle una pregunta.'", "'Assign one or more guides to your tutor and ask a question.'"),
    ("'Se detectará al usar un GGUF'", "'It will be detected when a GGUF is used'"),
    ("'Configuración general de IA'", "'General AI settings'"),
    ("'GGUF privado de Memora'", "'Memora private GGUF'"),
    ("'GGUF compartido'", "'Shared GGUF'"),
    ("'Gemini configurado'", "'Configured Gemini'"),
    ("'OpenAI / compatible configurado'", "'Configured OpenAI / compatible'"),
    ("'Ollama / servidor local configurado'", "'Configured Ollama / local server'"),
    ("'Ajustes de IA'", "'AI Settings'"),
    ("'Tutores'", "'Tutors'"),
    ("'Crear tutor'", "'Create tutor'"),
    ("'Editar tutor'", "'Edit tutor'"),
    ("'Nombre del tutor'", "'Tutor name'"),
    ("'Descripción'", "'Description'"),
    ("'Instrucciones'", "'Instructions'"),
    ("'Cancelar'", "'Cancel'"),
    ("'Guardar'", "'Save'"),
    ("'Guías del tutor'", "'Tutor guides'"),
    ("'Guardar guías'", "'Save guides'"),
    ("'Eliminar tutor'", "'Delete tutor'"),
    ("'Eliminar'", "'Delete'"),
    ("'Preparando respuesta…'", "'Preparing response…'"),
    ("'Rápido'", "'Fast'"),
    ("'Normal'", "'Normal'"),
    ("'Profundo'", "'Deep'"),
    ("'Enviar'", "'Send'"),
    ("'Detener'", "'Stop'"),
])

# Translate the built-in tutor descriptions/instructions by stable ID through
# source text replacements, then force saved built-ins to refresh from defaults.
p = Path('lib/tutor_page.dart')
s = p.read_text()
translations = {
"Explica con claridad, adapta la profundidad a la pregunta, divide los temas difíciles en pasos y comprueba que el estudiante entienda.": "Explain clearly, adapt depth to the question, break difficult topics into steps, and verify that the student understands.",
"Enseña finanzas, contabilidad e inversiones con fórmulas, intuición y práctica.": "Teaches finance, accounting, and investing with formulas, intuition, and practice.",
"Actúa como profesor de finanzas. Distingue conceptos contables, finanzas corporativas, mercados e inversiones. Explica intuición, definición formal y fórmula. Define variables y unidades. Muestra cálculos paso a paso, comprueba resultados, usa ejemplos numéricos y no inventes tasas ni datos que no estén en las bases asignadas.": "Act as a finance professor. Distinguish accounting concepts, corporate finance, markets, and investments. Explain intuition, formal definitions, and formulas. Define variables and units. Show calculations step by step, verify results, use numerical examples, and do not invent rates or facts that are not in the assigned sources.",
"Especialista en código, debugging, arquitectura y aprendizaje práctico.": "Specialist in code, debugging, architecture, and practical learning.",
"Actúa como profesor y revisor de programación. Explica qué hace el código y por qué. Ante errores, identifica la causa raíz. Da código completo cuando haga falta y explica las líneas importantes. Prioriza seguridad, mantenibilidad y simplicidad. Compara alternativas y crea ejercicios progresivos.": "Act as a programming teacher and reviewer. Explain what code does and why. For errors, identify the root cause. Provide complete code when needed and explain important lines. Prioritize security, maintainability, and simplicity. Compare alternatives and create progressive exercises.",
"Profesor multilingüe para vocabulario, gramática, conversación y corrección.": "Multilingual teacher for vocabulary, grammar, conversation, and correction.",
"Actúa como profesor de idiomas. Detecta el idioma objetivo. Adapta el nivel, combina explicación en español con práctica en el idioma objetivo, corrige gramática, vocabulario y naturalidad, usa mini diálogos y permite inmersión cuando se pida.": "Act as a language teacher. Detect the target language. Adapt the level, explain in English unless another language is requested, correct grammar, vocabulary, and naturalness, use mini-dialogues, and allow immersion when requested.",
"Descompone lo difícil en partes pequeñas y ordenadas.": "Breaks difficult material into small, ordered parts.",
"Enseña paso a paso. No saltes operaciones ni conceptos intermedios. Usa ejemplos sencillos antes de aumentar la dificultad y resume la idea clave al final.": "Teach step by step. Do not skip operations or intermediate concepts. Use simple examples before increasing difficulty and summarize the key idea at the end.",
"Te guía con preguntas para que descubras la respuesta.": "Guides you with questions so you can discover the answer.",
"Usa el método socrático. Haz preguntas útiles antes de entregar una solución completa; si el estudiante está bloqueado, da pistas graduales.": "Use the Socratic method. Ask useful questions before giving a complete solution; if the student is stuck, provide gradual hints.",
"Busca errores, exige precisión y comprueba dominio real.": "Finds errors, demands precision, and checks real mastery.",
"Actúa como examinador exigente pero respetuoso. Señala imprecisiones, pide definiciones exactas, formula preguntas de comprobación y explica por qué una respuesta está bien o mal.": "Act as a demanding but respectful examiner. Point out inaccuracies, request exact definitions, ask verification questions, and explain why an answer is correct or incorrect.",
"Respuestas breves, ideas clave y repasos rápidos.": "Brief answers, key ideas, and fast review.",
"Prioriza velocidad y retención. Da respuestas concisas, usa palabras clave, mini-resúmenes y reglas fáciles de recordar.": "Prioritize speed and retention. Give concise answers, use keywords, mini-summaries, and easy-to-remember rules.",
"Enseña principalmente mediante ejemplos y analogías.": "Teaches mainly through examples and analogies.",
"Explica cada concepto con ejemplos concretos y analogías cotidianas. Conecta después el ejemplo con la definición formal.": "Explain each concept with concrete examples and everyday analogies. Then connect the example to the formal definition.",
}
for old, new in translations.items():
    s = s.replace(old, new)

old = """        tutor.copyWith(
          modelSource: 'global',
          recommendedModels:"""
if old in s:
    new = """        tutor.copyWith(
          name: builtIn?.name ?? tutor.name,
          description: builtIn?.description ?? tutor.description,
          instructions: builtIn?.instructions ?? tutor.instructions,
          modelSource: 'global',
          recommendedModels:"""
    s = s.replace(old, new, 1)
# Strong output-language rule for tutor requests.
s = s.replace('Sigue las instrucciones del tutor. Usa las guías asignadas como fuente principal', 'Answer in English unless the user explicitly asks for another language. Follow the tutor instructions. Use assigned guides as the primary source')
p.write_text(s)

# -----------------------------------------------------------------------------
# Agents
# -----------------------------------------------------------------------------
replace_many('lib/agent_page.dart', [
    ("?? 'Agente'", "?? 'Agent'"),
    ("'Crea un agente, asígnale un prompt, una IA y sus bases de conocimiento.'", "'Create an agent, assign it a prompt, an AI, and its knowledge bases.'"),
    ("'Se detectará al usar un GGUF'", "'It will be detected when a GGUF is used'"),
    ("'GGUF privado'", "'Private GGUF'"),
    ("'GGUF compartido'", "'Shared GGUF'"),
    ("'Ollama / servidor local'", "'Ollama / local server'"),
    ("'Configuración general'", "'General settings'"),
    ("'Crear agente'", "'Create agent'"),
    ("'Editar agente'", "'Edit agent'"),
    ("'Nombre del agente'", "'Agent name'"),
    ("'Ej. Analista de gastos'", "'E.g. Expense Analyst'"),
    ("'Prompt del agente'", "'Agent prompt'"),
    ("'Define qué debe hacer, cómo responder y qué reglas seguir…'", "'Define what it should do, how it should respond, and what rules it should follow…'"),
    ("'IA / modelo del agente'", "'Agent AI / model'"),
    ("'GGUF privado de Memora'", "'Memora private GGUF'"),
    ("'Gemini configurado'", "'Configured Gemini'"),
    ("'OpenAI / compatible configurado'", "'Configured OpenAI / compatible'"),
    ("'Ollama / servidor local configurado'", "'Configured Ollama / local server'"),
    ("'Cancelar'", "'Cancel'"),
    ("'Guardar'", "'Save'"),
    ("'Agente ${created.name} creado. Asígnale sus bases de conocimiento.'", "'Agent ${created.name} created. Assign its knowledge bases.'"),
    ("'Bases de conocimiento del agente'", "'Agent knowledge bases'"),
    ("'Puedes asignar PDF, Excel u otras guías. Memora buscará primero los fragmentos más relacionados con cada solicitud.'", "'You can assign PDFs, Excel files, or other guides. Memora will first retrieve the fragments most relevant to each request.'"),
    ("'Guardar ${working.length} base(s)'", "'Save ${working.length} knowledge base(s)'"),
    ("'Eliminar agente'", "'Delete agent'"),
    ("'¿Eliminar a ${current.name}?'", "'Delete ${current.name}?'"),
    ("'Eliminar'", "'Delete'"),
    ("'Crea un agente para empezar.'", "'Create an agent to get started.'"),
    ("'Agente activo: ${activeAgent!.name}'", "'Active agent: ${activeAgent!.name}'"),
    ("'Preparando respuesta…'", "'Preparing response…'"),
    ("'El agente no pudo responder: ${AiService.userFacingError(e)}'", "'The agent could not respond: ${AiService.userFacingError(e)}'"),
    ("'Agentes'", "'Agents'"),
    ("'Crea tu primer agente'", "'Create your first agent'"),
])
p = Path('lib/agent_page.dart')
s = p.read_text()
s = s.replace("'''Eres un agente personalizado de Memora llamado ${agent.name}.", "'''You are a custom Memora agent named ${agent.name}. Always answer in English unless the user explicitly asks for another language.")
s = s.replace('PROMPT DEL AGENTE:', 'AGENT PROMPT:')
s = s.replace('FRAGMENTOS RELEVANTES DE SUS BASES:', 'RELEVANT KNOWLEDGE-BASE FRAGMENTS:')
s = s.replace('SOLICITUD DEL USUARIO:', 'USER REQUEST:')
s = s.replace('Sigue el prompt del agente. Usa los fragmentos asignados cuando sean relevantes. Si un dato solicitado debería estar en las bases pero no aparece, indícalo en vez de inventarlo. En modo rápido prioriza una respuesta breve; en modo profundo puedes desarrollar más el análisis.', 'Follow the agent prompt. Use assigned fragments when relevant. If requested information should be in the knowledge bases but is missing, say so instead of inventing it. In fast mode prioritize a brief answer; in deep mode you may provide a more developed analysis.')
p.write_text(s)

# -----------------------------------------------------------------------------
# TutorContext fallback labels/names used by exams and plans.
# -----------------------------------------------------------------------------
replace_many('lib/tutor_context_service.dart', [
    ("name: 'Tutor de Finanzas'", "name: 'Finance Tutor'"),
    ("name: 'Tutor de Programación'", "name: 'Programming Tutor'"),
    ("name: 'Tutor de Idiomas'", "name: 'Language Tutor'"),
    ("name: 'Profesor Paso a Paso'", "name: 'Step-by-Step Teacher'"),
    ("name: 'Tutor Socrático'", "name: 'Socratic Tutor'"),
    ("name: 'Examinador Estricto'", "name: 'Strict Examiner'"),
    ("name: 'Repaso Express'", "name: 'Quick Review'"),
    ("name: 'Tutor de Ejemplos'", "name: 'Examples Tutor'"),
    ("description: 'Tutor general de Memora.'", "description: 'Memora general tutor.'"),
    ("'GGUF privado'", "'Private GGUF'"),
    ("'GGUF compartido'", "'Shared GGUF'"),
    ("'Ollama / servidor local'", "'Ollama / local server'"),
    ("'GGUF del dispositivo'", "'On-device GGUF'"),
    ("'Configuración general de IA'", "'General AI settings'"),
])

print('Memora v1.18 English system patch applied successfully')
