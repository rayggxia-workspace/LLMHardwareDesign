from pathlib import Path
import sys,json,hashlib,collections
dest=Path('.').resolve();p=dest.parent/'v410-bulk-final-readback-20261030-442';src=p.parent/'v410-bulk-clearance-20261030-435';before=p.parent/'v410-bulk-name-readback-20261030-440';sys.path.insert(0,str(src/'helpers'))
from native_escape_audit import geometry,connectivity,readback
from native_escape import records,parse,signature
mapping={bytes.fromhex(a).decode():bytes.fromhex(b).decode()for a,b in(line.split()for line in(before/'name-map.tsv').read_text().splitlines())}
case=json.loads((src/'bulk/plan.json').read_text());plans=case['nets'];assert set(plans)==set(mapping)
for row in plans.values():
 for k in ('original_paths','final_paths'):row[k]=[dict(v,points=[tuple(q)for q in v['points']])for v in row[k]]
bg=geometry(before/'before-geometry.tsv');ag=geometry(p/'after-geometry.tsv');assert set(bg)==set(ag)
for n,rows in bg.items():
 if n not in mapping.values():assert collections.Counter(rows)==collections.Counter(ag[n]),n
bc={n:connectivity(bg[a])for n,a in mapping.items()};ac={n:connectivity(ag[a])for n,a in mapping.items()}
audit=readback(src/'bulk/before.def',src/'bulk/after.def',plans);assert audit['passed']
seen=set()
for text in records(src/'bulk/before.def'):
 n=text.lstrip().split()[1]
 if n in plans:assert signature(parse(text)[1])==signature(plans[n]['original_paths']);seen.add(n)
assert seen==set(plans)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for c in iter(lambda:f.read(8388608),b''):h.update(c)
 return h.hexdigest()
assert sha(src/'bulk/before.v')==sha(src/'bulk/after.v')
base=p.parents[1];baseline=base/'block-v1-20261030-411/tasks/revision300-drc-v/native-whole-drc.rpt';original=collections.Counter(r.strip()for r in baseline.read_text().split('violation type: ')[1:]);now=collections.Counter(r.strip()for r in(src/'bulk/native-whole-drc.rpt').read_text().split('violation type: ')[1:]);assert sum(original.values())==487
result=dict(read_only=True,mapping=mapping,before=bc,after=ac,all_connected=all(v['passed']for v in bc.values())and all(v['passed']for v in ac.values()),full_def_readback=audit,netlist_unchanged=True,native_count=sum(now.values()),removed=list((original-now).elements()),added=list((now-original).elements()),physical_qualified=False,scope='Corrected actual native-name selection, fresh-process editedODB export, complete330net connectivity/fullDEF/netlist readback. Original435 failed and native253/add110 remain rejected; no new repair or qualification.')
files=[before/'before-geometry.tsv',before/'name-map.tsv',p/'after-geometry.tsv']+[src/'bulk'/n for n in ('before.def','after.def','before.v','after.v','probe.odb','native-whole-drc.rpt')]
result['files']={str(f.relative_to(base)):dict(bytes=f.stat().st_size,sha256=sha(f))for f in files};(dest/'readback.json').write_text(json.dumps(result,indent=2)+'\n')
