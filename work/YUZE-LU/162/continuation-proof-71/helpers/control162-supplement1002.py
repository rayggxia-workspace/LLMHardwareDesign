from pathlib import Path
import subprocess,shlex,json,hashlib,base64,time
h=Path(__file__).parent;r=h/'LLMHardwareDesign-worktrees/issue-162-control';out=r/'work/YUZE-LU/162/continuation-proof-71';d=json.loads((out/'index.json').read_text(encoding='utf-8'))
q='''from pathlib import Path
import json,hashlib,base64
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');rows=[]
for name in ['r256-native-warm-active-pool-audit-999','r256-native-warm-variant-audit-1001']:
 p=b/name/'receipt.json';raw=p.read_bytes();assert json.loads(raw)['passed'];rows.append(dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),copied=True,base64=base64.b64encode(raw).decode()))
print(json.dumps(rows))
'''
rows=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]))
for row in rows:
 assert not any(x['relative']==row['relative']for x in d['rows']);raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True);p.write_bytes(raw);d['rows'].append(row)
items={}
for n in [996,997,998,999,1000,1001,1002]:
 for p in h.glob('control162-*'+str(n)+'.py'):items['helpers/'+p.name]=p
fs=sorted((h/'control162-progress997').glob('*.json'));items['live-snapshots/control162-progress997/'+fs[-1].name]=fs[-1]
for name,p in items.items():
 assert not any(x['relative']==name for x in d['helpers']);raw=p.read_bytes();target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);d['helpers'].append(dict(relative=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
d['supplement1002']=dict(time=time.time(),actual_four_pools_children=64,second_pools_receipts=[x['relative']for x in rows],scope='999 structured32actual-child/prefix/body/CPU/admission checks passed;1001 corrects copied999 scope prose to actualnode2/4,9920/1,congestion8/32,160GiB forecasts/208GiB thresholds. Earlier989 node5/6 checks retained. No fullroute or system qualification inferred.')
(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
p=r/'work/YUZE-LU/162/continuation-checkpoint-71.md';s=p.read_text(encoding='utf-8');s+='\n补充1002：999实际另两组32子进程、导入前缀/body、16CPU互斥及准入通过；其复制的scope文字仍写9810/1，1001保留原件并核对结构化证据，澄清实际为node2/4的9920/1、拥塞8/32、160GiB预测/208GiB阈值。四组累计64真实子进程已查。1001最初本地脚本条件表达式缺空格，未创建远程结果；修正后实际通过。\n';p.write_text(s,encoding='utf-8');print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
