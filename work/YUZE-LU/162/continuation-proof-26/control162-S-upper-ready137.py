import ast,subprocess,shlex
from pathlib import Path
t=ast.parse(Path(r'D:\Data\电路实验\control162-S-upper-ready121.py').read_text())
q=next(ast.literal_eval(n.value)for n in t.body if isinstance(n,ast.Assign)and any(isinstance(a,ast.Name)and a.id=='q'for a in n.targets))
q=q.replace('1182','1350').replace('source-121','source-137').replace('source121','source137')
q=q.replace('s-internal-qualified-02','s-escape-qualified-03').replace('s-internal-composition-01','s-escape-composition-03')
for i in range(4):q=q.replace(str(1230+i),str(1380+i))
q=q.replace("base/'topology/receipt.json'","base/'topology-audit/receipt.json'")
q=q.replace("assert g['passed']and g['S_external_link_instances']==0", "audit_path=base/'topology-audit/topology-audit.json';audit=json.loads(audit_path.read_text());ar=json.loads((audit_path.parent/'receipt.json').read_text());digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()\nassert ar['operation']=='topology-replay-audit'and ar['all_logic_fields_replayed']and ar['outputs']['topology-audit.json']==digest(audit_path)\nassert audit['passed']and all(audit['checks'].values())and audit['original_graph_sha256']==digest(signal)and audit['physical_manifest_sha256']==digest(manifest)\nassert ar['inputs'][str(signal)]==digest(signal)and ar['inputs'][str(manifest)]==digest(manifest)\nassert g['passed']and g['S_external_link_instances']==0")

old_queue="queue=b/('dynamic-04/node25'if node==25 else'dynamic-02/node26')/'pending'"
assert old_queue in q
q=q.replace(old_queue,"assert node in (2,4)\n queue=b/('dynamic-05/node'+str(node))/'pending'")
old_loop='for seed,node,weight in [(1380,25,1),(1381,26,4),(1382,25,8),(1383,26,16)]:'
assert old_loop in q
q=q.replace(old_loop,'for seed,node,weight in [(1380,4,1),(1381,2,4),(1382,4,8),(1383,2,16)]:')
q=q.replace(';assert not record.exists()',"\nif record.exists():print('Already appended:',record);raise SystemExit(0)")
compile(q,'same-S-actual-parallel-PG-upper','exec')
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
