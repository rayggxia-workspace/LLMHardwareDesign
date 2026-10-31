"""Exactly reversible Boolean encoding of real, stateless constant cells.

Physical views retain every tie. This is an explicit function substitution,
never a waiver for undriven inputs or a free state/boundary correspondence.
"""
import collections
import copy
import re
from native_cell_gate import group,attribute
from structural_view import digest


def project(data,liberty):
    validated={}
    for master,value in [('LOGIC0_X1','0'),('LOGIC1_X1','1')]:
        body=group(liberty,'cell',master)
        assert re.findall(r'\bpin\s*\(\s*"?([A-Za-z_][A-Za-z_0-9]*)"?\s*\)',body)==['Z']
        assert not re.search(r'\b(?:ff|ff_bank|latch|latch_bank|statetable)\s*\(',body)
        pin=group(body,'pin','Z');assert attribute(pin,'direction')=='output'and attribute(pin,'function')==value
        validated[master]=value
    result=copy.deepcopy(data);removed={};rewrites=[]
    for name,module in result['modules'].items():
        if module.get('attributes',{}).get('blackbox'):continue
        cells=module['cells'];drivers=collections.Counter()
        for p in module['ports'].values():
            if p['direction']in ('input','inout'):drivers.update(b for b in p['bits']if type(b)is int)
        for c in cells.values():
            for pin,bits in c['connections'].items():
                if c['port_directions'][pin]in ('output','inout'):drivers.update(b for b in bits if type(b)is int)
        constants={}
        for cell,entry in list(cells.items()):
            if entry['type']not in validated:continue
            assert entry.get('parameters',{})=={}and entry['port_directions']=={'Z':'output'}
            assert set(entry['connections'])=={'Z'}and len(entry['connections']['Z'])==1
            bit=entry['connections']['Z'][0];assert type(bit)is int and drivers[bit]==1 and bit not in constants
            constants[bit]=validated[entry['type']];removed[name+'/'+cell]=entry;del cells[cell]
        def rewrite(category,item,pin,bits):
            for index,bit in enumerate(bits):
                if bit in constants:
                    rewrites.append([name,category,item,pin,index,bit]);bits[index]=constants[bit]
        for category in ['ports','netnames']:
            for item,entry in module[category].items():rewrite(category,item,None,entry['bits'])
        for cell,entry in cells.items():
            for pin,bits in entry['connections'].items():rewrite('cells',cell,pin,bits)
    inverse=copy.deepcopy(result)
    for module,category,item,pin,index,bit in rewrites:
        entry=inverse['modules'][module][category][item]
        bits=entry['connections'][pin]if category=='cells'else entry['bits'];bits[index]=bit
    for key,entry in removed.items():
        name,cell=key.split('/',1);assert cell not in inverse['modules'][name]['cells'];inverse['modules'][name]['cells'][cell]=entry
    assert inverse==data
    return result,dict(schema='block-v1-constant-boolean-projection/1',passed=True,validated_functions=validated,
        removed_instances=removed,removed_count=len(removed),rewritten_bit_positions=rewrites,
        original_graph_sha256=digest(data),projected_graph_sha256=digest(result),exact_inverse_reconstruction=True,
        scope='Real Liberty single-output stateless function 0/1 substitution only; all physical resources retained; strict positive LEC/state-boundary correspondence remains mandatory')
