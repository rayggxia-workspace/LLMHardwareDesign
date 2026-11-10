"""Collect terminal Slurm evidence; this is I/O postprocessing, not simulation."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile

root = Path.cwd().resolve()
if root.parent != Path('/public/home/yuzelu/Melodydt/issue247-area-speed') or not re.fullmatch(r'run\d+', root.name):
    raise ValueError('outside the authorized run directory')
job = int(sys.argv[1])
status = subprocess.check_output(['sacct', '-j', str(job), '-X', '--noheader', '--parsable2',
    '--format=JobID,JobName,State,ExitCode,Elapsed,NodeList'], text=True)
rows = [line.split('|') for line in status.splitlines() if line.split('|')[0] == str(job)]
if len(rows) != 1 or rows[0][2] not in ('COMPLETED', 'FAILED', 'TIMEOUT', 'OUT_OF_MEMORY', 'CANCELLED'):
    raise ValueError('job is not in an inspected terminal state: ' + status)
if (root/'receipts.tar').exists():
    raise ValueError('refuse to overwrite a collection')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(root/'sacct.txt').write_text(status)
manifest = json.loads((root/'inputs.json').read_bytes())
for name, digest in manifest['code_sha256'].items():
    if sha(root/'source'/name) != digest:
        raise ValueError('deployed source drift '+name)
for name, digest in manifest['input_sha256'].items():
    if sha(root/name) != digest:
        raise ValueError('deployed input drift '+name)
outputs = sorted(p for p in (root/'results').rglob('*') if p.is_file())
if any(p.is_symlink() for p in outputs):
    raise ValueError('unexpected output symlink')
(root/'output-files.sha256').write_text(''.join(sha(p)+'  '+p.relative_to(root).as_posix()+'\n' for p in outputs))
selected = [p for p in outputs if p.suffix in ('.json','.log','.trace','.cpp','.hpp','.inc','.py','.csv','.jsonl','.txt')
            and not any(x.startswith('obj') for x in p.relative_to(root/'results').parts)]
result = json.loads((root/'results/result.json').read_bytes()) if (root/'results/result.json').exists() else {}
record = dict(run=root.name, job=job, run_root=str(root), source_commit=manifest['source_commit'],
    terminal_state=rows[0][2], exit_code=rows[0][3], node=rows[0][5], elapsed=rows[0][4],
    collection_succeeded=True, whole_run_passed=rows[0][2]=='COMPLETED' and rows[0][3]=='0:0' and result.get('passed') is True,
    total_result_files_hashed=len(outputs), result_files_selected=len(selected),
    classification='conditional_shared_S_direct_A_SystemC_research_not_native_RTL')
(root/'collection.json').write_text(json.dumps(record, indent=2)+'\n')
metadata = ['allocation.txt','sacct.txt','tools.sha256','source-files.sha256','input-files.sha256',
            'inputs.json','job.sh',f'slurm-{job}.log','output-files.sha256','collection.json']
selected += [root/name for name in metadata if (root/name).is_file()]
with tarfile.open(root/'receipts.tar', 'x') as archive:
    for path in selected:
        archive.add(path, arcname=path.relative_to(root).as_posix(), recursive=False)
print(json.dumps(dict(record, collected_files=len(selected), receipts_sha256=sha(root/'receipts.tar'),
    result_sha256=sha(root/'results/result.json') if result else None)))
