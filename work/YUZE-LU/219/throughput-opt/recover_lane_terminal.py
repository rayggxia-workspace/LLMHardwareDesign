"""Retrieve only completed owned lane-cover experiment files and check SHA."""
import hashlib,json,subprocess,tarfile
from pathlib import Path
remote='yuzelu@10.129.166.172';runtime=Path('D:/Data/电路实验/issue219-runtime-round24')
receipt=json.loads((runtime/'algorithm-fix-305-native-high16-cover-r2.json').read_text());directory=receipt['directory'];job=receipt['job']
assert directory.startswith('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/')
state=subprocess.check_output(['ssh',remote,'sacct','-j',job,'--format=JobID,State,ExitCode,Elapsed','-n','-P']).decode()
assert f'{job}|COMPLETED|0:0|' in state
out=Path('work/YUZE-LU/219/throughput-opt/results/native-lane-terminal-r24');out.mkdir(exist_ok=False)
names=['source.tar','native-lane.sbatch','input.sha256','output.sha256','tests.log','survey.log','generated/summary.json','generated/programs.json']
entries={}
for name in names:
    sha=subprocess.check_output(['ssh',remote,'sha256sum',directory+'/'+name]).decode().split()[0]
    target=out/name;target.parent.mkdir(exist_ok=True,parents=True)
    subprocess.run(['scp',remote+':'+directory+'/'+name,str(target)],check=True)
    assert hashlib.sha256(target.read_bytes()).hexdigest()==sha
    entries[name]={'sha256':sha,'bytes':target.stat().st_size}
with tarfile.open(out/'source.tar') as tar:
    assert {entry.name for entry in tar}==set(receipt['source_sha256'])
    for name,sha in receipt['source_sha256'].items():assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==sha
receipt.update(terminal_state=state,files=entries)
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'job':job,'terminal':'COMPLETED0:0','files':len(entries),'source_members':len(receipt['source_sha256'])}))
