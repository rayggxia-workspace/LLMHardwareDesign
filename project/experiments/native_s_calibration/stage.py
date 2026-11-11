"""Freeze committed calibration sources into a fresh, issue-owned Slurm run.

No compute runs locally.  The historical archive is an input, never modified.
"""
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
PREFIX = '/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-250-native-service-'


def run(args, **kwargs):
    return subprocess.run(args, check=True, stdin=subprocess.DEVNULL, **kwargs)


def freeze(commit):
    paths = subprocess.check_output([
        'git', 'ls-tree', '-r', '--name-only', commit, '--',
        'project/experiments/native_s_calibration',
        'work/YUZE-LU/250/performance/run-08.tar.gz.b64',
        'work/YUZE-LU/250/performance/recovery-08.json'], cwd=ROOT).decode().splitlines()
    assert paths
    files = {'source/' + p: subprocess.check_output(['git', 'show', commit + ':' + p], cwd=ROOT) for p in paths}
    files['source-commit.txt'] = (commit + '\n').encode()
    files['source.sha256'] = ''.join(hashlib.sha256(v).hexdigest() + '  ' + k + '\n'
                                     for k, v in sorted(files.items())).encode()
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        for name, data in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size = len(data)
            member.mode = 0o644
            archive.addfile(member, io.BytesIO(data))
    return stream.getvalue()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--suffix', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--source-ref',help='Freeze an explicit committed source while another audit is being prepared.')
    parser.add_argument('--round', default='reproduce', choices=['reproduce', 'native-1', 'stripe-1', 'tile-1', 'lookahead-1', 'product-1', 'consumer-1', 'G-overlap-1', 'rf-II1-1','dynamic15-1','native-dot-1','native-dot-stage64','native-dot-av-wave','native-dot-M2','native-dot-refill','measured-three-P-FFN','measured-S80','programmed-FFN'])
    args = parser.parse_args()
    assert args.suffix.replace('-', '').isalnum()
    if args.source_ref is None:
        assert not subprocess.check_output(['git', 'status', '--porcelain', '--', 'project/experiments/native_s_calibration'], cwd=ROOT)
    commit = subprocess.check_output(['git','rev-parse','--verify',f'{args.source_ref or "HEAD"}^{{commit}}'], cwd=ROOT).decode().strip()
    data = freeze(commit)
    args.out.mkdir(exist_ok=False, parents=True)
    package = args.out / 'source.tar.gz'
    package.write_bytes(data)
    remote = PREFIX + args.suffix
    run(['ssh', HOST, shlex.join(['mkdir', remote])])
    run(['scp', str(package), HOST + ':' + remote + '/source.tar.gz'])
    command = ' && '.join([
        'cd ' + shlex.quote(remote),
        shlex.join(['tar', '-xzf', 'source.tar.gz']),
        shlex.join(['sbatch', '--parsable', '--export=ALL,NS_ROUND=' + args.round, 'source/project/experiments/native_s_calibration/job.sh'])])
    job = subprocess.check_output(['ssh', HOST, command], stdin=subprocess.DEVNULL).decode().strip()
    record = dict(source_commit=commit, remote=remote, job=job,
                  source_archive_sha256=hashlib.sha256(data).hexdigest(),
                  allocation='c96 nodes=1 ntasks=8 cpus-per-task=12')
    (args.out / 'stage.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))
