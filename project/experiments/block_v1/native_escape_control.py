"""Declared synthetic controls for route grammar, anchors and geometry guards."""
import json
from pathlib import Path
import sys
from native_escape import parse,simplify,signature
from native_escape_audit import physical,connectivity,readback,header_identity


def verify(destination):
    assert not destination.exists()
    u='''- test ( PIN test ) ( sink A ) + USE SIGNAL
 + ROUTED metal10 ( 0 0 0 ) ( 0 120 )
 NEW metal10 ( 0 120 ) ( 160 120 )
 NEW metal10 ( 160 120 ) ( 160 0 )
 NEW metal9 ( 160 0 ) ( 320 0 )
 NEW metal8 ( 320 0 ) via8_0
 NEW metal9 ( 160 0 ) via9_0 ;
'''
    edited,p=simplify(u,(0,0));assert p['changed']and p['final_length_dbu']['metal10']==160
    assert [r for r in p['final_paths']if r['layer']=='metal10']==[
        dict(layer='metal10',points=[(0,0,0),(160,0,None)],via=None)]
    assert signature(parse(edited)[1])==signature(p['final_paths'])
    tree='''- test ( PIN test ) ( sink A ) + USE SIGNAL
 + ROUTED metal10 ( 0 0 0 ) ( 0 80 )
 NEW metal10 ( 0 80 ) ( 160 80 )
 NEW metal9 ( 0 0 ) ( 320 0 )
 NEW metal9 ( 0 0 ) ( 0 80 )
 NEW metal9 ( 0 80 ) ( 160 80 )
 NEW metal8 ( 320 0 ) via8_0
 NEW metal9 ( 160 80 ) via9_0 ;
'''
    edited2,p2=simplify(tree,(0,0))
    assert p2['kind']=='existing-m9-tree-prune-fixed-via9'and p2['final_length_dbu']==dict(metal9=400,metal10=240)
    assert p2['final_via9_dbu']==p2['original_via9_dbu']==(160,80)
    faults=dict(branch=u.replace(' NEW metal9 ( 160 0 ) ( 320 0 )',' NEW metal10 ( 0 120 ) ( -80 120 )\n NEW metal9 ( 160 0 ) ( 320 0 )'),
        duplicate_via=u.replace('via9_0 ;','via9_0\n NEW metal9 ( 0 0 ) via9_0 ;'),
        wrong_via_layer=u.replace('NEW metal9 ( 160 0 ) via9_0','NEW metal8 ( 160 0 ) via9_0'),
        unsupported_rect=u.replace('NEW metal9 ( 160 0 ) via9_0','NEW metal9 ( 160 0 ) RECT ( 0 0 10 10 )'),
        detached=u.replace('( 0 0 0 )','( 0 -40 0 )'),
        m9_cycle=tree.replace(' NEW metal8 ( 320 0 ) via8_0',' NEW metal9 ( 160 80 ) ( 320 80 )\n NEW metal9 ( 320 80 ) ( 320 0 )\n NEW metal8 ( 320 0 ) via8_0'))
    rejected={}
    for name,text in faults.items():
        try:simplify(text,(0,0))
        except (AssertionError,ValueError):rejected[name]=True
        else:raise AssertionError('Accepted '+name)
    rows=[('metal9','wire',(0,0,100,100)),('via9','wire-via',(20,20,80,80)),
          ('metal10','wire-via',(0,0,100,100)),('metal10','P-port',(10,10,90,90)),('metal9','I-sink',(10,10,90,90))]
    assert connectivity(rows)['passed']
    assert not connectivity([r for r in rows if r[0]!='via9'])['passed']
    short=physical(dict(test=rows,foreign=[('metal10','wire',(0,0,100,100))]),['test'])
    assert not short['passed']and short['cross_net_shorts']
    edge=physical(dict(test=rows,foreign=[('metal10','wire',(100,0,200,100))]),['test'])
    assert not edge['passed']and edge['cross_net_shorts']
    work=destination.parent/(destination.stem+'-fixtures');work.mkdir(exist_ok=False)
    def wrap(text):return 'VERSION 5.8 ;\nNETS 1 ;\n'+text+'END NETS\nEND DESIGN\n'
    (work/'before.def').write_text(wrap(u));(work/'after.def').write_text(wrap(edited))
    p['header']=parse(u)[0]
    assert readback(work/'before.def',work/'after.def',dict(test=p))['passed']
    (work/'bad.def').write_text(wrap(edited).replace('VERSION 5.8','VERSION 5.7'))
    try:readback(work/'before.def',work/'bad.def',dict(test=p))
    except AssertionError:rejected['outside_net_scope']=True
    else:raise AssertionError('Accepted altered native definitions')
    original_header=parse(u)[0]
    reordered=original_header.replace('( PIN test ) ( sink A )','( sink A ) ( PIN test )')
    assert reordered!=original_header and header_identity(reordered)==header_identity(original_header)
    for name,header in dict(wrong_cell=original_header.replace('sink A','other A'),
                           wrong_pin=original_header.replace('sink A','sink B'),
                           missing_terminal=original_header.replace('( sink A )',''),
                           extra_terminal=original_header.replace('+ USE','( extra A ) + USE'),
                           changed_use=original_header.replace('SIGNAL','CLOCK')).items():
        assert header_identity(header)!=header_identity(original_header),name
        rejected[name]=True
    try:header_identity(original_header+' + FIXEDBUMP')
    except AssertionError:rejected['unsupported_header_attribute']=True
    else:raise AssertionError('Accepted unsupported header attribute')
    result=dict(passed=True,synthetic_positive_cases=['U-to-line','M9-tree-prune','actual-mask-shape-grammar','DEF-readback','terminal-order-invariance'],rejected=rejected,
        missing_via_rejected=True,cross_net_short_rejected=True,cross_net_edge_touch_rejected=True,
        scope='Declared synthetic grammar, anchor, scope and connectivity controls only; actual native EDA and physical repair remain independently required')
    destination.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':verify(Path(sys.argv[1]))
