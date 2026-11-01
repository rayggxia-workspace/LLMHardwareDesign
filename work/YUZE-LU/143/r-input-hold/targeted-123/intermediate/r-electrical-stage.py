"""Intermediate GRT ECO check, never a substitute for final extracted all-zero gates."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path

def violations(text):
    result={'capacitance':{},'slew':{}};section=None
    for line in text.splitlines():
        line=line.strip()
        if line in ('max capacitance','max slew','max fanout'):
            section=line[4:] if line[4:] in result else None
            continue
        if '(VIOLATED)' not in line or section is None:continue
        fields=line.split();assert len(fields)==5 and fields[-1]=='(VIOLATED)',line
        pin,limit,value,slack=fields[:4]
        numbers=[Decimal(x) for x in (limit,value,slack)]
        assert all(x.is_finite() for x in numbers) and (numbers[2]<0 or numbers[2].is_zero() and numbers[2].is_signed()),line
        assert pin not in result[section],pin
        result[section][pin]=numbers[2]
    return result

def validate(before,after,before_counts,after_counts):
    b=violations(before);a=violations(after)
    assert len(before_counts)==len(after_counts)==4
    assert before_counts[2:]==after_counts[2:]==[0,0],(before_counts,after_counts)
    result=dict(passed=True,native_leaf_accepted=False,
        policy='Intermediate only: no new violating pins, no worse worst electrical slack; pre/post setup and hold0. Final actual-RC cap/slew/setup/hold must all0.',
        before_counts=before_counts,after_counts=after_counts,electrical={})
    for i,kind in enumerate(('capacitance','slew')):
        assert len(b[kind])==before_counts[i] and len(a[kind])==after_counts[i],kind
        assert not set(a[kind])-set(b[kind]),(kind,'new violating pins',sorted(set(a[kind])-set(b[kind])))
        wb=min(b[kind].values(),default=Decimal(0));wa=min(a[kind].values(),default=Decimal(0))
        # Display units are fF for capacitance and ns for slew. This only
        # absorbs <=1e-9 display-unit report rounding, never final RC slack.
        assert wa>=wb-Decimal('1e-9'),(kind,'worse worst slack',str(wb),str(wa))
        result['electrical'][kind]=dict(before_pins=sorted(b[kind]),after_pins=sorted(a[kind]),worst_before=str(wb),worst_after=str(wa))
    return result

def check_files(before,after,before_counts,after_counts):
    paths=list(map(Path,(before,after,before_counts,after_counts)))
    result=validate(paths[0].read_text(),paths[1].read_text(),
        list(map(int,paths[2].read_text().split())),list(map(int,paths[3].read_text().split())))
    result['files']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('before','after','before-counts','after-counts','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();result=check_files(a.before,a.after,a.before_counts,a.after_counts)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
