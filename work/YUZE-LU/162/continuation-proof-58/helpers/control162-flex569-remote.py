from pathlib import Path
import subprocess,json,re,time,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'route-selection-102/sready569-pending-c96-flexibility';assert not out.exists();out.mkdir();r=dict(passed=False,time=time.time(),whole_system_qualified=False,documentation='https://slurm.schedmd.com/scontrol.html')
def job():return subprocess.check_output(['scontrol','show','job','96222','-o'],universal_newlines=True)
def fields(s):return dict(x.split('=',1)for x in s.split()if'='in x)
try:
 before=job();r['before']=before;f=fields(before);assert f['JobId']=='96222'and f['UserId']=='yuzelu(10011)'and f['JobName']=='yzl-ctl162-rec237n26'and f['JobState']=='PENDING'and f['Partition']=='c96'and f['NumNodes']=='1'and f['NumCPUs']=='96'and f['ReqNodeList']=='node26'
 queue=b/'dynamic-06/node26';assert f['Command']==str(queue/'batch.sh')and not(queue/'queue-state.json').exists();r['batch_sha256']=hashlib.sha256((queue/'batch.sh').read_bytes()).hexdigest();assert '#SBATCH --nodelist'not in(queue/'batch.sh').read_text()
 partition=subprocess.check_output(['scontrol','show','partition','c96','-o'],universal_newlines=True);nodes=re.search(r'(?:^| )Nodes=([^ ]+)',partition).group(1);expanded=subprocess.check_output(['scontrol','show','hostnames',nodes],universal_newlines=True).split();assert set(expanded)<=set('node'+str(i)for i in range(13,27))and expanded;r['allowed_partition_nodes']=expanded;r['partition_before']=partition
 own=subprocess.check_output(['squeue','-u','yuzelu','-h','-o','%i|%j'],universal_newlines=True).splitlines();own=[x for x in own if'|yzl-ctl162-'in x];assert len(own)<=8 and any(x.startswith('96222|')for x in own);r['own_issue162_parent_jobs_before']=own
 tasks=json.loads((b/'route-selection-102/sready549-s-local-direction-cost-grid/tasks.json').read_text())['tasks'];assert len(tasks)==42
 for t in tasks:assert hashlib.sha256(Path(t['path']).read_bytes()).hexdigest()==t['sha256']
 command=['scontrol','update','JobId=96222','ReqNodeList='];r['command']=command;result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True);r['returncode']=result.returncode;r['stdout']=result.stdout;assert result.returncode==0
 after=job();r['after']=after;g=fields(after);assert g['ReqNodeList']=='(null)'
 for k in ['JobId','UserId','JobName','Partition','NumNodes','NumCPUs','Command','WorkDir','StdOut']:assert f[k]==g[k]
 r.update(passed=True,scope='Only remove own pending eighth96CPU job96222 artificial node26 pin, after verifying owner/name/state/exact batch path, unchanged42 candidate task SHA, <=8 own parent jobs and c96 partition contains only allowed node13..26. Keep same job ID, 96CPUs/one exclusive node, queue6x16, memory admission, software/physical sources and all tasks unchanged. No cancellation, new allocation, priority/admin/partition change or foreign/R operation. Scheduler may choose next available allowed c96; existing directory dynamic-06/node26 is a logical queue label, actual allocated hostname must be read from job/launch evidence. Documentation explicitly supports clearing own pending ReqNodeList with blank value. No execution/speed/physical qualification inferred.')
finally:(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=r['passed'],job=96222,state=g['JobState'],required_nodes=g['ReqNodeList'],cpus=g['NumCPUs'],new_jobs=0)))
