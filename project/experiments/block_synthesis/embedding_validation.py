"""Real checkpoint embedding quantization and indexed virtual-memory replay.

Uses the full benchmark's actual Gather node and complete embedding table.
This is an embedding conversion test, not a full-model success claim.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
from safetensors import safe_open

from indexed_memory import index_address
from numeric import Format, pack, unpack
from quantization import quantize
from run import compile_model


def replay(result, raw_table, ids):
    """Interpret emitted addresses/copies; do not read planner value contents."""
    ir=result['outputs']['program_ir']
    regions={r['value']:r for r in ir['external_regions']}
    table_name=next(iter(result['graph']['external_objects']))
    base=regions[table_name]['address_words']
    fmt=Format.read(result['graph']['external_objects'][table_name]['format'])
    table_words=raw_table.size//fmt.lanes
    external={}
    for n,v in result['graph']['values'].items():
        if v.get('site')==result['resolved_hardware']['external']:
            raw=[int(ids.reshape(-1)[v['offset_elements']])]
            external[regions[n]['address_words']]=pack(raw,Format.read(v['format']))[0]
    local={}
    def read(site,address):
        if site!=result['resolved_hardware']['external']:
            return local[(site,address)]
        if base<=address<base+table_words:
            start=(address-base)*fmt.lanes
            return pack(raw_table.reshape(-1)[start:start+fmt.lanes].tolist(),fmt)[0]
        return external[address]
    def put(site,address,value):
        if site==result['resolved_hardware']['external']:external[address]=value
        else:local[(site,address)]=value
    for request in sorted(ir['requests'],key=lambda r:(r['planned_interval'][1],r['id'])):
        if request['kind']=='copy':
            a,b=request['source'],request['destination']
            data=[read(a['site'],a['address_words']+i) for i in range(a['words'])]
            for i,word in enumerate(data):put(b['site'],b['address_words']+i,word)
        else:
            p=request['native_program'][0]
            if p['command']!='VirtualIndexedLoad':raise ValueError('unexpected service')
            a,b=request['inputs'][0],request['outputs'][0]
            index=unpack([read(a['site'],a['address_words'])],Format(p['index_bits'],0,1),1)[0]
            offset=index_address(index,p['rows'],p['row_words'],p['offset_words'],p['words'],p['address_bits'])//16
            words=[read(result['resolved_hardware']['external'],p['table_base_address_words']+offset+i)
                   for i in range(p['words'])]
            for i,word in enumerate(words):put(b['site'],b['address_words']+i,word)
    output=np.empty(ids.shape+(raw_table.shape[1],),dtype=np.int16).reshape(-1)
    for n in result['graph']['outputs']:
        v=result['graph']['values'][n]
        raw=unpack([read(result['resolved_hardware']['external'],regions[n]['address_words']+i)
                    for i in range(v['words'])],fmt,v['valid_elements'])
        output[v['offset_elements']:v['offset_elements']+len(raw)]=raw
    expected=np.take(raw_table,ids,axis=0).reshape(-1)
    if not np.array_equal(output,expected):raise ValueError('indexed memory replay differs from independent numpy.take')
    return {'elements':int(output.size),'output_sha256':hashlib.sha256(output.tobytes()).hexdigest(),
            'independent_reference':'numpy.take on actual quantized table', 'passed':True}


def main():
    p=argparse.ArgumentParser();p.add_argument('imported',type=Path);p.add_argument('hardware',type=Path)
    p.add_argument('checkpoint',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();a.output.mkdir(exist_ok=False)
    model=json.loads(a.imported.read_text());h=json.loads(a.hardware.read_text())
    node=next(t for t in model['tasks'] if t['op']=='Gather')
    table_name=node['inputs'][0]
    key=table_name.removeprefix('model.')
    index=json.loads((a.checkpoint/'model.safetensors.index.json').read_text())
    shard=a.checkpoint/index['weight_map'][key]
    with safe_open(str(shard),framework='pt',device='cpu') as f:
        table=f.get_tensor(key).float().numpy()
    # Chunked real conversion avoids a full FP64 copy of the 311M-element table.
    maximum=max(float(np.abs(table[r:r+1024]).max()) for r in range(0,len(table),1024))
    import math
    exponent=math.ceil(math.log2(maximum/32767)) if maximum else 0
    raw=np.lib.format.open_memmap(str(a.output/'embedding-int16.npy'),mode='w+',dtype='<i2',shape=table.shape)
    receipts=[]
    for r in range(0,len(table),1024):
        raw[r:r+1024],receipt=quantize(table[r:r+1024],exponent=exponent,lanes=2)
        receipts.append(receipt)
    raw.flush()
    selected=deepcopy(model);selected['tasks']=[node];selected['outputs']=node['outputs']
    selected['values']={n:deepcopy(model['values'][n]) for n in node['inputs']+node['outputs']}
    for n in (table_name,node['outputs'][0]):
        selected['values'][n]['format']={'bits':16,'exponent':exponent,'lanes':2}
        selected['values'][n]['dtype']='INT16'
    node=selected['tasks'][0];node['numeric']='INT16'
    ids=np.array([[1,2]],dtype=np.int64)
    if selected['values'][node['inputs'][1]]['shape']!=list(ids.shape):
        raise ValueError('this validation retains the existing B1/S2 export scope')
    result=compile_model(selected,h,seconds=1,rounds=0,cover_limit=1)
    if result['status']!='planned':raise ValueError('embedding has no verified plan')
    checks=[replay(result,raw,test) for test in (ids,np.array([[0,-1]],dtype=np.int64))]
    summary={'status':'embedding_verified','scope':'real complete 3B model embedding subgraph only',
        'table_shape':list(table.shape),'parameter_elements':int(table.size),'format':receipts[0]['format'],
        'clipped_elements':sum(r['clipped_elements'] for r in receipts),
        'max_abs_error':max(r['max_abs_error'] for r in receipts),
        'tasks':len(result['graph']['tasks']),'external_words':result['plan']['external_words'],
        'verification':result['verification'],'numeric_replays':checks,
        'address_generation':'functional virtual interface; timing/RTL unqualified',
        'remaining_full_model_work':['activation quantization and accuracy','graph normalization','runtime layouts','whole graph planning'],
        'inputs':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in (a.imported,a.hardware)},
        'checkpoint_shard':str(shard),'quantization_chunks':receipts}
    for name,obj in [('model.json',selected),('result.json',result),('summary.json',summary)]:
        (a.output/name).write_text(json.dumps(obj,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='quantization_chunks'}))


if __name__=='__main__':main()
