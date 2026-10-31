import json,re,subprocess,datetime
from pathlib import Path
base=Path('/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030')
jobs=[93853,93857,93884,93902,93924,93980,93982,94024]
def run(args):return subprocess.check_output(args,universal_newlines=True).strip()
def inspect(job):
 raw=run(['scontrol','show','job',str(job),'-o'])
 fields=dict(re.findall(r'(\w+)=([^ ]*)',raw))
 assert fields['JobState']=='PENDING' and fields['UserId']=='yuzelu(10011)' and fields['JobName']=='yzl-bv2-gates',raw
 assert fields['Command'].startswith(str(base)+'/snapshots/') and fields['Command'].endswith('/project/experiments/block_v2/remote_gates.sh'),raw
 assert fields['CPUs/Task'] if 'CPUs/Task' in fields else 'CPUs/Task=48' in raw
 assert 'CPUs/Task=48' in raw and fields['NumNodes']=='1' and fields['Dependency'].startswith('afterok:'),raw
 return raw,fields
initial={str(j):inspect(j)[0] for j in jobs}
record=dict(updated_cst=datetime.datetime.now().isoformat(),jobs={},measured_formal_peak_kib=146771828,
 formal_forecast_gib=192,ordinary_worker_forecast_gib=64,maximum_ready_independent_gates=3,
 scheduler_requested_memory_mib=0,actual_node_memory_admission_basis_gib=400,reserved_node_cpu=96,task_cpu=48,exclusive_flag=False,
 basis='One full proof measured140GiB peak; formal192 + two ordinary64 with20percent headroom and16GiB guard =400GiB. Keep48 task CPU and three16CPU ready workers unchanged; reserve all96 CPUs of a non-oversubscribed c96 node per mixed gate group. Shared=0 modification was denied. NumCPUs=96 succeeded. Initial400GiB scheduler request was corrected to0 before dependency eligibility: node RealMemory is configured1MiB despite actual503.5GiB. WholeCPU reservation prevents sharing; runtime ordinary memory admission remains active. No job replacement, cancellation or wider permissions used.',
 scope='Only eight owned pending Issue143 gate jobs. No running jobs, sources, dependencies, commands or final criteria modified.')
for job in jobs:
 before,fields=inspect(job)
 run(['scontrol','update','JobId='+str(job),'NumCPUs=96','MinMemoryNode=0'])
 after,new=inspect(job)
 assert new['NumCPUs']=='96' and new['MinMemoryNode']=='0',after
 for key in ('Command','Dependency','ExcNodeList','JobName','NumTasks','NumNodes'):
  assert fields[key]==new[key],(key,before,after)
 record['jobs'][str(job)]=dict(before=before,after=after)
 (base/'pending-r-gates-memory.json').write_text(json.dumps(record,indent=2)+'\n')
 print(str(job)+' full96CPU reservation,48CPU task/three16CPUworkers unchanged; scheduler memory0(actual RAM is not configured)',flush=True)
