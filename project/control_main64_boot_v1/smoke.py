"""Actual main profile interfaces and full-native elaboration, no simulation."""
from pathlib import Path
import json,os,subprocess
from stage import stage
out=Path(os.environ['STAGE_OUT']);stage(out)
d=json.loads((out/'sources.json').read_text())
cmd=['/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator','--lint-only','--timing','--Wall','-Wno-fatal','--top-module','main64_boot_top','-GKIND0=0','-GKIND1=0']
cmd+=['-I'+p for p in d['include_dirs']]+[d['waiver']]+d['sources']
with (out/'lint.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
if r.returncode:raise RuntimeError('full-native lint failed; inspect stage/lint.log')
print('PASS main64 unified full-native lint U/U')
