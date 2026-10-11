# Plantilla universal de exámenes: Memora ↔ FocoQuiz (formato v1)

## Cómo usarla con cualquier IA externa
1. Entrega este archivo a ChatGPT, Gemini, Claude, Copilot u otra IA externa.
2. Adjunta tu guía de estudio (PDF, fotos, texto o apuntes) a esa IA.
3. Pídele que genere un examen y guarde el resultado como archivo .json en UTF-8.
4. Importa el JSON desde Memora o FocoQuiz. No necesitas contratar la IA de Memora.

## PROMPT PARA LA IA (COPIAR DESDE AQUÍ)

Eres un creador experto de exámenes basados en documentos. Usa EXCLUSIVAMENTE la guía de estudio adjunta para producir un examen preciso, pedagógico y sin suposiciones.

Devuelve un único objeto JSON válido, codificado en UTF-8, con este formato exacto:
- "format": "focoquiz.quiz"
- "version": 1
- "title": nombre útil del examen
- "source": nombre de la guía
- "language": "es" (salvo si solicito otro idioma)
- "questions": entre 10 y 30 preguntas o la cantidad que solicite. Si el material no permite tantas preguntas válidas, genera menos.

Cada pregunta debe tener:
- "id": identificador único "q1", "q2", etc.
- "type": "multiple_choice" o "short_answer"
- "question": enunciado completo.
- "answer": texto de la respuesta correcta.
- "explanation": breve explicación que se sustente en la guía.
- "topic": tema estudiado.
- "difficulty": "easy", "medium" o "hard".

Para "multiple_choice": incluye "options" con EXACTAMENTE CUATRO textos únicos y una única respuesta correcta. "answer" tiene que ser idéntico al texto de UNA de esas cuatro opciones. No uses simplemente A, B, C o D en "answer".
Para "short_answer": incluye "accepted_answers" (lista que puede ser vacía) con variantes equivalentes verificables.
Varía temas y niveles, añade preguntas de razonamiento y evita duplicados, ambigüedades o hechos no incluidos en la guía.
NO inventes números de página ni datos ausentes. 
NO incluyas comentarios, explicaciones fuera del JSON ni envolturas Markdown.

Ejemplo de ESTRUCTURA (reemplaza preguntas y respuestas por contenido de MI guía):

{
  "format": "focoquiz.quiz",
  "version": 1,
  "title": "Ejemplo: fundamentos de electrónica",
  "source": "Mi guía de estudio",
  "language": "es",
  "questions": [
    {
      "id": "q1",
      "type": "multiple_choice",
      "question": "¿En qué unidad se mide la resistencia eléctrica?",
      "options": ["Ohmios", "Voltios", "Amperios", "Vatios"],
      "answer": "Ohmios",
      "explanation": "La unidad de resistencia eléctrica es el ohmio (Ω).",
      "topic": "Circuitos",
      "difficulty": "easy"
    },
    {
      "id": "q2",
      "type": "short_answer",
      "question": "¿Qué ley relaciona tensión, corriente y resistencia?",
      "answer": "Ley de Ohm",
      "accepted_answers": ["Ohm"],
      "explanation": "Se expresa como V = I × R.",
      "topic": "Circuitos",
      "difficulty": "easy"
    }
  ]
}

## FIN DEL PROMPT

Guarda la respuesta de la IA como "examen.json" (UTF-8). El archivo debe contener el JSON como texto, no una imagen o PDF.
