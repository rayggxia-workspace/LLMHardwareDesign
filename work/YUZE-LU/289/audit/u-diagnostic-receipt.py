import sys,json,hashlib,xml.etree.ElementTree as E,collections
from pathlib import Path
c=Path(sys.argv[1]);res=c/'flow/results/nangate45/u-overlay-current/base';o=dict(accepted=False,scope='Focused antenna and upper spacing diagnostics; full unchanged foundry deck and final fresh STA still required',gds_sha256=hashlib.sha256((res/'6_final.gds').read_bytes()).hexdigest())
for name in ('antenna-diagnostic','upper-diagnostic'):
 p=c/(name+'.lyrdb')
 if p.exists():
  rows=E.parse(str(p)).findall('.//items/item');counts=collections.Counter(i.findtext('category') for i in rows)
  o[name]=dict(items=len(rows),categories=dict(counts),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),markers=[dict(category=i.findtext('category'),cell=i.findtext('cell'),values=[v.text for v in i.findall('values/value')]) for i in rows])
(c/'diagnostic-receipt.json').write_text(json.dumps(o,indent=2));print(json.dumps(o,indent=2))
