from pathlib import Path

p = Path('lib/daily_exam_page.dart')
s = p.read_text()

old = r'''            const SizedBox(height: 12),
            if (!reveal)
              FilledButton(
                onPressed: () => setState(() => reveal = true),
                child: const Text('Show answer'),
              )
            else
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => _answer(false),
                      icon: const Icon(Icons.close_rounded),
                      label: const Text('I did not know it'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: () => _answer(true),
                      icon: const Icon(Icons.check_rounded),
                      label: const Text('I knew it'),
                    ),
                  ),
                ],
              ),
'''

new = r'''            SafeArea(
              top: false,
              minimum: const EdgeInsets.only(top: 14, bottom: 10),
              child: !reveal
                  ? FilledButton(
                      onPressed: () => setState(() => reveal = true),
                      style: FilledButton.styleFrom(
                        minimumSize: const Size.fromHeight(60),
                        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
                        textStyle: const TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w700,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(18),
                        ),
                      ),
                      child: const Text('Show answer'),
                    )
                  : Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: () => _answer(false),
                            icon: const Icon(Icons.close_rounded, size: 24),
                            label: const Text(
                              'I did not know it',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            style: OutlinedButton.styleFrom(
                              minimumSize: const Size.fromHeight(64),
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
                              textStyle: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w700,
                              ),
                              side: BorderSide(
                                width: 1.8,
                                color: Theme.of(context).colorScheme.outline,
                              ),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(20),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: FilledButton.icon(
                            onPressed: () => _answer(true),
                            icon: const Icon(Icons.check_rounded, size: 24),
                            label: const Text(
                              'I knew it',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            style: FilledButton.styleFrom(
                              minimumSize: const Size.fromHeight(64),
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
                              textStyle: const TextStyle(
                                fontSize: 17,
                                fontWeight: FontWeight.w800,
                              ),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(20),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
            ),
'''

if old not in s:
    raise RuntimeError('v1.33 exam bottom button block not found')

s = s.replace(old, new, 1)
p.write_text(s)
print('Memora v1.33 exam bottom buttons patch applied successfully')
