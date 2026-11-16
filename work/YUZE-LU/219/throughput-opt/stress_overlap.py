"""Repeat one frozen real trace with no model importer or NumPy dependency."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from resident_overlap import build,digest,search
from verify_resident_overlap import verify


def main():
    p=argparse.ArgumentParser();p.add_argument('case',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--repeats',type=int,default=12);a=p.parse_args();source=json.loads(a.case.read_text())
    dag=build(source['graph'],source['base_program'],source['dag']['channel_by_actor'])
    first=None;elapsed=[]
    for index in range(a.repeats):
        start=time.monotonic();solutions={}
        for name,width,policy in (('makespan_greedy',1,'makespan'),('critical_greedy',1,'critical_path'),('dp',8,'critical_path')):
            solutions[name]=search(dag,width=width,policy=policy)
        greedy=min((solutions[n] for n in ('makespan_greedy','critical_greedy')),key=lambda s:s['makespan'])
        solutions['backbone_dp']=search(dag,width=8,backbone=greedy)
        for s in solutions.values():verify(source['graph'],source['base_program'],dag,s,dag['channel_by_actor'])
        identity=digest(solutions)
        if first is None:first=(identity,solutions)
        elif identity!=first[0]:raise ValueError('identical trace scheduling was not deterministic')
        elapsed.append(time.monotonic()-start)
        print(json.dumps({'repeat':index,'passed':True,'schedule_sha256':identity,'seconds':elapsed[-1]}),flush=True)
    result={'passed':True,'repeats':a.repeats,'python':sys.version,'malloc':os.environ.get('PYTHONMALLOC','default'),
        'source_sha256':hashlib.sha256(a.case.read_bytes()).hexdigest(),'schedule_sha256':first[0],
        'solutions':first[1],'seconds':elapsed,'modules':sorted(sys.modules),
        'code_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(__file__),
            Path(sys.modules['resident_overlap'].__file__),Path(sys.modules['verify_resident_overlap'].__file__)]}}
    a.output.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
