"""Queue a weight1 product-history comparison before exact slow-slot refill."""
from pathlib import Path
import subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-product-route144.py');scope={}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],str(p),'exec'),scope)
q=scope['q'].replace('s-ready-history-product-source144.json','s-ready-history-product-refill-source144.json')
q=q.replace('options=[(1510,4,4,valid[1470])]','options=[(1511,25,1,valid[1470])]')
q=q.replace('assert node==4','assert node==25').replace("('dynamic-05/node4')","('dynamic-04/node25')")
assert 'options=[(1511,25,1,valid[1470])]'in q
compile(q,'actual_weight1_product_comparison','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
