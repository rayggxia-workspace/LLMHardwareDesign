"""Recover explicit owned terminal jobs, retaining failed experiments too."""
import hashlib,json,subprocess,tarfile
from pathlib import Path

runtime=Path('D:/Data/电路实验/issue219-runtime-round24')
remote='yuzelu@10.129.166.172'
cases=[('algorithm-fix-306-native-high16-cover-r4','native-lane-r4-terminal-r24','COMPLETED','native-lane.sbatch',
        ['output.sha256','survey.log','frontier-width.txt','generated/summary.json','generated/programs.json']),
       ('algorithm-fix-307-full-traffic-audit','full-traffic-failed-r24','FAILED','traffic-accounting.sbatch',['traffic.log'])]
for name,dest,expected,script,extra in cases:
    receipt=json.loads((runtime/(name+'.json')).read_text());job=receipt['job'];directory=receipt['directory']
    assert directory.startswith('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/')
    state=subprocess.check_output(['ssh',remote,'sacct','-j',job,'--format=JobID,State,ExitCode,Elapsed','-n','-P']).decode()
    assert f'{job}|{expected}|' in state
    out=Path('work/YUZE-LU/219/throughput-opt/results')/dest;out.mkdir(exist_ok=False)
    entries={}
    for path in ['source.tar',script,'input.sha256','tests.log']+extra:
        sha=subprocess.check_output(['ssh',remote,'sha256sum',directory+'/'+path]).decode().split()[0]
        target=out/path;target.parent.mkdir(exist_ok=True,parents=True)
        subprocess.run(['scp',remote+':'+directory+'/'+path,str(target)],check=True)
        assert hashlib.sha256(target.read_bytes()).hexdigest()==sha
        entries[path]={'sha256':sha,'bytes':target.stat().st_size}
    with tarfile.open(out/'source.tar') as tar:
        assert {m.name for m in tar}==set(receipt['source_sha256'])
        for path,sha in receipt['source_sha256'].items():
            assert hashlib.sha256(tar.extractfile(path).read()).hexdigest()==sha
    receipt.update(terminal_state=state,files=entries)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'job':job,'state':expected,'files':len(entries)}),flush=True)
