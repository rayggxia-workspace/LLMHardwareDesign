"""Recover the action-family lower-bound experiment without changing it."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess


def main():
    here=Path(__file__).resolve().parent
    receipt=json.loads((Path.home()/'AppData/Local/Codex/algorithm-fix-229-search-action-bounds.json').read_text())
    root=receipt['directory'];host='yuzelu@10.129.166.172'
    if not root.startswith('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-'):
        raise ValueError('unexpected evidence directory')
    out=here/'results/search-bound';out.mkdir(exist_ok=False)
    files={}
    for name in ('five-groups-bound.json','nine-groups-count-experiment-bound.json','tests.log','input.sha256','output.sha256','slurm.log'):
        remote=root+'/'+name;local=out/name
        subprocess.run(['scp','-q',host+':'+remote,str(local)],check=True,timeout=60)
        sha=hashlib.sha256(local.read_bytes()).hexdigest()
        expected=subprocess.check_output(['ssh',host,'sha256sum '+shlex.quote(remote)],timeout=30).decode().split()[0]
        if sha!=expected:raise ValueError('evidence hash mismatch '+name)
        files[name]={'server':remote,'sha256':sha}
    state=subprocess.check_output(['ssh',host,'sacct -j '+str(receipt['job'])+' --format=JobID,State,ExitCode,Elapsed,AllocCPUS,Timelimit -P'],timeout=30)
    (out/'slurm.psv').write_bytes(state)
    receipt['recovered']=files
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'job':receipt['job'],'recovered':len(files)}))


if __name__=='__main__':main()
