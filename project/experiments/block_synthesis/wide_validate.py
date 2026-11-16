"""Whole-model primitive-program replay; original ONNX is compile input only."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from frontend import import_onnx
from full_integer import Interpreter,Oracle
from wide_program import compile_program,execute


def main():
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('weights',type=Path)
    p.add_argument('calibration',type=Path);p.add_argument('logits',type=Path);p.add_argument('output',type=Path)
    p.add_argument('oracle',nargs=argparse.REMAINDER);a=p.parse_args();a.output.mkdir(exist_ok=False)
    model=import_onnx(a.model);weights=json.loads(a.weights.read_text());weights['_root']=str(a.weights.parent.parent)
    calibration=json.loads(a.calibration.read_text());oracle=Oracle(a.oracle)
    reference=Interpreter(model,weights,calibration,oracle)
    formats={name:entry['symmetric_s16_exponent']-8 for name,entry in calibration['values'].items()}
    program=compile_program(reference.m,reference.initial,calibration,formats)
    (a.output/'program.json').write_text(json.dumps(program,indent=2)+'\n')
    # Deserialize before replay; only emitted primitive instructions drive it.
    program=json.loads((a.output/'program.json').read_text())
    logits=np.load(a.logits);samples=[];bounds={}
    for i,ids in enumerate(([[1,2]],[[3,4]],[[42,43]])):
        output=execute(program,reference.initial,ids,oracle,bounds)[reference.m['outputs'][0]]
        actual=output.raw.astype(np.float64)*2.**output.exponent;expected=logits['reference'+str(i)]
        error=float(np.linalg.norm(actual-expected)/np.linalg.norm(expected))
        top=bool(np.array_equal(np.argmax(actual,axis=-1),np.argmax(expected,axis=-1)))
        row={'ids':ids,'relative_l2':error,'max_abs':float(np.abs(actual-expected).max()),'top1_equal':top,'passed':error<=.02 and top}
        samples.append(row);print(json.dumps(row),flush=True)
    oracle.close()
    report={'status':'primitive_program_passed' if all(s['passed'] for s in samples) else 'primitive_program_failed',
        'program_sha256':hashlib.sha256((a.output/'program.json').read_bytes()).hexdigest(),
        'native_accumulator_checks':bounds,
        'samples':samples,'instructions':len(program['instructions']),'source_sha256':model['sha256'],
        'inputs':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.model,a.weights,a.calibration,a.logits)}}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    if not all(s['passed'] for s in samples):raise ValueError('emitted primitive program failed numerical acceptance')


if __name__=='__main__':main()
