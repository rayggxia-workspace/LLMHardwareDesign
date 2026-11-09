"""Literal/native finite-S comparison for independent tile-column children.

Synthetic service timings are used only to construct test schedules. No
hardware latency, controller, energy or full-model qualification is claimed.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from dot_cache_replay import DotCache
from full_integer import round_shift
from loop_dp import search
from test_tile_partitions import example
from verify_loop_dp import verify
from wide_program import execute


def run(worker,output):
    output.mkdir(exist_ok=False);rng=np.random.default_rng(2201010);cases=[]
    for columns,k,shift in ((17,5,0),(19,7,8),(24,17,24),(32,2048,16)):
        ir=example(columns,two_e=True,k=k);node=ir['primitive_program']['instructions'][0]
        choices=[b for b in ir['tasks'][-1]['bindings'] if 'tile_partition' in b and
                 all(c['binding']['dot_tile']['tile'][1]>1 for c in b['parallel_shards']['children'])]
        b=min(choices,key=lambda b:b['ticks']);ir['tasks'][-1]['bindings']=[b]
        node['attributes']['shift']=shift
        for child in b['parallel_shards']['children']:child['binding']['dot_tile']['final_shift']=shift
        plan=search(ir['tasks'],ir['hardware'],width=8);verify(ir['tasks'],ir['hardware'],plan)
        a=rng.integers(-(1<<31),1<<31,size=(2,k),dtype=np.int64)
        a[0,:3]=[-2147483648,-32769,2147483647]
        weights=rng.integers(-32768,32768,size=(k,columns),dtype=np.int64)
        expected=np.clip(round_shift(a@weights,shift),-(1<<31),(1<<31)-1)
        reports={};results={}
        for kind,command in (('literal',None),('native',[str(worker.resolve())])):
            cache=DotCache(ir,plan,tile_worker=command)
            result=execute(ir['primitive_program'],{'a':a,'b':weights},[[1,2]],None,dot_executor=cache)
            np.testing.assert_array_equal(result['out'].raw,expected)
            reports[kind]=cache.report();results[kind]=result['out'].raw
        np.testing.assert_array_equal(results['literal'],results['native'])
        left=reports['literal']['tile_events'];right=reports['native']['tile_events']
        for l,r in zip(left,right):
            if l['counts']!=r['counts']:raise ValueError('tile partition native/literal transfer count differs')
        cases.append({'columns':columns,'K':k,'shift':shift,'plan':plan,'reports':reports,
            'input_sha256':hashlib.sha256(a.tobytes()+weights.tobytes()).hexdigest(),
            'output_sha256':hashlib.sha256(expected.tobytes()).hexdigest()})
    # A damaged deployed basis must affect an actual multi-column child.
    ir=example(17,two_e=True);b=next(b for b in ir['tasks'][-1]['bindings'] if 'tile_partition' in b and
        all(c['binding']['dot_tile']['tile'][1]>1 for c in b['parallel_shards']['children']))
    ir['tasks'][-1]['bindings']=[b];plan=search(ir['tasks'],ir['hardware'],width=1)
    ir['tile_constants']['records'][1][0]=0;cache=DotCache(ir,plan,tile_worker=[str(worker.resolve())])
    rejected=False
    try:execute(ir['primitive_program'],{'a':np.full((2,5),131071,dtype=np.int64),
        'b':np.ones((5,17),dtype=np.int64)},[[1,2]],None,dot_executor=cache)
    except ValueError:rejected=True
    finally:cache.tiles.close()
    if not rejected:raise ValueError('corrupted deployed basis was accepted')
    result={'passed':True,'cases':cases,'corrupted_basis_rejected':True,
        'worker_sha256':hashlib.sha256(worker.read_bytes()).hexdigest(),
        'scope':'finite-S native/literal arithmetic and transfer counts for tile partitions; no cycle/energy or system qualification'}
    (output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'cases':len(cases),'corrupted_basis_rejected':True}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('worker',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.worker,a.output)
