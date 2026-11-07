from pathlib import Path
import argparse,copy,hashlib,json,sys
from cases import make,cases_for,TARGETS
from compiler import compile_task
from audit import audit
from reference import evaluate
from host import replay_plan,load_plan,request,word

def good(task,inputs,case,task_sequence=1):
 bundle=compile_task(task);audit(task,bundle);ref=evaluate(task,inputs)
 if task_sequence!=1:
  for c in ref['checks']:
   if c['op']==13:c['value']=(c['value']&~(((1<<32)-1)<<235))|task_sequence<<235
 plan=replay_plan(task,bundle,inputs,ref);out=[]
 for c in plan:
  if c['op']==10 and c['status']==0 and task['target'].split('/')[1]!='J':
   c['mask']|=1<<281;c['value']|=int(case in ('saturating','continuous'))<<281
  out.append(c)
  if c['op']==8 and c['status']==0:
   out.extend([request(2,0,status=0x106),request(8,3,data=c['data'],status=0x106)])
 out.append(request(8,3,data=task['job']|task['epoch']<<32|task['sequence']<<64|task['generation']<<96,status=0x107))
 return bundle,ref,out

def main():
 p=argparse.ArgumentParser();p.add_argument('--target',choices=TARGETS,required=True);p.add_argument('output',type=Path);a=p.parse_args();manifest=[]
 for index,case in enumerate(cases_for(a.target)):
  task,inputs=make(a.target,case);bundle,ref,plan=good(task,inputs,case)
  prefix=[request(15,3,data=255,status=0x101),request(1,3,status=0x102),request(9,0,status=0x103),request(9,3,address=1,status=0x103)]
  commits=ref['commits']
  if case=='continuous':
   second=copy.deepcopy(task);second['job']+=1;second['sequence']+=1
   _,second_inputs=make(a.target,'baseline');b2,r2,p2=good(second,second_inputs,'baseline',2)
   assert bundle['images_hex']==b2['images_hex']
   plan+=p2[len(load_plan(second,b2)):];commits*=2
  elif case.startswith(('pm_error','pm_lost')):
   target=int(case[-1]);lost=case.startswith('pm_lost')
   before=load_plan(task,bundle);all_plan=replay_plan(task,bundle,inputs,ref)
   start=next(i for i,c in enumerate(all_plan) if c['op']==8 and c['status']==0)
   first=all_plan[:start]+[request(0,target,data=int(lost),mode=4),all_plan[start]]
   if lost:first.append(request(0,3,mode=5))
   else:
    status=0x200 if a.target.startswith('recovery/') else 10
    first.extend([request(9,3,mode=1,mask=1<<18,value=1<<18),request(10,3,mode=2,mask=((1<<112)-1),value=task['job']|task['epoch']<<32|task['sequence']<<64|status<<96)])
   plan=first+[request(0,3,mode=3)]+plan
  elif case=='crc_fault':
   load=load_plan(task,bundle);cut=next(i for i,c in enumerate(load) if c['op']==3 and c['target']==1)
   end=next(i for i,c in enumerate(load) if i>cut and c['op']==4 and c['target']==1)
   first=copy.deepcopy(load[:end+1]);first[cut]['value']=1;first[-1].update(status=0x104,mask=0,value=0)
   first.insert(cut,request(0,1,data=2,mode=4))
   plan=first+[request(5,1,status=0x105),request(0,3,mode=3)]+plan
  plan=prefix+plan
  folder=a.output/case;folder.mkdir(parents=True,exist_ok=True)
  (folder/'replay.mem').write_text(''.join(f'{word(c):0330x}\n' for c in plan))
  (folder/'count.mem').write_text(f'{len(plan):08x}\n{commits:08x}\n')
  for name,value in [('task',task),('inputs',inputs),('bundle',bundle),('reference',ref),('host-plan',plan)]:
   (folder/(name+'.json')).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
  manifest.append(dict(case=case,index=index,commands=len(plan),commits=commits,
     sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir()) if p.is_file()}))
 (a.output/'generated.json').write_text(json.dumps(dict(target=a.target,cases=manifest),indent=2)+'\n')
 print('PASS generated matrix',a.target,len(manifest),'cases')
if __name__=='__main__':main()
