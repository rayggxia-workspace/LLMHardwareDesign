"""Freeze this task's compiler and unchanged N RTL in a fresh own Slurm job."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile


def main():
    parser=argparse.ArgumentParser();parser.add_argument('attempt');args=parser.parse_args()
    if not args.attempt.startswith('algorithm-fix-') or any(c not in '-_.abcdefghijklmnopqrstuvwxyz0123456789' for c in args.attempt):
        raise ValueError('invalid own attempt name')
    root=Path(__file__).resolve().parents[4]
    cache=Path.home()/'AppData/Local/Codex';archive=cache/(args.attempt+'.tar')
    manifest={}
    files=[(f.name,f) for f in (root/'project/experiments/block_synthesis').iterdir()
        if f.suffix in ('.py','.sbatch','.cpp','.hpp','.sv','.vlt')]
    files += [('frozen-n/'+name,root/'project/rtl/block_v2'/name)
        for name in ('block_v2_n.sv','block_v2_n_group.sv','block_v2_n_exp.svh')]
    with tarfile.open(archive,'w') as tar:
        for name,file in sorted(files):
            data=file.read_text(encoding='utf-8').encode('utf-8')
            item=tarfile.TarInfo(name);item.size=len(data);tar.addfile(item,io.BytesIO(data))
            manifest[name]=hashlib.sha256(data).hexdigest()
    remote='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/'+args.attempt
    host='yuzelu@10.129.166.172'
    subprocess.run(['ssh','-o','BatchMode=yes',host,'mkdir',remote],check=True,timeout=30)
    subprocess.run(['scp','-q',str(archive),host+':'+remote+'/source.tar'],check=True,timeout=60)
    expected=hashlib.sha256(archive.read_bytes()).hexdigest()
    actual=subprocess.check_output(['ssh',host,'sha256sum',remote+'/source.tar'],timeout=30).decode().split()[0]
    if actual!=expected:raise ValueError('uploaded source SHA mismatch')
    subprocess.run(['ssh',host,'tar','-xf',remote+'/source.tar','-C',remote],check=True,timeout=30)
    job=subprocess.check_output(['ssh',host,'sbatch','--parsable','--output='+remote+'/slurm.log',
        remote+'/nexp-probe.sbatch',remote],timeout=30).decode().strip()
    receipt={'directory':remote,'job':job,'source_sha256':manifest,'archive_sha256':expected,
        'git_base':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip()}
    (cache/(args.attempt+'.json')).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'job':job,'directory':remote,'source_files':len(manifest)}))


if __name__=='__main__':main()
