from pathlib import Path
import sys,json,argparse
from cases import make,partial_producer,TARGETS,cases_for
from compiler import compile_task,CompileError
from audit import audit
from reference import evaluate

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path);a=p.parse_args();checks=[]
 for target in TARGETS:
  for case in cases_for(target):
   task,inputs=make(target,case);bundle=compile_task(task);assert audit(task,bundle)['passed'];ref=evaluate(task,inputs)
   assert ref['checks'];checks.append('accepted:'+target+':'+case)
 for target in ('recovery/U','recovery/F','recovery/C'):
  try:compile_task(partial_producer(target))
  except CompileError as e:assert 'per-word' in str(e);checks.append('reject-partial:'+target)
  else:raise AssertionError('partial producer accepted')
 task,_=make('five/P','baseline');next(b for b in task['buffers'] if b['name']=='b0_a')['initial']=False
 task['tasks'][0]['operations'].insert(0,dict(op='p_gate',a='b0_gx',b='b0_gg',dst='b0_a'))
 try:compile_task(task)
 except CompileError as e:assert 'per-word' in str(e);checks.append('reject-partial:P-feeder')
 else:raise AssertionError('partial feeder accepted')
 report=dict(passed=len(checks),total=len(checks),checks=checks,scope='software matrix cases and per-word producer regression')
 if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n')
 print('PASS matrix software',len(checks))
if __name__=='__main__':main()
