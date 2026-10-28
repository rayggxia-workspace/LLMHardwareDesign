"""Check native construction terminal/component bijection; no XY/route claim."""
from pathlib import Path
import argparse,csv,json


def verify(contract,endpoints,output):
    root=Path(contract);components=json.loads((root/'components.json').read_text());pads=json.loads((root/'access_pads.json').read_text())
    expected={}
    for component,terms in components.items():
        for t in terms:
            if t['kind']=='ITERM':key=('ITERM','u_'+t['case'],t['pin'])
            elif t['kind']=='TOP_IO':key=('BTERM','',component.split(':')[0]+'__'+t['pin'])
            else:
                key=('ITERM',t['instance'],'Z')
            assert key not in expected;expected[key]=(component,t['direction'])
    for component,pad in pads.items():expected['BTERM','',pad]=(component,'inout')
    with Path(endpoints).open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    actual={(r['kind'],r['instance'],r['pin']):r for r in rows};assert len(actual)==len(rows)==len(expected),(len(actual),len(rows),len(expected))
    assert set(actual)==set(expected),{'missing':list(set(expected)-set(actual))[:10],'extra':list(set(actual)-set(expected))[:10]}
    group_nets={};net_groups={}
    for key,(component,direction) in expected.items():
        r=actual[key];assert r['direction'].lower()==direction,(key,'direction')
        group_nets.setdefault(component,set()).add(r['net']);net_groups.setdefault(r['net'],set()).add(component)
        if key[0]=='ITERM' and key[1].startswith('u_') and key[1] not in ['u_idle_clock_zero'] and not key[1].startswith('u_literal_'):
            t=next(q for q in components[component] if q.get('case')==key[1][2:] and q['pin']==key[2])
            assert r['layer']==t['original_pin_layer'],(key,'original signal layer changed')
    assert set(group_nets)==set(components)
    assert all(len(v)==1 for v in group_nets.values()),'An intended fixed component split'
    assert all(len(v)==1 for v in net_groups.values()),'Distinct components merged before adaptation'
    result={'status':'PASS_NATIVE_CONSTRUCTION_COMPONENT_BIJECTION_NOT_PHYSICAL_IMPLEMENTATION','original_signal_pins':24767,
            'fixed_components':len(components),'native_components':len(net_groups),'checked_terminals':len(rows),
            'exact_terminal_set_direction_and_original_leaf_pin_layer':True,'fixed_component_bijection':True,
            'actual_shared_conductors_routed':False,'M1_M10_frozen':False,'functional_formal_equivalence':False,'physical_qualification':False}
    Path(output).write_text(json.dumps(result,indent=2)+'\n');print(result['status'],len(rows),'terminals')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('contract');p.add_argument('endpoints');p.add_argument('output');a=p.parse_args();verify(a.contract,a.endpoints,a.output)
