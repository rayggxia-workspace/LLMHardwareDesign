"""Queue two source-identical weighted search comparisons in existing c96 slots."""
from pathlib import Path
import subprocess,shlex

p=Path(r'D:\Data\电路实验\control162-cpp-local-full185.py');scope={}
exec(compile(p.read_text(encoding='utf-8').split("if __name__=='__main__':",1)[0],str(p),'exec'),scope);q=scope['q']
for a,b in [('s-ready-cpp-localdensity-source172.json','s-ready-cpp-weighted-local-source172.json'),('options=[(1850,2,1,valid[1702])]','options=[(1852,26,4,valid[1702]),(1853,25,4,valid[1700])]'),('for n in [1702]','for n in [1700,1702]'),('assert node==2','assert node in(25,26)'),("('dynamic-05/node2')","(('dynamic-04/'if node==25 else'dynamic-02/')+'node'+str(node))"),('for node,job in [(2,95341)]','for node,job in [(25,95204),(26,95119)]'),("b/'dynamic-05'/('node'+str(node))","b/('dynamic-04'if node==25 else'dynamic-02')/('node'+str(node))"),("assert len(state['active'])<=4","assert len(state['active'])<=6"),('sready185cpp-','sready192cpp-')]:
    assert a in q,a;q=q.replace(a,b)
start=q.index("'Actual235-instance/8990-net C++ negotiated router1850")
end=q.index("'",start+1)
q=q[:start]+repr('Two actual235-instance/8990-net C++ comparisons1852/1853 on exact native/minimum-pin-cleared1702/1700 placements, heuristic4 with congestion scale1,16 independent single-thread trials per16CPU slot. New weight1 placement1850 first round remains420696 conflicts and takes about30minutes; existing source145 regression validates the unchanged weighted kernel. Original80round schedule reduces heuristic to1, and every original source wire budget, grid/short/flood, geometry/PG/three-RC300MHz/program/delivery gate stays mandatory. Queue both full seven-stage chains before replacing only exact own old duplicate searches on nodes25/26. Same eight parent allocations,6x16 c96 dynamic slots/memory guard, R and others untouched; no physical pass claimed.')+q[end+1:]
compile(q,'actual_weighted_local_1852_1853','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
