"""Receive an owned, qualified leaf and validate its local source binding."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--remote-bundle', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    prefix = '/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030/outputs/'
    remote = PurePosixPath(a.remote_bundle)
    assert str(remote).startswith(prefix) and '..' not in remote.parts
    assert remote.name == 'bundle.json'
    a.out.mkdir(parents=True, exist_ok=True)
    index = a.out / 'bundle.json'
    if not index.exists():
        subprocess.run(['scp', '-q', 'yuzelu@10.129.166.172:' + str(remote), str(index)], check=True)
    d = json.loads(index.read_text(encoding='utf-8'))
    archive_path = PurePosixPath(d['archive']['path'])
    assert archive_path.parent == remote.parent and archive_path.name.endswith('.tar.gz')
    archive = a.out / archive_path.name
    if not archive.exists():
        partial = archive.with_suffix('.partial')
        subprocess.run(['scp', '-q', 'yuzelu@10.129.166.172:' + str(archive_path), str(partial)], check=True)
        assert sha(partial) == d['archive']['sha256']
        partial.rename(archive)
    verifier = Path(__file__).resolve().parents[1] / 'block_feed_v1/verify_bundle.py'
    subprocess.run([sys.executable, '-X', 'utf8', str(verifier), str(a.out)], check=True)
    root = a.out / 'unpacked'
    delivery = json.loads((root / 'native/delivery.json').read_text())
    src = root / 'meta/source'
    assert sha(src / 'receipt.json') == delivery['source_receipt_sha256']
    receipt = json.loads((src / 'receipt.json').read_text())
    assert receipt['passed']
    for name in ('final-source.json', 'config.mk', 'pins.json', 'pins.tcl', 'input.sdc'):
        assert sha(src / name) == receipt['outputs'][name]
    flow = json.loads((src / 'final-source.json').read_text())
    for relative, digest in flow['rtl_sha256'].items():
        path = PurePosixPath(relative)
        assert not path.is_absolute() and '..' not in path.parts
        assert sha(root / 'meta/rtl' / relative) == digest
    received = a.out / 'received.json'
    r = json.loads(received.read_text())
    r.update(sealed_source_verified=True, rtl_sha256=flow['rtl_sha256'],
             final_files={name: dict(path=str((root/'native'/name).resolve()), sha256=row['sha256'])
                          for name, row in delivery['final_files'].items()})
    received.write_text(json.dumps(r, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=True, macro=r['macro'], sealed_source_verified=True)))


if __name__ == '__main__':
    main()
