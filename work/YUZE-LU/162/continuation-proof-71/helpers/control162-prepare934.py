from pathlib import Path
import ast,json,subprocess,hashlib
h=Path(__file__).parent;repo=h/'LLMHardwareDesign-worktrees/issue-162-control';m=ast.parse((h/'control162-edit924.py').read_text(encoding='utf-8'));rules={}
for item in m.body:
 if isinstance(item,ast.Expr)and isinstance(item.value,ast.Call)and isinstance(item.value.func,ast.Name)and item.value.func.id=='edit':
  rules[ast.literal_eval(item.value.args[0])]=ast.literal_eval(item.value.args[1])
source=repo/'project/experiments/control_v1/system_upper.py';s=source.read_text(encoding='utf-8');a=s.index('        if a.native_refresh_regression_baseline:');z=s.index('        if a.native_prefix_snapshot_config:',a);dispatch=s[a:z]
for name,changes in rules.items():
 s=(repo/'project/experiments/control_v1'/name).read_text(encoding='utf-8')
 if name=='system_upper.py':assert s.count(dispatch)==1;s=s.replace(dispatch,'',1)
 for a,z in reversed(changes):assert s.count(z)==1,(name,z);s=s.replace(z,a,1)
 old=subprocess.check_output(['git','show','89cd9bbeb3ee01a6c277865ad33e733438e36c8d:project/experiments/control_v1/'+name],cwd=repo).decode()
 assert s==old,name
(h/'control162-backout934.json').write_bytes((json.dumps(dict(rules=rules,dispatch=dispatch),indent=2)+'\n').encode());print('all3 production sources exactly recover901 after removing only refresh additions')
