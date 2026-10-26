"""Unsigned structural view and exact bit-connectivity readback proof.

OpenSTA's structural Verilog reader rejects signed wire declarations. Signed
metadata has no operator semantics in a fully mapped gate-only circuit. Clear
only that metadata; independently prove all emitted/reparsed cells and pin-bit
connectivity, using named wire aliases to construct a bijection of bit IDs.
"""
import hashlib
import json


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def unsigned(data):
    before=digest({n:m.get('cells',{})for n,m in data['modules'].items()})
    removed=[]
    for name,module in data['modules'].items():
        for category in ['ports','netnames']:
            for item,entry in module.get(category,{}).items():
                if entry.get('signed'):
                    removed.append([name,category,item,entry['signed']])
                    entry['signed']=0
    assert before==digest({n:m.get('cells',{})for n,m in data['modules'].items()})
    assert removed
    return dict(cells_unchanged_sha256=before,removed_signed_metadata=removed)


def compare(expected, observed):
    gold={n:m for n,m in expected['modules'].items()if not m.get('attributes',{}).get('blackbox')}
    gate={n:m for n,m in observed['modules'].items()if not m.get('attributes',{}).get('blackbox')}
    def align(a,b,context,complete=True):
        mapping={};used=set()
        for key in a:
            choices=[k for k in [key,'\\'+key if key.startswith('$')else key]if k in b]
            choices=list(dict.fromkeys(choices))
            if not choices and not complete:continue
            assert len(choices)==1,(context,'Missing or ambiguous escaped identifier',key,choices)
            target=choices[0];assert target not in used,(context,'Identifier collision',key,target)
            mapping[key]=target;used.add(target)
        if complete:assert used==set(b),(context,'Unexpected identifiers',set(b)-used)
        return mapping
    module_names=align(gold,gate,'modules')
    result={}
    for name,a in gold.items():
        b=gate[module_names[name]];forward={};reverse={}
        def bind(x,y):
            if isinstance(x,str)or isinstance(y,str):
                assert x==y,(name,'Constant differs',x,y);return
            assert forward.setdefault(x,y)==y and reverse.setdefault(y,x)==x,(name,'Bit alias differs',x,y)
        port_names=align(a['ports'],b['ports'],(name,'ports'))
        for port,entry in a['ports'].items():
            other=b['ports'][port_names[port]]
            assert entry['direction']==other['direction']and len(entry['bits'])==len(other['bits'])
            for x,y in zip(entry['bits'],other['bits']):bind(x,y)
        wire_names=align(a['netnames'],b['netnames'],(name,'wires'),complete=False)
        for wire,target in wire_names.items():
            av=a['netnames'][wire]['bits'];bv=b['netnames'][target]['bits']
            assert len(av)==len(bv),(name,wire,'Width differs')
            for x,y in zip(av,bv):bind(x,y)
        cell_names=align(a.get('cells',{}),b.get('cells',{}),(name,'cells'))
        checked=0
        for cell,entry in a.get('cells',{}).items():
            other=b['cells'][cell_names[cell]]
            assert module_names.get(entry['type'],entry['type'])==other['type'],(name,cell,'Type differs')
            assert entry.get('parameters',{})==other.get('parameters',{}),(name,cell,'Parameters differ')
            assert entry['connections'].keys()==other['connections'].keys(),(name,cell,'Pins differ')
            for pin,bits in entry['connections'].items():
                values=other['connections'][pin];assert len(bits)==len(values)
                for x,y in zip(bits,values):
                    assert (x if isinstance(x,str)else forward[x])==y,(name,cell,pin,'Connection differs')
                    checked+=1
        result[name]=dict(cells=len(a.get('cells',{})),cell_pin_bits_checked=checked,bit_id_bijection=len(forward))
    return dict(schema='block-v1-structural-view-proof/1',passed=True,modules=result,
                escaped_module_identifiers={a:b for a,b in module_names.items()if a!=b})
