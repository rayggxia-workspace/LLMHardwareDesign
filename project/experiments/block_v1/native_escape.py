"""Bounded prefabrication escape simplification; no post-freeze metal editing.

Only a simple M10 path from one fixed BPin to one existing via9 is supported.
Its endpoint identities are preserved. If M9 already crosses the BPin centre,
the via can move there and unanchored M9 tree leaves can be removed. Every
other layer/path and all logical connections are retained. Actual geometry,
shorts, native DRC, regenerated RC/STA and final function remain separate gates.
"""
import collections
import copy
import re


def parse(text):
    start=re.search(r'\+ ROUTED\s+',text);assert start,'Missing routed net'
    header=text[:start.start()].rstrip();body=text[start.end():].strip()
    assert body.endswith(';');body=body[:-1].strip()
    paths=[]
    for raw in re.split(r'\s+NEW\s+',body):
        layer,rest=raw.split(None,1);assert re.fullmatch(r'metal(?:[1-9]|10)',layer)
        tokens=re.findall(r'\([^)]*\)|[^\s]+',rest);points=[];via=None
        for token in tokens:
            if token.startswith('('):
                values=token[1:-1].split();assert len(values)in (2,3)
                xy=[]
                for i,v in enumerate(values[:2]):
                    assert v=='*'or re.fullmatch(r'-?\d+',v)
                    assert v!='*'or points
                    xy.append(points[-1][i]if v=='*'else int(v))
                ext=None if len(values)==2 else int(values[2]);assert ext is None or ext>=0
                points.append((*xy,ext))
            else:
                assert via is None and re.fullmatch(r'via[1-9]_\d+',token),token
                via=token
        if via is None:
            assert len(points)==2 and points[0][:2]!=points[1][:2]
            assert points[0][0]==points[1][0]or points[0][1]==points[1][1]
        else:assert len(points)==1 and int(re.match(r'via(\d+)',via)[1])==int(layer[5:])
        paths.append(dict(layer=layer,points=points,via=via))
    assert paths
    return header,paths


def emit(header,paths):
    assert paths
    rows=[header]
    for i,p in enumerate(paths):
        prefix='+ ROUTED'if i==0 else'NEW'
        coords=' '.join('( '+' '.join(map(str,point[:2]))+
                       (''if point[2]is None else' '+str(point[2]))+' )'for point in p['points'])
        rows.append('      '+prefix+' '+p['layer']+' '+coords+(' '+p['via']if p['via']else''))
    return '\n'.join(rows)+' ;\n'


def graph(paths,indices):
    adjacent=collections.defaultdict(list)
    for i in indices:
        a,b=[p[:2]for p in paths[i]['points']]
        adjacent[a].append((b,i));adjacent[b].append((a,i))
    assert adjacent
    seen=set();todo=[next(iter(adjacent))]
    while todo:
        p=todo.pop()
        if p in seen:continue
        seen.add(p);todo.extend(n for n,i in adjacent[p])
    assert len(seen)==len(adjacent),'Disconnected path graph'
    assert len(indices)==len(adjacent)-1,'Path graph has a cycle'
    return adjacent


def on_segment(point,path):
    a,b=[p[:2]for p in path['points']]
    return (a[0]==b[0]==point[0]and min(a[1],b[1])<=point[1]<=max(a[1],b[1]))or(
        a[1]==b[1]==point[1]and min(a[0],b[0])<=point[0]<=max(a[0],b[0]))


def path_length(paths,layer):
    return sum(abs(p['points'][0][0]-p['points'][1][0])+abs(p['points'][0][1]-p['points'][1][1])
               for p in paths if p['layer']==layer and p['via']is None)


def signature(paths):
    return sorted((p['layer'],p['via']or'',tuple(sorted((a,b,-1 if c is None else c)for a,b,c in p['points'])))for p in paths)


def simplify(text,pin):
    """One deterministic candidate, with no seed/coordinate/constraint sweep."""
    header,original=parse(text);paths=copy.deepcopy(original);pin=tuple(pin)
    ten=[i for i,p in enumerate(paths)if p['layer']=='metal10'and p['via']is None]
    via=[i for i,p in enumerate(paths)if p['via']and p['layer']=='metal9']
    assert len(via)==1 and ten and len(ten)<=8
    vi=via[0];anchor=paths[vi]['points'][0][:2]
    adjacent=graph(paths,ten)
    assert all(len(v)<=2 for v in adjacent.values())
    assert {p for p,v in adjacent.items()if len(v)==1}=={pin,anchor}
    assert len(pin)==2 and all(type(x)is int for x in pin)
    for i in ten:
        for p in paths[i]['points']:
            assert p[2]is None or(p[:2]==pin and p[2]==0),'Unexpected escape extension'
    nine=[i for i,p in enumerate(paths)if p['layer']=='metal9'and p['via']is None]
    root=[i for i in nine if on_segment(pin,paths[i])]
    remove=set(ten);replacement=[];kind='anchored-m10-shortest-L'
    if root:
        # Restrict this branch to existing graph vertices. Splitting arbitrary
        # wires, cycles, M9 cell pins and extra via9 anchors is unsupported.
        g=graph(paths,nine);assert pin in g
        anchors={p['points'][0][:2]for p in paths if p['via']and p['layer']=='metal8'}
        assert anchors and anchors<=set(g)and anchor in g
        assert len(g[anchor])==1,'Old via9 is not an M9 tree leaf'
        keep=set()
        for dest in anchors:
            queue=collections.deque([pin]);parent={pin:None}
            while queue and dest not in parent:
                p=queue.popleft()
                for q,i in g[p]:
                    if q not in parent:parent[q]=(p,i);queue.append(q)
            assert dest in parent
            p=dest
            while p!=pin:p,i=parent[p];keep.add(i)
        assert keep
        remove.update(set(nine)-keep)
        paths[vi]['points']=[(*pin,None)]
        kind='existing-m9-root-via-and-tree-prune'
    else:
        bend=(anchor[0],pin[1]);points=[pin,bend,anchor]
        points=[p for i,p in enumerate(points)if i==0 or p!=points[i-1]]
        for a,b in zip(points,points[1:]):
            replacement.append(dict(layer='metal10',points=[(*a,0 if a==pin else None),(*b,None)],via=None))
    result=[p for i,p in enumerate(paths)if i not in remove]+replacement
    for layer in ['metal9','metal10']:
        assert path_length(result,layer)<=path_length(original,layer)
    assert [p for p in result if int(p['layer'][5:])<=8]==[p for p in original if int(p['layer'][5:])<=8]
    assert collections.Counter(p['via']for p in result if p['via'])==collections.Counter(p['via']for p in original if p['via'])
    changed=signature(result)!=signature(original)
    if not changed:result=original
    return (emit(header,result)if changed else text),dict(changed=changed,kind=kind,pin_dbu=pin,original_via9_dbu=anchor,
        final_via9_dbu=next(p['points'][0][:2]for p in result if p['via']and p['layer']=='metal9'),
        removed_paths=sorted(remove),original_paths=original,final_paths=result,
        original_length_dbu={m:path_length(original,m)for m in ['metal9','metal10']},
        final_length_dbu={m:path_length(result,m)for m in ['metal9','metal10']})


def records(path):
    """Stream complete canonical NETS records, retaining all other sections."""
    section=False;rows=[]
    with path.open()as stream:
        for line in stream:
            clean=line.lstrip()
            if re.fullmatch(r'NETS \d+ ;\s*',clean):section=True;continue
            if clean.startswith('END NETS'):
                if rows:yield ''.join(rows)
                return
            if not section:continue
            if not rows and not clean.strip():continue
            if clean.startswith('- '):
                if rows:yield ''.join(rows)
                rows=[]
            rows.append(line)
    raise AssertionError('Missing END NETS')
