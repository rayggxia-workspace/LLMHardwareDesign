import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-139';index=b/'route-selection-102/s-ready-predict139.json';assert not index.exists();rows=[]
def add(node,name,script,args,deps,out,memory):
 f=b/('dynamic-05/node'+str(node))/'pending'/(name+'.json');assert not f.exists()and not out.exists()
 spec=dict(script=script,source_root=str(source),forecast_gib=memory,requires=list(map(str,deps)),args=list(map(str,args+['--out',out])));tmp=f.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(f);rows.append(dict(path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),spec=spec))
pre=b/'s-ready-predict-01/rtl'
add(2,'00-a-s-ready139-rtl','run.py',['--model','adapter_s','--verify-only'],[],pre,16)
for number,density,node in [(1390,'0.42',2),(1391,'0.45',4)]:
 raw=b/'s-ready-predict-01'/('candidate-'+str(number));g=b/'s-ready-gates-01'/str(number)
 add(node,'00-b-s-ready139-physical-'+str(number),'run.py',['--model','adapter_s','--physical','--strong-output-drivers','--placement-density',density],[pre/'receipt.json'],raw,64)
 common=['--producer',raw,'--source-root',source]
 add(node,'00-c-s-ready139-seal-'+str(number),'gates.py',['seal',*common],[raw/'receipt.json'],g/'sealed',32)
 for op,mem in [('physical',64),('drc',32),('function',32),('formal',64)]:
  deps=[g/'sealed/receipt.json']+([g/'function/receipt.json']if op=='formal'else[])
  add(node,'00-d-s-ready139-'+op+'-'+str(number),'gates.py',[op,*common,'--sealed',g/'sealed','--gates',g],deps,g/op,mem)
 add(node,'00-e-s-ready139-deliver-'+str(number),'gates.py',['deliver',*common,'--sealed',g/'sealed','--gates',g],[g/op/'receipt.json'for op in ['physical','drc','function','formal']],g/'deliver',32)
index.write_text(json.dumps(dict(time=time.time(),tasks=rows,source_commit='c2ca8b00b3c701d196d8307aee6c45e9d43eb0c3',scope='Actual S adapter two readiness state bits; all original S files/other blocks unchanged; complete independent gates and composition requalification required.'),indent=2));print('Appended',len(rows),'tasks',index)
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
