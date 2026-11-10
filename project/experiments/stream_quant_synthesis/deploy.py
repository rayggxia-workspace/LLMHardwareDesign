"""Submit an immutable source snapshot to a new, task-owned Slurm directory."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from prepare import REPO

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('tag');p.add_argument('--out',type=Path,required=True)
    mode=p.add_mutually_exclusive_group()
    mode.add_argument('--metadata-audit',action='store_true')
    mode.add_argument('--bottleneck',action='store_true');a=p.parse_args()
    if not a.tag.isdigit():raise ValueError('numeric run tag required')
    a.out.mkdir(parents=True,exist_ok=True)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    archive=a.out/('source-'+a.tag+'.tar')
    subprocess.run(['git','-c','core.autocrlf=false','archive','--format=tar','--output',str(archive),'HEAD',
                    'project/experiments','project/rtl','work/Melodydt/247/speed-iterations/round04/run23'],cwd=REPO,check=True)
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    root='/public/home/yuzelu/project-circuit/issue248-stream-quant-20261110-'+a.tag
    host='yuzelu@10.129.166.172'
    command=['ssh','-o','BatchMode=yes',host,'python3 -']
    create='from pathlib import Path\np=Path('+repr(root)+')\np.mkdir(exist_ok=False)\n(p/"source").mkdir()\n'
    subprocess.run(command,input=create,text=True,check=True)
    subprocess.run(['scp','-q',str(archive),host+':'+root+'/source.tar'],check=True)
    payload='''import hashlib,json,subprocess
from pathlib import Path
r=Path(ROOT)
assert hashlib.sha256((r/'source.tar').read_bytes()).hexdigest()==DIGEST
subprocess.run(['tar','-xf',str(r/'source.tar'),'-C',str(r/'source')],check=True)
(r/'source-commit.txt').write_text(COMMIT+'\\n')
rows=[]
for p in sorted((r/'source').rglob('*')):
 if p.is_file():rows.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(r/'source').as_posix())
(r/'source-files.sha256').write_text('\\n'.join(rows)+'\\n')
job_script=(r/'source/project/experiments/stream_quant_synthesis/job.sh').read_bytes()
if AUDIT:job_script=job_script.replace(b'/run.py"',b'/audit.py"')
if BOTTLENECK:
 job_script=job_script.replace(b'/run.py"',b'/bottleneck.py"').replace(b'yl-sq-four-rounds',b'yl-sq-bottleneck')
(r/'job.sh').write_bytes(job_script)
job=subprocess.check_output(['sbatch','--parsable','job.sh'],cwd=r,universal_newlines=True).strip()
print(json.dumps(dict(root=str(r),job=job,source_commit=COMMIT,archive_sha256=DIGEST,metadata_audit=AUDIT,bottleneck=BOTTLENECK)))
'''.replace('ROOT',repr(root)).replace('COMMIT',repr(commit)).replace('DIGEST',repr(digest)).replace('AUDIT',repr(a.metadata_audit)).replace('BOTTLENECK',repr(a.bottleneck))
    result=subprocess.check_output(command,input=payload,text=True)
    (a.out/('submission-'+a.tag+'.json')).write_text(result,encoding='utf8');print(result)
