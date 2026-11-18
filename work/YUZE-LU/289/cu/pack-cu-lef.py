"""Create a conservative CU parent abstract from accepted same-source artifacts.
Preserves raw exported pins; exact upper metal plus actual hierarchical GDS cut OBS.
Independent reimport/geometry validation is required before release.
"""
from pathlib import Path
from decimal import Decimal
import hashlib,json,re,subprocess,sys
raw,gds,output=map(Path,sys.argv[1:])
assert raw.is_file() and gds.is_file() and not output.exists()
head,mark,rest=raw.read_text().partition('\n  OBS\n')
assert mark
width,height=map(Decimal,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',head).groups())
sections=re.split(r'(?m)^(    LAYER \S+ ;\n)',rest)
assert not sections[0]
for i in range(1,len(sections),2):
 if re.fullmatch(r'    LAYER metal[1-6] ;\n',sections[i]):
  body=sections[i+1];footer=''
  if '\n  END' in body:body,tail=body.split('\n  END',1);footer='  END'+tail
  rects=re.findall(r'RECT\s+([\d. -]+) ;',body)
  assert len(rects)==sum(bool(line.strip()) for line in body.splitlines())
  x0,y0,x1,y1=zip(*(map(Decimal,rect.split()) for rect in rects))
  sections[i+1]=f'     RECT {min(min(x0),0)} {min(min(y0),0)} {max(max(x1),width)} {max(max(y1),height)} ;\n'+footer
abstract=head+mark+''.join(sections)
helper=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs/leaf_cut_obs.py')
cuts=output.with_suffix('.cuts.lefpart')
with output.with_suffix('.cuts.log').open('w') as log:
 subprocess.run(['klayout','-b','-rd',f'GDS={gds}','-rd',f'CUTS={cuts}','-r',str(helper)],stdout=log,stderr=subprocess.STDOUT,check=True)
body,end,footer=abstract.rpartition('  END\n')
assert end and cuts.read_text().strip()
output.write_text(body+cuts.read_text()+end+footer)
def pins(s):return s.split('\n  PIN ',1)[-1].split('\n  OBS',1)[0]
assert pins(raw.read_text())==pins(output.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
output.with_suffix('.binding.json').write_text(json.dumps(dict(independent_reimport_required=True,pins_text_exact=True,sha256={str(p):sha(p) for p in [raw,gds,output,cuts,helper,Path(__file__)]}),indent=2))