from pathlib import Path
import json,xml.etree.ElementTree as E
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-v27-physical';p.mkdir(exist_ok=False)
s=(r/'c-focused.sh').read_text().replace('out=$root/c-physical/focused-$(basename "$run")','out=$root/audit/C-v27-physical/focused');(p/'focused.sh').write_text(s)
s=(r/'c-focused.sbatch').read_text().replace('/c-focused.sh "$1"','/audit/C-v27-physical/focused.sh /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v27-joint-e20-h30').replace('/c-focused-%j.log','/audit/C-v27-focused-%j.log');(p/'focused.sbatch').write_text(s)
report=r/'audit/C-main-clock4-physical-v1/full/full.lyrdb';rows=[]
for it in E.parse(report).findall('.//items/item'):
 if it.findtext('category') in ("'METAL1.5'","'METAL10.7'"):rows.append(dict(category=it.findtext('category'),cell=it.findtext('cell'),values=[x.text for x in it.findall('values/value')]))
assert len(rows)==3;(p/'baseline-extra-three.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
