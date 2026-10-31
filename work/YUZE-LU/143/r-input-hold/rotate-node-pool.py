import datetime,json,re,subprocess
from pathlib import Path
base=Path('/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030')
allowed=['node'+str(i) for i in (13,14,15,16,17,18,25,26)]
def run(args):return subprocess.check_output(args,universal_newlines=True).strip()
def inspect(job):
 raw=run(['scontrol','show','job',str(job),'-o']);fields=dict(re.findall(r'(\w+)=([^ ]*)',raw))
 assert fields['UserId']=='yuzelu(10011)' and fields['JobName'].startswith('yzl-bv2-'),raw
 assert fields['Command'].startswith(str(base)+'/'),raw
 assert fields['NumNodes']=='1' and fields['JobState'] in ('RUNNING','PENDING'),raw
 return raw,fields
jobs=[int(line.split()[0]) for line in run(['squeue','-u','yuzelu','-h','-o','%i %j']).splitlines() if line.split()[1].startswith('yzl-bv2-')]
initial={job:inspect(job) for job in jobs}
assert all(row['NodeList'] in allowed for raw,row in initial.values() if row['JobState']=='RUNNING')
record=dict(updated_cst=datetime.datetime.now().isoformat(),maximum_task_nodes=8,allowed_c96_nodes=allowed,
 scope='Only owned pending Issue143 eligibility changes; no running job moved, no CPU/dependency/command changes',
 reason='Rotate unused node19/20 slots to idle node25/26. Node13-20 was an implementation choice for eight-node cap, not a user restriction on IDs; project permits c96 node13-26. Running nodes13/14/15 stay within the new eight-node set.',
 resource_snapshot=run(['sinfo','-N','-n','node13,node14,node15,node16,node17,node18,node19,node20,node25,node26','-h','-o','%N %t %C']),jobs={})
for job,(raw,fields) in initial.items():
 if fields['JobState']=='RUNNING':
  record['jobs'][str(job)]=dict(state='RUNNING',node=fields['NodeList'],unchanged=True)
  continue
 before,fields=inspect(job);assert fields['JobState']=='PENDING'
 run(['scontrol','update','JobId='+str(job),'ExcNodeList=node[19-24]'])
 after,new=inspect(job)
 assert new['ExcNodeList']=='node[19-24]',after
 for key in ('Command','Dependency','NumCPUs','NumTasks','NumNodes','TimeLimit'):
  assert fields[key]==new[key],(key,before,after)
 record['jobs'][str(job)]=dict(before=before,after=after)
 (base/'owned-node-budget-current.json').write_text(json.dumps(record,indent=2)+'\n')
 print(str(job)+' pending eligibility -> node13-18/25-26',flush=True)
print(json.dumps(dict(task_node_limit=8,running_nodes=sorted({row['NodeList'] for raw,row in initial.values() if row['JobState']=='RUNNING'}),allowed=allowed)))
