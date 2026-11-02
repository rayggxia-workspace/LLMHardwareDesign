import ast,subprocess,shlex
from pathlib import Path
original=ast.literal_eval(ast.parse(Path(r'D:\Data\电路实验\control162-ready-upper140.py').read_text()).body[1].value)
tail=original[original.index("regression=b/"):]
tail=tail.replace('assert node in (2,4,25)','assert node in (2,3,4,6)')
tail=tail.replace("(('dynamic-04/'if node==25 else'dynamic-05/')+'node'+str(node))","(('dynamic-05/'if node in (2,4)else'dynamic-02/')+'node'+str(node))")
tail=tail.replace("for seed,node,weight in [(1410,2,1),(1411,4,4),(1412,25,8),(1413,25,16)]:", "for seed,node,weight,chosen in options:\n required=required_base+[chosen/'receipt.json']")
tail=tail.replace("selected_placement=str(chosen)","selected_placements=[str(p)for _,_,_,p in options]")
tail=tail.replace("Four independent routes and24 downstream gates", "Four independent lower-density alternative routes and24 downstream gates")
head=r'''from pathlib import Path
import hashlib,json,os,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-140';base=b/'s-ready-composition-01/1391';record=b/'route-selection-102/s-ready-capacity-upper-source140.json'
if record.exists():print('Already appended:',record);raise SystemExit(0)
residual=base/'capacity-native-residual-01';rr=residual/'receipt.json'
if not rr.exists():print('Actual residual gate not yet complete');raise SystemExit(0)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=json.loads(rr.read_text());assert r['passed']and r['outputs']['native-cap-residual.json']==sha(residual/'native-cap-residual.json')
d=json.loads((residual/'native-cap-residual.json').read_text());valid={int(Path(row['placement']).name):Path(row['placement'])for row in d['placements']if not any(row['violations'].values())}
print('Actual residual clear candidates',sorted(valid))
assert valid
selected=1391;manifest=base/'selected/physical.json';signal=base/'topology/boundary-graph.json';g=json.loads(signal.read_text());m=json.loads(manifest.read_text())
assert g['passed']and len(g['instances'])==235 and g['S_external_link_instances']==0 and g['S_internal_drive']['all_four_gates_fresh']
required_base=[b/'s-ready-qualified-01/1391/pg-delivery/receipt.json',base/'selected/receipt.json',base/'topology/receipt.json',base/'native-sta/native-system-audit.json',rr]
assert all(json.loads(p.read_text())['passed']for p in required_base)
native=json.loads((base/'native-sta/receipt.json').read_text());assert native['execution_passed']and native['typed_native_timing_passed']and native['inputs'][str(signal)]==sha(signal)
tr=json.loads((base/'topology/receipt.json').read_text());assert tr['outputs']['boundary-graph.json']==sha(signal)and tr['inputs'][str(manifest)]==sha(manifest)
options=[(seed,node,1,valid[n])for seed,node,n in [(1430,2,1420),(1431,4,1421),(1432,3,1422),(1433,6,1424)]if n in valid]
required=required_base
'''
q=head+tail
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
