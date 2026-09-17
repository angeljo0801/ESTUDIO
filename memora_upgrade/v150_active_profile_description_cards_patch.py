from pathlib import Path

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

# Agents historically use their prompt as the text that describes their job.
# Reuse it in a dedicated description card rather than adding a second field.
anchor = """                        onChanged: (value) async {
                          if (value == null) return;
                          setState(() => activeId = value);
                          await _save();
                        },
                      ),
                      const SizedBox(height: 10),
"""
card = """                        onChanged: (value) async {
                          if (value == null) return;
                          setState(() => activeId = value);
                          await _save();
                        },
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
    if anchor not in s:
        raise RuntimeError('active agent selector anchor not found')
    s = s.replace(anchor, card, 1)
p.write_text(s)

print('Active tutor and agent description cards added')
