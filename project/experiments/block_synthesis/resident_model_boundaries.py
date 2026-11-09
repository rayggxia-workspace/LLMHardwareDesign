"""Real-weight full-graph exports driving sampled finite-S resident regions.

Extra reference outputs observe original SSA tensors without changing the
executed instructions. This is not full-model residency or timing simulation.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import numpy as np

from full_integer import Interpreter,Oracle
from native_pointwise import execute as native_execute
from resident_replay import replay
from resident_survey import run
from resident_timing import audit,read_qualification
from verify_primitive_cost import verify
from wide_program import execute


def main():
    p=argparse.ArgumentParser()
    for name in ('full_ir','cut_ir','regions','proof','weights','calibration','logits','output'):
        p.add_argument(name,type=Path)
    p.add_argument('oracle',nargs=argparse.REMAINDER);a=p.parse_args();a.output.mkdir(exist_ok=False)
    def save(name,value):(a.output/(name+'.json')).write_text(json.dumps(value,separators=(',',':'))+'\n')
    full=json.loads(a.full_ir.read_text());cut=json.loads(a.cut_ir.read_text());regions=json.loads(a.regions.read_text())
    full_sha=hashlib.sha256(a.full_ir.read_bytes()).hexdigest()
    if cut['primitive_program']['diagnostic_cut']['source_sha256']!=full_sha:
        raise ValueError('resident boundary cut has a different enclosing full source')
    verify(full);verify(cut)
    timing=read_qualification(a.proof,[a.proof/('simulate-'+str(i)+'.log') for i in range(3)])
    save('qualification',timing)
    survey=run(cut,regions,cases=1,service_timing=timing);save('timed-survey',survey)
    rows=survey['rows'];graphs=[g for r in regions for g in r['graphs']]
    if len(rows)!=len(graphs):raise ValueError('resident boundary graph coverage differs')
    program=deepcopy(full['primitive_program']);nodes={n['id']:n for n in program['instructions']}
    want={n for graph in graphs for n in graph['primitives']}
    want|={o['tensor'] for graph in graphs for o in graph['objects'].values() if o['kind']=='external'}
    for node in cut['primitive_program']['instructions']:
        if nodes.get(node['id'])!=node:raise ValueError('diagnostic primitive differs from enclosing graph')
    for name in want:
        if name in nodes:program['outputs']['resident-boundary:'+name]=name
        elif name not in program['initial_formats']:raise ValueError('resident boundary has no enclosing producer')
    weights=json.loads(a.weights.read_text());weights['_root']=str(a.weights.parent.parent)
    calibration=json.loads(a.calibration.read_text());oracle=Oracle(a.oracle)
    original=Interpreter(full['model'],weights,calibration,oracle);hf=np.load(a.logits)
    samples=[];fixtures=[]
    for sample,ids in enumerate(([[1,2]],[[3,4]],[[42,43]])):
        outputs=execute(program,original.initial,ids,oracle)
        final=outputs[full['model']['outputs'][0]]
        values=final.raw.astype(np.float64)*2.**final.exponent;reference=hf['reference'+str(sample)]
        error=float(np.linalg.norm(values-reference)/np.linalg.norm(reference))
        top=bool(np.array_equal(np.argmax(values,axis=-1),np.argmax(reference,axis=-1)))
        if error>.02 or not top:raise ValueError('enclosing full model reference acceptance failed')
        native_count=0
        for index,(graph,row) in enumerate(zip(graphs,rows)):
            if row['primitives']!=graph['primitives'] or row['index']!=graph['index']:
                raise ValueError('resident region/sample association differs')
            inputs={}
            for obj in graph['objects'].values():
                if obj['kind']!='external' or 'literal' in obj:continue
                name=obj['tensor'];source=outputs.get('resident-boundary:'+name,original.initial.get(name))
                if source is None:raise ValueError('actual resident source value missing')
                inputs[(name,obj['index'])]=int(np.asarray(source.raw).reshape(-1)[obj['index']])
            gold=native_execute(graph,inputs)
            for name,key in graph['primitive_outputs'].items():
                word=gold[key]&0xffffffff;actual=word-(1<<32) if word&(1<<31) else word
                expected=int(outputs['resident-boundary:'+name].raw.reshape(-1)[graph['index']])
                if actual!=expected:raise ValueError('resident primitive differs from real enclosing model '+name)
            for strategy,metrics in row['plans'].items():
                plan={**metrics,'events':row['events'][strategy],'actors':survey['actors'],
                      'zero_address':cut['native_constants']['0']['address_words'],'service_timing':timing}
                audit(plan,timing);observed=replay(graph,plan,inputs)['observed_native_outputs']
                if observed!={n['output']:gold[n['output']] for n in graph['operations']}:
                    raise ValueError('real model finite-S resident program differs')
            native_count+=len(graph['operations'])
            fixtures.append({'sample':sample,'ids':ids,'region_index':index,'element':graph['index'],
                             'inputs':[[name,i,value] for (name,i),value in inputs.items()]})
        record={'sample':sample,'ids':ids,'regions':len(graphs),'native_operations_per_strategy':native_count,
                'relative_l2':error,'top1_equal':top,'logits_raw_sha256':hashlib.sha256(final.raw.tobytes()).hexdigest(),'passed':True}
        samples.append(record);print(json.dumps(record),flush=True)
    oracle.close();save('actual-boundary-fixtures',fixtures)
    save('report',{'passed':True,'samples':samples,'actual_region_cases':len(fixtures),
        'strategies':list(rows[0]['plans']),'inputs_sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest()
            for f in (a.full_ir,a.cut_ir,a.regions,a.weights,a.calibration,a.logits)},
        'scope':'three real-weight full original integer executions and sampled resident regions; not full-model resident execution, LC/DMA timing, SystemC, physical, energy or token/s qualification'})


if __name__=='__main__':main()
