"""Require every native same-net landing patch in the actual final DEF.

The DEF comes from the final ODB; GDS and RCX retain their independent final
bindings. This check never edits a producer, changes a gate or awards timing.
"""
import collections,re


def inspect(definition, inventory):
    region=re.search(r'(?ms)^NETS\s+\d+\s*;(.*?)^END NETS\s*$',definition)
    assert region,'Missing actual DEF signal NETS'
    nets={name:body for name,body in re.findall(r'(?ms)^\s*-\s+(\S+)\s+(.*?);',region.group(1))}
    actual=collections.Counter()
    pattern=r'(?:NEW|ROUTED)\s+metal3\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+RECT\s+\(\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*\)'
    for name,body in nets.items():
        for match in re.finditer(pattern,body):
            x,y,a,b,c,d=map(int,match.groups())
            actual[(name,x+a,y+b,x+c,y+d)]+=1
    expected=collections.Counter();banks=collections.Counter()
    for row in inventory.splitlines():
        bank,pin,net,*coords=row.split('\t');coords=tuple(map(int,coords))
        assert len(coords)==4 and net in nets
        connection=r'\(\s*'+re.escape(bank)+r'\s+'+re.escape(pin)+r'\s*\)'
        assert re.search(connection,nets[net]),(bank,pin,net,'Wrong actual bank pin/net')
        expected[(net,*coords)]+=1;banks[bank]+=1
    assert len(banks)==4 and all(n==267 for n in banks.values())
    missing=expected-actual
    assert not missing,('Actual final DEF misses landing patches',list(missing.items())[:4])
    return dict(passed=True,patches=sum(expected.values()),banks=dict(banks),
                all_same_net_rectangles_present=True,all_bank_pin_connections_present=True)
