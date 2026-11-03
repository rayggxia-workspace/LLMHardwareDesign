"""Check Issue151 documents and fixed sources; this is not a hardware test."""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

REQUIRED = {'attention', 'extra_norm', 'gated_ffn', 'gdn', 'ssm', 'moe'}
DOCUMENTS = [
    'docs/SIX_CONNECTION_SCHEMES_STUDY.md',
    'docs/SIX_CONNECTION_BRIDGE_AUDIT.md',
    'docs/SIX_CONNECTION_COORDINATION_CANDIDATE.md',
    'docs/handoffs/2026-10-31-issue-151-six-connections.md',
    'progress/Melodydt/STATUS.md',
    'work/Melodydt/151/README.md',
]
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^\s)]+)\)')
SHA40 = re.compile(r'^[0-9a-f]{40}$')

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--source-dir', type=Path)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    root = a.root.resolve()
    aux = root / 'work/Melodydt/151'
    sources = json.loads((aux / 'source-index.json').read_text(encoding='utf-8'))
    connections = json.loads((aux / 'connection-index.json').read_text(encoding='utf-8'))
    errors = []
    rows = sources['sources']
    by_id = {r['id']: r for r in rows}
    by_url = {unquote(r['url']): r for r in rows}
    if len(by_id) != len(rows):
        errors.append('duplicate source id')
    if set(s['id'] for s in connections['schemes']) != REQUIRED:
        errors.append('six scheme coverage differs')
    for r in rows:
        if not SHA40.fullmatch(r['ref']) or not SHA40.fullmatch(r['git_blob_sha']):
            errors.append('invalid Git ref/blob: ' + r['id'])
        if r['path'].startswith('ref-project/'):
            errors.append('out of scope reference package: ' + r['id'])
    for s in connections['schemes']:
        if s['end_to_end_status'] != 'candidate_not_implemented_in_this_issue':
            errors.append('unsupported end-to-end claim: ' + s['id'])
        if not s['functional_paths'] or not s['proposed_changes'] or not s['required_validation']:
            errors.append('incomplete scheme: ' + s['id'])
        for sid in s['source_ids']:
            if sid not in by_id:
                errors.append('missing source: ' + sid)
        for locus in s['change_locations']:
            if locus not in connections['ownership_categories']:
                errors.append('unknown ownership category: ' + locus)
    for mechanism in connections['existing_mechanisms']:
        for sid in mechanism['source_ids']:
            if sid not in by_id:
                errors.append('mechanism source missing: ' + sid)
    if a.source_dir:
        for r in rows:
            q = a.source_dir / r['snapshot_name']
            if not q.is_file():
                errors.append('source snapshot missing: ' + str(q))
                continue
            raw = q.read_bytes()
            git = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            if git != r['git_blob_sha'] or digest(raw) != r['sha256'] or len(raw) != r['bytes']:
                errors.append('source byte/hash mismatch: ' + r['id'])
    links = 0
    blob_links = 0
    artifacts = []
    for name in DOCUMENTS:
        q = root / name
        raw = q.read_bytes()
        text = raw.decode('utf-8')
        artifacts.append({'path': name, 'bytes': len(raw), 'sha256': digest(raw)})
        for target in LINK.findall(text):
            links += 1
            u = urlsplit(target.strip('<>'))
            if u.scheme in ('https', 'http'):
                if '/blob/' not in u.path:
                    continue
                key = unquote(u.scheme + '://' + u.netloc + u.path)
                row = by_url.get(key)
                if not row:
                    errors.append('unindexed source URL: ' + key)
                    continue
                blob_links += 1
                if u.fragment.startswith('L'):
                    m = re.fullmatch(r'L(\d+)(?:-L?(\d+))?', u.fragment)
                    if not m or not 1 <= int(m.group(1)) <= int(m.group(2) or m.group(1)) <= row['lines']:
                        errors.append('invalid source line anchor: ' + target)
            elif not u.scheme:
                if u.path and not (q.parent / unquote(u.path)).resolve().exists():
                    errors.append('broken local link in ' + name + ': ' + target)
        if any(line.rstrip() != line for line in text.splitlines()):
            errors.append('trailing whitespace: ' + name)
    for name in ['work/Melodydt/151/source-index.json', 'work/Melodydt/151/connection-index.json', 'work/Melodydt/151/verify_study.py']:
        raw = (root / name).read_bytes()
        artifacts.append({'path':name,'bytes':len(raw),'sha256':digest(raw)})
    result = {
        'schema_version':1,
        'checked_at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
        'passed':not errors,
        'python':sys.version.split()[0],
        'checks':{
            'six_schemes':len(connections['schemes']),
            'indexed_source_files':len(rows),
            'source_bytes':'PASS' if a.source_dir and not any('source snapshot' in e or 'source byte/' in e for e in errors) else 'NOT_EXECUTED' if not a.source_dir else 'FAIL',
            'markdown_links':links,
            'indexed_blob_links':blob_links,
        },
        'artifacts':artifacts,
        'errors':errors,
        'not_executed':['RTL simulation','SystemC simulation','synthesis','placement/routing','physical qualification','full-model numerical quality'],
    }
    encoded = json.dumps(result,ensure_ascii=False,indent=2) + '\n'
    if a.output:
        with a.output.open('w',encoding='utf-8',newline='\n') as f:
            f.write(encoded)
    print(encoded)
    return 0 if result['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
