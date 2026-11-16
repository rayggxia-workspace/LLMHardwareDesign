"""Full integer graph execution with selected resident loops replacing ops.

All elements of each selected region execute finite-S/ACK events. Other graph
instructions use the existing integer interpreter. This is not a full selected
hardware/DMA/controller or system-timing simulation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np

from full_integer import Interpreter,Oracle
from resident_loop_replay import Execution
from resident_timing import read_qualification
from verify_cover_frontier import verify as verify_schedule
from verify_primitive_cost import verify as verify_original
from verify_resident_bindings import verify as verify_resident
from wide_program import execute


def main():
    p=argparse.ArgumentParser()
    for name in ('full_ir','cover_ir','plan','proof','weights','calibration','logits','gold','output'):
        p.add_argument(name,type=Path)
    p.add_argument('oracle',nargs=argparse.REMAINDER);a=p.parse_args();a.output.mkdir(exist_ok=False)
    def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    full=json.loads(a.full_ir.read_text());ir=json.loads(a.cover_ir.read_text());plan=json.loads(a.plan.read_text())
    gold=json.loads(a.gold.read_text());frozen=set(gold['inputs'].values())
    if any(sha(path) not in frozen for path in (a.full_ir,a.weights,a.calibration,a.logits)):
        raise ValueError('resident enclosing input differs from accepted original reference')
    cut=ir['primitive_program'].get('diagnostic_cut')
    if cut:
        if cut['source_sha256']!=sha(a.full_ir):raise ValueError('resident cut source differs')
    elif ir['primitive_program']!=full['primitive_program']:raise ValueError('resident full source differs')
    q=read_qualification(a.proof,[a.proof/('simulate-'+str(i)+'.log') for i in range(3)])
    if q!=ir['resident_timing']:raise ValueError('resident measured profile differs from frozen proof')
    audits={'original':verify_original(full),'resident':verify_resident(ir),
            'schedule':verify_schedule(ir['tasks'],ir['hardware'],ir['resident_actions'],plan,18)}
    actions={x['id']:x for x in ir['resident_actions']};recipes=[]
    for row in plan['tasks']:
        if row['id'] not in actions:continue
        b=next(b for b in actions[row['id']]['bindings'] if b['id']==row['binding'])
        recipes.append(ir['resident_recipes'][b['resident_region']['recipe']])
    if not recipes:raise ValueError('selected plan has no resident loop to verify')
    nodes={n['id']:n for n in full['primitive_program']['instructions']}
    cutnodes={n['id']:n for n in ir['primitive_program']['instructions']}
    if any(nodes.get(n)!=cutnodes[n] for r in recipes for n in r['primitives']):
        raise ValueError('resident primitive changed from full source')
    weights=json.loads(a.weights.read_text());weights['_root']=str(a.weights.parent.parent)
    calibration=json.loads(a.calibration.read_text());oracle=Oracle(a.oracle)
    original=Interpreter(full['model'],weights,calibration,oracle);hf=np.load(a.logits);samples=[]
    for i,reference in enumerate(gold['samples']):
        began=time.monotonic();ids=reference['ids'];backend=Execution(full['primitive_program'],recipes)
        result=execute(full['primitive_program'],original.initial,ids,oracle,region_executor=backend)
        final=result[full['model']['outputs'][0]];digest=hashlib.sha256(final.raw.tobytes()).hexdigest()
        if digest!=reference['logits_raw_sha256']:raise ValueError('resident full integer logits differ from accepted original')
        values=final.raw.astype(np.float64)*2.**final.exponent;expected=hf['reference'+str(i)]
        error=float(np.linalg.norm(values-expected)/np.linalg.norm(expected))
        top=bool(np.array_equal(np.argmax(values,axis=-1),np.argmax(expected,axis=-1)))
        if error>.02 or not top:raise ValueError('resident full graph HF acceptance failed')
        sample={'ids':ids,'bit_exact_to_original':True,'relative_l2':error,'top1_equal':top,
            'logits_raw_sha256':digest,'resident':backend.report(),'host_replay_seconds':time.monotonic()-began}
        samples.append(sample);print(json.dumps(sample),flush=True)
    oracle.close()
    report={'passed':True,'samples':samples,'audits':audits,
        'inputs_sha256':{str(path):sha(path) for path in (a.full_ir,a.cover_ir,a.plan,a.weights,a.calibration,a.logits,a.gold)},
        'scope':'full original integer graph with selected resident regions executed at every element through finite-S/ACK replay; other ops remain integer interpreter; not full selected hardware/control/DMA/SystemC/physical/time/energy/token/s qualification'}
    (a.output/'report.json').write_text(json.dumps(report,separators=(',',':'))+'\n')


if __name__=='__main__':main()
