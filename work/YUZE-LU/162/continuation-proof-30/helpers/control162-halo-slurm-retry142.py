"""Append unique retries for proven pre-execution Slurm transport failures."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');base=b/'s-ready-composition-01/1391';queue=b/'dynamic-03/node5';pending=queue/'pending';record=b/'route-selection-102/s-ready-halo-slurm-retry-source142.json'
assert not record.exists();rows=[];proofs=[];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
state=json.loads((queue/'queue-state.json').read_text());assert str(state['job'])=='95155'
assert json.loads((base/'final-composition/receipt.json').read_text())['passed']
def append(name,spec):
 p=pending/(name+'.json');assert not p.exists();out=Path(spec['args'][spec['args'].index('--out')+1]);assert not out.exists()
 t=p.with_suffix('.tmp');t.write_text(json.dumps(spec));t.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
for old,new in [(1471,1473),(1472,1474)]:
 name='00-s-sready142-halo-'+str(old);p=pending/(name+'.json');spec=json.loads(p.read_text());log=queue/(name+'.log');text=log.read_text();f=state['finished'][name]
 assert f['returncode']==1 and f['spec_sha256']==sha(p)and 'srun: error:'in text and 'Unexpected message received'in text and 'OPENROAD:'not in text
 out=Path(spec['args'][spec['args'].index('--out')+1]);assert not out.exists()
 proofs.append(dict(old_spec=str(p),old_spec_sha256=sha(p),old_log=str(log),old_log_sha256=sha(log),old_queue_result=f,old_output_absent=True))
 args=list(spec['args']);args[args.index('--out')+1]=str(base/'halo-cap-candidates'/str(new));args[args.index('--seed')+1]=str(new)
 append('00-s-sready142-halo-slurm-retry-'+str(new),dict(spec,args=args))
config=b/'route-selection-102/sready142-halo-native-cap-config-02.json';assert not config.exists();config.write_text(json.dumps(dict(native_sta=str(base/'native-sta'),placements=[str(base/'halo-cap-candidates'/str(n))for n in [1470,1473,1474]]),indent=2))
residual=base/'halo-native-residual-02';pin=base/'halo-native-pin-load-02'
for name,args,deps,out in [
 ('00-t-sready142-halo-native-residual-retry02',['--native-cap-residual-config',str(config)],[base/'native-sta/native-system-audit.json',base/'final-composition/receipt.json']+[base/'halo-cap-candidates'/str(n)/'receipt.json'for n in [1470,1473,1474]],residual),
 ('00-u-sready142-halo-native-pin-load-retry02',['--native-pin-load-residual',str(residual/'native-cap-residual.json')],[residual/'receipt.json'],pin)]:
 append(name,dict(script='system_upper.py',source_root=str(b/'source-142'),forecast_gib=32,requires=list(map(str,deps)),args=['--manifest',str(base/'selected/physical.json'),'--graph',str(base/'topology/boundary-graph.json')]+args+['--out',str(out)]))
record.write_text(json.dumps(dict(time=time.time(),source='source-142',tasks=rows,original_preexecution_failures=proofs,original_specs_and_results_preserved=True,scope='Slurm Unexpected message received before Python/EDA start, no output directory. Two unique same-hardware diagnostics and two unchanged bound computations; no physical failure waived, no qualification granted.'),indent=2));print('Appended',len(rows),'unique retry/bound tasks, old failures preserved.')
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
