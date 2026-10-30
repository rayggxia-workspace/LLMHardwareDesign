"""Two explicitly bounded pre-freeze via9 repairs for actual full-chip shorts.

All metal1--8 paths, every other via, cell and fixed port remain identical.
The accepted lower-layer via8 anchor is joined to one new via9 landing; no
post-freeze editing or general route legalization is implied.
"""
import copy
from native_escape import parse,emit,signature,path_length,graph


def relocate(text,pin,target):
    header,old=parse(text);pin=tuple(pin);target=tuple(target)
    assert len(pin)==len(target)==2 and all(type(x)is int for x in pin+target)
    via=[p for p in old if p['via']and p['layer']=='metal9'];assert len(via)==1
    original=via[0]['points'][0][:2]
    ten=[i for i,p in enumerate(old)if p['layer']=='metal10'and not p['via']]
    g=graph(old,ten)
    assert all(len(v)<=2 for v in g.values())
    assert {p for p,v in g.items()if len(v)==1}=={pin,original}
    for i in ten:
        assert all(p[2]is None or(p[:2]==pin and p[2]==0)for p in old[i]['points'])
    anchors={p['points'][0][:2]for p in old if p['via']and p['layer']=='metal8'}
    assert len(anchors)==1,'Only one unchanged lower-stack anchor is supported'
    anchor=next(iter(anchors))
    nine=[i for i,p in enumerate(old)if p['layer']=='metal9'and not p['via']]
    if nine:
        tree=graph(old,nine)
        assert {p for p,v in tree.items()if len(v)==1}=={anchor,original}
        assert all(len(v)<=2 for v in tree.values())
    else:assert anchor==original
    # One deterministic Manhattan connection per layer. The displacement is
    # supplied by the report-bound repair specification, never searched.
    result=[copy.deepcopy(p)for i,p in enumerate(old)if i not in set(nine+ten)]
    moved=next(p for p in result if p['via']and p['layer']=='metal9')
    moved['points']=[(*target,None)]
    for layer,start,end in [('metal9',anchor,target),('metal10',pin,target)]:
        points=[start,(end[0],start[1]),end]
        points=[p for i,p in enumerate(points)if i==0 or p!=points[i-1]]
        for a,b in zip(points,points[1:]):
            result.append(dict(layer=layer,points=[(*a,0 if layer=='metal10'and a==pin else None),(*b,None)],via=None))
    assert signature([p for p in old if int(p['layer'][5:])<=8])==signature([p for p in result if int(p['layer'][5:])<=8])
    assert signature([p for p in old if p['via']and p['layer']!='metal9'])==signature([p for p in result if p['via']and p['layer']!='metal9'])
    assert sorted(p['via']for p in old if p['via'])==sorted(p['via']for p in result if p['via'])
    assert sum(path_length(result,m)for m in ['metal9','metal10'])<=sum(path_length(old,m)for m in ['metal9','metal10'])
    return emit(header,result),dict(changed=True,kind='report-bound-two-via9-prefreeze-repair',pin_dbu=pin,original_via9_dbu=original,
        final_via9_dbu=target,unchanged_via8_dbu=anchor,original_paths=old,final_paths=result,header=header,
        original_length_dbu={m:path_length(old,m)for m in ['metal9','metal10']},final_length_dbu={m:path_length(result,m)for m in ['metal9','metal10']})
