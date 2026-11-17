"""Replay real RMS intermediate and gamma products through compact E32 RTL."""
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
from verify_arithmetic_capture import rounded as rne

root,bundle,out=map(Path,sys.argv[1:4]); captures=list(map(Path,sys.argv[4:]))
out.mkdir(); cases=[]; receipts=[]
def fit(x):
    if not -2**31<=x<2**31: raise ValueError('unrepresentable E32 operand/result '+str(x))
    return x
def beats(values):
    return [sum((fit(v)&0xffffffff)<<(32*j) for j,v in enumerate(values[i:i+2])) for i in (0,2)]
for path in captures:
    data=json.loads(path.read_text())
    for sample in data['samples']:
        shift=13+sample['extra'] if sample['shifted_format'] else 13
        for i in range(0,len(sample['source']),4):
            x=[fit(v<<sample['shift']) for v in sample['source'][i:i+4]]
            factor=[fit(sample['factor'])]*4; gamma=sample['gamma'][i:i+4]
            mid=[fit(rne(v*f,shift)) for v,f in zip(x,factor)]
            final=[fit(rne(v*g,17+sample['output_shift'])) for v,g in zip(mid,gamma)]
            if final!=sample['expected'][i:i+4]: raise ValueError('captured RMS output mismatch')
            cases.extend([(shift,x,factor,mid),(17+sample['output_shift'],mid,gamma,final)])
    receipts.append(dict(path=str(path),sha256=sha256(path.read_bytes()).hexdigest(),samples=len(data['samples'])))
(out/'vectors.txt').write_text(''.join(str(s)+' '+ ' '.join('{:016x}'.format(v) for vec in (a,b,y) for v in beats(vec))+'\n' for s,a,b,y in cases))
rtl=root/'m-product/wide-38792112/source/project/rtl/w8a16_v1'
sources=[rtl/'e_s32_native.sv',rtl/'e_s32_ap64.sv',bundle/'tb_rms_e32.sv']
verilator=Path.home()/'LLMHardware/opt/verilator-5.042/bin/verilator'
with (out/'build.log').open('w') as log:
    subprocess.run([str(verilator),'--binary','--timing','-Wno-fatal','-j','12','--top-module','tb_rms_e32',
                    '--Mdir',str(out/'obj')]+list(map(str,sources)),stdout=log,stderr=subprocess.STDOUT,check=True)
run=subprocess.run([str(out/'obj/Vtb_rms_e32'),'+vectors='+str(out/'vectors.txt')],capture_output=True,text=True)
(out/'rtl.log').write_text(run.stdout+run.stderr); run.check_returncode()
match=re.search(r'RMS_E32_PASS cases=(\d+) min_driver_cycles=(\d+) max_driver_cycles=(\d+)',run.stdout)
if not match or int(match[1])!=len(cases): raise ValueError('RTL receipt mismatch')
result=dict(passed=True,product_packets=len(cases),inputs=receipts,
    min_driver_cycles=int(match[2]),max_driver_cycles=int(match[3]),
    cycle_scope='continuous input beats and always-ready output after input; first input through final output inclusive; not full scheduler latency',
    period_ps=3334,reference_clock='nominal 300MHz (integer ps period)',
    sources_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in sources},
    verilator_version=subprocess.check_output([str(verilator),'--version'],text=True).strip(),
    scope='real bounded RMS operands exact E32 products; no SRAM scan/apply wrapper, power or timing signoff')
(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
