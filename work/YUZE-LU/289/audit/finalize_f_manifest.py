from pathlib import Path
import json,hashlib
f=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4');release=f/'release';p=release/'accepted-parent.json';r=json.loads(p.read_text());r.update(corner='Nangate45 TT',clock_uncertainty_ns=0.1,clock_transition_ns=0.05,hold_margin_ps=r['hold_worst_ns']*1000,scope='Standalone F block with accepted S X8 at Nangate45 TT, nominal300MHz, original0.1ns uncertainty; no PVT robustness or A/B top RC acceptance claim')
p.write_text(json.dumps(r,indent=2)+'\n');(f/'accepted-parent.json').write_text(p.read_text())
manifest={Path(k).name:v for k,v in r['hashes'].items()};manifest[p.name]=hashlib.sha256(p.read_bytes()).hexdigest();(release/'manifest.sha256').write_text(''.join(v+'  '+k+'\n' for k,v in sorted(manifest.items())))
print(manifest[p.name])
