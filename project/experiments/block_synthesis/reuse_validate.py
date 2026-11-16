"""Full 3B selected cache program versus all-spill integer execution and HF."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from full_integer import Interpreter,Oracle
from wide_program import execute
from dot_cache_replay import DotCache,order_program
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost


def main():
    p=argparse.ArgumentParser();p.add_argument('ir',type=Path);p.add_argument('plan',type=Path)
    p.add_argument('weights',type=Path);p.add_argument('calibration',type=Path);p.add_argument('logits',type=Path)
    p.add_argument('--tile-worker',type=Path)
    p.add_argument('output',type=Path);p.add_argument('oracle',nargs=argparse.REMAINDER);a=p.parse_args()
    a.output.mkdir(exist_ok=False);ir=json.loads(a.ir.read_text());plan=json.loads(a.plan.read_text())
    audit=verify(ir['tasks'],ir['hardware'],plan);cost=verify_cost(ir)
    weights=json.loads(a.weights.read_text());weights['_root']=str(a.weights.parent.parent)
    calibration=json.loads(a.calibration.read_text());oracle=Oracle(a.oracle)
    reference=Interpreter(ir['model'],weights,calibration,oracle)
    original=ir['primitive_program'];selected=order_program(original,plan,ir.get('primitive_stages'))
    (a.output/'selected-program.json').write_text(json.dumps(selected,indent=2)+'\n')
    selected=json.loads((a.output/'selected-program.json').read_text())
    logits=np.load(a.logits);samples=[];bounds={}
    for i,ids in enumerate(([[1,2]],[[3,4]],[[42,43]])):
        base=execute(original,reference.initial,ids,oracle)[reference.m['outputs'][0]]
        cache=DotCache(ir,plan,tile_worker=[str(a.tile_worker)] if a.tile_worker else None)
        result=execute(selected,reference.initial,ids,oracle,bounds,dot_executor=cache)[reference.m['outputs'][0]]
        equal=base.exponent==result.exponent and np.array_equal(base.raw,result.raw)
        actual=result.raw.astype(np.float64)*2.**result.exponent;expected=logits['reference'+str(i)]
        error=float(np.linalg.norm(actual-expected)/np.linalg.norm(expected))
        top=bool(np.array_equal(np.argmax(actual,axis=-1),np.argmax(expected,axis=-1)))
        row={'ids':ids,'bit_exact_to_all_spill':equal,'relative_l2':error,'top1_equal':top,
            'logits_raw_sha256':hashlib.sha256(result.raw.tobytes()).hexdigest(),
            'cache':cache.report(),'passed':equal and error<=.02 and top}
        samples.append(row);print(json.dumps({k:v for k,v in row.items() if k!='cache'}),flush=True)
    oracle.close()
    report={'status':'selected_cache_program_passed' if all(s['passed'] for s in samples) else 'failed',
        'samples':samples,'audit':audit,'native_cost_check':cost,'bounds':bounds,
        'source_sha256':ir['model']['sha256'],
        'inputs':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.ir,a.plan,a.weights,a.calibration,a.logits)},
        'scope':'full generated integer model, selected finite SRAM stripes/tiles and real scalar conversion semantics; compiler simulation, not MC/LC binary, DMA, timing or RTL'}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    if report['status']=='failed':raise ValueError('cache program numerical acceptance failed')


if __name__=='__main__':main()
