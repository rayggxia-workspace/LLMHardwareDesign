"""Independent rectangle connectivity for every selected-net real access shape.

Same-layer closed-rectangle overlap joins conductor shapes; actual DB via
definition and same cell/BTerm pin ports join their respective access rectangles.
This is LEF/OpenDB connectivity, not GDS LVS or a full-block all-net proof.
"""
import csv,gzip,itertools,json,sys
from collections import defaultdict
from pathlib import Path

def check(path,whole=False):
    path=Path(path);opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt') as f:return check_rows(csv.DictReader(f,delimiter='\t'),whole)

def check_rows(reader,whole=False):
    result={};seen=set();checked_nets=0;checked_terms=0;checked_shapes=0;pass_nets=0;layers_seen=set()
    # Native export emits one whole net at a time, so memory is bounded by the
    # largest individual net rather than the full routed design.
    for nn,group in itertools.groupby(reader,key=lambda r:r['net']):
        assert nn not in seen,'Input is not grouped by net';seen.add(nn)
        rows=list(group)
        for r in rows:
            for q in ['x0','y0','x1','y1']:r[q]=int(r[q])
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
        passed=len(components)==1 and len(allroots-set(components))==0 and not any(r['kind']=='UNROUTED' for r in rows)
        rec={'access_shapes':len(rows),'terminals':len(terms),'terminal_components':len(components),
            'all_conductor_components':len(allroots),'stray_conductor_components':len(allroots-set(components)),
            'terminal_groups':list(components.values()),'pass_all_selected_net_terminals_connected':len(components)==1,
            'checked_layers':sorted(bylayer)}
        checked_nets+=1;checked_terms+=len(terms);checked_shapes+=len(rows);layers_seen.update(bylayer);pass_nets+=int(passed)
        if not whole or not passed:result[nn]=rec
    return {'scope':('ALL multi-terminal signal/clock nets in the entire block, including all their terminals; one-terminal unused nets excluded' if whole else 'ALL terminals of ALL selected nets')+'; actual DB rectangle/closed-overlap and via definition connectivity; not GDS LVS',
            'pass':checked_nets>0 and checked_nets==pass_nets,'checked_nets':checked_nets,'connected_nets':pass_nets,'checked_terminals':checked_terms,'checked_shapes':checked_shapes,'checked_layers':sorted(layers_seen),
            'failed_nets':checked_nets-pass_nets,'nets':result,'nets_detail':'failures only' if whole else 'all selected nets'}

if __name__=='__main__':
    p=Path(sys.argv[1]);r=check(p,'--whole' in sys.argv[2:]);dest=p.with_suffix('.json');dest.write_text(json.dumps(r,indent=2)+'\n');print('ACCESS_CONNECTIVITY',r['pass'],r['checked_nets'],r['failed_nets'])
