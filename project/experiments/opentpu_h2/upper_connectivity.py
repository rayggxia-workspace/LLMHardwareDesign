"""Independent rectangular conductor connectivity on actual routed upper DEF."""
import collections
import re
from freeze_audit import section
from integrate import routed_parts

def verify(deftext,plan,landings,techtext):
    widths={};vias=collections.defaultdict(list)
    for line in techtext.splitlines():
        p=line.split()
        if p[0]=='LAYER':widths[p[1]]=int(p[2])
        else:
            _,name,layer,*box=p
            if layer.startswith('metal'):vias[name].append((layer,*map(int,box)))
    forests={f['proxy']:f for f in plan['forests']}
    covered=[index for f in forests.values() for index in f['landings']]
    assert len(covered)==len(set(covered)) and set(covered)==set(range(len(landings))),'Boundary access coverage differs'
    rows={routed_parts(row)[0].split()[0]:routed_parts(row) for row in section(deftext,'NETS')}
    assert set(rows)==set(forests),'Routing forest inventory differs'
    result=[]
    for name,f in forests.items():
        assert all(landings[i]['net']==f['original_net'] for i in f['landings']),'Forest maps to wrong original signal net'
        shapes=[];links=[]
        for path in rows[name][1:]:
            pts=re.findall(r'\(\s*(-?\d+|\*)\s+(-?\d+|\*)(?:\s+(-?\d+))?\s*\)',path)
            tokens=re.sub(r'\([^)]*\)','',path).split()
            layer=tokens[0];assert layer in ('metal8','metal9','metal10')
            assert pts and '*' not in pts[0][:2]
            x,y=map(int,pts[0][:2]);start=pts[0][2]
            if len(tokens)==2:
                assert tokens[1] in vias and len(pts)==1
                ids=[]
                for l,x1,y1,x2,y2 in vias[tokens[1]]:
                    ids.append(len(shapes));shapes.append((l,x+x1,y+y1,x+x2,y+y2))
                links.append(ids)
            else:
                assert len(tokens)==1
                half=widths[layer]//2
                for px,py,end in pts[1:]:
                    nx=x if px=='*' else int(px);ny=y if py=='*' else int(py)
                    a=half if not start else int(start);b=half if not end else int(end)
                    assert (x==nx) != (y==ny),'Non-segment upper geometry'
                    if y==ny:
                        lo,hi=(x-a,nx+b) if x<nx else (nx-b,x+a)
                        box=(layer,lo,y-half,hi,y+half)
                    else:
                        lo,hi=(y-a,ny+b) if y<ny else (ny-b,y+a)
                        box=(layer,x-half,lo,x+half,hi)
                    shapes.append(box);x,y,start=nx,ny,end
        terminals=[]
        for index in f['landings']:
            pad=landings[index];ids=[]
            for l,x1,y1,x2,y2 in vias[pad['via']]:
                if l=='metal8':
                    ids.append(len(shapes));shapes.append((l,pad['x']+x1,pad['y']+y1,pad['x']+x2,pad['y']+y2))
            assert ids;terminals.append(ids[0]);links.append(ids)
        parent=list(range(len(shapes)))
        def root(i):
            while parent[i]!=i:i=parent[i]
            return i
        def union(a,b):parent[root(a)]=root(b)
        for ids in links:
            for i in ids[1:]:union(ids[0],i)
        for i,a in enumerate(shapes):
            for j in range(i):
                b=shapes[j]
                if a[0]==b[0] and max(a[1],b[1])<min(a[3],b[3]) and max(a[2],b[2])<min(a[4],b[4]):union(i,j)
        connected=len({root(i) for i in terminals})==1
        result.append(dict(proxy=name,original_net=f['original_net'],terminals=len(terminals),shapes=len(shapes),connected=connected))
    return dict(passed=all(r['connected'] for r in result),forest_count=len(result),results=result,
        scope='Actual routed metal rectangles with native technology widths/via enclosures, exact endpoint extension and prepaid V7 M8 landing rectangles. Require positive-area contact; no net-name-only or tolerance-based connection.')
