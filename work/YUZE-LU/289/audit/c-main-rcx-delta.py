from pathlib import Path
import re,json
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-main-clock4-physical-v1/rcx-material-119977')
a=json.loads((p/'material/receipt.json').read_text())
for d in a['geometry_differences']:
 print('\nNET',d['net'])
 for side in ('before','after'):
  text=(p/(side+'.def')).read_text();m=re.search(r'^\s*-\s+'+re.escape(d['net'])+r'\s+(.*?);\s*$',text,re.M|re.S);assert m
  (p/(side+'-'+str(a['geometry_differences'].index(d))+'.defpart')).write_text(m[0])
  print(side)
  for row in m[0].splitlines():
   if 'metal10' in row or any(s in row for s in ('325','1436','253','1145')):print(row)
