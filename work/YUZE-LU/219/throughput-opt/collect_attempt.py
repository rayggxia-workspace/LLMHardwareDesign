"""Recover selected immutable attempt evidence, checking every SHA-256.

Large IRs and simulator binaries remain in the authorized project storage;
their hashes are retained in each job's output manifest.
"""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import shlex
import subprocess


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('attempt');parser.add_argument('destination');parser.add_argument('files',nargs='+')
    parser.add_argument('--receipt',type=Path)
    args=parser.parse_args()
    if not args.attempt.startswith('algorithm-fix-') or any(c not in '-_.abcdefghijklmnopqrstuvwxyz0123456789' for c in args.attempt):
        raise ValueError('invalid attempt')
    destination=PurePosixPath(args.destination)
    if destination.is_absolute() or '..' in destination.parts:raise ValueError('invalid output path')
    receipt_path=args.receipt or Path.home()/'AppData/Local/Codex'/(args.attempt+'.json')
    receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
    root=receipt['directory'];host='yuzelu@10.129.166.172'
    if root!='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/'+args.attempt:
        raise ValueError('unexpected remote evidence directory')
    out=Path(__file__).resolve().parent/'results'/args.destination;out.mkdir(parents=True,exist_ok=True)
    recovered={};previous=out/'receipt.json'
    if previous.exists():
        old=json.loads(previous.read_text(encoding='utf-8'))
        if any(old.get(k)!=receipt.get(k) for k in ('directory','job','source_sha256')):
            raise ValueError('existing evidence receipt belongs to a different frozen job')
        recovered.update(old.get('recovered',{}))
    for name in args.files:
        relative=PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('invalid evidence path')
        remote=root+'/'+name;local=out/name;local.parent.mkdir(parents=True,exist_ok=True)
        expected=subprocess.check_output(['ssh',host,'sha256sum '+shlex.quote(remote)],timeout=30).decode().split()[0]
        if not local.exists():subprocess.run(['scp','-q',host+':'+remote,str(local)],check=True,timeout=90)
        actual=hashlib.sha256(local.read_bytes()).hexdigest()
        if actual!=expected:raise ValueError('evidence mismatch '+name)
        recovered[name]={'server':remote,'sha256':actual}
    state=subprocess.check_output(['ssh',host,'sacct -j '+shlex.quote(str(receipt['job']))+
                                   ' --format=JobID,State,ExitCode,Elapsed,AllocCPUS,Timelimit -P'],timeout=30)
    (out/'slurm.psv').write_bytes(state)
    receipt['recovered']=recovered
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',newline='\n')
    print(json.dumps({'job':receipt['job'],'verified_files':len(recovered)}))


if __name__=='__main__':main()
