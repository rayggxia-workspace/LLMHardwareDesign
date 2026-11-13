"""Non-force Git Database API publication when Git HTTPS is unreachable.

Only this task branch is allowed. Verify the complete tree against the local
commit, retain any differing unpublished local commit, and reread remote ref.
Credentials remain inside gh; only commit/tree IDs are printed.
"""
import argparse
from datetime import datetime, timezone
import itertools
import json
from pathlib import Path
import re
import subprocess
import tempfile

REPO = 'rayggxia-workspace/LLMHardwareDesign'


def git(*args, data=None):
    return subprocess.check_output(['git', *args], input=data)


def api(path, method='GET', body=None):
    # gh structured input preserves Unicode, HTML and actual newlines; no
    # shell interpolation, command substitution or credential extraction.
    for attempt in range(3):
        try:
            if body is None:
                command = ['gh', 'api', path]
                result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=60)
            else:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', encoding='utf-8', delete=False) as f:
                    json.dump(body, f, ensure_ascii=False)
                    name = Path(f.name)
                try:
                    result = subprocess.run(['gh', 'api', path, '--method', method, '--input', str(name)],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=90)
                finally:
                    name.unlink(missing_ok=True)
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            if attempt == 2:
                raise


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base', required=True)
    p.add_argument('--branch', required=True, choices=['task/219-general-block-search'])
    a = p.parse_args()
    assert git('branch', '--show-current').decode().strip() == a.branch
    assert git('rev-parse', 'HEAD^').decode().strip() == a.base, 'only one reviewed local commit may be published'
    endpoint = f'repos/{REPO}/git'
    assert api(endpoint + '/ref/heads/' + a.branch)['object']['sha'] == a.base, 'remote advanced; do not overwrite'
    local = git('rev-parse', 'HEAD').decode().strip()
    expected_tree = git('rev-parse', 'HEAD^{tree}').decode().strip()
    rows = []
    for name in git('diff', '--name-only', a.base, 'HEAD').decode().splitlines():
        mode = git('ls-tree', 'HEAD', '--', name).decode().split()[0]
        assert mode == '100644', 'only regular text files are supported'
        content = git('show', 'HEAD:' + name).decode('utf-8')
        rows.append({'path': name, 'mode': mode, 'type': 'blob', 'content': content})
    tree = api(endpoint + '/trees', 'POST', {'base_tree': git('rev-parse', a.base + '^{tree}').decode().strip(), 'tree': rows})
    assert tree['sha'] == expected_tree, 'remote tree bytes differ from reviewed local tree'
    raw = git('cat-file', 'commit', 'HEAD')
    header, message = raw.split(b'\n\n', 1)
    people, identities = {}, {}
    for line in header.decode().splitlines():
        match = re.match(r'^(author|committer) (.+) <([^<>]+)> (\d+) ([+-]\d{4})$', line)
        if match:
            role, name, email, epoch, zone = match.groups()
            assert name == 'YUZE-LU', 'use the actual task author'
            people[role] = {'name': name, 'email': email,
                'date': datetime.fromtimestamp(int(epoch), timezone.utc).isoformat()}
            identities[role] = (name, email, epoch, zone)
    assert len(people) == 2 and b'gpgsig' not in header
    commit = api(endpoint + '/commits', 'POST', {'message': message.decode(), 'tree': expected_tree,
                 'parents': [a.base], **people})
    remote = commit['sha']
    if remote != local:
        found = None
        for az, cz in itertools.product(['+0000', identities['author'][3]], ['+0000', identities['committer'][3]]):
            candidate = f'tree {expected_tree}\nparent {a.base}\n'
            for role, zone in [('author', az), ('committer', cz)]:
                name, email, epoch, _ = identities[role]
                candidate += f'{role} {name} <{email}> {epoch} {zone}\n'
            data = candidate.encode() + b'\n' + message
            if git('hash-object', '-t', 'commit', '--stdin', data=data).decode().strip() == remote:
                found = data
                break
        assert found is not None, 'cannot reconstruct remote metadata; branch remains unchanged'
        assert git('hash-object', '-t', 'commit', '-w', '--stdin', data=found).decode().strip() == remote
    # Non-force fast-forward; server also rejects any concurrent diverging ref.
    api(endpoint + '/refs/heads/' + a.branch, 'PATCH', {'sha': remote, 'force': False})
    assert api(endpoint + '/ref/heads/' + a.branch)['object']['sha'] == remote
    if remote != local:
        git('branch', 'task/219-local-before-api-' + local[:8], local)
        git('update-ref', 'refs/heads/' + a.branch, remote, local)
    git('update-ref', 'refs/remotes/origin/' + a.branch, remote)
    print(json.dumps({'remote_commit': remote, 'tree': expected_tree, 'local_backup_commit': local, 'files': len(rows)}))


if __name__ == '__main__':
    main()
