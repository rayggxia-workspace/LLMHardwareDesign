"""Read back only this experiment's known Slurm allocations and source receipts."""
from pathlib import Path
import json,subprocess,datetime
R=Path(__file__).resolve().parents[3];D=R/'work/YUZE-LU/157';E=D/'evidence/extended'

def main():
 rows=[]
 for p in sorted((R/'.local/157').glob('deployment*.json')):
  r=json.loads(p.read_text());r['receipt']=p.name;rows.append(r)
 ids=sorted({str(r['job_id'])for r in rows if 'job_id'in r})
 cmd=['ssh','yuzelu@10.129.166.172','sacct -j '+','.join(ids)+' -X -n -P --format=JobIDRaw,JobName,State,ExitCode,Elapsed,Start,End,AllocCPUS,NodeList,TotalCPU']
 raw=subprocess.check_output(cmd,text=True);status={}
 fields=['job_id','name','state','exit','elapsed','start','end','allocated_cpus','nodes','total_cpu']
 for line in raw.splitlines():
  values=line.split('|');status[values[0]]=dict(zip(fields,values))
 for row in rows:row['slurm']=status.get(str(row.get('job_id')),{'state':'not returned'})
 data=dict(updated=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),scope='Only known Issue157 jobs, not all account jobs. Running is never PASS.',remote_root='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture',attempts=rows)
 (D/'EXECUTION_INDEX.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(known_attempts=len(rows),running=[r['job_id']for r in rows if r['slurm']['state']=='RUNNING'])))

if __name__=='__main__':main()
