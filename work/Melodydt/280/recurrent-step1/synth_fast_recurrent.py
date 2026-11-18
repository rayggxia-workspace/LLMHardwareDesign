"""Same RTL, direct memory mapping without the expensive memory port sharing pass."""
from pathlib import Path
from hashlib import sha256
import json, subprocess

root=Path.cwd()
lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
def digest(p):return sha256(p.read_bytes()).hexdigest()
script=[
    'read_verilog -sv block_v1_r.sv',
    'hierarchy -check -top block_v1_r',
    'proc','opt -fast','memory_map','opt -fast','techmap','opt -fast',
    'dfflibmap -liberty '+str(lib),'abc -liberty '+str(lib),'clean',
    'read_liberty -lib '+str(lib),'check -assert','stat -liberty '+str(lib),
    'write_verilog -noattr -noexpr mapped.v','write_json mapped.json']
(root/'synth.ys').write_text('\n'.join(script)+'\n')
subprocess.run(['yosys','-l','synth.log','synth.ys'],check=True)
d=json.loads((root/'mapped.json').read_bytes())['modules']['block_v1_r']
assert not any(x['type'].startswith('$') for x in d['cells'].values())
result=dict(rtl_sha256=digest(root/'block_v1_r.sv'),netlist_sha256=digest(root/'mapped.v'),
            liberty_sha256=digest(lib),cell_count=len(d['cells']),
            flow='direct memory mapping; no memory_share; fast optimization; full mapped check')
(root/'synth-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print('MAPPED_RECURRENT_PASS',len(d['cells']),flush=True)
