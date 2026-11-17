from pathlib import Path
import re
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/U-v15-guardant-f67-h3-u1.2/flow/results/nangate45/u-overlay-current/base/6_final.def')
s=p.read_text()
for pat in (r'NONDEFAULTRULES .*?END NONDEFAULTRULES',r'^\s*- '+re.escape(r'datapath.legacy_rsp_data\[90\]')+r'.*?;'):
 m=re.search(pat,s,re.M|re.S)
 print(m.group(0)[:18000] if m else 'NO_MATCH',flush=True)
