"""Receive frozen source SHA against original Git blobs, without tensor math."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(repository, index, selected):
    entries = {x['path']: x for x in index['files']}
    records = []
    with zipfile.ZipFile(selected) as archive:
        bindings = sorted(n for n in archive.namelist()
                          if n.startswith('phase') and n.endswith('/binding.json')
                          and n.count('/') == 1)
        for name in bindings:
            raw = archive.read(name)
            if sha(raw) != entries[name]['sha256']:
                raise ValueError('binding SHA mismatch')
            binding = json.loads(raw)
            phase = name.split('/')[0]
            for path, expected in binding['sources'].items():
                parsed = PurePosixPath(path)
                if parsed.is_absolute() or '..' in parsed.parts or '\\' in path:
                    raise ValueError('unsafe source path')
                source = subprocess.check_output(
                    ['git', 'cat-file', 'blob', binding['commit']+':'+path],
                    cwd=repository)
                entry = entries[phase+'/'+path]
                if sha(source) != expected or expected != entry['sha256'] or len(source) != entry['bytes']:
                    raise ValueError('original Git blob differs: '+phase+'/'+path)
                records.append({'phase': phase, 'commit': binding['commit'],
                                'path': path, 'bytes': len(source), 'sha256': expected})
    if len(bindings) != 10:
        raise ValueError('all ten frozen phases required')
    return {'schema': 'issue74-original-git-byte-reception-v1', 'status': 'PASS',
            'phases': len(bindings), 'sources_verified': len(records), 'sources': records,
            'limits': ['Original Git blob bytes against frozen binding and delivery index only.',
                       'Selected archive requires separate byte reception; no tensor math or hardware acceptance.']}


def main():
    p = argparse.ArgumentParser(__doc__)
    for name in ('repository', 'index', 'selected', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('refuse receipt overwrite')
    result = verify(a.repository, json.loads(a.index.read_text(encoding='utf-8')), a.selected)
    with a.out.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(result['status'], result['phases'], result['sources_verified'])


if __name__ == '__main__':
    main()
