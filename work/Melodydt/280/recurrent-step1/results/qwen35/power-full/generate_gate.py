"""Generate a gate simulator with synthesized underscore nets explicitly traced."""
from pathlib import Path
from hashlib import sha256
import json, os, subprocess

work=Path.cwd()
verilator=Path('/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator')
cells=Path('/public/home/yuzelu/project-circuit/issue250-p-final-native-diode-gate-GlrL0V/cells.v')
os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
args=[str(verilator),'--cc','--exe','--main','--timing','--trace','--trace-depth','2',
      '--trace-underscore','--assert','-Wno-fatal','--output-groups','0',
      '--Mdir','obj_generated','--top-module','calibrate_tb',str(work.parent/'mapped.v'),
      str(cells),'calibrate_tb.sv']
assert not (work/'obj_generated').exists()
with (work/'generate.log').open('w') as f:
    subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True)
paths=[work.parent/'mapped.v',cells,work/'calibrate_tb.sv']
(work/'generation-receipt.json').write_text(json.dumps(dict(command=args,
    inputs={str(p):sha256(p.read_bytes()).hexdigest() for p in paths}),indent=2)+'\n')
print('FULL_TRACE_GENERATION_PASS',flush=True)
