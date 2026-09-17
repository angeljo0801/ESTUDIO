from pathlib import Path
import subprocess

p = Path('v159_agent_orchestrator_directory_patch.py')
s = p.read_text()

replacements = [
    ("profiles = r'''", 'profiles = r"""'),
    ("\n'''\n\nagent_page = r'''", '\n"""\n\nagent_page = r"""'),
    ("\n'''\n\norchestrator = r'''", '\n"""\n\norchestrator = r"""'),
    ("\n'''\n\nPath('lib/agent_profiles.dart')", '\n"""\n\nPath(\'lib/agent_profiles.dart\')'),
]
for old, new in replacements:
    if old not in s:
        raise SystemExit('v161 source delimiter anchor missing: ' + old[:40])
    s = s.replace(old, new, 1)
p.write_text(s)

subprocess.run(['python3', 'v159_agent_orchestrator_directory_patch.py'], check=True)
subprocess.run(['python3', 'v160_agent_orchestrator_compile_fix.py'], check=True)
subprocess.run(['python3', 'v162_unified_prompt_generators_patch.py'], check=True)
subprocess.run(['python3', 'v163_orchestrator_bottom_safe_area_patch.py'], check=True)
print('v161 applied: v159 source repaired; directory generated; v160/v162/v163 fixes applied')
