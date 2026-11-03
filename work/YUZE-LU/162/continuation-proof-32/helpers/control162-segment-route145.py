"""Admit source145 only after all140 actual outputs are exactly preserved."""
from pathlib import Path
import subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-product-route144.py');scope={}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],str(p),'exec'),scope)
q=scope['q']
changes={"source=b/'source-144'":"source=b/'source-145'","source='source-144'":"source='source-145'",'s-ready-history-product-source144.json':'s-ready-segment-source145.json','router-history-product-regression-01':'router-segment-regression-01','sready144-history-product-comparison.json':'sready145-segment-comparison.json',"proof['identical_default_routes']==132 and proof['independent_product_cases']==8":"proof['identical_successful_route_count']==140 and len(proof['actual_cache_oracles'])==145",'options=[(1510,4,4,valid[1470])]':'options=[(1512,26,1,valid[1470])]','assert node==4':'assert node==26',"('dynamic-05/node4')":"('dynamic-02/node26')",'sready144product-':'sready145segments-'}
for old,new in changes.items():assert old in q,old;q=q.replace(old,new)
compile(q,'actual_exact_segment_product_route','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
