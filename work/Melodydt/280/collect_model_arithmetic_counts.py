"""Export accepted call counts and operand shapes without copying large vectors."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

def digest(p):return sha256(p.read_bytes()).hexdigest()
def shape(v):
    if isinstance(v,list):return [len(v)]+(shape(v[0]) if v else [])
    return []

def collect(run, phases, destination):
    subprocess.run(['sha256sum','--quiet','-c','results.sha256'],cwd=run,check=True)
    result=dict(run=str(run),manifest_sha256=digest(run/'results.sha256'),phases={})
    for name,dirname in phases.items():
        p=run/dirname; op=p/'operator-observation.json';rms=p/'arithmetic-observation.json'
        accepted=json.loads((p/'operator-capture-check.json').read_text())
        if not accepted['passed'] or digest(op)!=accepted['capture_sha256']:raise ValueError('operator capture not accepted')
        o=json.loads(op.read_text());a=json.loads(rms.read_text())
        if not a['n_counts_reconciled']:raise ValueError('RMS counts not reconciled')
        samples={}
        for s in o['samples']:
            item=dict(kind=s['kind'],shape=s['shape'],input_shapes={k:shape(v) for k,v in s['inputs'].items()})
            if s['signature'] in samples and samples[s['signature']]!=item:raise ValueError('shape changes within signature')
            samples[s['signature']]=item
        if set(samples)!=set(o['counts']):raise ValueError('unsampled operator signature')
        result['phases'][name]=dict(operator_counts=o['counts'],operator_shapes=samples,rms_counts=a['rms_service_counts'],
                                   operator_capture=str(op),operator_sha256=digest(op),rms_capture=str(rms),rms_sha256=digest(rms))
    destination.write_text(json.dumps(result,indent=2)+'\n')
    print('ARITHMETIC_COUNTS_ACCEPTED',destination.name)

if __name__=='__main__':
    root,out=map(Path,sys.argv[1:3]);out.mkdir(exist_ok=True)
    for model,job in [('llama',38830188),('granite',38830189),('phi',38830190),('gemma',38830191),('qwen35',38830192),('falcon',38830193)]:
        collect(root/'operator-capture-02'/('run-%s'%job),dict(prefill='prefill',decode='decode'),out/(model+'.json'))
    if len(sys.argv)>3:
        collect(root/'qwen3-operator-capture-01'/('qwen3-'+sys.argv[3]),
                dict(prefill='prefill-w4-tile128-pr272-combined',decode='decode-live-w4-tile128-pr272-combined'),out/'qwen3.json')
