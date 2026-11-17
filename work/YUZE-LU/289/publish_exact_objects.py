"""Publish existing commits through small REST Git objects, preserving every SHA.

Fallback for interrupted Git transport. Uses the already authenticated gh account;
never reads credentials. Uploads at most six independent blobs concurrently and
updates only the task branch after all local commit identities have been checked.
"""
import base64
import concurrent.futures
import json
import subprocess
import time

REPO = 'repos/rayggxia-workspace/LLMHardwareDesign'
BRANCH = 'task/289-ab-x8'


def git(*args):
    return subprocess.check_output(['git', *args])


def api(endpoint, data=None, method=None):
    args = ['gh', 'api', REPO + '/' + endpoint]
    if data is not None:
        args += ['--method', method or 'POST', '--input', '-']
    for attempt in range(3):
        try:
            return json.loads(subprocess.check_output(
                args, input=None if data is None else json.dumps(data).encode(),
                timeout=90, stderr=subprocess.PIPE))
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def entries(spec):
    result = []
    for row in git('ls-tree', '-z', spec).split(b'\0'):
        if not row:
            continue
        meta, name = row.split(b'\t', 1)
        mode, kind, sha = meta.decode().split()
        result.append(dict(path=name.decode('utf-8'), mode=mode, type=kind, sha=sha))
    return result


def upload_blob(sha):
    raw = git('cat-file', 'blob', sha)
    reply = api('git/blobs', dict(content=base64.b64encode(raw).decode(), encoding='base64'))
    assert reply['sha'] == sha, 'Blob bytes changed'
    return sha


assert subprocess.check_output(['gh', 'api', 'user', '--jq', '.login']).strip() == b'YUZE-LU'
remote = api('git/ref/heads/' + BRANCH)['object']['sha']
head = git('rev-parse', 'HEAD').decode().strip()
subprocess.run(['git', 'merge-base', '--is-ancestor', remote, head], check=True)
seen_blobs = set()
for commit in git('rev-list', '--reverse', remote + '..' + head).decode().splitlines():
    raw = git('cat-file', 'commit', commit)
    message = raw.split(b'\n\n', 1)[1].decode('utf-8')
    fields = git('show', '-s', '--format=%P%x00%T%x00%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI', commit).decode().strip().split('\0')
    parents, tree, an, ae, ad, cn, ce, cd = fields
    assert len(parents.split()) == 1
    paths = [p.decode('utf-8') for p in git('diff-tree', '--no-commit-id', '--name-only', '-z', '-r', parents, commit).split(b'\0') if p]
    dirs = {''}
    blobs = set()
    for path in paths:
        bits = path.split('/')
        dirs.update('/'.join(bits[:i]) for i in range(1, len(bits)))
        item = git('ls-tree', '-z', commit, '--', path)
        if item:
            mode, kind, sha = item.split(b'\t', 1)[0].decode().split()
            assert kind == 'blob'
            blobs.add(sha)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for sha in pool.map(upload_blob, sorted(blobs - seen_blobs)):
            seen_blobs.add(sha)
    print('Exact blobs uploaded:', len(blobs), 'for', commit, flush=True)
    for directory in sorted(dirs, key=lambda p: (-p.count('/'), -len(p))):
        spec = commit + (':' + directory if directory else '^{tree}')
        try:
            expected = git('rev-parse', '--verify', spec).decode().strip()
        except subprocess.CalledProcessError:
            continue  # Deleted directory: its parent's entry list omits it.
        reply = api('git/trees', dict(tree=entries(spec)))
        assert reply['sha'] == expected, ('Tree changed', directory)
    reply = api('git/commits', dict(tree=tree, parents=[parents], message=message,
                author=dict(name=an, email=ae, date=ad), committer=dict(name=cn, email=ce, date=cd)))
    assert reply['sha'] == commit, ('Commit metadata changed', reply['sha'], commit)
    print('Exact commit verified:', commit, flush=True)
assert api('git/ref/heads/' + BRANCH)['object']['sha'] == remote, 'Concurrent remote change; do not overwrite'
reply = api('git/refs/heads/' + BRANCH, dict(sha=head, force=False), 'PATCH')
assert reply['object']['sha'] == head
assert api('git/ref/heads/' + BRANCH)['object']['sha'] == head
print('Published and read back:', head, flush=True)
