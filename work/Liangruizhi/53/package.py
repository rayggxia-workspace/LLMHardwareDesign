"""Allowlisted small evidence packaging: no weights, wheels, credentials or venv."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--scratch', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    files = {}
    for i in (1, 2):
        folder = a.scratch / f'server-return0{i}'
        for f in sorted(folder.rglob('*')):
            if f.is_file():
                files[f'round{i}/' + f.relative_to(folder).as_posix()] = f.read_bytes()
        f = a.scratch / f'server-return0{i}.zip'
        files['raw/' + f.name] = f.read_bytes()
        f = a.scratch / f'audit0{i}.json'
        files['validation/' + f.name] = f.read_bytes()
    for name in ['transfer-manifest.json', 'fix-wheel.sha256', 'probe.log', 'env-probe.log', 'bootstrap.log',
                 'setup-retry.log', 'pilot-submit.log', 'pilot-resubmit.log', 'repeat-cpu.log',
                 'negative-audit.json', 'negative-token.log', 'negative-shape.log', 'negative-timing.log',
                 'negative-audit.py', 'run-input01.zip']:
        f = a.scratch / name
        files['history/' + name] = f.read_bytes()
    here = Path(__file__).resolve().parents[3] / 'project/experiments/cpu_pilot'
    files['validation/audit.py'] = (here / 'audit.py').read_bytes()
    files['analysis/package.py'] = Path(__file__).read_bytes()
    archive = a.output / 'evidence.zip'
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as z:
        for name, raw in sorted(files.items()):
            item = zipfile.ZipInfo(name, (2026, 10, 23, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(item, raw)
    raw = archive.read_bytes()
    index = {'schema': 'issue53-evidence/1', 'source_commit': '70c0157e348dc4bc1b3792fdb12ee3d78a342a57',
        'archive': {'file': archive.name, 'bytes': len(raw), 'sha256': digest(raw)},
        'members': {name: {'bytes': len(data), 'sha256': digest(data)} for name, data in sorted(files.items())}}
    (a.output / 'index.json').write_text(json.dumps(index, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'archive': index['archive'], 'members': len(files)}))


if __name__ == '__main__':
    main()
