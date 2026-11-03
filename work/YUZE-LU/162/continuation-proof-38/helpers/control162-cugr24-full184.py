"""Matched full-scene CUGR24 only after its actual three-fixture proof passes."""
from pathlib import Path
import subprocess,shlex

p=Path(r'D:\Data\电路实验\control162-fastroute-full177.py');scope={}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],str(p),'exec'),scope);q=scope['q']
for a,b in [('s-ready-fastroute24phase-source172.json','s-ready-cugr24phase-source172.json'),('options=[(1770,4,1,valid[1702])]','options=[(1840,4,1,valid[1702])]'),('router-fastroute24phase-preflight-172','router-cugr24phase-preflight-178'),('sready177fast-','sready184cugr24-'),("'--openroad-global-router','fastroute'","'--openroad-global-router','cugr'"),("proof['global_router']=='fastroute'","proof['global_router']=='cugr'")]:
    assert a in q,a;q=q.replace(a,b)
old='One actual235-instance/8990-net FastRoute candidate1770 on original1702 measured-budget/local-density placement, after actual172 three fixture detailed routes and original phase/grid/checkerboard/flood/9 negative checks pass. Earlier170 coarse global overflow and171 off-grid failures retained; no waiver/remapping/allow_congestion. Only search guides change:24um guide tiles and exact original190/140DBU phase, real M11/M12 tracks4um and all final geometry/PG/RC300MHz gates unchanged.'
assert old in q
q=q.replace(old,'Matched actual235-instance/8990-net CUGR50 candidate1840 reuses exactly the same1702 placement and source172 as1770 FastRoute50, both24um global guide cells and190/140DBU phase. Require actual178 three detailed-route fixtures, zero DRC, original strict grid/checkerboard/flood and9 negatives before queue admission. Every original geometry/PG/three-RC300MHz/delivery stage retained. Existing nine60um CUGR searches and original1770 evidence preserved. No new node, global-overflow waiver, geometry relaxation or R change.')
compile(q,'actual_matched_cugr24_full1840','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
