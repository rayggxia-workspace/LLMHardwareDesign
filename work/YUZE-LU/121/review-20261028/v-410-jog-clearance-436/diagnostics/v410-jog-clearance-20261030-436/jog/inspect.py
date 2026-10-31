from pathlib import Path
import collections,hashlib,json,re,shutil,subprocess,sys
sys.path.insert(0,str(Path('..')/'helpers'))
from native_escape import parse,signature,path_length,emit,records
from native_escape_audit import readback,geometry,connectivity,physical
case=json.loads(Path('plan.json').read_bytes());case['final_paths']=[dict(p,points=[tuple(v)for v in p['points']])for p in case['final_paths']]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for c in iter(lambda:f.read(8388608),b''):h.update(c)
 return h.hexdigest()
audit=readback(Path('before.def'),Path('after.def'),{case['net']:case});assert audit['passed']
assert sha(Path('before.v'))==sha(Path('after.v'))
old=next(t for t in records(Path('before.def'))if t.lstrip().split()[1]==case['net']);assert sha(Path('patch.def'))==case['patch_sha256']
assert signature(parse(old)[1])==signature([dict(p,points=[tuple(v)for v in p['points']])for p in case['original_paths']])
bg=geometry(Path('before-geometry.tsv'));ag=geometry(Path('after-geometry.tsv'));assert set(bg)==set(ag)
for name,rows in bg.items():
 if name!=case['net']:assert collections.Counter(rows)==collections.Counter(ag[name]),name
bc=connectivity(bg[case['net']]);ac=connectivity(ag[case['net']]);assert bc['passed']and ac['passed']
upper=physical(ag,[case['net']])if case['layer']=='metal9'else None
with Path('def-diff.txt').open('w')as f:r=subprocess.run(['diff','-u','before.def','after.def'],stdout=f);assert r.returncode in (0,1)
assert Path('def-diff.txt').stat().st_size<30000
tech=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef');shutil.copyfile(str(tech),'native.tech.lef')
files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))for p in Path('.').iterdir()if p.name in ('before.def','after.def','before.v','after.v','probe.odb','before-geometry.tsv','after-geometry.tsv','native-whole-drc.rpt','native.tech.lef')}
types=dict(collections.Counter(s.splitlines()[0]for s in Path('native-whole-drc.rpt').read_text().split('violation type: ')[1:]))
Path('probe-result.json').write_text(json.dumps(dict(passed=True,diagnostic_only=True,readback=audit,netlist_unchanged=True,before_connectivity=bc,after_connectivity=ac,after_upper_audit=upper,files=files,native_types=types,native_violations=sum(types.values()),physical_qualified=False,scope='One via2_5 moved140nm along its existingM2 leg and M3 jog added. All M1 anchors and all other nets/nonNETS geometry, exact endpoint multiset and via types/count retained; actual native DRC result is diagnostic. RCX/STA/full GDS/function/LEC remain required for any adoption.'),indent=2)+'\n')
