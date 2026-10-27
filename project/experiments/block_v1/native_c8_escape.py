"""Bounded C8 text proposals, keeping every lower-stack path and fixed port.

Complex M9 graphs stay intact in the fixed-via fallback. Relocation accepts
only one original lower via8 anchor and one simple original M9 path. These
text transformations still require actual geometry/native DRC/RC/STA gates.
"""
import copy
from native_escape import parse,emit,graph,signature,path_length,simplify


def propose(text,pin,landing=None,m9_horizontal_first=True,m10_horizontal_first=True):
    header,old=parse(text);pin=tuple(pin)
    vias=[p for p in old if p['via']and p['layer']=='metal9'];assert len(vias)==1
    anchor=vias[0]['points'][0][:2]
    ten=[i for i,p in enumerate(old)if p['layer']=='metal10'and not p['via']]
    assert 1<=len(ten)<=16,'Only one bounded 16-edge M10 simple path is supported'
    tree=graph(old,ten);assert all(len(v)<=2 for v in tree.values())
    assert {p for p,v in tree.items()if len(v)==1}=={pin,anchor}
    for i in ten:
        assert all(p[2]is None or(p[:2]==pin and p[2]==0)for p in old[i]['points'])
    if landing is None:
        try:
            result,plan=simplify(text,pin)
            return result,dict(plan,header=header,scope='Same bounded fixed-via native proposal')
        except (AssertionError,ValueError,KeyError):pass
    target=anchor if landing is None else tuple(landing)
    assert len(target)==2 and all(type(v)is int for v in target)
    removed=set(ten);replacement=[]
    def connection(layer,start,end,horizontal_first):
        bend=(end[0],start[1])if horizontal_first else(start[0],end[1])
        points=[start,bend,end];points=[p for i,p in enumerate(points)if i==0 or p!=points[i-1]]
        for a,b in zip(points,points[1:]):
            replacement.append(dict(layer=layer,points=[(*a,0 if layer=='metal10'and a==pin else None),(*b,None)],via=None))
    if landing is not None:
        anchors={p['points'][0][:2]for p in old if p['via']and p['layer']=='metal8'}
        assert len(anchors)==1,'Relocation needs exactly one unchanged via8 anchor'
        lower=next(iter(anchors))
        nine=[i for i,p in enumerate(old)if p['layer']=='metal9'and not p['via']]
        if nine:
            tree=graph(old,nine);assert all(len(v)<=2 for v in tree.values())
            assert {p for p,v in tree.items()if len(v)==1}=={lower,anchor}
        else:assert lower==anchor
        removed.update(nine);connection('metal9',lower,target,m9_horizontal_first)
    connection('metal10',pin,target,m10_horizontal_first)
    result=[copy.deepcopy(p)for i,p in enumerate(old)if i not in removed]+replacement
    if landing is not None:next(p for p in result if p['via']and p['layer']=='metal9')['points']=[(*target,None)]
    assert signature([p for p in result if int(p['layer'][5:])<=8])==signature([p for p in old if int(p['layer'][5:])<=8])
    assert signature([p for p in result if p['via']and p['layer']!='metal9'])==signature([p for p in old if p['via']and p['layer']!='metal9'])
    assert sorted(p['via']for p in result if p['via'])==sorted(p['via']for p in old if p['via'])
    if landing is None:assert signature([p for p in result if p['layer']=='metal9'])==signature([p for p in old if p['layer']=='metal9'])
    assert sum(path_length(result,m)for m in ['metal9','metal10'])<=sum(path_length(old,m)for m in ['metal9','metal10'])
    changed=signature(result)!=signature(old)
    return (emit(header,result)if changed else text),dict(changed=changed,header=header,pin_dbu=pin,original_via9_dbu=anchor,
        final_via9_dbu=target,original_paths=old,final_paths=result,kind='c8-single-anchor-relocation'if landing is not None else'c8-fixed-via-m10-only-fallback',
        original_length_dbu={m:path_length(old,m)for m in ['metal9','metal10']},final_length_dbu={m:path_length(result,m)for m in ['metal9','metal10']},
        scope='Text proposal only; real edit, all-net geometry/native DRC, new RC/STA/function remain mandatory')
