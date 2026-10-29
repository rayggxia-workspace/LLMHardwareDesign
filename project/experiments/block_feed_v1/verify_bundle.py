import argparse,contextlib,hashlib,json,tarfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();root=a.folder
index=json.loads((root/'bundle.json').read_text())
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(2**20),b''):h.update(block)
 return h.hexdigest()
archive=root/Path(index['archive']['path']).name
assert index['passed'] and index['native_leaf_accepted']
assert archive.stat().st_size==index['archive']['bytes'] and sha(archive)==index['archive']['sha256']
out=root/'unpacked';fresh=not out.exists()
if fresh:out.mkdir(exist_ok=False)
assert out.is_dir()
with tarfile.open(archive,'r:gz') as stream:
 seen=set()
 for member in stream:
  name=member.name
  assert name in index['members'] and name not in seen and member.isfile() and not member.issym() and not member.islnk()
  assert not Path(name).is_absolute() and '..' not in Path(name).parts
  target=out/name
  if fresh:target.parent.mkdir(parents=True,exist_ok=True)
  assert out.resolve() in target.resolve().parents and not target.is_symlink()
  h=hashlib.sha256();count=0
  destination=target.open('wb') if fresh else contextlib.nullcontext()
  with stream.extractfile(member) as src,destination as dst:
   for block in iter(lambda:src.read(2**20),b''):
    if dst is not None:dst.write(block)
    h.update(block);count+=len(block)
  assert count==index['members'][name]['bytes']==member.size and h.hexdigest()==index['members'][name]['sha256']
  if not fresh:assert target.is_file() and target.stat().st_size==count and sha(target)==h.hexdigest()
  seen.add(name)
 assert seen==set(index['members'])
delivery=json.loads((out/'native/delivery.json').read_text());assert delivery['passed'] and delivery['native_leaf_accepted']
for name,row in delivery['final_files'].items():assert sha(out/'native'/name)==row['sha256']
reports={}
for op,row in delivery['gate_receipts'].items():
 receipt=out/'evidence'/op/'receipt.json';assert sha(receipt)==row['sha256']
 r=json.loads(receipt.read_text());assert r['passed']
 report=out/'evidence'/op/Path(row['report_path']).name;assert sha(report)==row['report_sha256']==r['outputs'][report.name]
 j=json.loads(report.read_text());assert j['passed'] and j['source_receipt_sha256']==delivery['source_receipt_sha256'];reports[op]=j
assert all(reports['physical']['checks'].values())
assert reports['drc']['full_deck']['total_items']==0 and not (out/'evidence/drc/native-whole-drc.rpt').read_bytes()
assert len(reports['function']['initial_runs'])==3
assert all(reports['formal']['strict_native_lec']['checks'].values()) and reports['formal']['strict_native_lec']['passed']
assert reports['formal']['function_receipt_sha256']==sha(out/'evidence/function/receipt.json')
r=dict(passed=True,archive_sha256=sha(archive),verified_members=len(seen),macro=delivery['macro'],native_leaf_accepted=True,final_files={name:sha(out/'native'/name) for name in delivery['final_files']},scope='Verified downloaded bytes and exact all-gate receipts; original files unchanged.')
(root/'received.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
