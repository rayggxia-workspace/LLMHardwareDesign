"""Admit one real source143 route only after executed exact-output regression."""
from pathlib import Path
import subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-halo-route142.py');scope={}
exec(compile(p.read_text(encoding='utf-8').split("if '--submit' in sys.argv:",1)[0],str(p),'exec'),scope)
q=scope['q'].replace("source=b/'source-142'","source=b/'source-143'").replace("source='source-142'","source='source-143'")
q=q.replace('s-ready-halo-routes-source142.json','s-ready-cache-source143.json')
q=q.replace('options=[(seed,5,4,valid[n])for seed,n in [(1480,1470),(1481,1473),(1482,1474)]if n in valid]',
            'options=[(1490,5,4,valid[1470])]')
q=q.replace("regression=b/'router-congestion-regression-01/receipt.json'","regression=b/'router-exact-cache-regression-01/receipt.json'")
anchor="reg=json.loads(regression.read_text());assert reg['passed'];"
insert="""comparison=b/'route-selection-102/sready143-exact-cache-comparison.json';proof=json.loads(comparison.read_text());assert proof['passed']and proof['identical_successful_route_count']==132 and proof['new_receipt_sha256']==sha(regression);required_base.append(comparison)
"""
assert anchor in q;q=q.replace(anchor,insert+anchor,1)
q=q.replace('sready142halo-','sready143cache-')
compile(q,'actual_cache_route_admission','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
