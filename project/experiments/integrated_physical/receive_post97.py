"""Physical97 complete selected gates against fixed raw/RTL and original74 integer oracle."""
import argparse,copy,importlib.util,sys
from common import *
from admission97 import admit,INPUT,SOURCE,R97
from post_audit97 import audit_post
p=argparse.ArgumentParser();p.add_argument('--original',type=Path,required=True);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--runs',type=Path,nargs=4,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);ad=admit();pm=artifacts(a.original);need(pm['status']=='EXACT_ACCEPTED97_GATE_EXPORT_AND_DECLARED_MEMORY_CUT'and load(a.original/'admission.json')==ad,'exact original97 cut');postpm,cert,proof=audit_post(a.original,a.prepared,a.out/'post-wrapper',ad);bm=artifacts(a.build);need(bm['status']=='POSTPHYSICAL97_GATE_BUILT_NOT_EXECUTED'and bm['prepared_manifest_sha256']==sha(a.prepared/'manifest.json')and bm['original_prepared_manifest_sha256']==sha(a.original/'manifest.json')and sha(a.build/'obj/Vchain97')==bm['binary_sha256'],'precise physical97 binary')
sys.path.insert(0,str(SOURCE/'project/experiments/v_consumer'))
from reference import reference,check
from gate_receive import typed_pilot
cases=load(INPUT/'cases.json');refs={};summary=[];neg=[]
for run,(stall,pilot,ci)in zip(a.runs,[(0,1,0),(0,2,5),(1,1,0),(1,2,5)]):
 m=artifacts(run);need(m['status']=='POSTPHYSICAL97_GATE_EXECUTED_NOT_RECEIVED'and type(m['stall'])is int and m['stall']==stall and type(m['pilot'])is int and m['pilot']==pilot and m['build_manifest_sha256']==sha(a.build/'manifest.json')and m['prepared_manifest_sha256']==sha(a.prepared/'manifest.json')and m['input_manifest_sha256']==sha(INPUT/'manifest.json')and m['admission']==ad,'exact physical97 run/stall/pilot/source/input');rr=[__import__('json').loads(s)for s in(run/'actual.jsonl').read_text().splitlines()];goldroot=R97/f'gatep{pilot}s{stall}';artifacts(goldroot);gold=[__import__('json').loads(s)for s in(goldroot/'actual.jsonl').read_text().splitlines()];need(rr==gold and len(rr)==2,'all physicalgate fields equal frozen rawgate andRTL');proto=load(run/'actual.jsonl.protocol.json');typed_pilot(proto);need(proto==load(goldroot/'actual.jsonl.protocol.json'),'complete strict same raw protocol');c=cases[ci]
 if c['name']not in refs:refs[c['name']]=reference(INPUT,c)
 outcomes=[]
 for row in rr:need(row['name']==c['name'],'exact original case');outcomes.append(check(row,refs[c['name']]))
 for label,change in [('out',lambda row:row['out'].__setitem__(0,row['out'][0]^1)),('missing',lambda row:row.pop('out'))]:
  bad=copy.deepcopy(rr[1]);change(bad);nf=a.out/f'negative-p{pilot}s{stall}-{label}.json';put(nf,bad)
  try:check(load(nf),refs[c['name']])
  except (ValueError,KeyError):neg.append({'path':nf.name,'sha256':sha(nf)})
  else:raise ValueError('malformed physical97 output accepted')
 summary.append({'run_directory':str(run),'run_manifest_sha256':sha(run/'manifest.json'),'stall':stall,'pilot':pilot,'records':2,'outcomes':outcomes,'protocol':proto})
put(a.out/'receipt.json',{'schema':'gate98-post97-v1','status':'PASS_POSTPHYSICAL97_SELECTED_GATES_AND_ORIGINAL_ORACLE','source':sources(),'admission':ad,'prepared_manifest_sha256':sha(a.original/'manifest.json'),'post_prepared_directory':str(a.prepared),'post_prepared_manifest_sha256':sha(a.prepared/'manifest.json'),'build_directory':str(a.build),'build_manifest_sha256':sha(a.build/'manifest.json'),'postphysical':proof,'structure':cert,'results':summary,'negative_files':neg,'limits':['Four selected normal gate runs/eight outputs only; original50command errors/recovery/Qinjection remain RTL-only.','Zero-delay exact physical netlist plus all original pin/FF function certificate, not PVT/SRAM/CDC qualification.']});print('PASS_POSTPHYSICAL97_SELECTED_GATES_AND_ORIGINAL_ORACLE')
