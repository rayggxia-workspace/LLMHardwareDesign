from pathlib import Path
import sys,json,hashlib
out=Path(sys.argv[1]).resolve();p=out/'original-geometry.tsv';q=out/'final-geometry.tsv'
def parts(p):
 allrows=set(p.read_text().splitlines());pg={s for s in allrows if s.startswith(('PIN\tVDD\t','PIN\tVSS\t'))};return allrows-pg,pg
a,ap=parts(p);b,bp=parts(q);assert a==b,('Signal/die/macro geometry changed',a-b,b-a)
r=dict(passed=True,signal_die_macro_exact=True,power_rectangles_removed=sorted(ap-bp),power_rectangles_added=sorted(bp-ap),scope='PG BPin changes are explicit and require separate actual connectivity/full-GDS checks',hashes={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in (p,q)})
(out/'geometry-receipt.json').write_text(json.dumps(r,indent=2));print('signal/macro exact; PG rectangles removed',len(ap-bp),'added',len(bp-ap))
