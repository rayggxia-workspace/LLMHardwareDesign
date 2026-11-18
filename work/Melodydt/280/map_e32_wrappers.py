"""Map candidate common arithmetic leaves; no activity or energy claim yet."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

bundle, out = map(Path, sys.argv[1:])
lib = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
rtl = bundle / 'rtl'
sources = sorted(rtl.glob('*.sv'))
tops = ['e_s32_ap64', 's32_rms_range_scan', 's32_rms_apply_s128', 'rope_e32_ap64']
def digest(p):
    return sha256(p.read_bytes()).hexdigest()
def run(top):
    work = out/top
    work.mkdir()
    script = '\n'.join([
        'read_slang --top {} -I{} {}'.format(top,rtl,' '.join(map(str,sources))),
        'synth -top {} -flatten -noabc -noshare'.format(top),
        'dfflibmap -liberty '+str(lib), 'abc -liberty '+str(lib),
        'clean', 'read_liberty -lib '+str(lib), 'check -assert',
        'stat -liberty '+str(lib),
        'write_verilog -noattr -noexpr '+str(work/'mapped.v'),
        'write_json '+str(work/'mapped.json')])+'\n'
    (work/'map.ys').write_text(script)
    with (work/'console.log').open('w') as log:
        code=subprocess.call(['yosys','-l',str(work/'map.log'),str(work/'map.ys')],stdout=log,stderr=subprocess.STDOUT)
    receipt={'top':top,'exit_code':code,'scope':'candidate mapped cells; activity, numerical equivalence and model binding pending',
             'inputs_sha256':{str(p):digest(p) for p in sorted(rtl.iterdir()) if p.is_file()},'liberty_sha256':digest(lib)}
    if code==0:
        design=json.loads((work/'mapped.json').read_text())['modules'][top]
        unmapped=sorted({c['type'] for c in design['cells'].values() if c['type'].startswith('$')})
        receipt.update(cells=len(design['cells']),unmapped=unmapped,outputs_sha256={p.name:digest(p) for p in (work/'mapped.v',work/'mapped.json',work/'map.log')})
        if unmapped:receipt['exit_code']=1
    (work/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt
out.mkdir()
with ThreadPoolExecutor(max_workers=3) as pool:
    receipts=list(pool.map(run,tops))
(out/'summary.json').write_text(json.dumps(receipts,indent=2)+'\n')
sys.exit(0 if all(r['exit_code']==0 for r in receipts) else 1)
