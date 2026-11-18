"""Read-only published release verification. This checks evidence and artifact identity, not a new EDA run.
Usage: python3 verify-AB-X8-final-release-v1.py [joint-index.json]
Run on allocated node for large file hashing; only Python stdlib required.
"""
from pathlib import Path
import hashlib,json,sys
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
index=Path(sys.argv[1]) if len(sys.argv)>1 else root/'audit/AB-X8-final-joint-release-index.json'
cache={}
def sha(p):
 p=Path(p)
 if p not in cache:
  h=hashlib.sha256()
  with p.open('rb') as f:
   for c in iter(lambda:f.read(4194304),b''):h.update(c)
  cache[p]=h.hexdigest()
 return cache[p]
def read(p):return json.loads(Path(p).read_text())
d=read(index);assert d['macro_block_backend_checks_accepted'];b=d['bindings']
for k,v in b.items():assert sha(v['path'])==v['sha256'],('Index binding changed',k)
C,U,F=[read(b[k]['path']) for k in ('C','U','F')];assert all(x['passed'] for x in (C,U,F))
assert C['accepted_by_checks'] and U['accepted_by_checks']
cm=read(b['C_manifest']['path']);assert cm['accepted_receipt_sha256']==sha(b['C']['path'])
for path,row in cm['files'].items():
 assert sha(path)==row['sha256'] and sha(row['source'])==row['sha256'],('C artifact changed',path)
for name,row in U['artifacts'].items():assert sha(row['path'])==row['sha256'],('U artifact changed',name)
for path,h in F['hashes'].items():
 if path.startswith('/OpenROAD-flow-scripts/'):
  assert Path(path).exists(), 'Use pinned ORFS container to verify platform hashes'
 assert sha(path)==h,('F evidence/artifact changed',path)
coverage=read(b['coverage_340']['path']);assert coverage['coverage_passed'] and coverage['counts']==d['selected_union_counts']
assert coverage['counts']=={'total':340,'A':306,'B':340,'C':153,'U':153,'G':33,'S':1}
assert len(coverage['rows'])==340 and len({r['driver'] for r in coverage['rows']})==340
for row in coverage['rows']:assert row['master']=='BUF_X8' and row['unique_driver_count']==1 and row['direction']=='OUTPUT'
for path,h in coverage['C_final_artifacts'].items():assert sha(path)==h
for k in ('G_leaf','S_leaf'):assert read(b[k]['path'])['passed']
rd=read(b['root_disposition']['path']);rv=read(b['root_verification']['path']);assert rd['approved'] and rv['verification_passed']
assert rd['verification_receipt_sha256']==sha(b['root_verification']['path']) and rd['verifier_script_sha256']==sha(b['root_verifier']['path'])
assert rd['full_report_sha256']==sha(rd['full_report'])
assert C['counts']=={'setup':0,'hold':0,'capacitance':0,'slew':0,'fanout':0} and min(C['setup_slack_ns'],C['hold_slack_ns'])>=0
assert C['full_deck_items']==0 and U['full_foundry_deck_items']==0 and F['full_deck_items']==0
print(json.dumps({'read_only_verification_passed':True,'files_hashed':len(cache),'selected_targets':coverage['counts'],'C_setup_ns':C['setup_slack_ns'],'C_hold_ns':C['hold_slack_ns'],'scope':'Published same-source macro/block evidence and artifact verification; no new STA/DRC or top RC simulation is performed.'},indent=2))
