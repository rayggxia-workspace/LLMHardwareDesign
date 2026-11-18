import sys
from pathlib import Path
sys.path.insert(0,'/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit');from compare_lef import parse
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs/candidate-S-minimal-localv4/parent-abstract-v3/local_s_base.lef');d=parse(p)
for name,boxes in d['pins'].items():
 for layer,x0,y0,x1,y1 in boxes:
  if layer=='metal10' and x0<1743500 and x1>1743390 and ((y0<413740 and y1>408140) or(y0<70140 and y1>69740)):print(name,[x0,y0,x1,y1])
