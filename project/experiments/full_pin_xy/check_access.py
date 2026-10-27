"""Independent rectangle connectivity for every selected-net real access shape.

Same-layer closed-rectangle overlap joins conductor shapes; actual DB via
definition and same cell/BTerm pin ports join their respective access rectangles.
This is LEF/OpenDB connectivity, not GDS LVS or a full-block all-net proof.
"""
import csv,json,sys
from collections import defaultdict
from pathlib import Path

def check(path):
    nets=defaultdict(list)
    with Path(path).open() as f:
        for r in csv.DictReader(f,delimiter='\t'):
            for q in ['x0','y0','x1','y1']:r[q]=int(r[q])
            nets[r['net']].append(r)
    result={}
    for nn,rows in nets.items():
        parent=list(range(len(rows)));bylayer=defaultdict(list);links=defaultdict(list)
        def find(i):
            while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
            return i
        def union(i,j):parent[find(i)]=find(j)
        for i,r in enumerate(rows):bylayer[r['layer']].append(i);links[r['link']].append(i)
        for ids in links.values():
            for i in ids[1:]:union(i,ids[0])
        for ids in bylayer.values():
            ids.sort(key=lambda i:rows[i]['x0']);active=[]
            for i in ids:
                r=rows[i];active=[j for j in active if rows[j]['x1']>=r['x0']]
                for j in active:
                    q=rows[j]
                    if q['y0']<=r['y1'] and q['y1']>=r['y0']:union(i,j)
                active.append(i)
        terms={link:find(ids[0]) for link,ids in links.items() if link.startswith(('I:','B:'))}
        components=defaultdict(list)
        for term,root in terms.items():components[root].append(term)
        allroots={find(i) for i in range(len(rows))}
        result[nn]={'access_shapes':len(rows),'terminals':len(terms),'terminal_components':len(components),
            'all_conductor_components':len(allroots),'stray_conductor_components':len(allroots-set(components)),
            'terminal_groups':list(components.values()),'pass_all_selected_net_terminals_connected':len(components)==1,
            'checked_layers':sorted(bylayer)}
    return {'scope':'ALL terminals of ALL selected nets; actual DB rectangle/closed-overlap and via definition connectivity; not full-block/GDS LVS',
            'pass':bool(result) and all(v['pass_all_selected_net_terminals_connected'] and v['stray_conductor_components']==0 for v in result.values()),'nets':result}

if __name__=='__main__':
    p=Path(sys.argv[1]);r=check(p);p.with_suffix('.json').write_text(json.dumps(r,indent=2)+'\n');print('SELECTED_ACCESS_CONNECTIVITY',r['pass'],len(r['nets']))
