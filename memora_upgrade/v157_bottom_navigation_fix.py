from pathlib import Path
import subprocess

p = Path('lib/app_shell.dart')
s = p.read_text()

# v157: rebuild the shell explicitly so destinations and IndexedStack pages
# always have a 1:1 mapping. Guide Creator remains accessible from Library.
# Do not leave a hidden/empty slot for Create.
imports = """import 'package:flutter/material.dart';

import 'agent_page.dart';
import 'daily_exam_page.dart';
import 'general_ai_chat_page.dart';
import 'guide_store.dart';
import 'home_page.dart';
import 'study_plan_page.dart';
import 'tutor_page.dart';

"""

body = r'''class AppShell extends StatefulWidget {
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
            DailyExamPage(store: widget.store),
            StudyPlanPage(store: widget.store),
            GeneralAiChatPage(store: widget.store),
          ],
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: i,
          onDestinationSelected: (v) => setState(() => i = v),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.library_books), label: 'Biblioteca'),
            NavigationDestination(icon: Icon(Icons.psychology), label: 'Tutor'),
            NavigationDestination(icon: Icon(Icons.smart_toy_outlined), label: 'Agentes'),
            NavigationDestination(icon: Icon(Icons.fact_check), label: 'Examen'),
            NavigationDestination(icon: Icon(Icons.calendar_month), label: 'Plan'),
            NavigationDestination(icon: Icon(Icons.chat_bubble_outline), label: 'Chat IA'),
          ],
        ),
      );
}
'''

p.write_text(imports + body)

# Guard against future index drift.
out = p.read_text()
if 'GuideCreatorPage(store: widget.store)' in out or "label: 'Crear'" in out:
    raise SystemExit('Create still present in bottom navigation')
required = [
    'HomePage(store: widget.store)',
    'TutorPage(store: widget.store)',
    'AgentPage(store: widget.store)',
    'DailyExamPage(store: widget.store)',
    'StudyPlanPage(store: widget.store)',
    'GeneralAiChatPage(store: widget.store)',
]
for item in required:
    if out.count(item) != 1:
        raise SystemExit('Navigation page invariant failed: ' + item)
if out.count('NavigationDestination(') != 6:
    raise SystemExit('Bottom navigation must contain exactly six destinations')

subprocess.run(['python3', 'v158_optional_orchestrator_recommendations_patch.py'], check=True)
subprocess.run(['python3', 'v159_agent_orchestrator_directory_patch.py'], check=True)
print('v157 applied: navigation fixed; v158 recommendations and v159 agent/orchestrator directory chained')
