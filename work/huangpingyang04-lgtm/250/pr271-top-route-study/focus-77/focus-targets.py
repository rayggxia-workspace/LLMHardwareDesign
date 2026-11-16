"""Select only the exact 77 endpoints reported by job 118302."""
import csv
import json
from pathlib import Path
import sys


spec, source = map(Path, sys.argv[1:])
nets = json.loads(spec.read_bytes())['nets']
index = {n['id']: i for i,n in enumerate(nets)}
assert len(nets)==len(index)==1184
out=[]
with source.open() as f:
    for row in csv.DictReader(f,delimiter='\t'):
        if row['cause'] not in ('driver_access','sink_access'):
            continue
        i=index[row['net_id']]; net=nets[i]
        pin=row['affected_pin']; j=(net['driver'],*net['sinks']).index(pin)
        assert row['fixed_pins_only'] in ('available','geometry')
        out.append((i,j,int(row['fixed_pins_only']=='geometry')))
assert len(out)==len({x[0] for x in out})==77 and sum(x[2] for x in out)==7
for item in sorted(out): print(*item,sep='\t')
