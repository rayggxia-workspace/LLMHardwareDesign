from pathlib import Path
import re,json
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v27-physical/rcx-material-120031');r=json.loads((p/'material/receipt.json').read_text())
for d in r['geometry_differences']:
 print('NET',d['net'])
 for side in ('before','after'):
  text=(p/(side+'.def')).read_text();sec=re.search(r'\nNETS\s+\d+\s*;(.*?)\nEND NETS',text,re.S)[1];m=re.search(r'^\s*-\s+'+re.escape(d['net'])+r'\s+(.*?);\s*$',sec,re.M|re.S);assert m
  (p/(side+'-'+str(r['geometry_differences'].index(d))+'.defpart')).write_text(m[0]);print(side)
  for row in m[0].splitlines():
   if 'metal10' in row or any(v in row for v in ('2089','2090','1208','2505','2506','1157')):print(row)
