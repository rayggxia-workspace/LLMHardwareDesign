"""Six bounded alternate bridges selected from actual605 geometry, not delivery."""
CASES={
    'alt-upper-plain':(25,'net80238'),
    'alt-upper-stack':(29,'net87868'),
    'alt-lower-stack':(31,'$abc$1437224$new_n120762'),
    'alt-both-stack':(32,'net79959'),
    'alt-corner-upper':(0,'net71774'),
    'alt-corner-lower':(1,'$abc$1437224$new_n105265'),
}


def build(paths,row,case):
    from revision300_v_via_batch import contains
    assert case in CASES
    def via(point,layer,required=True):
        found=[p for p in paths if p['layer']==layer and p['via'] and len(p['points'])==1
               and tuple(p['points'][0][:2])==point]
        assert len(found)<=1
        if required:assert found
        return found[0]if found else None
    if case.startswith('alt-corner-'):
        upper=case=='alt-corner-upper'
        a,b=((357010,2376780),(357010,2377060))if upper else((361190,1337700),(361190,1337980))
        layer='metal2'if upper else'metal1';bridge_layer='metal3'if upper else'metal1'
        remove=via(a,layer);assert remove['via'].startswith('via2_'if upper else'via1_')
        assert via(b,layer,False)is None
        wires=[p for p in paths if contains(p,'metal2',a,b)];assert len(wires)==1
        assert any(p['layer']=='metal2'and not p['via']and any(tuple(q[:2])==b for q in p['points'])
                   and not contains(p,'metal2',a,b)for p in paths)
        guards=[(remove['via'],'metal2','metal3')if upper else(remove['via'],'metal1','metal2')]
        keep=wires[0]
    else:
        assert len(row['route_options'])==1
        ends=[tuple(row['route_options'][0][k])for k in ('a','b')]
        tops=[point for point in ends if via(point,'metal3',False)]
        assert len(tops)==1;a=tops[0];b=next(p for p in ends if p!=a)
        remove=via(a,'metal3');keep=via(b,'metal2')
        assert remove['via'].startswith('via3_')and keep['via'].startswith('via2_')
        assert via(b,'metal3',False)is None and via(a,'metal2',False)is None
        upper=via(a,'metal4',False);lower=via(b,'metal1',False)
        assert bool(upper)==(case in('alt-upper-stack','alt-both-stack'))
        assert bool(lower)==(case in('alt-lower-stack','alt-both-stack'))
        if upper:assert upper['via'].startswith('via4_')and any(contains(p,'metal5',a,a)for p in paths)
        else:assert any(contains(p,'metal4',a,a)for p in paths)
        if lower:assert lower['via'].startswith('via1_')
        else:assert any(contains(p,'metal2',b,b)for p in paths)
        wires=[p for p in paths if contains(p,'metal3',a,b)];assert len(wires)==1
        layer='metal3';bridge_layer='metal4'
        guards=[(remove['via'],'metal3','metal4'),(keep['via'],'metal2','metal3')]
        if upper:guards.append((upper['via'],'metal4','metal5'))
        if lower:guards.append((lower['via'],'metal1','metal2'))
    assert(a[0]==b[0]or a[1]==b[1])and 0<abs(a[0]-b[0])+abs(a[1]-b[1])<=2000
    moved=dict(layer=layer,points=[(*b,None)],via=remove['via'])
    bridge=dict(layer=bridge_layer,points=[(*a,None),(*b,None)],via=None)
    return dict(removed=remove,added=[bridge,moved],retained=keep,wire=wires[0],guards=guards)
