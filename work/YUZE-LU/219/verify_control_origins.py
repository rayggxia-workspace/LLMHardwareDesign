"""Verify pinned control inputs against GitHub Git blob identities."""
import hashlib
import json
import sys
from pathlib import Path

from publish_branch import api


def main():
    root = Path(__file__).resolve().parents[3]
    source = Path.home() / 'AppData/Local/Codex/issue219-control-source'
    index = json.loads((source / 'index.json').read_text())
    trees = {}
    rows = []
    for path, row in index['files'].items():
        commit = row.get('source_commit', index['ref'])
        if commit not in trees:
            cache = root.parent / ('issue219-git-tree-' + commit + '.json')
            if cache.exists():
                trees[commit] = {name: r['sha'] for name, r in json.loads(cache.read_text()).items()}
            else:
                tree = api('repos/rayggxia-workspace/LLMHardwareDesign/git/trees/' + commit + '?recursive=1')
                trees[commit] = {r['path']: r['sha'] for r in tree['tree'] if r['type'] == 'blob'}
        data = (source / path).read_bytes()
        sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert sha == row['git_blob'] == trees[commit][path], path
        assert hashlib.sha256(data).hexdigest() == row['sha256'], path
        rows.append({'path': path, 'commit': commit, 'git_blob': sha, 'sha256': row['sha256']})
    version = 'mutex-control-v2' if '--current-only' in sys.argv else 'mutex-control-v1'
    output = root / ('work/YUZE-LU/219/results/' + version + '/control-origin-verification.json')
    output.write_bytes((json.dumps({'verified': rows}, indent=2) + '\n').encode())
    print(json.dumps({'pinned_control_files_verified': len(rows)}))


if __name__ == '__main__':
    main()
