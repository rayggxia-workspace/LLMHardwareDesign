"""Freeze committed bytes; only submit compute to an owned fresh Slurm run."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
HOST = 'yuzelu@10.129.166.172'
PREFIX = '/public/home/yuzelu/project-circuit/issue250-dynamic-'


def call(argv, **kwargs):
    return subprocess.run(argv, check=True, stdin=subprocess.DEVNULL, **kwargs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--suffix', required=True)
    parser.add_argument('--map-proof')
    parser.add_argument('--calibration-proof')
    parser.add_argument('--m-source',help='Exact immutable commit of the six unchanged M-provider modules')
    parser.add_argument('--out', type=Path, required=True); args = parser.parse_args()
    assert args.suffix.replace('-', '').isalnum()
    assert not subprocess.check_output(['git', 'status', '--porcelain', '--',
        'project/experiments/w8a16_dynamic', 'project/rtl/w8a16_v1/dynamic_s32_merge.sv',
        'project/rtl/w8a16_v1/dynamic_s32_packer.sv','project/rtl/w8a16_v1/dynamic_s32_weight_source.sv'], cwd=ROOT)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', commit, '--',
        'project/experiments/w8a16_dynamic', 'project/rtl/w8a16_v1'], cwd=ROOT).decode().splitlines()
    files = {'source/' + p: subprocess.check_output(['git', 'show', commit + ':' + p], cwd=ROOT) for p in paths}
    if args.m_source:
        exact=subprocess.check_output(['git','rev-parse',args.m_source+'^{commit}'],cwd=ROOT).decode().strip()
        overrides={}
        for name in ('m_native_leaf_s32','m_native_s32','weight_records','m_group_s32',
                     'projection_context_s32','scale_group_s32'):
            path='project/rtl/w8a16_v1/'+name+'.sv'
            files['source/'+path]=subprocess.check_output(['git','show',exact+':'+path],cwd=ROOT)
            overrides[path]=hashlib.sha256(files['source/'+path]).hexdigest()
        files['m-provider-source.json']=(json.dumps(dict(commit=exact,files=overrides,
            scope='Read-only canonical M provider snapshot; dynamic files remain from source-commit.txt'),indent=2)+'\n').encode()
    files['source-commit.txt'] = (commit + '\n').encode()
    files['source.sha256'] = ''.join(hashlib.sha256(v).hexdigest() + '  ' + k + '\n'
                                    for k, v in sorted(files.items())).encode()
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        for name, data in sorted(files.items()):
            member = tarfile.TarInfo(name); member.size = len(data); member.mode = 0o644
            archive.addfile(member, io.BytesIO(data))
    args.out.mkdir(parents=True, exist_ok=False)
    package = args.out / 'source.tar.gz'; package.write_bytes(stream.getvalue())
    remote = PREFIX + args.suffix
    call(['ssh', HOST, shlex.join(['mkdir', remote])])
    call(['scp', str(package), HOST + ':' + remote + '/source.tar.gz'])
    upstream = '/public/home/yuzelu/project-circuit/issue250-control-prep-20261110-40/upstream/'
    bank = '/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v'
    command = ' && '.join([shlex.join(['mkdir',remote+'/upstream']),
        shlex.join(['cp',upstream+'local_s_base.sv',upstream+'block_feed_s16k_sram.sv',bank,remote+'/upstream/']),
        'sha256sum '+shlex.quote(remote)+'/upstream/*'])
    upstream_sha=subprocess.check_output(['ssh',HOST,command],stdin=subprocess.DEVNULL).decode()
    assert '6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7' in upstream_sha
    job_script='job.sh';export=[]
    if args.map_proof:
        assert args.map_proof.startswith(PREFIX)
        job_script='map_job.sh';export=['--export=ALL,DYNAMIC_PROOF='+args.map_proof]
    if args.calibration_proof:
        assert not args.map_proof and args.calibration_proof.startswith(PREFIX)
        job_script='calibration_job.sh';export=['--export=ALL,DYNAMIC_CALIBRATION_PROOF='+args.calibration_proof]
    command = ' && '.join(['cd ' + shlex.quote(remote), 'tar -xzf source.tar.gz',
        shlex.join(['sbatch','--parsable',*export,'source/project/experiments/w8a16_dynamic/'+job_script])])
    job = subprocess.check_output(['ssh', HOST, command], stdin=subprocess.DEVNULL).decode().strip()
    report = dict(source_commit=commit, job=job, remote=remote,
                  m_provider_commit=exact if args.m_source else 'f08aefb93df071535f461da24b6829c5949bf5bf' if args.calibration_proof else commit,
                  reused_binary_proof=args.calibration_proof,
                  upstream_sha256=upstream_sha,
                  source_archive_sha256=hashlib.sha256(package.read_bytes()).hexdigest(),
                  allocation='c64 nodes=1 ntasks=6 cpus-per-task=10')
    (args.out / 'stage.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
