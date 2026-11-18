from pathlib import Path
import re,json,collections
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu')
r=root/'runs/C-v20-native-clock4'
s=(r/'estimated-electrical.rpt').read_text();kind=None;spec=[]
for line in s.splitlines():
 if line.strip() in ('max slew','max capacitance','max fanout'):kind=line.strip().replace('max ','')
 m=re.match(r'^(.+?)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+\(VIOLATED\)',line)
 if m:spec.append((kind,m[1].strip()))
(root/'c-global-electrical-specs.tcl').write_text('set specs {\n'+''.join(' {'+kind+' {'+pin+'}}\n' for kind,pin in spec)+'}\n')
s=(r/'estimated-paths.rpt').read_text();paths=[]
for b in s.split('Startpoint: ')[1:]:
 m=re.search(r'Endpoint: (\S+)',b);t=re.search(r'Path Type: (\S+)',b);v=re.search(r'([-\d.]+)\s+slack \(VIOLATED\)',b)
 if m and t and v:paths.append(dict(start=b.splitlines()[0],end=m[1],type=t[1],slack=float(v[1])))
(root/'c-global-path-summary.json').write_text(json.dumps(paths,indent=2))
print('VIOLATED electrical pins',collections.Counter(k for k,n in spec))
print('Worst max',sorted((x for x in paths if x['type']=='max'),key=lambda x:x['slack'])[:8])