from pathlib import Path

p = Path('lib/home_page.dart')
s = p.read_text()

old = '''    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 22),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
'''

new = '''    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      showDragHandle: true,
      builder: (context) => FractionallySizedBox(
        heightFactor: .78,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
          child: ListView(
            padding: EdgeInsets.only(
              bottom: MediaQuery.of(context).padding.bottom + 20,
            ),
            children: [
'''

if old not in s:
    raise RuntimeError('Add-menu bottom sheet pattern not found')

p.write_text(s.replace(old, new, 1))
print('Memora v1.5.1 library sheet layout patch applied successfully')
