from pathlib import Path
import hashlib,json
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-antenna-eco-v1')
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
m=json.loads((p/'manifest.json').read_text())
for n,h in m['source_sha256'].items():assert sha(Path(n))==h,n
d=p/'dry-edit-119966';r=json.loads((d/'receipt.json').read_text());assert r['passed'] and not r['accepted']
files=[q for q in p.iterdir() if q.is_file() and q.name!='package-frozen.json']
files += [d/n for n in ['receipt.json','inputs-before.sha256','inputs-after.sha256','antenna-insertions.tsv','selected-drivers.tsv','diode-readback.tsv']]
out={'frozen_trial_package':True,'accepted':False,'dry_edit_job':119966,'hook_sha256':sha(p/'hook.tcl'),'scope':'547 source-bound INPUT networks; copy-only structural edit validated; later candidate must rerun exact binding and all post-route gates.','files_sha256':{str(q):sha(q) for q in sorted(files)}}
(p/'package-frozen.json').write_text(json.dumps(out,indent=2)+'\n')
print(sha(p/'package-frozen.json'))
