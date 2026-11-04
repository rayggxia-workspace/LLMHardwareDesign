"""Package only explicit task inputs; create a NEW server root and sbatch."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parents[3]
INPUTS = [
    'project/rtl/block_feed_v1/block_feed_s_macro.sv',
    'project/rtl/block_feed_v1/block_feed_s16k.sv',
    'project/rtl/block_feed_v1/block_feed_loader.sv',
    'project/rtl/block_v2/block_v2_m.sv',
    'project/rtl/hbm_feed/hbm_async_fifo.sv',
    'project/rtl/hbm_feed/hbm_s_endpoint.sv',
    'project/experiments/hbm_feed/hbm_s_pool.sv',
    'project/experiments/hbm_feed/test_hbm.cpp',
    'project/experiments/hbm_feed/run_server.py',
    'project/experiments/hbm_feed/job.sh',
    'project/experiments/hbm_feed/launch.py',
]


def run(cmd):
    return subprocess.check_output(cmd, text=True, encoding='utf-8').strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--attempt', required=True)
    p.add_argument('--package-dir', required=True, type=Path)
    a = p.parse_args()
    if not a.attempt.replace('-', '').isalnum():
        raise SystemExit('Use an alphanumeric attempt with hyphens')
    a.package_dir.mkdir(parents=True, exist_ok=False)
    binding = dict(git_commit=run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']),
                   base_commit='4b1df2c7cbdaa0fa6f9f468f2b5b854cec875609',
                   files={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in INPUTS})
    # Require task inputs to be exactly committed; documentation may be edited separately.
    for path, sha in binding['files'].items():
        blob = subprocess.check_output(['git', '-C', str(ROOT), 'show', f'HEAD:{path}'])
        if hashlib.sha256(blob).hexdigest() != sha:
            raise SystemExit(f'Uncommitted input: {path}')
    manifest = a.package_dir / 'source_binding.json'
    manifest.write_text(json.dumps(binding, indent=2) + '\n', encoding='utf-8')
    archive = a.package_dir / 'source.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        for path in INPUTS:
            tar.add(ROOT / path, arcname=path)
        tar.add(manifest, arcname='source_binding.json')
    target = 'yuzelu@10.129.166.172'
    root = f'/public/home/yuzelu/PingyangHuang/issue181-hbm-{a.attempt}'
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=12', target]
    # Refuse symlinked roots or existing attempts. Never touch an old task.
    create = ("set -eu; test \"$(realpath /public/home/yuzelu/PingyangHuang)\" = "
              "/public/home/yuzelu/PingyangHuang; "
              f'test ! -e {root}; mkdir {root}; mkdir {root}/source {root}/tmp {root}/cache')
    run([*ssh, create])
    subprocess.run(['scp', '-o', 'BatchMode=yes', str(archive), f'{target}:{root}/source.tar.gz'], check=True)
    extract = f'set -eu; tar -xzf {root}/source.tar.gz -C {root}/source; '
    submit = (f'sbatch --parsable --output={root}/slurm-%j.out --error={root}/slurm-%j.err '
              f'{root}/source/project/experiments/hbm_feed/job.sh {root}')
    job = run([*ssh, extract + submit]).splitlines()[-1]
    receipt = dict(job_id=job, remote_root=root, source=binding,
                   archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(), submitted=time.time())
    (a.package_dir / 'submission.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
