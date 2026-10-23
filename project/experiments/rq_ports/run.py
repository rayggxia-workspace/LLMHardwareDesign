"""Frozen 384-run E2a local fixture; exact values and conditional service times."""
import argparse
from collections import Counter
import gzip
import itertools
import json
from pathlib import Path
import statistics
from common import HERE,provenance,save,npz,digest
from model import build,audit_schedule
from numeric import make_fixtures


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--development',action='store_true');a=p.parse_args()
    if a.output.exists():raise ValueError('refuse overwrite')
    prod=provenance(a.development);cfg=json.loads((HERE/'experiment.json').read_text())
    fixtures,arrays,source=make_fixtures(cfg);runs=[];graphs={}
    for fixture in fixtures:
        for lanes,window,cost,policy,placement in itertools.product(cfg['lanes'],cfg['windows'],
                cfg['consumer_costs_per_8_values'],cfg['policies'],cfg['placements']):
            graph=build(fixture['rows'],fixture['K'],fixture['scale_mode'],placement,lanes,window,cost,cfg['jobs_per_fixture'])
            scheduled=graph.schedule(policy);audit=audit_schedule(graph,scheduled)
            name=fixture['name']+f'.l{lanes}.w{window}.c{cost}.{policy}.{placement}'
            runs.append(dict(name=name,fixture=fixture['name'],rows=fixture['rows'],K=fixture['K'],scale_mode=fixture['scale_mode'],
                placement=placement,lanes=lanes,window=window,consumer_cost=cost,policy=policy,
                cycles=scheduled['cycles'],busy=scheduled['busy'],traffic=dict(graph.bytes),audit=audit,
                output_sha256=fixture['output_sha256'],row_sum_sha256=fixture['row_sum_sha256']))
    if len(runs)!=384:raise AssertionError('frozen case count')
    pairs=[]
    for i in range(0,len(runs),2):
        near,shared=runs[i:i+2]
        assert near['placement']=='near' and shared['placement']=='shared'
        assert near['output_sha256']==shared['output_sha256'] and near['row_sum_sha256']==shared['row_sum_sha256']
        pairs.append(dict(near=near['name'],shared=shared['name'],rows=near['rows'],lanes=near['lanes'],policy=near['policy'],
            near_cycles=near['cycles'],shared_cycles=shared['cycles'],
            near_speedup=shared['cycles']/near['cycles'],cycle_reduction_fraction=(shared['cycles']-near['cycles'])/shared['cycles'],
            wire_saved=shared['traffic']['wire']-near['traffic']['wire']))
    a.output.mkdir(parents=True);save(a.output/'fixtures.json',dict(source=source,fixtures=fixtures));npz(a.output/'integer-fixtures.npz',arrays)
    save(a.output/'runs.json',runs);save(a.output/'pairs.json',pairs)
    summary={'runs':len(runs),'pairs':len(pairs),'audited_nodes':sum(x['audit']['nodes'] for x in runs),
        'audited_packets':sum(x['audit']['packets'] for x in runs),
        'near_faster':sum(x['near_cycles']<x['shared_cycles'] for x in pairs),
        'equal_cycles':sum(x['near_cycles']==x['shared_cycles'] for x in pairs),
        'near_slower':sum(x['near_cycles']>x['shared_cycles'] for x in pairs),
        'minimum_cycle_reduction':min(x['cycle_reduction_fraction'] for x in pairs),
        'maximum_cycle_reduction':max(x['cycle_reduction_fraction'] for x in pairs),
        'median_cycle_reduction':statistics.median(x['cycle_reduction_fraction'] for x in pairs),
        'scope':'conditional fixed-semantic service fixture; not calibrated hardware cycles/PPA/end-to-end LLM'}
    save(a.output/'summary.json',summary)
    # Choose extremal and decode witnesses after the frozen sweep, explicitly for audit, not parameter tuning.
    chosen=[min(pairs,key=lambda x:x['cycle_reduction_fraction']),max(pairs,key=lambda x:x['cycle_reduction_fraction']),
            next(x for x in pairs if x['rows']==1)]
    witnesses=[]
    byname={r['name']:r for r in runs}
    for pair in chosen:
        for side in ('near','shared'):
            name=pair[side]
            if name in witnesses:continue
            r=byname[name];g=build(r['rows'],r['K'],r['scale_mode'],r['placement'],r['lanes'],r['window'],r['consumer_cost'],cfg['jobs_per_fixture'])
            s=g.schedule(r['policy'])
            raw=json.dumps(dict(run=name,nodes=g.nodes,packets=g.packets,leases=g.leases,sizes=g.sizes,scheduled=s),
                           sort_keys=True,separators=(',',':')).encode()
            filename=f'witness-{len(witnesses):02}.json.gz';(a.output/filename).write_bytes(gzip.compress(raw,mtime=0))
            witnesses.append(name)
    save(a.output/'witnesses.json',witnesses)
    save(a.output/'manifest.json',dict(producer=prod,source=source,
        artifacts={p.name:{'bytes':p.stat().st_size,'sha256':digest(p)} for p in a.output.iterdir() if p.is_file()}))
    print(json.dumps(summary))

if __name__=='__main__':main()
