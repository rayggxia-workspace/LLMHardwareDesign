"""Copy-only residency experiments on actual source-closed pointwise regions.

Numerics use declared synthetic boundary fixtures, not model weights/tokens.
The exact original integer pointwise program is an independent reference.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import time

from memory import descriptor_ticks
from native_pointwise import execute
from resident_records import plan
from resident_replay import replay
from verify_primitive_cost import verify


def reference(program,graph,values):
    import numpy as np
    from full_integer import Q
    from wide_program import execute as original
    nodes={n['id']:n for n in program['instructions']};initial={}
    for o in graph['objects'].values():
        if o['kind']!='external':continue
        v=o['literal'] if 'literal' in o else values[(o['tensor'],o['index'])]
        initial[o['tensor']]=Q(np.asarray(v,dtype=np.int64),0)
    instructions=[{**deepcopy(nodes[name]),'shape':[]} for name in graph['primitives']]
    scalar={'instructions':instructions,'outputs':{n['id']:n['id'] for n in instructions}}
    return {name:int(v.raw) for name,v in original(scalar,initial,[],None).items()}


def run(ir,region_rows,*,width=8,cases=12):
    verify(ir);h=ir['hardware'];groups=h['tile_service_bindings']
    # Explicitly use an already declared P and E service instance. Do not
    # infer its surrounding SRAM/adapter capability from a macro letter.
    actors={}
    for kind,role in (('M','P'),('E','E')):
        group=sorted(groups[role])[0];m=h['leaf_inventory'][group]
        actors[group]={'kind':kind,'site':m['site'],'words':h['sites'][m['site']]['words'],
            'stride':8 if kind=='M' else 1,
            'load_ticks':descriptor_ticks(h['virtual_memory'],1,'load',m['io_write_ticks']),
            'store_ticks':descriptor_ticks(h['virtual_memory'],1,'store',m['io_read_ticks'])}
    zero=ir['native_constants']['0']['address_words']
    rows=[];rng=random.Random(220142)
    for rr in region_rows:
        # Each index was separately resolved/audited by the preceding survey.
        for graph in rr['graphs']:
            plans={};seconds={}
            strategies=(('spill',1,True,'copy_cost'),('greedy',1,False,'copy_cost'),
                ('dp',width,False,'copy_cost'),('future_greedy',1,False,'future_copies'),
                ('future_dp',width,False,'future_copies'))
            for name,w,spill,rank in strategies:
                began=time.monotonic();plans[name]=plan(graph,actors,zero,width=w,spill_all=spill,rank_policy=rank)
                seconds[name]=time.monotonic()-began
                if plans[name]['status']!='planned':raise ValueError('no resident region candidate')
            for trial in range(cases):
                values={}
                for o in graph['objects'].values():
                    if o['kind']!='external' or 'literal' in o:continue
                    value=(0,1,-1,32767,-32768)[trial] if trial<5 else rng.randrange(-(1<<20),1<<20)
                    if o['bits']==16:value=max(-32768,min(32767,value))
                    values[(o['tensor'],o['index'])]=value
                gold=execute(graph,values);expected=reference(ir['primitive_program'],graph,values)
                for name,key in graph['primitive_outputs'].items():
                    raw=gold[key]&0xffffffff;actual=raw-(1<<32) if raw&(1<<31) else raw
                    if actual!=expected[name]:raise ValueError('original integer program differs '+name)
                for candidate in plans.values():
                    actual=replay(graph,candidate,values)['observed_native_outputs']
                    if actual!={n['output']:gold[n['output']] for n in graph['operations']}:
                        raise ValueError('finite-S native execution differs')
            greedy_name=min(('greedy','future_greedy'),key=lambda name:plans[name]['copy_ticks'])
            selected=min(plans,key=lambda name:plans[name]['copy_ticks'])
            rows.append({'primitives':graph['primitives'],'index':graph['index'],'numerical_cases':cases,
                'plans':{name:{k:v[k] for k in ('copy_ticks','external_words','external_load_words','external_store_words','expanded','bound_calls')}
                         for name,v in plans.items()},'search_seconds':seconds,
                'same_pool_copy_gain_fraction':1-plans['dp']['copy_ticks']/plans['greedy']['copy_ticks'],
                'strongest_greedy':greedy_name,'selected':selected,
                'selected_vs_strongest_greedy_copy_gain_fraction':1-plans[selected]['copy_ticks']/plans[greedy_name]['copy_ticks'],
                'events':{name:v['events'] for name,v in plans.items()}})
            print(json.dumps({k:v for k,v in rows[-1].items() if k not in ('events','primitives')}),flush=True)
    return {'passed':True,'actors':actors,'rows':rows,'numerical_cases':sum(r['numerical_cases'] for r in rows),
        'scope':'native SSA copy-model DP and finite-S synthetic boundary fixtures; not actual-weight/full-model numerics, whole-region runtime, RTL, SystemC or energy qualification',
        'qualification_gap':'new K2 M feeds/width16 finals and E Min/Select residency require unchanged-RTL execution of emitted events before registering candidates'}


def main():
    p=argparse.ArgumentParser();p.add_argument('ir',type=Path);p.add_argument('regions',type=Path)
    p.add_argument('output',type=Path);p.add_argument('--width',type=int,default=8)
    p.add_argument('--cases',type=int,default=12);a=p.parse_args()
    if a.cases<1:raise ValueError('positive fixture count required')
    result=run(json.loads(a.ir.read_text()),json.loads(a.regions.read_text()),width=a.width,cases=a.cases)
    result['inputs_sha256']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.ir,a.regions)}
    a.output.write_text(json.dumps(result,separators=(',',':'))+'\n')


if __name__=='__main__':main()
