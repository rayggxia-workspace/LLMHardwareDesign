from pathlib import Path
import ast,subprocess,sys,json,hashlib,re
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control'); rel='project/experiments/control_v1/'; sys.path.insert(0,str(r/rel))
from openroad_router_probe import landing_markers
old=subprocess.check_output(['git','show','HEAD:'+rel+'openroad_router_probe.py'],cwd=r).decode()
expr=[n.args[0] for n in ast.walk(ast.parse(old)) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='marker_lef' and n.func.attr=='write_text']; assert len(expr)==1
legacy=eval(compile(ast.Expression(expr[0]),'<legacy committed marker expression>','eval'))
assert legacy==landing_markers(False)
s=landing_markers(True); assert s.count('MACRO ')==4 and s.count(' LAYER via11 ;')==2
for direction in ('input','output'):
 for parity in ('even','odd'):
  name='search_landing_'+direction+'_'+parity
  part=s.split('MACRO '+name+'\n')[1].split('END '+name+'\n')[0]
  assert 'SIZE 2 BY 2' in part and 'RECT 0 0 2 2' in part
  assert ('RECT 0.9995 0.9995 1.0005 1.0005' in part)==(parity=='odd')
from decimal import Decimal
for x,y in [(8,9),(9,8),(0,1),(1000,999),(2344,2343)]:
 assert (x+y)%2==1
 for center in (190+8000*x,140+8000*y):
  assert [center-2000+int(Decimal(v)*2000) for v in ('0.9995','1.0005')]==[center-1,center+1]
root=r.parent.parent/'control162-local1638'; assert not root.exists(); root.mkdir()
cases=[[],['--router','openroad','--reuse-placement','none','--openroad-snapshot-config','none'],['--router','openroad','--reuse-placement','none','--cap-lower-bound-only'],['--plan-only']]
rows=[]
for i,args in enumerate(cases):
 out=root/str(i);cmd=[sys.executable,str(r/rel/'system_upper.py'),'--manifest','none','--graph','none','--out',str(out),'--openroad-parity-aware-markers']+args
 p=subprocess.run(cmd,cwd=r,capture_output=True,text=True)
 assert p.returncode!=0 and 'Parity markers require' in p.stderr and not out.exists(),p.stderr
 rows.append(dict(args=args,rejected=True,stderr=p.stderr))
for f in ('openroad_router_probe.py','system_upper.py'):compile((r/rel/f).read_bytes(),f,'exec')
(root/'receipt.json').write_text(json.dumps(dict(passed=True,legacy_lef_byteexact=True,new_masters=4,odd_obstructions=2,duplicate_global_keepout_exact=True,negative_contexts=rows,whole_system_qualified=False,scope='Local source/legacy compatibility/context verification only; actual 5-case EDA preflight not yet executed.'),indent=2))
print(json.dumps(dict(passed=True,legacy_byteexact=True,negative_contexts=len(rows),out=str(root))))
