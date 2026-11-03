"""One actual product-history comparison; all physical gates unchanged."""
from pathlib import Path
import subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-cache-route143.py');scope={}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],str(p),'exec'),scope)
q=scope['q'].replace("source=b/'source-143'","source=b/'source-144'").replace("source='source-143'","source='source-144'")
q=q.replace('s-ready-cache-source143.json','s-ready-history-product-source144.json').replace('router-exact-cache-regression-01','router-history-product-regression-01')
q=q.replace('sready143-exact-cache-comparison.json','sready144-history-product-comparison.json').replace("proof['identical_successful_route_count']==132","proof['identical_default_routes']==132 and proof['independent_product_cases']==8")
q=q.replace('options=[(1490,5,4,valid[1470])]','options=[(1510,4,4,valid[1470])]').replace('assert node==5','assert node==4').replace("('dynamic-03/node5')","('dynamic-05/node4')")
q=q.replace("'--route-congestion-scale',1,'--negotiate-priority-routes'","'--route-congestion-scale',1,'--multiply-congestion-history','--negotiate-priority-routes'")
q=q.replace('sready143cache-','sready144product-')
assert "'--multiply-congestion-history'"in q
compile(q,'actual_product_history_route_admission','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
