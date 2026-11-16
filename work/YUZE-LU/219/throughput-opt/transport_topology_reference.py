"""Strengthen the greedy reference by enumerating a small static path catalog.

For two directed paths this is a useful exact topology reference; exponential
enumeration is explicitly not offered as a general nine-group algorithm.
The greedy allocator still makes state-dependent placements/copy decisions.
"""
import argparse
from itertools import combinations
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from resident_continuation import compile_loop
from verify_resident_continuation import verify
from transport_survey import check,attribution


def main():
    p=argparse.ArgumentParser()
    for name in ('ir','survey','output'):p.add_argument(name,type=Path)
    a=p.parse_args();a.output.mkdir(exist_ok=False);ir=json.loads(a.ir.read_text());rows=[]
    groups={}
    for r in ir['resident_recipes'].values():
        if r.get('continuation_loop'):groups.setdefault(tuple(r['primitives']),r)
    recipe=sorted(groups.values(),key=lambda r:len(r['graph']['operations']),reverse=True)[0]
    # Already completed candidate case supplies exactly the original path
    # timings/IDs and finite-S contract; do not improve them for this baseline.
    seed=json.loads((a.survey/'region-0-extra-1-budget-1-dp.json').read_text())
    paths=seed['programs'][0]['transports'];actors=recipe['plan']['actors']
    for count in range(2):
        for subset in combinations(paths,count):
            for policy in ('copy_cost','future_copies'):
                start=time.monotonic()
                seq=compile_loop(recipe['graph'],recipe['loop'],actors,recipe['plan']['zero_address'],width=1,
                                 rank_policy=policy,service_timing=ir['resident_timing'],transports=subset,transport_net_budget=1)
                verify(recipe['graph'],recipe['loop'],seq,actors,recipe['plan']['zero_address'],ir['resident_timing'])
                checked=check(recipe,seq);key=f'case-{len(rows)}'
                (a.output/(key+'.json')).write_text(json.dumps(seq,separators=(',',':'))+'\n')
                row={'paths':[x['id'] for x in subset],'policy':policy,'seconds':time.monotonic()-start,
                     'numeric_elements':checked,**seq['totals'],'traffic':attribution(recipe,seq)}
                rows.append(row);print(json.dumps(row),flush=True)
    best=min(rows,key=lambda r:r['total_ticks'])
    result={'passed':True,'cases':rows,'best':best,
            'scope':'stronger greedy reference on two unqualified candidate paths; exact subset enumeration only for this tiny catalog, not full graph or current product performance'}
    (a.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
