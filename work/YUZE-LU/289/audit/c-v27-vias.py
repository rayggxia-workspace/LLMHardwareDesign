from pathlib import Path
import json
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v27-physical/non-dot-upper-net-candidates.json')
for m in json.loads(p.read_text()):
 if m['category']=="'VIA9.2'":print(json.dumps(m,indent=2))
