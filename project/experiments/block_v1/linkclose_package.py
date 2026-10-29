"""Package bounded, SHA-checked closure receipts without rewriting their bytes."""
import argparse
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def package(folder):
    evidence = folder / 'evidence'
    files = []
    for run in sorted(evidence.glob('closure-run*')):
        index = json.loads((run / 'index.json').read_text())
        for name, record in index['files'].items():
            path = run / name
            assert path.is_file() and path.resolve().is_relative_to(run.resolve())
            raw = path.read_bytes()
            assert digest(raw) == record['sha256'] and len(raw) == record['bytes']
        files.extend(p for p in run.rglob('*') if p.is_file())
    assert files, 'Expand or collect the closure evidence before packaging'
    destination = folder / 'closure-evidence.tar.gz'
    members = {}
    with destination.open('wb') as output:
        with gzip.GzipFile(fileobj=output, mode='wb', filename='', mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode='w', format=tarfile.PAX_FORMAT) as tar:
                for path in sorted(files):
                    name = path.relative_to(evidence).as_posix()
                    data = path.read_bytes()
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    info.mode = 0o644
                    info.mtime = info.uid = info.gid = 0
                    tar.addfile(info, io.BytesIO(data))
                    members[name] = dict(bytes=len(data), sha256=digest(data))
    # Reopen the actual deliverable and independently compare every member.
    with tarfile.open(destination, 'r:gz') as tar:
        assert set(tar.getnames()) == set(members)
        for member in tar:
            assert member.isfile() and '..' not in Path(member.name).parts
            raw = tar.extractfile(member).read()
            assert members[member.name] == dict(bytes=len(raw), sha256=digest(raw))
    manifest = dict(archive=destination.name, sha256=digest(destination.read_bytes()),
                    bytes=destination.stat().st_size, members=len(members),
                    uncompressed_file_bytes=sum(r['bytes'] for r in members.values()),
                    qualification='Bounded captured reports and receipts; excluded raw files remain on the authorized server with original hashes in each index. No full native database or full original SPEF is in this archive.',
                    files=members)
    (folder / 'closure-evidence-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({k: v for k, v in manifest.items() if k != 'files'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('folder', type=Path)
    package(parser.parse_args().folder)
