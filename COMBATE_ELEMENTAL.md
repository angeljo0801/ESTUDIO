# Reglas de combate elemental (propuesta inicial implementada)
- Reserva común de estamina por combate, tanto para magia como para ataques físicos. Sin recuperación durante el encuentro. Se comprueba victoria antes de agotamiento.
- Fallo base 2%; evasión lo aumenta; precisión mejora la probabilidad crítica. Daño crítico configurable.
- Las técnicas admiten status, statusChance, statusTurns, precision, critChance, critDamage, minIntelligence. Probabilidades por técnica.
- Cada coincidencia del mismo elemento con la técnica anterior o espíritu activo aporta +8% de potencia y +8 puntos porcentuales de estado (tope 85%); reacciones cruzadas compatibles también aportan sinergia.
- Espíritu activo: resistencia +3 puntos al elemento propio, acumulable con resistencias existentes. Préstamo, manifestación con reserva propia, fusión y encantamiento inicial de arma.
- Valores provisionales; requieren pruebas de equilibrio, compilación y revisión de interfaz.
