import json
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve();case=root/'nine-channel'
pending=set(map(int,(case/'paths.txt.pending').read_text().split()))
rows=[]
for line in (case/'helpers.txt').read_text().splitlines():
 v=list(map(int,line.split()))
 if v[0] in pending and v[1:3]!=v[3:5]:rows.append(line)
(case/'helpers-retry.txt').write_text('\n'.join(rows)+'\n')
s=(root/'channel_route.cpp').read_text()
s=s.replace('for(auto p:frozen[h.id].vias)board.copper.add(-3,p,p,2);',
            'if(abs(h.a.x-h.b.x)+abs(h.a.y-h.b.y)>=1000) for(auto p:frozen[h.id].vias)board.copper.add(-3,p,p,2);')
s=s.replace('joined.vias.insert(joined.vias.end(),found.route.vias.begin(),found.route.vias.end());',
'''for(auto p:found.route.vias) {
 bool exists=false;
 for(auto q:joined.vias)if(p.x==q.x && p.y==q.y)exists=true;
 if(!exists)joined.vias.push_back(p);
}''')
(root/'channel_retry.cpp').write_text(s)
print('Retry native C access gaps:',len(rows))
