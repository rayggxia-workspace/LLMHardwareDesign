"""Collect raw lightweight evidence with server/local SHA equality checks."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text(encoding='utf-8'))
    root = receipt['remote_root']
    if not root.startswith('/public/home/yuzelu/PingyangHuang/issue181-hbm-') or '..' in root:
        raise SystemExit('Unexpected remote root')
    if not str(receipt['job_id']).isdigit():
        raise SystemExit('Invalid job ID')
    args.out.mkdir(parents=True, exist_ok=False)
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=12', 'yuzelu@10.129.166.172']
    script = r'''
import hashlib,json,tarfile
from pathlib import Path
root=Path(ROOT)
assert root.resolve()==root
files=[root/'source/source_binding.json',root/'result/results.json']
files += sorted((root/'result').glob('*.log'))
files += sorted((root/'result').glob('*.ys'))
files += [p for p in [root/'result/profiles.json',root/('slurm-'+JOB+'.out'),root/('slurm-'+JOB+'.err')] if p.exists()]
files=list(dict.fromkeys(files))
index={'remote_root':str(root),'job_id':JOB,'files':{}}
for p in files:
 b=p.read_bytes();index['files'][str(p.relative_to(root))]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
for p in [root/'source.tar.gz',root/'result/obj/Vhbm_s_pool',root/'result/obj/Vhbm_dma_system',*sorted((root/'result').glob('synth-*.json'))]:
 if p.exists():
  b=p.read_bytes();index.setdefault('remote_large_files',{})[str(p.relative_to(root))]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
dest=root/'reception-index.json'
with dest.open('x') as f:json.dump(index,f,indent=2)
archive=root/'reception.tar.gz'
with tarfile.open(archive,'x:gz') as tar:
 for p in files+[dest]:tar.add(p,arcname=str(p.relative_to(root)))
print(json.dumps({'archive':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}))
'''.replace('ROOT', repr(root)).replace('JOB', repr(receipt['job_id']))
    # The script only creates new reception files in this task's own root.
    proc = subprocess.run([*ssh, 'python3 -B -I -S'], input=script, text=True,
                          capture_output=True, check=True)
    package = json.loads(proc.stdout)
    archive = args.out / 'reception.tar.gz'
    subprocess.run(['scp', '-o', 'BatchMode=yes', f'{ssh[-1]}:{package["archive"]}', str(archive)], check=True)
    if sha(archive) != package['sha256']:
        raise RuntimeError('Archive SHA mismatch')
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts or not member.isfile():
                raise RuntimeError('Unsafe archive member')
            destination = args.out / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(tar.extractfile(member).read())
    index = json.loads((args.out / 'reception-index.json').read_text())
    for name, expected in index['files'].items():
        p = args.out / name
        if p.stat().st_size != expected['bytes'] or sha(p) != expected['sha256']:
            raise RuntimeError(f'Raw evidence mismatch: {name}')
    scheduler = subprocess.check_output([*ssh,
        f"sacct -j {receipt['job_id']} --format=JobID,State,ExitCode,Elapsed,AllocCPUS,Timelimit -n -P; "
        f"scontrol show job {receipt['job_id']}"], text=True)
    (args.out / 'scheduler.txt').write_text(scheduler, encoding='utf-8')
    (args.out / 'submission.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    report = dict(pass_all=True, raw_files=len(index['files']),
                  bytes=sum(x['bytes'] for x in index['files'].values()), archive_sha256=sha(archive),
                  index_sha256=sha(args.out / 'reception-index.json'), job_id=receipt['job_id'])
    (args.out / 'LOCAL_RECEPTION.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
