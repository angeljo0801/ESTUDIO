from pathlib import Path

# v181: keep the ENTIRE mandatory card-cleaning job inside Memora's Android
# foreground service, not just each individual model request.
#
# This means:
# - minimizing Memora does not stop the card-cleaning loop;
# - screen-off is protected by the native partial wake lock;
# - opening Review does not stop later AI batches;
# - the persistent Android notification reports reviewed-card progress;
# - nested AiService calls reuse the same foreground-service lifetime.

p = Path('lib/guide_detail_page.dart')
s = p.read_text()

if "import 'background_task_service.dart';" not in s:
    anchor = "import 'ai_card_review_service.dart';\n"
    if anchor not in s:
        raise SystemExit('v181 GuideDetail background import anchor missing')
    s = s.replace(
        anchor,
        anchor + "import 'background_task_service.dart';\n",
        1,
    )

old = """    setState(() {
      _generatingCards = true;
      _cardProgress = 0;
    });

    try {
"""
new = """    setState(() {
      _generatingCards = true;
      _cardProgress = 0;
    });

    await BackgroundTaskService.begin(
      title: 'Memora is cleaning study cards',
      body: '0/$requestedCount reviewed cards ready',
    );
    await BackgroundTaskService.update(
      title: 'Memora is cleaning study cards',
      body: '0/$requestedCount reviewed cards ready',
      progress: 0,
      max: requestedCount,
    );

    try {
"""
if old not in s:
    raise SystemExit('v181 foreground start anchor missing')
s = s.replace(old, new, 1)

old = """        if (mounted) {
          setState(() => _cardProgress = produced);
        }

        await Future<void>.delayed(const Duration(milliseconds: 80));
"""
new = """        if (mounted) {
          setState(() => _cardProgress = produced);
        }

        await BackgroundTaskService.update(
          title: 'Memora is cleaning study cards',
          body: '$produced/$requestedCount reviewed cards ready • '
              '$reviewedCount checked • $fixedCount fixed • $rejectedCount rejected',
          progress: produced,
          max: requestedCount,
        );

        await Future<void>.delayed(const Duration(milliseconds: 80));
"""
if old not in s:
    raise SystemExit('v181 foreground progress anchor missing')
s = s.replace(old, new, 1)

old = """    } finally {
      if (mounted) setState(() => _generatingCards = false);
    }
  }
"""
new = """    } finally {
      await BackgroundTaskService.finish(immediately: true);
      if (mounted) setState(() => _generatingCards = false);
    }
  }
"""
if old not in s:
    raise SystemExit('v181 foreground finish anchor missing')
s = s.replace(old, new, 1)

p.write_text(s)

print('v181 applied: mandatory card review now owns one continuous Android foreground-service job')
