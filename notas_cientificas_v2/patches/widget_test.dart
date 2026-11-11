import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:notas_cientificas/main.dart';
import 'package:notas_cientificas/storage.dart';

void main() {
  Future<void> openApp(WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    final store = await LocalStore.open();
    await tester.pumpWidget(NotesCalculatorApp(store: store));
    await tester.pumpAndSettle();
  }

  testWidgets('Cambiar entre notas y calculadora no provoca errores', (tester) async {
    await openApp(tester);
    expect(find.text('Mis notas'), findsOneWidget);
    await tester.tap(find.byIcon(Icons.calculate_outlined).first);
    await tester.pumpAndSettle();
    expect(find.text('Calculadora'), findsWidgets);
    await tester.tap(find.text('Notas').last);
    await tester.pumpAndSettle();
    expect(find.text('Mis notas'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Crear nota, guardarla y cerrar el editor', (tester) async {
    await openApp(tester);
    await tester.tap(find.text('Nueva nota'));
    await tester.pumpAndSettle();
    expect(find.byTooltip('Escritura con S Pen'), findsOneWidget);
    await tester.enterText(find.byType(TextField).first, 'Prueba de guardado');
    await tester.pump(const Duration(milliseconds: 850));
    await tester.tap(find.byIcon(Icons.arrow_back).first);
    await tester.pumpAndSettle();
    expect(find.text('Prueba de guardado'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
