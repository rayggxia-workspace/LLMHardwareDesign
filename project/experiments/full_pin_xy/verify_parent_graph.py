"""Check the actual native parent graph BEFORE PG generation and routing."""
from pathlib import Path
from collections import defaultdict
import argparse,csv,json

def validate_graph(path,contract,expected):
    with Path(path).open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    norm=lambda s:s.replace('\\','')
    key=lambda r:(r['kind'],norm(r.get('instance','')),norm(r['pin']))
    physical={key(r):r for r in rows};logical={key(r):r for r in expected}
    assert len(physical)==len(rows)==len(expected),('Terminal counts',len(rows),len(expected))
    assert set(logical)==set(physical),'Native terminal set changed or disconnected'
    top={p['pin']:p for p in contract['external_pins']};bit_nets=defaultdict(set);net_bits=defaultdict(set)
    for k,want in logical.items():
        got=physical[k];assert got['direction'].lower()==want['direction'],(k,'direction')
        layer=want.get('original_leaf_pin_layer',top[want['pin']]['layer'] if want['kind']=='BTERM' else None)
        assert got['layer']==layer,(k,'physical endpoint layer',got['layer'],layer)
        bit_nets[want['parent_bit']].add(got['net']);net_bits[got['net']].add(want['parent_bit'])
    assert all(len(v)==1 for v in bit_nets.values()) and all(len(v)==1 for v in net_bits.values()),'Logical bits merged or split'
    return {'exact_terminal_set_direction_layer_and_bit_graph':True,'endpoints':len(rows),'parent_bits':len(bit_nets),
      'independent_constant_nets_preserved':True,'normalization':'Only OpenDB backslash name escaping; reject any key collision before comparing graph'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('contract');p.add_argument('expected');p.add_argument('actual');p.add_argument('--out',required=True);a=p.parse_args()
    result=validate_graph(a.actual,json.loads(Path(a.contract).read_text()),json.loads(Path(a.expected).read_text()))
    with Path(a.out).open('x') as f:json.dump(result,f,indent=2)
    print('EXACT_NATIVE_PARENT_GRAPH',result['endpoints'],result['parent_bits'])
