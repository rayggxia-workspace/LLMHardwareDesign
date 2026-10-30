from pathlib import Path
import sys,json,hashlib,collections
p=Path('.');src=p.parent/'v410-bulk-clearance-20261030-435';sys.path.insert(0,str(src/'helpers'))
from native_escape_audit import geometry,connectivity
mapping={bytes.fromhex(a).decode():bytes.fromhex(b).decode()for a,b in(line.split()for line in(p/'name-map.tsv').read_text().splitlines())}
bg=geometry(p/'before-geometry.tsv');ag=geometry(p/'after-geometry.tsv');assert set(bg)==set(ag)
for n,rows in bg.items():
 if n not in mapping.values():assert collections.Counter(rows)==collections.Counter(ag[n]),n
before={n:connectivity(bg[a])for n,a in mapping.items()};after={n:connectivity(ag[a])for n,a in mapping.items()}
result=dict(read_only=True,mapping=mapping,before=before,after=after,all_connected=all(v['passed']for v in before.values())and all(v['passed']for v in after.values()),scope='Geometry selection corrected using actual native names. Original435 failed and fullnative253/add110 remain rejected. No reroute or finalqualification.')
result['files']={n:dict(bytes=(p/n).stat().st_size,sha256=hashlib.sha256((p/n).read_bytes()).hexdigest())for n in ('before-geometry.tsv','after-geometry.tsv','name-map.tsv')}
(p/'readback.json').write_text(json.dumps(result,indent=2)+'\n')
