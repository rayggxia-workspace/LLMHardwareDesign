"""Publish the concrete backend release to the existing PR/Issue, then read back."""
import datetime, hashlib, json, os, pathlib, subprocess, tempfile

T = pathlib.Path(__file__).resolve().parents[1]
REPO = 'rayggxia-workspace/LLMHardwareDesign'
os.environ.pop('GODEBUG', None)

def api(path, method='GET', payload=None, missing=False):
    command = ['gh', 'api', '--method', method, path]
    temp = None
    try:
        if payload is not None:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.json', delete=False) as stream:
                json.dump(payload, stream, ensure_ascii=False)
                temp = pathlib.Path(stream.name)
            command += ['--input', str(temp)]
        for attempt in range(2):
            environment = dict(os.environ)
            if attempt:
                environment['GODEBUG'] = 'http2client=0'
            try:
                result = subprocess.run(command, capture_output=True, encoding='utf-8', timeout=20, env=environment)
                break
            except subprocess.TimeoutExpired:
                if attempt:
                    raise
        if result.returncode:
            if missing and '(HTTP 404)' in result.stderr:
                return None
            raise RuntimeError(result.stderr[:800])
        return json.loads(result.stdout)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)

assert api('user')['login'] == 'YUZE-LU'
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=T).decode().strip()
assert api(f'repos/{REPO}/git/ref/heads/task/289-ab-x8')['object']['sha'] == commit
for role in ('C', 'U', 'F'):
    receipt = json.loads((T / f'audit/evidence/{role}/accepted-parent.json').read_text(encoding='utf-8'))
    assert receipt['passed'] is True
    if role in ('C', 'U'):
        assert receipt['accepted_by_checks'] is True
    assert receipt.get('full_deck_items', receipt.get('full_foundry_deck_items')) == 0

pr_body = (T / 'pr-body-current.md').read_text(encoding='utf-8')
issue_body = (T / 'issue-body-current.md').read_text(encoding='utf-8')
assert pr_body.startswith('Closes #289') and '\ufffd' not in pr_body + issue_body
commit_line = f'\n\n本次最终工程证据 commit：`{commit}`。\n'
if commit_line not in pr_body:
    pr_body += commit_line
    (T / 'pr-body-current.md').write_bytes(pr_body.encode('utf-8'))
title = '完成 A/B 非 P 接口 340 个 BUF_X8 驱动及宏/block 后端验证'
current_pr = api(f'repos/{REPO}/pulls/290')
if current_pr['title'] != title or current_pr['body'] != pr_body:
    api(f'repos/{REPO}/pulls/290', 'PATCH', {'title': title, 'body': pr_body})
issue = api(f'repos/{REPO}/issues/289')
assert [person['login'] for person in issue['assignees']] == ['YUZE-LU']
api(f'repos/{REPO}/labels/status:in_review')
labels = [label['name'] for label in issue['labels'] if not label['name'].startswith('status:')]
labels.append('status:in_review')
if issue['body'] != issue_body or {label['name'] for label in issue['labels']} != set(labels):
    api(f'repos/{REPO}/issues/289', 'PATCH', {'body': issue_body, 'labels': labels})
before_ready = api(f'repos/{REPO}/pulls/290')
if before_ready['draft']:
    ready = api('graphql', 'POST', {
        'query': 'mutation($id:ID!){markPullRequestReadyForReview(input:{pullRequestId:$id}){pullRequest{id isDraft}}}',
        'variables': {'id': before_ready['node_id']},
    })
    assert not ready.get('errors') and ready['data']['markPullRequestReadyForReview']['pullRequest']['isDraft'] is False
pr = api(f'repos/{REPO}/pulls/290')
issue = api(f'repos/{REPO}/issues/289')
assert not pr['draft'] and pr['state'] == 'open' and pr['head']['sha'] == commit
assert pr['body'] == pr_body and issue['body'] == issue_body and issue['state'] == 'open'
assert [label['name'] for label in issue['labels'] if label['name'].startswith('status:')] == ['status:in_review']
registration = api('repos/rayggxia-workspace/management-hub/pulls/5')
board = api(f'repos/{REPO}/contents/config/board.json?ref=main', missing=True)
project_env = dict(os.environ, GODEBUG='http2client=0')
projects = subprocess.run(['gh', 'api', 'graphql', '-f', 'query={organization(login:"rayggxia-workspace"){projectV2(number:1){id title}}}'], capture_output=True, encoding='utf-8', timeout=20, env=project_env)
assert projects.returncode != 0 and 'INSUFFICIENT_SCOPES' in projects.stdout and 'read:project' in projects.stderr
result = {
    'published_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'commit': commit, 'backend_accepted': True, 'PR': pr['html_url'], 'PR_draft': pr['draft'],
    'Issue': issue['html_url'], 'Issue_status': 'in_review', 'Issue_closed': False,
    'exact_body_readback': True, 'PR_body_sha256': hashlib.sha256(pr_body.encode()).hexdigest(),
    'Issue_body_sha256': hashlib.sha256(issue_body.encode()).hexdigest(),
    'reviewer': 'pending designation; no approval or merge performed',
    'registration': {'url': registration['html_url'], 'merged': registration['merged'], 'state': registration['state']},
    'repository_board_config': 'missing on main' if board is None else 'present; further board verification required',
    'Projects': 'unverified / synchronization pending; actual read:project query rejected with INSUFFICIENT_SCOPES; existing Issue7 handoff retained',
}
(T / 'audit/publication-final-backend.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result, indent=2))
