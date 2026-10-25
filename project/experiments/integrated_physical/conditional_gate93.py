"""At most one preregistered exact-binary retry, only after verified original timeout."""
import argparse,copy,importlib.util,sys,traceback
from common import *
from admission93 import admit,SOURCE,INPUT,R93
R=Path('/public/home/yuzelu/RuizhiLiang/issue98-integrated-physical-20261025')
p=argparse.ArgumentParser();p.add_argument('--stall',type=int,choices=[0,1],required=True);a=p.parse_args();out=R/f'final93-budget-s{a.stall}';out.mkdir(exist_ok=False);cfg=load(HERE/'final93_extension.json');m={'status':'ERROR_NOT_RETRIED','source':sources(),'resources':resource_snapshot(),'stall':a.stall,'contract_sha256':sha(HERE/'final93_extension.json')}
try:
 need(cfg['max_retries_per_stall']==1 and cfg['new_child_seconds']==16000 and cfg['new_slurm_minutes']==280,'fixed sole extension budget');ad=admit();original=R/f'jointpost93s{a.stall}01';prepared=R/'jointpost93-prep01';build=R/'jointpost93-build01';om=artifacts(original);artifacts(prepared);bm=artifacts(build)
 for path,key in [(prepared/'manifest.json','prepared_manifest_sha256'),(build/'manifest.json','build_manifest_sha256'),(build/'obj/Vchain93','binary_sha256'),(prepared/'chain_gate.cpp','driver_sha256'),(INPUT/'manifest.json','input_manifest_sha256'),(INPUT/'vectors93.tsv','input_vectors_sha256')]:need(sha(path)==cfg[key],'immutable extension input '+key)
 need(om['source']['commit']==cfg['source_commit'] and om['admission']==ad and type(om['stall'])is int and om['stall']==a.stall and om['resources']['slurm_job']==str(cfg['original_jobs'][a.stall]),'exact original attempted job source/stall');cmd=load(original/'simulation-command.json');need(cmd['timeout_seconds']==10500 and cmd['argv'][-4:]==[str(build/'obj/Vchain93'),str(INPUT/'vectors93.tsv'),str(original/'actual.jsonl'),str(a.stall)],'original exact binary/input/driver output and budget');m.update(original_directory=str(original),original_manifest_sha256=sha(original/'manifest.json'),original_simulation_command_sha256=sha(original/'simulation-command.json'))
 if om['status']=='POSTPHYSICAL93_GATE_EXECUTED_NOT_RECEIVED':
  need(cmd['exit']==0 and cmd['error'] is None,'original completed normally');m.update(status='ORIGINAL_FINISHED_NO_RETRY_NOT_YET_GATE_ACCEPTANCE',selected_run_directory=str(original))
 else:
  need(om['status']=='ERROR' and cmd['exit'] is None and type(cmd['error'])is str and cmd['error'].startswith('TimeoutExpired('),'only actual original child timeout may retry')
  raw=(original/'actual.jsonl').read_bytes().splitlines(keepends=True);rows=[];partial=0
  for i,line in enumerate(raw):
   if not line.endswith(b'\n'):need(i==len(raw)-1,'only final record may be truncated by timeout');partial+=1;continue
   rows.append(json.loads(line))
  gold=[json.loads(s)for s in(R93/f'rtl-s{a.stall}03/actual.jsonl').read_text().splitlines()];need(0<len(rows)<=51 and len(gold)==51,'actual nonempty bounded complete prefix')
  spec=importlib.util.spec_from_file_location('independent93',SOURCE/'project/experiments/gamma_stream/verify.py');ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref);cases={c['name']:c for c in load(INPUT/'cases.json')};old=Path(load(INPUT/'manifest.json')['old_root']);refs={};checks=[]
  for i,(row,g)in enumerate(zip(rows,gold)):
   need(row['name']in cases and type(row['cache'])is int and row['cache']in(0,1),'typed prefix case');key=(row['name'],row['cache']);c=cases[row['name']]
   if key not in refs:refs[key]=ref.matrix_reference(old,c,row['cache'])if c['kind']=='chain'else{'x':ref.ints(bytes.fromhex(c['x'])),'gamma':ref.ints(bytes.fromhex(c['gamma']))}
   checks.append(ref.check(row,c,refs[key]));norm=copy.deepcopy(row)
   if g['role']=='last-legal-epoch':need(norm['role']=='gate-last-normal-command' and type(norm['epoch'])is int and norm['epoch']==2,'same declared final fixture exception');norm['role']=g['role'];norm['epoch']=g['epoch']
   need(norm==g,'every complete timed-out prefix observable matches original RTL')
  put(out/'prefix.json',{'status':'PASS_COMPLETE_PREFIX_ONLY_NOT_FULL_GATE_ACCEPTANCE','records':len(rows),'trailing_partial_records_ignored':partial,'checks':checks,'original_actual_sha256':sha(original/'actual.jsonl')});retry=R/f'jointpost93s{a.stall}02';need(not retry.exists(),'sole new retry output must not already exist');m.update(status='EXACT_ORIGINAL_TIMEOUT_PREFIX_CHECKED_RETRY_RUNNING',selected_run_directory=str(retry),prefix_receipt_sha256=sha(out/'prefix.json'));put(out/'guard.json',m)
  argv=['postgate.py','sim','--original',str(R/'prepare9302'),'--prepared',str(prepared),'--build',str(build),'--stall',str(a.stall),'--seconds','16000','--out',str(retry)];put(out/'retry-command.json',{'argv':argv,'existing_binary_sha256':cfg['binary_sha256'],'no_rebuild_or_input_change':True});sys.argv=argv
  import postgate
  postgate.main();rm=artifacts(retry);need(rm['status']=='POSTPHYSICAL93_GATE_EXECUTED_NOT_RECEIVED'and rm['build_manifest_sha256']==cfg['build_manifest_sha256'],'same exact retry completed');m.update(status='SOLE_EXACT_RETRY_EXECUTED_NOT_YET_GATE_ACCEPTANCE',retry_manifest_sha256=sha(retry/'manifest.json'))
except Exception as e:m.update(previous_status=m['status'],status='ERROR_GUARD_OR_RETRY_NOT_ACCEPTED',error=str(e),traceback=traceback.format_exc());raise
finally:put(out/'guard.json',m)
print(m['status'])
