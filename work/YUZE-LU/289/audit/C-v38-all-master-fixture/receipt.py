from pathlib import Path
import json,hashlib,xml.etree.ElementTree as ET,collections
p=Path.cwd();report=p/'full.lyrdb';root=ET.parse(report).getroot()
markers=[dict(category=x.findtext('category'),cell=x.findtext('cell'),values=[v.text for v in x.findall('values/value')]) for x in root.findall('.//items/item')]
binding=json.loads((p/'export-binding.json').read_text())
result=dict(passed=not markers,scope='Isolated library fixture only. Does not qualify final C placement, routing, timing, antenna or full merged GDS.',masters=binding['masters'],count=len(markers),by_category=dict(collections.Counter(x['category'] for x in markers)),markers=markers,files_sha256={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [p/'export-binding.json',p/'fixture.gds',report,p/'inputs-before.sha256',p/'inputs-after-check.txt',p/'deck-identity.txt',p/'export.py',p/'receipt.py',p/'run.sbatch']})
(p/'receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
