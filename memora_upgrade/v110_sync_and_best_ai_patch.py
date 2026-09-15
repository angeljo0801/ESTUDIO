from pathlib import Path

# -----------------------------------------------------------------------------
# Daily exam: refresh tutor/guide assignments whenever the IndexedStack updates.
# -----------------------------------------------------------------------------
p = Path('lib/daily_exam_page.dart')
s = p.read_text()

anchor = """  @override
  void initState() {
    super.initState();
    _load();
  }
"""
insert = """
  @override
  void didUpdateWidget(covariant DailyExamPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    _refreshTutors();
  }

  Future<void> _refreshTutors() async {
    final loaded = await TutorContextService.loadProfiles();
    if (!mounted) return;
    setState(() {
      tutors = loaded;
      if (loaded.isEmpty) {
        customTutorId = null;
      } else if (customTutorId == null ||
          !loaded.any((tutor) => tutor.id == customTutorId)) {
        customTutorId = loaded.first.id;
      }
    });
  }
"""
if anchor not in s:
    raise RuntimeError('DailyExam initState anchor not found')
s = s.replace(anchor, anchor + insert, 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# Study plan: refresh tutors too, and make "Best AI" really fall back across
# configured providers instead of getting stuck on an unreachable Ollama URL.
# -----------------------------------------------------------------------------
p = Path('lib/study_plan_page.dart')
s = p.read_text()

anchor = """  @override
  void initState() {
    super.initState();
    _load();
  }
"""
insert = """
  @override
  void didUpdateWidget(covariant StudyPlanPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    _refreshTutors();
  }

  Future<void> _refreshTutors() async {
    final loaded = await TutorContextService.loadProfiles();
    if (!mounted) return;
    setState(() {
      tutors = loaded;
      if (contentOwner != 'library' &&
          !loaded.any((tutor) => tutor.id == contentOwner)) {
        contentOwner = 'library';
      }
      if (creator != 'best' &&
          !loaded.any((tutor) => tutor.id == creator)) {
        creator = 'best';
      }
    });
  }
"""
if anchor not in s:
    raise RuntimeError('StudyPlan initState anchor not found')
s = s.replace(anchor, anchor + insert, 1)

old = """    final creatorTutor = creator == 'best' ? null : _tutorById(creator);
    final provider = creatorTutor == null
        ? await TutorContextService.bestAvailableProvider()
        : creatorTutor.modelSource;
    final sourceLabel = TutorContextService.sourceLabel(provider ?? 'global');
    final content = TutorContextService.contentForGuides(guides, maxChars: 18000);
"""
new = """    final creatorTutor = creator == 'best' ? null : _tutorById(creator);
    final providerCandidates = creatorTutor == null
        ? await TutorContextService.bestAvailableProviders()
        : <String>[creatorTutor.modelSource];
    if (providerCandidates.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'No encontré una IA disponible. Configura Gemini/OpenAI, importa un GGUF o inicia tu servidor Ollama.',
          ),
        ),
      );
      return;
    }
    final content = TutorContextService.contentForGuides(guides, maxChars: 18000);
"""
if old not in s:
    raise RuntimeError('StudyPlan provider selection anchor not found')
s = s.replace(old, new, 1)

old = """      usedSource = sourceLabel;
"""
new = """      usedSource = creatorTutor == null
          ? 'Buscando una IA disponible…'
          : TutorContextService.sourceLabel(providerCandidates.first);
"""
if old not in s:
    raise RuntimeError('StudyPlan usedSource anchor not found')
s = s.replace(old, new, 1)

old = """      final result = await AiService.askTaskConfigured(
        prompt: prompt,
        providerOverride: provider,
        responseMode: 'normal',
      );
      if (!mounted) return;
      setState(() => plan = result);
"""
new = """      String? result;
      String? successfulProvider;
      Object? lastError;

      for (final candidate in providerCandidates) {
        try {
          result = await AiService.askTaskConfigured(
            prompt: prompt,
            providerOverride: candidate,
            responseMode: 'normal',
          );
          successfulProvider = candidate;
          break;
        } catch (e) {
          final message = AiService.userFacingError(e).toLowerCase();
          if (message.contains('cancelada') || message.contains('cancelled')) {
            rethrow;
          }
          lastError = e;
        }
      }

      final completedPlan = result;
      final completedProvider = successfulProvider;
      if (completedPlan == null || completedProvider == null) {
        throw lastError ?? Exception('Ninguna IA disponible pudo crear el plan.');
      }
      if (!mounted) return;
      setState(() {
        plan = completedPlan;
        usedSource = TutorContextService.sourceLabel(completedProvider);
      });
"""
if old not in s:
    raise RuntimeError('StudyPlan AI call anchor not found')
s = s.replace(old, new, 1)

old = """                                ? 'Memora prioriza una IA online ya configurada cuando esté disponible; si no, usa tu configuración general.'
"""
new = """                                ? 'Memora prueba las IA configuradas y cambia automáticamente a otra si una falla. Ollama solo se usa si el servidor está accesible.'
"""
if old not in s:
    raise RuntimeError('StudyPlan best AI help text anchor not found')
s = s.replace(old, new, 1)

p.write_text(s)

print('Memora v1.10 tutor sync and best-AI fallback patch applied successfully')
