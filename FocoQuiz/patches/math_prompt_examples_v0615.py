#!/usr/bin/env python3
"""FocoQuiz v0.6.15: seed examples and prompt for varied numeric quiz questions."""
from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]

# Upgrade bundled fallback arithmetic demos to parametric question templates.
store=root/"app/src/main/java/com/focoquiz/app/LockStore.kt"
s=store.read_text(encoding="utf-8")
replacements=[
('''StudyQuestion("¿Cuánto es 7 × 8?", "56", questionId = "demo1", difficulty = QuizDifficulty.EASY)''',
 '''StudyQuestion("¿Cuánto es {a} × {b}?", "56", questionId = "demo1",
            difficulty = QuizDifficulty.EASY,
            numericVariation = NumericVariation(listOf(
                NumericVariable("a", 3.0, 16.0, 1.0),
                NumericVariable("b", 4.0, 14.0, 1.0)), "{a}*{b}", 0))'''),
('''StudyQuestion("¿Cuánto es 15 + 27?", "42", questionId = "demo2", difficulty = QuizDifficulty.EASY)''',
 '''StudyQuestion("¿Cuánto es {a} + {b}?", "42", questionId = "demo2",
            difficulty = QuizDifficulty.EASY,
            numericVariation = NumericVariation(listOf(
                NumericVariable("a", 7.0, 55.0, 1.0),
                NumericVariable("b", 8.0, 60.0, 1.0)), "{a}+{b}", 0))'''),
('''StudyQuestion("¿Cuánto es 9 × 6?", "54", questionId = "demo3", difficulty = QuizDifficulty.EASY)''',
 '''StudyQuestion("¿Cuánto es {a} × {b}?", "54", questionId = "demo3",
            difficulty = QuizDifficulty.EASY,
            numericVariation = NumericVariation(listOf(
                NumericVariable("a", 2.0, 12.0, 1.0),
                NumericVariable("b", 3.0, 19.0, 1.0)), "{a}*{b}", 0))'''),
('''StudyQuestion("¿Cuánto es 144 ÷ 12?", "12", questionId = "demo5", difficulty = QuizDifficulty.EASY)''',
 '''StudyQuestion("Si {a} objetos se reparten en {b} grupos iguales, ¿cuántos van por grupo?", "12",
            questionId = "demo5", difficulty = QuizDifficulty.EASY,
            numericVariation = NumericVariation(listOf(
                NumericVariable("a", 60.0, 144.0, 12.0),
                NumericVariable("b", 3.0, 12.0, 1.0)), "{a}/{b}", 2))'''),
('''StudyQuestion("¿Cuánto es 13 × 4?", "52", questionId = "demo9", difficulty = QuizDifficulty.EASY)''',
 '''StudyQuestion("¿Cuánto es {a} × {b}?", "52", questionId = "demo9",
            difficulty = QuizDifficulty.EASY,
            numericVariation = NumericVariation(listOf(
                NumericVariable("a", 11.0, 25.0, 1.0),
                NumericVariable("b", 2.0, 12.0, 1.0)), "{a}*{b}", 0))'''),
('''StudyQuestion("¿Cuál es el voltaje si 2 A pasan por 5 Ω?", "10", questionId = "demo10")''',
 '''StudyQuestion("¿Cuál es el voltaje si {I} A pasan por {R} Ω?", "10",
            questionId = "demo10",
            numericVariation = NumericVariation(listOf(
                NumericVariable("I", 1.0, 12.0, 1.0),
                NumericVariable("R", 2.0, 30.0, 1.0)), "{I}*{R}", 0, "V"))''')
]
for a,b in replacements:
    if a not in s: raise RuntimeError("Built-in arithmetic example anchor missing: "+a[:90])
    s=s.replace(a,b,1)
store.write_text(s,encoding="utf-8")

# The same source prompt is shared with a downstream AI to make every math
# item a generator, not just a fixed answer.
instructions="""- IMPORTANTE PARA EVITAR MEMORIZACIÓN: En CADA pregunta que tenga cálculos numéricos, añade un objeto opcional "numeric_variation". Las preguntas teóricas NO necesitan este objeto. FocoQuiz vuelve a sortear los datos de numeric_variation para cada nuevo intento y recalcula la respuesta y las cuatro opciones.
- Conserva también "question" y "answer" con valores de ejemplo coherentes para compatibilidad. El texto de "question" DEBE contener variables como {V}, {R} en vez de números fijos; en el objeto "numeric_variation", "answer_expression" DEBE usar esos mismos nombres entre llaves, y dar el resultado correcto según la fórmula de la guía.
- Ejemplo válido de un problema basado en la ley de Ohm:
  "question": "Si una resistencia de {R} Ω está conectada a {V} V, ¿qué corriente circula? (A)",
  "numeric_variation": {
    "variables": [{"name":"R","min":2,"max":12,"step":1},{"name":"V","min":6,"max":24,"step":2}],
    "answer_expression":"{V}/{R}", "decimals":2, "unit":"A",
    "wrong_expressions":["{V}*{R}","{R}/{V}","{V}+{R}"]
  }
- Cada variable requiere "name", "min", "max", "step". "min" y "max" son números; "step" es la diferencia entre posibles valores. Debe haber al menos 2 valores permitidos. Incluye entre 1 y 5 variables por pregunta. Elige rangos realistas basados EXCLUSIVAMENTE en los principios y unidades de la guía, y evita dividir entre cero o raíces/logaritmos fuera de dominio.
- "answer_expression" admite +, -, *, /, ^, √, %, paréntesis y funciones de la calculadora científica como sqrt(...), sin(...), cos(...), tan(...), log(...), ln(...). Escribe operaciones explícitas, por ejemplo "{V}/{R}" y NO "{V}{R}" ni ecuaciones con "=". No inventes fórmulas fuera del documento.
- "decimals" es un entero de 0 a 6 para redondear la respuesta; "unit" indica la unidad (puede ser ""). Para selección múltiple puedes dar de 0 a 3 "wrong_expressions" que representen errores comunes de cálculo: FocoQuiz vuelve a calcular las opciones, sin repetir la correcta. Elige fórmulas incorrectas que produzcan resultados distintos en rangos normales.
- Cada nuevo intento debe tener una respuesta diferente cuando cambian los datos: evita plantear fórmulas que cancelen todas las variables. Los valores numéricos se generan LOCALMENTE, sin conexión ni IA externa una vez importado el examen.
- NO basta con cambiar el orden de las preguntas: el objetivo es comprobar el MÉTODO y no memorizar un resultado. Nunca incluyas la respuesta ya sustituida dentro del texto de la pregunta o de la explicación previa.
"""
for p in (root/"app/src/main/assets/plantilla_prompt_ia.md",
          root/"quiz-format/PLANTILLA_Y_PROMPT_PARA_CUALQUIER_IA.md"):
    if not p.exists():continue
    text=p.read_text(encoding="utf-8")
    marker="- NO agregues hechos que no estén en la guía."
    if marker in text:
        updated=text.replace(marker,instructions+marker,1)
    elif "## PROMPT PARA LA IA" in text:
        start=text.index("## PROMPT PARA LA IA")
        next_line=text.find("\n",start)
        updated=text[:next_line+1]+"\n"+instructions+"\n"+text[next_line+1:]
    else:
        updated=instructions+"\n"+text
    p.write_text(updated,encoding="utf-8")

# Bundled JSON actually demonstrates how a teacher/AI supplies the formula data.
for path in (root/"app/src/main/assets/ejemplo_examen.json",
             root/"quiz-format/EJEMPLO_EXAMEN.json"):
    if not path.exists():continue
    content=json.loads(path.read_text(encoding="utf-8"))
    # Existing theory questions remain untouched.
    content["questions"].append({
        "id":"q3",
        "type":"multiple_choice",
        "question":"Si una resistencia de {R} Ω está conectada a {V} V, ¿qué corriente circula? (A)",
        "options":["3 A","4 A","6 A","12 A"],
        "answer":"3 A",
        "explanation":"Por la ley de Ohm, I=V/R. Los valores son V={V} V y R={R} Ω.",
        "topic":"Circuitos",
        "difficulty":"medium",
        "formula_ids":["f1"],
        "numeric_variation":{
            "variables":[{"name":"R","min":2,"max":12,"step":1},
                         {"name":"V","min":6,"max":24,"step":2}],
            "answer_expression":"{V}/{R}",
            "decimals":2,
            "unit":"A",
            "wrong_expressions":["{V}*{R}","{R}/{V}","{V}+{R}"]
        }
    })
    path.write_text(json.dumps(content,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

print("v0.6.15: built-in math demos vary per attempt, AI prompt and JSON example updated.")
