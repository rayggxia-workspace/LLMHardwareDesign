"""One-shot evidence manifest; no recurring monitoring or physical work."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from search import verify


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('results',type=Path);p.add_argument('full',type=Path)
    p.add_argument('--jobs',required=True);p.add_argument('--source-commit',required=True)
    a=p.parse_args(); checks=[]
    for f in a.results.glob('*.plan.json'):
        plan=json.loads(f.read_text())
        if plan['status']!='analytical_plan':continue
        name,rest=f.name.rsplit('-s',1); capacity=rest.split('-')[0]
        graph=json.loads((a.results/(name+'.graph.json')).read_text())
        arch=json.loads((a.results/(name+'.hardware-'+capacity+'.json')).read_text())
        verify(plan,graph,arch);checks.append(f.name)
    inputs={}
    for f in a.results.glob('*.graph.json'):
        graph=json.loads(f.read_text()); path=Path(graph['source'])
        inputs[str(path)]={'sha256':sha(path),'bytes':path.stat().st_size}
    receipt=json.loads((a.full/'receipt.json').read_text())
    for f in Path(receipt['checkpoint']).glob('*.safetensors'):
        inputs[str(f)]={'sha256':sha(f),'bytes':f.stat().st_size}
    outputs={f.name:{'sha256':sha(f),'bytes':f.stat().st_size} for f in a.results.iterdir()
             if f.is_file() and f.name!='delivery.json'}
    accounting=subprocess.check_output(['sacct','-j',a.jobs,'--parsable2',
                        '--format=JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,NodeList'],text=True)
    readbacks={j:subprocess.check_output(['scontrol','-o','show','job',j],text=True)
               for j in a.jobs.split(',')}
    record={'source_commit':a.source_commit,'inputs':inputs,'outputs':outputs,
            'independently_replayed_plans':checks,'accounting':accounting,'scheduler':readbacks,
            'scope':'analytical only; failures retained; no native control image or physical verification'}
    (a.results/'delivery.json').write_text(json.dumps(record,indent=2))


if __name__=='__main__':main()
