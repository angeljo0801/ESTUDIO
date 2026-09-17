from pathlib import Path
import os

# Show the selected tutor/agent description as its own compact card directly
# below the active-profile selector. Existing data is reused; no duplicate
# description field is introduced.

p = Path('lib/tutor_page.dart')
s = p.read_text()

anchor = """                    onChanged: _selectTutor,
                  ),
                  const SizedBox(height: 10),
"""
card = """                    onChanged: _selectTutor,
                  ),
                  const SizedBox(height: 10),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(16, 12, 16, 14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.description_outlined, size: 20),
                              const SizedBox(width: 8),
                              Text(
                                'Description',
                                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                      fontWeight: FontWeight.w700,
                                    ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 7),
                          Text(
                            activeTutor.description.trim().isEmpty
                                ? 'No description has been added for this tutor yet.'
                                : activeTutor.description.trim(),
                            maxLines: 3,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
"""
if "No description has been added for this tutor yet." not in s:
    if anchor not in s:
        raise RuntimeError('active tutor selector anchor not found')
    s = s.replace(anchor, card, 1)
p.write_text(s)

p = Path('lib/agent_page.dart')
s = p.read_text()

agent_card = """                      Card(
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(16, 12, 16, 14),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  const Icon(Icons.description_outlined, size: 20),
                                  const SizedBox(width: 8),
                                  Text(
                                    'Description',
                                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                          fontWeight: FontWeight.w700,
                                        ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 7),
                              Text(
                                activeAgent!.prompt.trim().isEmpty
                                    ? 'No description has been added for this agent yet.'
                                    : activeAgent!.prompt.trim(),
                                maxLines: 3,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(context).textTheme.bodyMedium,
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 10),
"""

if "No description has been added for this agent yet." not in s:
    value_pos = s.find('initialValue: activeAgent!.id')
    if value_pos < 0:
        value_pos = s.find('value: activeAgent!.id')
    if value_pos < 0:
        raise RuntimeError('active agent dropdown not found')
    next_section = s.find('const SizedBox(height: 10),', value_pos)
    if next_section < 0:
        raise RuntimeError('active agent dropdown trailing spacing not found')
    insert_pos = next_section + len('const SizedBox(height: 10),')
    s = s[:insert_pos] + '\n' + agent_card + s[insert_pos:]

p.write_text(s)
print('Active tutor and agent description cards added')

_v151=Path(os.environ['GITHUB_WORKSPACE'])/'memora_upgrade'/'v151_persistent_agent_description_patch.py'
exec(compile(_v151.read_text(),str(_v151),'exec'))
