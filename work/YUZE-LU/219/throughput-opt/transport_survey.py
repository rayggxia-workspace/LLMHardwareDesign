"""Sensitivity experiment on explicit, unqualified inter-S service candidates.

All policies receive the same paths, finite stores, native work and net budget.
This cannot be used as current-hardware token/s or a qualified speedup claim.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from native_pointwise import execute
from resident_continuation import compile_loop,visits
from resident_loop_replay import element
from resident_replay import replay
from verify_resident_continuation import verify


def check(recipe,sequence):
    r={**recipe,'plan':sequence['programs'][0],'continuation_loop':sequence};session=None
    count=min(sequence['elements'],2*len(sequence['programs'])+1)
    for index in range(count):
        graph,p=element(r,index);values={}
        for o in graph['objects'].values():
            if o['kind']=='external' and 'literal' not in o:
                values[o['tensor'],o['index']]=1 if r['loop']['sources'][o['tensor']]=='scalar' else (index%3-1)*32767
        actual=replay(graph,p,values,session=session,return_session=True);session=actual['session']
        gold=execute(graph,values)
        if actual['observed_native_outputs']!={n['output']:gold[n['output']] for n in graph['operations']}:
            raise ValueError('candidate transport native output differs')
    return count


def attribution(recipe,sequence):
    rows=Counter();graph=recipe['graph'];live=set(graph['live_out'].values())
    for p,count in zip(sequence['programs'],visits(sequence)):
        for e in p['events']:
            op=e['op']
            if op=='TRANSFER':category='candidate_onchip_transfers'
            elif op=='LOAD_ZERO':category='guard_zero_reads'
            elif op=='STORE':category='live_out_stores' if e['record'] in live else 'intermediate_spills'
            elif op=='LOAD':
                o=graph['objects'][e['record']]
                category='intermediate_reloads' if o['kind']=='produced' else 'constant_reads' if o['kind']=='constant' or 'literal' in o else 'input_reads'
            else:continue
            rows[category]+=count
    return dict(rows)


def main():
    p=argparse.ArgumentParser();p.add_argument('ir',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--regions',type=int,default=2);p.add_argument('--width',type=int,default=8)
    p.add_argument('--extra-ticks',type=int,nargs='+',default=[1,36,78])
    p.add_argument('--net-budgets',type=int,nargs='+',default=[0,1,2])
    p.add_argument('--strategies',nargs='+',choices=['greedy','future_greedy','dp','future_dp'],
                   default=['greedy','future_greedy','dp','future_dp']);a=p.parse_args()
    a.output.mkdir(exist_ok=False);ir=json.loads(a.ir.read_text());groups={};rows=[]
    frozen=a.output/'source';frozen.mkdir();source_hashes={}
    for source in [*Path('project/experiments/block_synthesis').glob('*.py'),Path(__file__)]:
        data=source.read_bytes();(frozen/source.name).write_bytes(data)
        source_hashes[source.as_posix()]=hashlib.sha256(data).hexdigest()
    (a.output/'source-manifest.json').write_text(json.dumps(source_hashes,indent=2)+'\n')
    for r in ir['resident_recipes'].values():
        if r.get('continuation_loop'):groups.setdefault(tuple(r['primitives']),r)
    for ri,r in enumerate(sorted(groups.values(),key=lambda r:len(r['graph']['operations']),reverse=True)[:a.regions]):
        actors=r['plan']['actors'];names=tuple(actors);h=ir['hardware']
        for extra in a.extra_ticks:
            paths=[{'kind':'resident-transport-candidate-v1','id':s+'->'+d,'source':s,'destination':d,
                    'word_bits':128,'ticks':h['leaf_inventory'][s]['io_read_ticks']+h['leaf_inventory'][d]['io_write_ticks']+extra,
                    'nets':[s+'->'+d+'.stored-link-bundle'],
                    'resources':[h['leaf_inventory'][s]['io_resource'],h['leaf_inventory'][d]['io_resource'],s+'.tx-hold'],
                    'protocol':'reserved-sink/source-held-through-write-ack',
                    'provenance':'unqualified sensitivity candidate; declared IO abstraction plus explicit extra ticks; not product path calibration'}
                   for s,d in (names,names[::-1])]
            for budget in a.net_budgets:
                # Repeating budget-zero for each timing is intentional: it
                # checks the fallback is invariant to unavailable path costs.
                for name,width,rank in (('greedy',1,'copy_cost'),('future_greedy',1,'future_copies'),
                                        ('dp',a.width,'copy_cost'),('future_dp',a.width,'future_copies')):
                    if name not in a.strategies:continue
                    start=time.monotonic()
                    seq=compile_loop(r['graph'],r['loop'],actors,r['plan']['zero_address'],width=width,
                                     rank_policy=rank,service_timing=ir['resident_timing'],
                                     transports=paths,transport_net_budget=budget)
                    verify(r['graph'],r['loop'],seq,actors,r['plan']['zero_address'],ir['resident_timing'])
                    checked=check(r,seq);key=f'region-{ri}-extra-{extra}-budget-{budget}-{name}'
                    (a.output/(key+'.json')).write_text(json.dumps(seq,separators=(',',':'))+'\n')
                    row={'region':ri,'primitives':r['primitives'],'strategy':name,'net_budget':budget,'extra_ticks':extra,
                         'path_ticks':[p['ticks'] for p in paths],'programs':len(seq['programs']),'numeric_elements':checked,
                         'seconds':time.monotonic()-start,**seq['totals'],'traffic':attribution(r,seq),
                         'static_transport_nets':sorted({n for p in seq['programs'] for n in p['transport_nets']})}
                    rows.append(row);print(json.dumps(row),flush=True)
    report={'passed':True,'rows':rows,'ir_sha256':hashlib.sha256(a.ir.read_bytes()).hexdigest(),
            'scope':'candidate-path sensitivity, supplied finite S/native work and synthetic values only; no qualified P/U path, actual weights, full graph, controller, energy or token/s'}
    (a.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
