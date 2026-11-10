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
UPSTREAM={
 'local_s_base.sv':('/public/home/yuzelu/project-circuit/issue250-control-prep-20261110-40/upstream/local_s_base.sv',
                    '084a4c63e4fbe0a5e56c6319e542c5a7c6561e9ec5af0a07ed98ef0bd5aa21f4'),
 'block_feed_s16k_sram.sv':('/public/home/yuzelu/project-circuit/issue250-control-prep-20261110-40/upstream/block_feed_s16k_sram.sv',
                           'a1ba89671305fd76f99e1b0c2a6fdadcbc73c783a0383c2b9640b496577317ef'),
 's_sram_256x128_freepdk45.v':('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v',
                             '6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'),
}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--suffix',required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--kind',choices=('core','s128-real','stage64-real','map','route'),default='core')
    p.add_argument('--proof-run',default='20261111-07')
    p.add_argument('--map-top',choices=('both','service'),default='both')
    p.add_argument('--map-run',default='20261111-map02');p.add_argument('--rows',type=int,choices=(1,2,4),default=4)
    p.add_argument('--side',type=int,default=0);p.add_argument('--density',type=float,default=.48)
    args=p.parse_args();assert args.suffix.replace('-','').isalnum()
    assert not subprocess.check_output(['git','status','--porcelain','--','project/rtl/native_s32_dot','project/experiments/native_s32_dot'],cwd=ROOT)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
    prefixes=['project/rtl/native_s32_dot','project/experiments/native_s32_dot']
    if args.kind=='route':prefixes += ['project/experiments/'+p for p in ('block_v1','block_v2','block_feed_v1')]
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only',commit,'--',*prefixes],cwd=ROOT).decode().splitlines()
    files={'source/'+path:subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT) for path in paths}
    if args.kind in ('s128-real','stage64-real'):
        for name,(path,digest) in UPSTREAM.items():
            data=subprocess.check_output(['ssh',HOST,shlex.join(['cat',path])],stdin=subprocess.DEVNULL)
            assert hashlib.sha256(data).hexdigest()==digest
            files['upstream/'+name]=data
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
    assert args.proof_run.replace('-','').isalnum() and args.map_run.replace('-','').isalnum()
    if args.kind=='map':
        job_script='map_job.sh';options='NATIVE32_PROOF='+PREFIX+args.proof_run+',NATIVE32_MAP_TOP='+args.map_top
    elif args.kind=='route':
        job_script='route_job.sh';options=f'NATIVE32_MAPPING={PREFIX}{args.map_run},NATIVE32_ROWS={args.rows},NATIVE32_SIDE={args.side},NATIVE32_DENSITY={args.density}'
    else:
        job_script='job.sh';options='NATIVE32_CHECK='+{'core':'check.py','s128-real':'check_s128.py','stage64-real':'check_stage64.py'}[args.kind]
    command=' && '.join(['cd '+shlex.quote(remote),'tar -xzf source.tar.gz',
        shlex.join(['sbatch','--parsable','--export=ALL,'+options,'source/project/experiments/native_s32_dot/'+job_script])])
    job=subprocess.check_output(['ssh',HOST,command],stdin=subprocess.DEVNULL).decode().strip()
    report=dict(source_commit=commit,job=job,remote=remote,source_archive_sha256=hashlib.sha256(package.read_bytes()).hexdigest(),
                allocation='c64 nodes1 tasks6 cores10',base='c4d7b960599b9d292f27eb4429d5f226a7156c95',issue=252,kind=args.kind)
    (args.out/'stage.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
