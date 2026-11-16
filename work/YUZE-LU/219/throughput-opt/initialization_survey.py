"""Measure paid initialization versus repeated finite-S replacement costs.

All initialization is real LOAD_ZERO work. Only the timing of existing guard
preparation changes; no extra capacity or free warm predecessor is assumed.
This is an experiment on supplied native regions, not a model-specific rule.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from native_pointwise import execute
from resident_continuation import invariants,totals
from resident_loop_replay import element
from resident_records import plan
from resident_replay import replay
from verify_resident_continuation import verify


def initialized_loop(graph,loop,actors,zero,timing,cells,*,width=8,rank='copy_cost'):
    persistent=invariants(graph,loop);count=loop['elements'];programs=[];seen={};cycle=None
    initial={'kind':'resident-readonly-continuation-v1','actors':{
        n:{'slots':[None]*(a['words']//a['stride']),
           'padding':list(range(cells)) if a['kind']=='M' else [],'bank':None} for n,a in actors.items()}}
    prologue=[]
    for name,a in actors.items():
        if a['kind']!='M':continue
        if cells>a['words']//a['stride']:raise ValueError('initializer exceeds real actor capacity')
        prologue.extend({'op':'LOAD_ZERO','actor':name,'address':at*a['stride']+offset,
                         'external_address':zero,'wait_ack':True} for at in range(cells) for offset in range(1,a['stride']))
    seed=initial if cells else None
    while len(programs)<count:
        key=json.dumps(seed,sort_keys=True,separators=(',',':'))
        if key in seen:cycle=seen[key];break
        # The first paid prologue cannot be part of a repeatable warm cycle.
        if programs:seen[key]=len(programs)
        if len(programs)>=256:raise ValueError('initialization policy did not close')
        p=plan(graph,actors,zero,persistent=persistent,initial=seed,width=width,
               rank_policy=rank,service_timing=timing)
        if p['status']!='planned':raise ValueError('initialized policy has no legal native program')
        if not programs and prologue:
            ticks=sum(actors[e['actor']]['load_ticks'] for e in prologue)
            p={**p,'initial_continuation':None,'events':prologue+p['events'],
               'copy_ticks':p['copy_ticks']+ticks,'total_ticks':p['total_ticks']+ticks,
               'external_load_words':p['external_load_words']+len(prologue),
               'external_words':p['external_words']+len(prologue)}
        programs.append(p);seed=p['continuation']
    sequence={'kind':'readonly-resident-loop-v1','elements':count,'persistent_records':persistent,
              'programs':programs,'cycle_start':cycle,'initialized_cells_per_M':cells}
    sequence['totals']=totals(sequence);verify(graph,loop,sequence,actors,zero,timing)
    return sequence


def check_values(recipe,sequence):
    r={**recipe,'plan':sequence['programs'][0],'continuation_loop':sequence}
    steps=min(r['loop']['elements'],2*len(sequence['programs'])+1);session=None
    for index in range(steps):
        graph,p=element(r,index);values={}
        for o in graph['objects'].values():
            if o['kind']=='external' and 'literal' not in o:
                value=1 if r['loop']['sources'][o['tensor']]=='scalar' else (index%3-1)*32767
                values[(o['tensor'],o['index'])]=value
        actual=replay(graph,p,values,session=session,return_session=True);session=actual['session']
        gold=execute(graph,values)
        if actual['observed_native_outputs']!={n['output']:gold[n['output']] for n in graph['operations']}:
            raise ValueError('initialized native finite-S program differs')
    return steps


def main():
    p=argparse.ArgumentParser();p.add_argument('ir',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--regions',type=int,default=2);p.add_argument('--width',type=int,default=8);a=p.parse_args()
    a.output.mkdir(exist_ok=False);ir=json.loads(a.ir.read_text());groups={}
    for r in ir['resident_recipes'].values():
        if r.get('continuation_loop'):groups.setdefault(tuple(r['primitives']),r)
    rows=[]
    for ri,r in enumerate(sorted(groups.values(),key=lambda r:len(r['graph']['operations']),reverse=True)[:a.regions]):
        actors=r['plan']['actors'];capacity=min(x['words']//x['stride'] for x in actors.values() if x['kind']=='M')
        budgets=sorted({0,capacity}|{2**n for n in range(capacity.bit_length())})
        for cells in budgets:
            for name,width,rank in (('greedy',1,'copy_cost'),('future_greedy',1,'future_copies'),
                                    ('dp',a.width,'copy_cost'),('future_dp',a.width,'future_copies')):
                start=time.monotonic()
                sequence=initialized_loop(r['graph'],r['loop'],actors,r['plan']['zero_address'],ir['resident_timing'],
                                          cells,width=width,rank=rank)
                checked=check_values(r,sequence)
                key=f'region-{ri}-cells-{cells}-{name}'
                (a.output/(key+'.json')).write_text(json.dumps(sequence,separators=(',',':'))+'\n')
                row={'region':ri,'primitives':r['primitives'],'strategy':name,'initial_cells':cells,
                     'programs':len(sequence['programs']),'numeric_elements':checked,'seconds':time.monotonic()-start,
                     **sequence['totals']}
                rows.append(row);print(json.dumps(row),flush=True)
    result={'passed':True,'rows':rows,'ir_sha256':hashlib.sha256(a.ir.read_bytes()).hexdigest(),
            'scope':'paid initialization, source native work, finite-S/ACK and synthetic changing elements; not full graph, actual weights, new RTL or system performance'}
    (a.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
