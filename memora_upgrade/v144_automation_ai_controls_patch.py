from pathlib import Path
import os

# v1.44 is now a stable bridge: v1.43 already produces the complete app sources,
# and v1.45 applies the remaining user-facing improvements on top.
print('Memora v1.44 bridge applied successfully')
_v145 = Path(os.environ['GITHUB_WORKSPACE']) / 'memora_upgrade' / 'v145_remaining_improvements_patch.py'
exec(compile(_v145.read_text(), str(_v145), 'exec'))
