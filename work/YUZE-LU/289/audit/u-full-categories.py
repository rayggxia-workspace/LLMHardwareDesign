import xml.etree.ElementTree as E,collections
from pathlib import Path
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/U-v7-macropdn-x8-seed0/signoff/full.lyrdb')
r=E.parse(str(p));its=r.findall('.//items/item');c=collections.Counter(x.findtext('category') for x in its);print(c)
for cat,count in c.items():
 print(cat,count)
 for x in [x for x in its if x.findtext('category')==cat][:2]:print(E.tostring(x,encoding='unicode')[:1000])
