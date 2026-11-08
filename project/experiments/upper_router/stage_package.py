"""Copy a SHA-bound accepted archive into a new task directory, validating files.

No shell extraction, symlinks, absolute paths or parent traversal are accepted.
Only the requested new destination is written. Original evidence stays read-only.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import tarfile


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(8 << 20), b''):
            h.update(data)
    return h.hexdigest()


def stage(archive, expected, target):
    archive, target = Path(archive), Path(target)
    if sha(archive) != expected:
        raise ValueError('archive SHA-256 mismatch')
    target.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive) as t:
        for item in t:
            p = PurePosixPath(item.name)
            if p.is_absolute() or PureWindowsPath(item.name).drive or '..' in p.parts or item.issym() or item.islnk():
                raise ValueError('unsafe archive member: ' + item.name)
            if item.isdir():
                continue
            if not item.isfile():
                raise ValueError('non-file archive member')
            destination = target.joinpath(*p.parts)
            destination.resolve().relative_to(target.resolve())
            destination.parent.mkdir(parents=True, exist_ok=True)
            with t.extractfile(item) as src, destination.open('xb') as dst:
                for data in iter(lambda: src.read(8 << 20), b''):
                    dst.write(data)
    manifests = [p for name in ('FILES.sha256', 'SHA256SUMS') for p in target.glob(name)]
    if len(manifests) != 1:
        raise ValueError('one top-level manifest required')
    count = 0
    for row in manifests[0].read_text().splitlines():
        digest, name = row.split(maxsplit=1)
        name = name.lstrip('*')
        p = PurePosixPath(name)
        if p.is_absolute() or PureWindowsPath(name).drive or '..' in p.parts:
            raise ValueError('unsafe manifest path')
        target.joinpath(*p.parts).resolve().relative_to(target.resolve())
        if sha(target.joinpath(*p.parts)) != digest:
            raise ValueError('member SHA-256 mismatch: ' + name)
        count += 1
    report = {'archive': str(archive.resolve()), 'archive_sha256': expected,
              'verified_files': count, 'output': str(target.resolve())}
    target.with_suffix('.stage.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('archive'); p.add_argument('sha256'); p.add_argument('target')
    a = p.parse_args()
    stage(a.archive, a.sha256, a.target)
