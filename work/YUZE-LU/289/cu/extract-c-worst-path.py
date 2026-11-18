from pathlib import Path
import re
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu')
s=(root/'runs/C-v20-native-clock4/estimated-paths.rpt').read_text()
a=[]
for b in s.split('Startpoint: ')[1:]:
 m=re.search(r'([-\d.]+)\s+slack \(VIOLATED\)',b)
 if m and 'Path Type: max' in b:a.append((float(m[1]),'Startpoint: '+b))
v,b=min(a)
(root/'c-global-worst-max.rpt').write_text(b)
print(b)