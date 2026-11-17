import json
from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/U-v8-postroute-h02-e10-independent-v1/formal')
a,b=[json.loads((r/(n+'-physical.json')).read_text())['modules']['u_n32_controlled_dma_64']['cells'] for n in ('gold','gate')]
from collections import Counter
print(Counter((a[n]['type'],b[n]['type']) for n in a.keys()&b.keys() if a[n]['type']!=b[n]['type']))
