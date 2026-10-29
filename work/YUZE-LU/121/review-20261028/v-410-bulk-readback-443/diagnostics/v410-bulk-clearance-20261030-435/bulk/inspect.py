from pathlib import Path
import collections,hashlib,json,re,shutil,subprocess,sys
sys.path.insert(0,str(Path('..')/'helpers'))
from native_escape import parse,signature,path_length,emit,records
from native_escape_audit import readback,geometry,connectivity,physical
case=json.loads(Path('plan.json').read_bytes());plans=case['nets']
for row in plans.values():
 for k in ('original_paths','final_paths'):row[k]=[dict(p,points=[tuple(v)for v in p['points']])for p in row[k]]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for c in iter(lambda:f.read(8388608),b''):h.update(c)
 return h.hexdigest()
audit=readback(Path('before.def'),Path('after.def'),plans);assert audit['passed']
assert sha(Path('before.v'))==sha(Path('after.v'))
assert sha(Path('patch.def'))==case['patch_sha256']
seen=set()
for old in records(Path('before.def')):
 n=old.lstrip().split()[1]
 if n in plans:assert signature(parse(old)[1])==signature(plans[n]['original_paths']);seen.add(n)
assert seen==set(plans)
bg=geometry(Path('before-geometry.tsv'));ag=geometry(Path('after-geometry.tsv'));assert set(bg)==set(ag)
for name,rows in bg.items():
 if name not in case['actual_names'].values():assert collections.Counter(rows)==collections.Counter(ag[name]),name
bc={n:connectivity(bg[case['actual_names'][n]])for n in plans};ac={n:connectivity(ag[case['actual_names'][n]])for n in plans}
assert all(v['passed']for v in bc.values())and all(v['passed']for v in ac.values())
upper=None
with Path('def-diff.txt').open('w')as f:r=subprocess.run(['diff','-u','before.def','after.def'],stdout=f);assert r.returncode in (0,1)
assert Path('def-diff.txt').stat().st_size<3000000
tech=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef');shutil.copyfile(str(tech),'native.tech.lef')
files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))for p in Path('.').iterdir()if p.name in ('before.def','after.def','before.v','after.v','probe.odb','before-geometry.tsv','after-geometry.tsv','native-whole-drc.rpt','native.tech.lef')}
types=dict(collections.Counter(s.splitlines()[0]for s in Path('native-whole-drc.rpt').read_text().split('violation type: ')[1:]))
Path('probe-result.json').write_text(json.dumps(dict(passed=True,diagnostic_only=True,readback=audit,netlist_unchanged=True,before_connectivity=bc,after_connectivity=ac,after_upper_audit=upper,files=files,native_types=types,native_violations=sum(types.values()),physical_qualified=False,scope='Bulk deterministic330net local prefreeze proposals; all untouched nets/nonNETS geometry and exact endpoint multiset retained; via changes limited to explicit plans; actual native DRC result is diagnostic. RCX/STA/full GDS/function/LEC remain required for any adoption.'),indent=2)+'\n')
