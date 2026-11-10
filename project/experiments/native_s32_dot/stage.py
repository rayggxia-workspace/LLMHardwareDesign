"""Submit committed new Issue252 sources; no numerical work locally/login."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[3]
HOST='yuzelu@10.129.166.172'
PREFIX='/public/home/yuzelu/project-circuit/issue252-native32-'


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--suffix',required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();assert args.suffix.replace('-','').isalnum()
    assert not subprocess.check_output(['git','status','--porcelain','--','project/rtl/native_s32_dot','project/experiments/native_s32_dot'],cwd=ROOT)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only',commit,'--',
        'project/rtl/native_s32_dot','project/experiments/native_s32_dot'],cwd=ROOT).decode().splitlines()
    files={'source/'+path:subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT) for path in paths}
    files['source-commit.txt']=(commit+'\n').encode()
    files['source.sha256']=''.join(hashlib.sha256(v).hexdigest()+'  '+k+'\n' for k,v in sorted(files.items())).encode()
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w:gz') as archive:
        for name,data in sorted(files.items()):
            member=tarfile.TarInfo(name);member.size=len(data);member.mode=0o644
            archive.addfile(member,io.BytesIO(data))
    args.out.mkdir(parents=True,exist_ok=False);package=args.out/'source.tar.gz';package.write_bytes(stream.getvalue())
    remote=PREFIX+args.suffix
    subprocess.run(['ssh',HOST,shlex.join(['mkdir',remote])],check=True,stdin=subprocess.DEVNULL)
    subprocess.run(['scp',str(package),HOST+':'+remote+'/source.tar.gz'],check=True,stdin=subprocess.DEVNULL)
    command=' && '.join(['cd '+shlex.quote(remote),'tar -xzf source.tar.gz',
        shlex.join(['sbatch','--parsable','source/project/experiments/native_s32_dot/job.sh'])])
    job=subprocess.check_output(['ssh',HOST,command],stdin=subprocess.DEVNULL).decode().strip()
    report=dict(source_commit=commit,job=job,remote=remote,source_archive_sha256=hashlib.sha256(package.read_bytes()).hexdigest(),
                allocation='c64 nodes1 tasks6 cores10',base='c4d7b960599b9d292f27eb4429d5f226a7156c95',issue=252)
    (args.out/'stage.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
