"""Reapply the admitted CFJ parent abstract recipe to the new physical leaf.
Source recipe: project/experiments/cfj_leaf_base/physical.py lines 42-91.
"""
import sys,re,json,subprocess,hashlib
from pathlib import Path
from decimal import Decimal
role,arg=sys.argv[1:];c=Path(arg).resolve();out=c/'parent-abstract-v3';out.mkdir()
name='block_v2_g' if role=='G' else 'local_s_base'
old=Path('/public/home/yuzelu/project-circuit')/('issue250-c-native-frame-20261112-01' if role=='G' else 'issue250-f-native-frame-20261112-01')/(name+'.lef')
nickname='bv1_block_v2_g' if role=='G' else 'local_s_base'
gds=c/'qualification-v2/flow/results/nangate45'/nickname/'base/6_final.gds'
assert json.loads((c/'accepted-leaf.json').read_text())['passed']
def run(args,log):
 with (out/log).open('w') as f:subprocess.run(list(map(str,args)),cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
raw=out/(name+'-raw.lef')
tcl=out/'export.tcl';tcl.write_text(f'set_thread_count 8\nread_db {{{c}/candidate.odb}}\nwrite_abstract_lef -bloat_factor 0 {{{raw}}}\n')
run(['openroad','-no_init','-exit',tcl],'export.log')
def pins(text):return text.split('\n  PIN ',1)[-1].split('\n  OBS',1)[0]
assert pins(old.read_text())==pins(raw.read_text()),'Original accepted pin declarations changed'
head,marker,remainder=raw.read_text().partition('\n  OBS\n');assert marker
mw,mh=re.search(r'SIZE ([\d.]+) BY ([\d.]+)',head).groups()
sections=re.split(r'(?m)^(    LAYER \S+ ;\n)',remainder);assert not sections[0]
for i in range(1,len(sections),2):
 if re.fullmatch(r'    LAYER metal[1-6] ;\n',sections[i]):
  body=sections[i+1];footer=''
  if '\n  END' in body:body,tail=body.split('\n  END',1);footer='  END'+tail
  rects=re.findall(r'RECT\s+([\d. -]+) ;',body)
  assert len(rects)==sum(bool(line.strip()) for line in body.splitlines())
  x0,y0,x1,y1=zip(*(map(Decimal,rect.split()) for rect in rects))
  sections[i+1]=f'     RECT {min(min(x0),0)} {min(min(y0),0)} {max(max(x1),Decimal(mw))} {max(max(y1),Decimal(mh))} ;\n'+footer
abstract=head+marker+''.join(sections)
cuts=out/(name+'-cuts.lefpart')
run(['klayout','-b','-rd',f'GDS={gds}','-rd',f'CUTS={cuts}','-r',Path(__file__).with_name('leaf_cut_obs.py')],'cuts.log')
body,end,footer=abstract.rpartition('  END\n');assert end and cuts.read_text().strip()
final=out/(name+'.lef');final.write_text(body+cuts.read_text()+end+footer)
assert pins(final.read_text())==pins(old.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'receipt.json').write_text(json.dumps(dict(passed=True,recipe='admitted CFJ zero-bloat exact upper metal + native GDS upper cut OBS; conservative lower M1-M6 covering rectangles',pins_exactly_unchanged=True,sha256={str(p):sha(p) for p in [c/'candidate.odb',gds,old,raw,final,cuts,tcl,Path(__file__).with_name('leaf_cut_obs.py')]}),indent=2))
