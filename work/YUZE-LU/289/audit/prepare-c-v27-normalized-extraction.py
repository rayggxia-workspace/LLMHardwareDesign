from pathlib import Path
import re,json
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-v27-rcx-normalization-v2';out=p/'reextract-encoder';out.mkdir(exist_ok=False);old=r/'audit/C-rcx-zero-normalization-v1/reextract-encoder'
for n in ('geometry-all.tcl','def-material.py'):(out/n).write_bytes((old/n).read_bytes())
code=(r/'audit/prepare-c-zero-encoder.py').read_text();a=code.index('receipt=json.loads');b=code.index("s=(old/'extract-consistency.tcl')");fragment=code[a:b].replace('audit/C-main-clock4-physical-v1/rcx-material-119977','audit/C-v27-physical/rcx-material-120031');exec(compile(fragment,'frozen_encoder_generator','exec'))
(out/'extract-consistency.tcl').write_text((old/'extract-consistency.tcl').read_text().replace('C-rcx-zero-normalization-v1','C-v27-rcx-normalization-v2'))
(out/'check-import.py').write_text('''from pathlib import Path
import re,json
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v27-rcx-normalization-v2');names=json.loads((p/'edit-receipt.json').read_text())['target_nets'];vals=[]
def signature(body):
 operations=[];prefix=None
 for m in re.finditer(r'(?:\\+ ROUTED|\\bNEW)\\s+(\\S+)\\s+(.*?)(?=\\bNEW|$)',body,re.S):
  if prefix is None:prefix=' '.join(body[:m.start()].split())
  layer,seq=m.groups();operations.append(('PATH',layer));prev=None
  for t in re.finditer(r'\\(\\s*(\\*|-?\\d+)\\s+(\\*|-?\\d+)(?:\\s+(-?\\d+))?\\s*\\)|(\\S+)',seq):
   x,y,e,v=t.groups()
   if x is not None:
    pt=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y));operations.append(('POINT',*pt,None if e is None else int(e)));prev=pt
   else:operations.append(('VIA_OR_TOKEN',v))
 return prefix,operations
for path in (p/'normalized.def',Path('before.def')):
 t=path.read_text();sec=re.search(r'\\nNETS\\s+\\d+\\s*;(.*?)\\nEND NETS',t,re.S)[1];b={m[1]:m[2] for m in re.finditer(r'^\\s*-\\s+(\\S+)\\s+(.*?);\\s*$',sec,re.M|re.S)};vals.append({n:signature(b[n]) for n in names})
assert vals[0]==vals[1], 'Actual imported route operations differ from proven normalized source'
Path('import-target-encoding.json').write_text(json.dumps(dict(passed=True,targets=names,exact_semantic_route_operations=True,only_absolute_vs_star_coordinate_spelling_normalized=True),indent=2))
''')
s=(r/'audit/C-rcx-zero-normalization-v1/reextract-encoder.sbatch').read_text().replace('C-rcx-zero-normalization-v1','C-v27-rcx-normalization-v2').replace('C-v20-native-clock4','C-v27-joint-e20-h30').replace(' "$r/audit/C-v27-rcx-normalization-v2/two-net-only.def"','');(p/'reextract.sbatch').write_text(s)
