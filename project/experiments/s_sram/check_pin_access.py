"""Replay exact conservative pin-window text transformation and native boxes."""
import hashlib, json, re
from decimal import Decimal
from pathlib import Path

def check(original, refined, proof, native):
    rect = r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*;'
    changes=[]; rows=[]
    for pin in re.finditer(r'(?ms)^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$',original):
        for part in re.finditer(r'(?s)LAYER\s+(\S+)\s*;(.*?)(?=\bLAYER\b|\bEND\b|\Z)',pin.group(2)):
            for m in re.finditer(rect,part.group(2)):
                values=[Decimal(x)*2000 for x in m.groups()]
                assert all(x == int(x) for x in values)
                old=list(map(int,values))
                new=[((x+9)//10)*10 if i<2 else (x//10)*10 for i,x in enumerate(old)]
                assert new[0]<new[2] and new[1]<new[3]
                rows.append(dict(pin=pin.group(1),layer=part.group(1),original=old,access=new))
                changes.append((pin.start(2)+part.start(2)+m.start(),pin.start(2)+part.start(2)+m.end(),'RECT '+' '.join(format(Decimal(x)/2000,'.4f')for x in new)+' ;'))
    expected=original
    for start,end,value in reversed(changes):expected=expected[:start]+value+expected[end:]
    assert refined == expected, 'Only the specified inward PIN RECT transform is allowed'
    assert proof['passed'] and proof['rectangles']==rows
    assert proof['manufacturing_grid_dbu']==10 and proof['dbu_per_um']==2000
    assert proof['only_pin_rectangles_changed'] and proof['all_windows_nonempty_subsets_and_covered_by_actual_metal']
    boxes=sorted((r['pin'],r['layer'],*r['access'])for r in rows)
    assert boxes == sorted(native), 'Native MTerm/MPin geometry differs'
    return dict(passed=True,rectangles=len(rows),native_exact=True,only_conservative_pin_rectangles_changed=True)

def validate(folder, original, gds):
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    p=folder/'receipt.json';n=folder/'native-receipt.json';t=folder/'native-pins.tsv'
    proof=json.loads(p.read_text());native=json.loads(n.read_text());lef=Path(proof['output'])
    assert proof['inputs'][str(original)]==sha(original) and proof['inputs'][str(gds)]==sha(gds)
    assert sha(lef)==proof['output_sha256']==native['lef_sha256']
    assert native['passed'] and native['proof_sha256']==sha(p) and native['tsv_sha256']==sha(t)
    assert native['script_sha256']==sha(folder/'native-readback.tcl')
    boxes=[(x[0],x[1],*map(int,x[2:]))for x in (line.split()for line in t.read_text().splitlines())]
    result=check(original.read_text(),lef.read_text(),proof,boxes)
    return lef,[p,n,t,folder/'native-readback.tcl',lef],result
