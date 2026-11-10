"""Freeze committed byte-identical sources into a fresh owned Slurm directory."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import tarfile

HOST = 'yuzelu@10.129.166.172'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    p.add_argument('--package-dir', required=True, type=Path)
    a = p.parse_args()
    assert re.fullmatch(r'/public/home/yuzelu/project-circuit/issue250-weight-20261111-[0-9]+', a.root)
    a.package_dir.mkdir(parents=True, exist_ok=False)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', commit, '--',
        'project/rtl/w8a16_v1/weight_records.sv', 'project/rtl/w8a16_v1/m_group_s32.sv',
        'project/experiments/w8a16_m/vectors/closure-m-run38.txt',
        'project/experiments/w8a16_weight']).decode().splitlines()
    data = {name: subprocess.check_output(['git', 'show', commit + ':' + name]) for name in paths}
    data['source-commit.txt'] = (commit + '\n').encode()
    manifest = ''.join(hashlib.sha256(value).hexdigest() + '  ' + name + '\n' for name, value in sorted(data.items()))
    package = a.package_dir / 'source.tar.gz'
    with tarfile.open(package, 'w:gz') as archive:
        for name, value in data.items():
            item = tarfile.TarInfo('source/' + name)
            item.size = len(value)
            item.mode = 0o755 if name.endswith('.sh') else 0o644
            archive.addfile(item, io.BytesIO(value))
        raw = manifest.encode()
        item = tarfile.TarInfo('source.sha256')
        item.size = len(raw)
        archive.addfile(item, io.BytesIO(raw))
    subprocess.run(['ssh', '-o', 'BatchMode=yes', HOST, 'mkdir ' + shlex.quote(a.root)], check=True)
    subprocess.run(['scp', '-q', str(package), HOST + ':' + a.root + '/source.tar.gz'], check=True)
    submitted = subprocess.check_output(['ssh', '-o', 'BatchMode=yes', HOST,
        'cd ' + shlex.quote(a.root) + ' && tar xzf source.tar.gz && sbatch --output=' +
        shlex.quote(a.root + '/slurm-%j.log') + ' source/project/experiments/w8a16_weight/job.sh']).decode().strip()
    receipt = dict(source_commit=commit, remote_root=a.root, source_files=len(data),
                   package_SHA256=hashlib.sha256(package.read_bytes()).hexdigest(), submit=submitted)
    (a.package_dir / 'submission.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
