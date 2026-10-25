"""Read-only full-cycle progress estimate; never a numerical acceptance receipt."""
import argparse,json,subprocess,time
from common import *
from admission93 import R93
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);results=[]
for tag,job,stall in [('gate93s002','90940',0),('gate93s102','90941',1),('postgate93s001','90990',0),('postgate93s101','90991',1)]:
 q=subprocess.run(['sacct','-j',job,'-n','-X','-P','-o','JobID,State,ElapsedRaw'],capture_output=True,text=True,check=True);(a.out/(tag+'-sacct.txt')).write_text(q.stdout+q.stderr);fields=q.stdout.strip().splitlines()[0].split('|');need(fields[0]==job,'same own job');elapsed=int(fields[2]);gold=[json.loads(s)for s in(R93/f'rtl-s{stall}03/actual.jsonl').read_text().splitlines()];f=a.root/tag/'actual.jsonl';data=f.read_bytes();raw=data.splitlines(keepends=True);rows=[];partial=0
 for i,line in enumerate(raw):
  if not line.endswith(b'\n'):
   need(i==len(raw)-1,'only last file record can be incomplete');partial+=1;continue
  rows.append(json.loads(line))
 need(len(rows)<=51 and len(gold)==51,'actual/gold count');actual_cycles=sum(v['cycles']for v in rows);total_cycles=sum(v['cycles']for v in gold);gold_prefix=sum(v['cycles']for v in gold[:len(rows)]);need(actual_cycles==gold_prefix,'completed prefix cycle sum equals reference');results.append({'run':tag,'job':job,'state':fields[1],'elapsed_seconds':elapsed,'output_bytes':len(data),'complete_records':len(rows),'trailing_partial_records_ignored':partial,'completed_cycles':actual_cycles,'full_51_cycle_count':total_cycles,'conservative_total_seconds_at_complete_prefix_rate':None if actual_cycles==0 else elapsed*total_cycles/actual_cycles,'budget_seconds':10800,'child_budget_seconds':10500,'not_accepted':True})
put(a.out/'progress.json',{'status':'READ_ONLY_CYCLE_PROGRESS_NOT_GATE_ACCEPTANCE','source':sources(),'resources':resource_snapshot(),'observed_unix_time':time.time(),'runs':results,'limits':['Completed prefix and unflushed output make throughput estimate conservative and stage dependent. Not a guarantee or authorization to extend fixed budget.','Numerical correctness/full51 protocol qualification remains independent final receiver only.']});print('READ_ONLY_CYCLE_PROGRESS_NOT_GATE_ACCEPTANCE')
