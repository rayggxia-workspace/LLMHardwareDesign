"""Admit actual FastRoute only after full original phase/grid fixtures pass."""
from pathlib import Path
import subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-local-density-routes169.py');scope={}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],str(p),'exec'),scope);q=scope['q']
for a,b in [("source=b/'source-157'","source=b/'source-172'"),("source='source-157'","source='source-172'"),('s-ready-local-density-openroad-source157.json','s-ready-fastroute24phase-source172.json'),('options=[(1690,3,1,valid[1700]),(1691,6,1,valid[1702])]','options=[(1770,4,1,valid[1702])]'),('for n in [1700,1702]','for n in [1702]'),('router-openroad-effort-preflight-157','router-fastroute24phase-preflight-172'),('assert node in (3,6)','assert node==4'),("('dynamic-02/node'+str(node))","('dynamic-05/node4')"),('sready169local-','sready177fast-'),("'--openroad-congestion-iterations',5","'--openroad-congestion-iterations',50,'--openroad-global-router','fastroute','--openroad-guide-pitch-um',1.6"),('for node,job in [(3,95098),(6,95101)]','for node,job in [(4,95391)]'),("b/'dynamic-02'/('node'+str(node))","b/'dynamic-05'/('node'+str(node))")]:
 assert a in q,a;q=q.replace(a,b)
anchor="proof=json.loads(report.read_text());assert proof['passed']"
assert anchor in q;q=q.replace(anchor,"proof=json.loads(report.read_text());assert proof['global_router']=='fastroute'and proof['unused_lower_search_track_pitch_um']==1.6 and proof['global_guide_origin_dbu']==[190,140];assert proof['passed']")
q=q.replace('Actual235-instance/8990-net local-density placement1700/1702 route comparison.',
 'One actual235-instance/8990-net FastRoute candidate1770 on original1702 measured-budget/local-density placement, after actual172 three fixture detailed routes and original phase/grid/checkerboard/flood/9 negative checks pass. Earlier170 coarse global overflow and171 off-grid failures retained; no waiver/remapping/allow_congestion. Only search guides change:24um guide tiles and exact original190/140DBU phase, real M11/M12 tracks4um and all final geometry/PG/RC300MHz gates unchanged.')
compile(q,'actual_FastRoute_full_scene1770','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
