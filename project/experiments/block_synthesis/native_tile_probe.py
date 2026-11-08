"""Cross-check accelerated numeric host interpreter against literal SRAM replay.

Service durations here are explicitly synthetic: this qualifies the numerical
simulator/protocol, never a new hardware timing table or system performance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from full_integer import round_shift
from native_tile_replay import NativeTileReplay
from test_tile_recipe import fixture
from tile_recipe import cost
from tile_replay import TileReplay


def main():
    parser=argparse.ArgumentParser();parser.add_argument('worker',type=Path);parser.add_argument('output',type=Path)
    a=parser.parse_args();a.worker=a.worker.resolve();a.output.mkdir(exist_ok=False)
    hardware,q=fixture()
    for site in hardware['sites'].values():site['words']=1024
    ir={'hardware':hardware,'tile_constants':{'records':[[0]*8]+[[int(i==j) for i in range(8)] for j in range(8)]}}
    p=hardware['leaf_inventory']['matrix'];e=hardware['leaf_inventory']['vector']
    literal=TileReplay(ir);native=NativeTileReplay(ir,[str(a.worker)])
    rng=np.random.default_rng(22081);cases=[];began=time.monotonic()
    shapes=[(r,n,5+(r*n)%7,(r+n)%4*8) for r in range(1,9) for n in range(1,9)]
    shapes.extend([(2,8,2048,16),(8,8,33,24),(1,8,17,0),(3,5,7,8)])
    def inputs(rows,columns,k):
        source=rng.integers(-(1<<31),1<<31,size=(rows,k),dtype=np.int64)
        source[0,:min(k,4)]=[-2147483648,-32769,-32768,2147483647][:min(k,4)]
        weights=rng.integers(-32768,32768,size=(k,columns),dtype=np.int64)
        lo=(source+32768)%65536-32768
        records=np.stack([lo,source>>16,(lo<0).astype(np.int64)],axis=-1)
        return source,weights,records
    for case,(rt,ct,k,shift) in enumerate(shapes):
        rows,columns=rt+1,ct+3
        source,weights,records=inputs(rows,columns,k)
        node={'id':'case-'+str(case),'shape':[rows,columns]}
        binding={'macro_binding':{'M':'matrix',**({'E':'vector'} if ct>1 else {})},
            'dot_tile':{'rows':rows,'columns':columns,'K':k,'tile':[rt,ct],'final_shift':shift},
            'tile_work':cost(rows,columns,k,rt,ct,q,hardware['virtual_memory'],p,e)}
        raw,canonical=literal.dot(node,records,weights,binding)
        native_raw,native_final=native.dot(node,records,weights,binding)
        gold=source@weights
        expected=np.clip(round_shift(gold,shift),-(1<<31),(1<<31)-1)
        for actual,wanted in ((raw,gold),(native_raw,gold),(canonical,expected),(native_final,expected)):
            np.testing.assert_array_equal(actual,wanted)
        lhs=literal.events[-1];rhs=native.events[-1]
        if lhs!=rhs:raise ValueError('literal/native finite-S event counts differ')
        cases.append({'case':case,'rows':rows,'columns':columns,'K':k,'tile':[rt,ct],'shift':shift,
            'raw_sha256':hashlib.sha256(native_raw.tobytes()).hexdigest(),
            'final_sha256':hashlib.sha256(native_final.tobytes()).hexdigest(),'event':rhs})
    native.close()
    # Independent negative: accepted native arithmetic must expose corrupt
    # basis constants rather than quietly substitute a reference matmul.
    source,weights,records=inputs(2,8,3);node={'id':'corrupt-basis','shape':[2,8]}
    binding={'macro_binding':{'M':'matrix','E':'vector'},
        'dot_tile':{'rows':2,'columns':8,'K':3,'tile':[2,8],'final_shift':16},
        'tile_work':cost(2,8,3,2,8,q,hardware['virtual_memory'],p,e)}
    native=NativeTileReplay(ir,[str(a.worker)])
    native.constants={'records':[[0]*8 for _ in range(9)]}
    _,bad=native.dot(node,records,weights,binding);native.close()
    expected=np.clip(round_shift(source@weights,16),-(1<<31),(1<<31)-1)
    if np.array_equal(bad,expected):raise ValueError('corrupt-basis negative was not observable')
    result={'passed':True,'cases':cases,'case_count':len(cases),'corrupt_basis_observed':True,
        'seconds':time.monotonic()-began,'worker_sha256':hashlib.sha256(a.worker.read_bytes()).hexdigest(),
        'source_sha256':{name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ('native_tile_probe.py','native_tile_replay.cpp','native_tile_replay.py','tile_replay.py')},
        'scope':'host numeric simulator, literal finite S and exact descriptor/command counts; synthetic service table; not RTL/cycle/energy/system qualification'}
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'}),flush=True)


if __name__=='__main__':main()
