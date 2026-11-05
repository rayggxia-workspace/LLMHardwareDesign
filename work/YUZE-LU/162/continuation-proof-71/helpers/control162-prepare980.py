from pathlib import Path
import ast,json,subprocess
h=Path(__file__).parent;repo=h/'LLMHardwareDesign-worktrees/issue-162-control';m=ast.parse((h/'control162-edit968.py').read_text(encoding='utf-8'));rules={}
for item in m.body:
 if isinstance(item,ast.Expr)and isinstance(item.value,ast.Call)and isinstance(item.value.func,ast.Name)and item.value.func.id=='edit':rules[ast.literal_eval(item.value.args[0])]=ast.literal_eval(item.value.args[1])
rules['tree_router_cpp.py'].append(('        resource_search_header_sha256=sha(source.with_name("resource_search.h")),','        native_prefix_seed_header_sha256=sha(source.with_name("native_prefix_seed.h")),\n        resource_search_header_sha256=sha(source.with_name("resource_search.h")),'))
rules['system_upper.py'].append(("            header=Path(__file__).with_name('resource_search.h');receipt['inputs'][str(header)]=sha(header)","            header=Path(__file__).with_name('resource_search.h');receipt['inputs'][str(header)]=sha(header)\n            header=Path(__file__).with_name('native_prefix_seed.h');receipt['inputs'][str(header)]=sha(header)"))
rules['system_upper.py'].append(("    p.add_argument('--pin-release-regression-config',type=Path)","    p.add_argument('--pin-release-regression-config',type=Path)\n    p.add_argument('--native-warm-regression-config',type=Path)"))
s=(repo/'project/experiments/control_v1/system_upper.py').read_text(encoding='utf-8');a=s.index('        if a.native_warm_regression_config:');z=s.index('        if a.pin_release_regression_config:',a);dispatch=s[a:z]
for name,changes in rules.items():
 s=(repo/'project/experiments/control_v1'/name).read_text(encoding='utf-8')
 if name=='system_upper.py':s=s.replace(dispatch,'',1)
 for a,z in reversed(changes):assert s.count(z)==1,(name,z);s=s.replace(z,a,1)
 old=subprocess.check_output(['git','show','4d526c6d0297e199f60ec564b79c24ad5b148917:project/experiments/control_v1/'+name],cwd=repo).decode();assert s==old,name
(h/'control162-backout980.json').write_text(json.dumps(dict(rules=rules,dispatch=dispatch),indent=2),encoding='utf-8');print('all3 production files exact recover947')
