from pathlib import Path
import json,hashlib,subprocess,shlex,time,base64
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');out=repo/'work/YUZE-LU/162/block-delivery-r256-current298';assert not out.exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
q="from pathlib import Path;import json,base64;p=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-274');print(json.dumps({str(f.relative_to(p)):base64.b64encode(f.read_bytes()).decode()for f in [p/'selected/physical.json',p/'selected/receipt.json',p/'topology/boundary-graph.json',p/'topology/receipt.json']}))"
remote=json.loads(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40));out.mkdir();snap={}
for name,data in remote.items():
 raw=base64.b64decode(data);p=out/'remote-selection'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);snap[name]=dict(path=str(p.relative_to(repo)),sha256=sha(p))
m=json.loads(base64.b64decode(remote['selected/physical.json']));g=json.loads(base64.b64decode(remote['topology/boundary-graph.json']));assert g['instance_count']==345 and len(g['connections'])==11122
for n in ['selected/receipt.json','topology/receipt.json']:assert json.loads(base64.b64decode(remote[n]))['passed']
replacements={'control_c','control_route','control_s_arbiter','control_status','control_reset_distribution'};leaves={};inputs={};receipts={}
for key in ['ready140','r256-five260','r256-c285','r256-r296']:
 index=repo/('work/YUZE-LU/162/block-delivery-'+key+'/index.json');d=json.loads(index.read_text());inputs[str(index.relative_to(repo))]=sha(index)
 reception=repo/('work/YUZE-LU/162/block-local-reception-'+key+'/RECEPTION.json');r=json.loads(reception.read_text());assert r['passed']and r['all_archives_readback_passed'];receipts[str(reception.relative_to(repo))]=sha(reception)
 archives={v['top']:v for v in r['blocks']}
 for row in d['leaves']:
  top=row['top']
  if key=='ready140'and top in replacements:continue
  assert top not in leaves and top in archives
  assert row['final_files']==m['leaves'][top]['final_files'],top
  leaves[top]=dict(source_index=str(index.relative_to(repo)),six_files=row['final_files'],image=row['image'],local_archive=archives[top],qualified_individually=True,whole_system_qualified=False)
assert set(leaves)==set(m['leaves'])and len(leaves)==23
r=dict(passed=True,scope='Canonical current23 individually qualified types, exactly matched to actual final-PG scene274 selection. Individual local archive CRC/SHA receipts retained. All complete-system gates remain independently required.',whole_system_qualified=False,instance_count=345,logical_net_count=11122,link8_instances=316,source_indices=inputs,local_reception_receipts=receipts,actual_selection_snapshots=snap,leaves=leaves,captured_at=time.time())
(out/'index.json').write_bytes((json.dumps(r,indent=2)+'\n').encode());print('current types',len(leaves),'six files',len(leaves)*6,'all match actual selected PG scene; no system qualification')
