"""Full independent gate receiver after successful exact-original/retry selection."""
import argparse,sys
from common import *
R=Path('/public/home/yuzelu/RuizhiLiang/issue98-integrated-physical-20261025')
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);cfg=load(HERE/'final93_extension.json');selected=[];guards=[]
for stall in(0,1):
 directory=R/f'final93-budget-s{stall}';g=load(directory/'guard.json');need(type(g['stall'])is int and g['stall']==stall and g['contract_sha256']==sha(HERE/'final93_extension.json'),'exact typed guard/contract')
 status=g['status'];need(status in('ORIGINAL_FINISHED_NO_RETRY_NOT_YET_GATE_ACCEPTANCE','SOLE_EXACT_RETRY_EXECUTED_NOT_YET_GATE_ACCEPTANCE'),'guard actually terminated successfully, not prefix/running/error')
 expected=R/('jointpost93s'+str(stall)+('01'if status.startswith('ORIGINAL_')else'02'))
 need(g['selected_run_directory']==str(expected),'only exact original or sole preregistered retry directory');rm=artifacts(expected);cmd=load(expected/'simulation-command.json');need(cmd['exit']==0 and cmd['error']is None,'selected actual command succeeded')
 need(cmd['timeout_seconds']==(10500 if status.startswith('ORIGINAL_')else 16000),'original/retry exact execution budget');need(rm['build_manifest_sha256']==cfg['build_manifest_sha256'],'same immutable binary build')
 selected.append(expected);guards.append({'stall':stall,'guard_sha256':sha(directory/'guard.json'),'status':status,'selected_run_directory':str(expected),'selected_manifest_sha256':sha(expected/'manifest.json')})
put(a.out/'selection.json',{'status':'SUCCESSFUL_RUN_SELECTION_ONLY_FULL_RECEPTION_REQUIRED','source':sources(),'guards':guards})
sys.argv=['receive_gate.py','--prepared',str(R/'prepare9302'),'--post-prepared',str(R/'jointpost93-prep01'),'--build',str(R/'jointpost93-build01'),'--runs',*map(str,selected),'--out',str(a.out/'gate')]
import receive_gate
receive_gate.main();g=load(a.out/'gate/receipt.json');need(g['status']=='PASS_POSTPHYSICAL93_COMPLETE_GATES_AND_DECLARED_EPOCH_EXCEPTION','complete independent receiver actual success');manifest(a.out,{'status':'FULL_FINAL93_GATE_RECEIVED_AFTER_EXACT_SUCCESSFUL_RUN_SELECTION','source':sources(),'gate_receipt_sha256':sha(a.out/'gate/receipt.json')});print('FULL_FINAL93_GATE_RECEIVED_AFTER_EXACT_SUCCESSFUL_RUN_SELECTION')
