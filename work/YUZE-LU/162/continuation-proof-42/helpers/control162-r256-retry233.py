"""Retry two exact CTS failures, keeping the original acceptance chain."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-232';record=b/'route-selection-102/sready233-r256-hold-retry';assert not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=json.loads((source/'source-manifest.json').read_text());assert m['commit']=='a33a64215e860561f0e19f3002c49faac5e8db84'
rows=[]
def add(node,name,script,args,deps,out,memory):
 p=b/'dynamic-02'/('node'+str(node))/'pending'/(name+'.json');assert not p.exists()and not out.exists()
 spec=dict(script=script,source_root=str(source),forecast_gib=memory,requires=list(map(str,deps)),args=list(map(str,args))+['--out',str(out)])
 temp=p.with_suffix('.tmp');temp.write_text(json.dumps(spec));temp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
for old,number,node in [(2290,2330,7),(2293,2333,26)]:
 verified=b/'r256-native-229'/str(old)/'native';r=json.loads((verified/'receipt.json').read_text());assert not r['passed']and r['rtl_passed']and r['mapped']['passed']
 last=r['commands'][-1];assert last['returncode']==2 and 'do-cts'in last['command']
 log=verified/last['log'];assert sha(log)==last['sha256']and '[ERROR RSZ-0060] Max buffer count reached.'in log.read_text()
 root=b/'r256-native-233'/str(number);raw=root/'native';g=root/'gates'
 add(node,'00-a-sready233-native-'+str(number),'physical_only.py',['--source-root',source,'--verified',verified,'--failed-producer-hold-budget','--strong-output-drivers'],[],raw,48)
 common=['--producer',raw,'--source-root',source]
 add(node,'00-b-sready233-seal-'+str(number),'gates.py',['seal',*common],[raw/'receipt.json'],g/'sealed',16)
 for op,mem in [('physical',64),('drc',32),('function',32),('formal',64)]:
  deps=[g/'sealed/receipt.json']+([g/'function/receipt.json']if op=='formal'else[])
  add(node,'00-c-sready233-'+op+'-'+str(number),'gates.py',[op,*common,'--sealed',g/'sealed','--gates',g],deps,g/op,mem)
 add(node,'00-d-sready233-deliver-'+str(number),'gates.py',['deliver',*common,'--sealed',g/'sealed','--gates',g],[g/op/'receipt.json'for op in ['physical','drc','function','formal']],g/'deliver',32)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,source_commit=m['commit'],whole_system_qualified=False,scope='Exact failed CTS producer RTL/mapping reuse only; new full P&R with larger hold buffer implementation budget. Original 300MHz setup/hold/electrical/native DRC/final-cell three-initial/strict formal and delivery gates unchanged. Own existing eight nodes, dynamic independent sixteen-CPU slots and unchanged actual-memory admission.'),indent=2))
print(json.dumps(dict(queued=len(rows),record=str(record))))
'''
compile(q,'r256_retry233','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
