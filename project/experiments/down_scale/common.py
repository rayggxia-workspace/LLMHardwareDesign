"""Commit-bound provenance; deterministic data bytes; no remote execution."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import io
import os
import platform
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''): h.update(block)
    return h.hexdigest()


def save(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def npz(path, arrays):
    import numpy as np
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, value in sorted(arrays.items()):
            buf = io.BytesIO(); np.save(buf, np.asarray(value), allow_pickle=False)
            info = zipfile.ZipInfo(name+'.npy', (2026, 10, 23, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED; z.writestr(info, buf.getvalue())


def config(): return json.loads((HERE/'experiment.json').read_text(encoding='utf-8'))


def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def provenance(development=False):
    commit = git('rev-parse', 'HEAD'); bindings = {}
    files = [*HERE.glob('*.py'), HERE/'experiment.json', ROOT/config()['model_contract'],
             HERE.parent/'rq_ports/model.py']
    for path in sorted(files):
        rel = path.relative_to(ROOT).as_posix(); raw = path.read_bytes()
        old = subprocess.run(['git', 'show', f'{commit}:{rel}'], cwd=ROOT, capture_output=True)
        bindings[rel] = {'sha256': hashlib.sha256(raw).hexdigest(), 'matches_commit': old.returncode == 0 and old.stdout == raw}
    dirty = bool(git('status', '--porcelain'))
    if not development and (dirty or not all(v['matches_commit'] for v in bindings.values())):
        raise ValueError('formal run requires clean commit-bound source')
    return {'commit': commit, 'development': development, 'dirty': dirty, 'sources': bindings,
            'python': platform.python_version(), 'numpy': importlib.metadata.version('numpy'),
            'executable': sys.executable, 'command': sys.argv,
            'threads': {n: os.environ.get(n) for n in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS')},
            'host': 'Liangruizhi local Windows CPU; no remote jobs'}


def manifest(output, producer, **extra):
    output = Path(output)
    save(output/'manifest.json', {'producer': producer, **extra, 'artifacts': {
        p.name: {'bytes': p.stat().st_size, 'sha256': digest(p)} for p in sorted(output.iterdir()) if p.is_file() and p.name != 'manifest.json'}})


def checked_manifest(directory):
    directory = Path(directory); m = json.loads((directory/'manifest.json').read_text())
    if m.get('status') != 'PASS': raise ValueError('input not passed')
    for name, record in m['artifacts'].items():
        p = directory/name
        if digest(p) != record['sha256'] or p.stat().st_size != record['bytes']: raise ValueError('artifact mismatch '+name)
    return m
