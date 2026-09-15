import 'package:flutter/material.dart';

import 'agent_page.dart';
import 'daily_exam_page.dart';
import 'guide_creator_page.dart';
import 'guide_store.dart';
import 'home_page.dart';
import 'study_plan_page.dart';
import 'tutor_page.dart';

class AppShell extends StatefulWidget {
  const AppShell({super.key, required this.store});
  final GuideStore store;

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int i = 0;

  @override
  Widget build(BuildContext context) => Scaffold(
        body: IndexedStack(
          index: i,
          children: [
            HomePage(store: widget.store),
            TutorPage(store: widget.store),
            AgentPage(store: widget.store),
            GuideCreatorPage(store: widget.store),
            DailyExamPage(store: widget.store),
            StudyPlanPage(store: widget.store),
          ],
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: i,
          onDestinationSelected: (v) => setState(() => i = v),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.library_books), label: 'Biblioteca'),
            NavigationDestination(icon: Icon(Icons.psychology), label: 'Tutor'),
            NavigationDestination(icon: Icon(Icons.smart_toy_outlined), label: 'Agentes'),
            NavigationDestination(icon: Icon(Icons.auto_awesome), label: 'Crear'),
            NavigationDestination(icon: Icon(Icons.fact_check), label: 'Examen'),
            NavigationDestination(icon: Icon(Icons.calendar_month), label: 'Plan'),
          ],
        ),
      );
}
