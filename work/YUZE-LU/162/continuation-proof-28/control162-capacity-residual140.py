import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native=c/'native-sta/receipt.json';audit=c/'native-sta/native-system-audit.json';r=json.loads(native.read_text());assert r['execution_passed']and r['typed_native_timing_passed']and json.loads(audit.read_text())['passed']and r['outputs']['native-system-audit.json']==sha(audit)
record=b/'route-selection-102/sready140-capacity-residual1420-1425.json';assert not record.exists()
placements=[]
for n in range(1420,1426):
 p=c/'cap-capacity-candidates'/str(n);rr=json.loads((p/'receipt.json').read_text());assert rr['passed']and rr['outputs']['wire-cap-lower-bound.json']==sha(p/'wire-cap-lower-bound.json')
 d=json.loads((p/'wire-cap-lower-bound.json').read_text())
 if all(all(v<=row['physical_driver']['max_capacitance_ff']+1e-9 for v in row['wire_capacitance_lower_bound_ff'].values())for row in d['rows']):placements.append(str(p))
assert len(placements)==4
config=b/'route-selection-102/sready140-capacity-residual-config1420-1425.json';assert not config.exists();config.write_text(json.dumps(dict(native_sta=str(c/'native-sta'),placements=placements),indent=2))
old=b/'dynamic-05/node4/pending/00-o-sready140-residual-after-final-receipt-1391.json';spec=json.loads(old.read_text());args=spec['args'];print('original args',args)
index=next(i for i,x in enumerate(args)if x.endswith('sready140-residual-1391.json'));args[index]=str(config)
out=c/'capacity-native-residual-01';args[args.index('--out')+1]=str(out);spec['requires']=[str(audit)]+[str(Path(p)/'receipt.json')for p in placements]
f=b/'dynamic-05/node2/pending/00-q-sready140-capacity-residual.json';assert not f.exists()and not out.exists();tmp=f.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(f)
record.write_text(json.dumps(dict(time=time.time(),spec=str(f),sha256=sha(f),config=str(config),config_sha256=sha(config),completed_native_receipt_sha256=sha(native),placements=placements,scope='Unmodified source140 native-ground plus optimistic upper capacitance failure screen only; all actual geometry/PG/three-corner distributed RC and 300MHz gates remain mandatory.'),indent=2));print('Appended',f)
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
