import 'package:flutter/material.dart';
import 'package:pdfrx/pdfrx.dart';
import 'guide_store.dart';
import 'app_shell.dart';
import 'completion_notification_service.dart';
import 'daily_exam_headless.dart' as daily_headless;

@pragma('vm:entry-point')
Future<void> dailyExamHeadlessMain() async {
  WidgetsFlutterBinding.ensureInitialized();
  await daily_headless.dailyExamHeadlessMain();
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  pdfrxFlutterInitialize();
  final store = GuideStore();
  await store.load();
  runApp(MemoraApp(store: store));
  await CompletionNotificationService.initialize();
}

class MemoraApp extends StatelessWidget {
  const MemoraApp({super.key, required this.store});
  final GuideStore store;
  @override
  Widget build(BuildContext context) {
    final colorScheme = ColorScheme.fromSeed(seedColor: const Color(0xFF6C63FF), brightness: Brightness.dark);
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Memora',
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: colorScheme,
        scaffoldBackgroundColor: const Color(0xFF0E0F14),
        cardTheme: CardThemeData(elevation: 0,color: const Color(0xFF171922),shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22))),
        inputDecorationTheme: InputDecorationTheme(filled:true,fillColor:const Color(0xFF171922),border:OutlineInputBorder(borderRadius:BorderRadius.circular(18),borderSide:BorderSide.none)),
      ),
      home: AppShell(store: store),
    );
  }
}
