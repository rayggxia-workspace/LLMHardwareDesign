"""Recover the completed, independently checked whole-graph traffic audit."""
import hashlib,json,subprocess,tarfile
from pathlib import Path
runtime=Path('D:/Data/电路实验/issue219-runtime-round24');remote='yuzelu@10.129.166.172'
name='algorithm-fix-308-full-traffic-cover-audit'
receipt=json.loads((runtime/(name+'.json')).read_text());directory=receipt['directory'];job=receipt['job']
assert directory.startswith('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/')
state=subprocess.check_output(['ssh',remote,'sacct','-j',job,'--format=JobID,State,ExitCode,Elapsed','-n','-P']).decode()
assert f'{job}|COMPLETED|0:0|' in state
out=Path('work/YUZE-LU/219/throughput-opt/results/full-traffic-terminal-r24');out.mkdir(exist_ok=False)
entries={}
for name in ('source.tar','traffic-accounting.sbatch','input.sha256','output.sha256','tests.log','traffic.log','traffic-accounting.json'):
    sha=subprocess.check_output(['ssh',remote,'sha256sum',directory+'/'+name]).decode().split()[0]
    target=out/name;subprocess.run(['scp',remote+':'+directory+'/'+name,str(target)],check=True)
    assert hashlib.sha256(target.read_bytes()).hexdigest()==sha
    entries[name]={'sha256':sha,'bytes':target.stat().st_size}
with tarfile.open(out/'source.tar') as tar:
    assert {m.name for m in tar}==set(receipt['source_sha256'])
    for name,sha in receipt['source_sha256'].items():
        assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==sha
receipt.update(terminal_state=state,files=entries)
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
report=json.loads((out/'traffic-accounting.json').read_text())
assert report['passed'] and sum(report['logical_scalar_record_words'].values())==report['total_logical_words']
print(json.dumps({'job':job,'state':'COMPLETED0:0','files':len(entries),
    **{k:report[k] for k in ('total_logical_words','logical_scalar_record_words','cached_Dot_services')}}))
