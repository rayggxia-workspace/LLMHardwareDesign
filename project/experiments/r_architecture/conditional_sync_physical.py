"""One bounded R1024 revision, only after the baseline and its validations end."""
from pathlib import Path
import json, subprocess, sys

B=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture')
root=B/'attempt062/B1024/physical'
rec=json.loads((root/'receipt.json').read_text())
metrics=root/'flow/logs/nangate45/rarch157_B1024/base/6_report.json'
if rec['exit']==0 and metrics.exists():
 v=json.loads(metrics.read_text())
 if v['finish__timing__setup__ws']>=0 and v['finish__timing__hold__ws']>=0 and all(v[k]==0 for k in [
  'finish__timing__drv__setup_violation_count','finish__timing__drv__hold_violation_count',
  'finish__timing__drv__max_cap','finish__timing__drv__max_slew']):
  Path('SKIPPED.json').write_text(json.dumps(dict(reason='Baseline STA passed; do not launch an unnecessary revision',source=str(root)),indent=2)+'\n')
  raise SystemExit(0)
unit=json.loads((B/'attempt071/results/1024/receipt.json').read_text())
assert unit['passed'] and unit['mapped'] and unit['read_latency_cycles']==2
rows=json.loads((B/'attempt074/results/RESULTS.json').read_text())
assert rows and all(r['exit']==0 for r in rows)
cmd=[sys.executable,str(Path(__file__).parent/'physical.py'),'--candidate','B1024S',
 '--capacity','1024','--die','1600','--density','.40','--setup-margin','.10','--hold-margin','.06']
raise SystemExit(subprocess.run(cmd).returncode)
