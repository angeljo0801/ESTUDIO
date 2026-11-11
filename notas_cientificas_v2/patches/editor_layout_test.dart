import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_quill/flutter_quill.dart' as quill;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:notas_cientificas/main.dart';
import 'package:notas_cientificas/storage.dart';

void main() {
  testWidgets('El editor no queda oculto al escribir muchas lineas', (tester) async {
    tester.view.physicalSize = const Size(1080, 1920);
    tester.view.devicePixelRatio = 3;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
      tester.view.resetViewInsets();
    });
    SharedPreferences.setMockInitialValues({});
    final store = await LocalStore.open();
    await tester.pumpWidget(NotesCalculatorApp(store: store));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Nueva nota'));
    await tester.pumpAndSettle();
    final body = find.byKey(const Key('note-body-editor'));
    final toolbar = find.byKey(const Key('note-fixed-toolbar'));
    expect(body, findsOneWidget);
    expect(toolbar, findsOneWidget);
    expect(tester.getRect(body).bottom, lessThanOrEqualTo(tester.getRect(toolbar).top + 1));
    expect(tester.getSize(body).height, greaterThan(100));
    expect(tester.takeException(), isNull);

    final quillEditor = tester.widget<quill.QuillEditor>(body);
    final text = List.generate(90, (i) => 'Linea ${i + 1}: texto de prueba.').join('\n');
    quillEditor.controller.replaceText(0, 0, text,
      TextSelection.collapsed(offset: text.length));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);

    tester.view.viewInsets = const FakeViewPadding(bottom: 900);
    await tester.pumpAndSettle();
    expect(tester.getRect(body).bottom, lessThanOrEqualTo(tester.getRect(toolbar).top + 1));
    expect(tester.getSize(body).height, greaterThan(40));
    expect(tester.takeException(), isNull);
  });
}
