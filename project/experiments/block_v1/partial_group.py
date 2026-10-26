"""Two independent 48-CPU field fixtures inside one 96-CPU allocation."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import sys


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root,out,cpus,run):
    assert cpus==96
    modes=['partial-branch-fv','partial-via-fv']
    child_code='''import os,sys
root,mode,cpus,destination=sys.argv[1:]
os.chdir(destination)
os.environ.update(OMP_NUM_THREADS=cpus,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',MAKEFLAGS='-j'+cpus)
os.execv(sys.executable,[sys.executable,root+'/project/experiments/block_v1/worker.py',root,mode,cpus])
'''
    def launch(mode):
        folder=out.parent/mode;folder.mkdir(exist_ok=False)
        command=[sys.executable,'-c',child_code,str(root),mode,'48',str(folder)]
        command_ok=True
        try:run(command,mode+'.log')
        except RuntimeError:command_ok=False
        result=dict(mode=mode,cpus=48,directory=str(folder),command_ok=command_ok)
        for name in ['receipt.json','partial-field-fv.json']:
            path=folder/name
            if path.is_file():result[name]=dict(sha256=sha(path),content=json.loads(path.read_text()))
        receipt=result.get('receipt.json',{}).get('content',{})
        evidence=result.get('partial-field-fv.json',{})
        result['passed']=bool(command_ok and receipt.get('passed')is True and evidence.get('content',{}).get('passed')is True
            and receipt.get('outputs',{}).get('partial-field-fv.json')==evidence.get('sha256'))
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
        results=list(pool.map(launch,modes))
    record=dict(schema='block-v1-partial-geometry-group/1',passed=all(r['passed']for r in results),
        allocated_cpus=cpus,max_child_cpus=96,children=results,
        scope='Two independent local charge fixtures; general graph extraction and native/new-layer stitching remain unqualified')
    (out/'partial-geometry-group.json').write_text(json.dumps(record,indent=2)+'\n')
    assert record['passed'],'At least one locked local field fixture failed; preserve both child outputs'
