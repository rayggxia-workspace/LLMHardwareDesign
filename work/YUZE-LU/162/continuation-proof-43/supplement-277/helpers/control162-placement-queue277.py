import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time,re,shutil
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');queue=b/'dynamic-07/node7';record=b/'route-selection-102/sready277-r256-placement-envelope';assert not record.exists();record.mkdir();rows=[];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();source=b/'source-276';reg=b/'r256-placement-regression-277'
def add(name,script,args,deps,out,memory=32):
 assert re.fullmatch('[a-z0-9_-]+',name);p=queue/'pending'/(name+'.json');assert not p.exists()and not out.exists();spec=dict(script=script,source_root=str(source),forecast_gib=memory,requires=list(map(str,deps)),args=list(map(str,args))+['--out',str(out)]);t=p.with_suffix('.tmp');t.write_text(json.dumps(spec));t.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
add('00-c-sready277-placement-contract','run.py',['--model','r256_placement_contract','--verify-only'],[],reg)
inputs=b/'r256-composition-259/function-inputs';top=b/'r256-composition-259/topology';initial=b/'r256-early-electrical-266/initial'
add('00-d-sready277-r-early-placement','system_upper.py',['--manifest',inputs/'physical.json','--graph',top/'boundary-graph.json','--cap-lower-bound-only','--pin-aware-placement','--seed',2770,'--channel-gap-um',64,'--electrical-placement-report',initial/'wire-cap-lower-bound.json','--placement-capacity-target','.35'],[initial/'receipt.json',reg/'receipt.json'],b/'r256-early-electrical-277/optimized')
archive=record/'replaced-never-admitted';archive.mkdir()
for n in [2631,2632,2633]:
 p=queue/'pending'/('00-d-sready263-placement-'+str(n)+'.json');assert p.exists()and not(queue/'commands'/p.name).exists()and not(queue/'results'/p.name).exists();spec=json.loads(p.read_text());args=spec['args'];dest=Path(args[args.index('--out')+1]);assert not dest.exists();before=sha(p);copy=archive/p.name;shutil.copyfile(p,copy);assert sha(copy)==before;p.unlink()
 add(p.stem+'-r256-envelope276',spec['script'],args[:-2],list(map(Path,spec['requires']))+[reg/'receipt.json'],dest,spec['forecast_gib'])
 rows[-1]['replaced_unadmitted']=dict(original_path=str(p),archived_path=str(copy),sha256=before,reason='Existing search contract accepted26 base owners only; new actualR256 scene has29. Closed scene marker and11122/11124 net checks added, default legacy unchanged. No physical acceptance gate changed.')
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,whole_system_qualified=False,scope='Actual legacy26-macro full output byte replay and five invalid R scene inputs precede actual29-macro placement, whose16 trial costs/nonoverlap still independently recomputed. Failed early266 optimized evidence unchanged. Only three never-admitted final-scene placement specs replaced; actual completed components/gates preserved.'),indent=2));print(json.dumps(dict(queued=len(rows),retargeted_never_admitted=3)))
'''
compile(q,'queue277','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
