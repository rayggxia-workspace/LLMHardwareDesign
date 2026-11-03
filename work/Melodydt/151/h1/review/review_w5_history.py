"""Independent in-memory W5 history tamper audit; no source files are edited."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf8'))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[5])
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    root = args.root.resolve()
    review = root / 'work/Melodydt/151/h1/review'
    output = args.output.resolve()
    if review not in output.parents or output.exists():
        raise ValueError('use a new output in this package review directory')
    baseline = root.parents[1] / 'quality-77b47e3/integrated'
    source = root / 'scripts/check_w5_if.py'
    raw_source = source.read_bytes()
    spec = importlib.util.spec_from_file_location('w5_history_target', str(source))
    target = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(target)
    prefix = 'work/Melodydt/151/h1/historical-w5/'
    manifest_path = prefix + 'document-transform.json'
    manifest = read_json(root / manifest_path)
    assert len(manifest['documents']) == 2
    lock_paths = ['w5-if-source-lock.json', 'w5-if-contract.json', 'w5-if-native-audit.json',
                  'w5-if-family-audit.json', 'w5-if-protocol-channels.json', 'w5-if-example-traces.json']
    unchanged = []
    for path in lock_paths:
        name = 'work/Melodydt/151/' + path
        assert (root / name).read_bytes() == (baseline / name).read_bytes()
        unchanged.append(name)
    old_lines = (baseline / 'scripts/check_w5_if.py').read_text(encoding='utf8').splitlines()
    iterator = iter(raw_source.decode('utf8').splitlines())
    assert all(any(candidate == old for candidate in iterator) for old in old_lines), 'old lines/checks removed'
    old_runtime = []
    for directory in ['project/rtl', 'project/tb']:
        for path in sorted((baseline / directory).rglob('*')):
            if path.is_file():
                name = path.relative_to(baseline).as_posix()
                assert path.read_bytes() == (root / name).read_bytes(), name
                old_runtime.append(name)
    assert len(old_runtime) == 54
    results = []

    def check(condition, label):
        if not condition:
            raise ValueError(label)

    def invoke(name, path=None, current=None, transform=None, archive=None, expect_reject=True):
        doc = copy.deepcopy(manifest['documents'][0])
        mm = copy.deepcopy(manifest)
        old = (root / doc['historical_path']).read_bytes()
        now = (root / doc['path']).read_bytes() if current is None else current
        requested = doc['path'] if path is None else path
        if transform:
            transform(mm, now)
        data = {manifest_path: (json.dumps(mm, ensure_ascii=False) + '\n').encode('utf8')}
        for entry in mm['documents']:
            data[entry['historical_path']] = (root / doc['historical_path']).read_bytes() if archive is None else archive
        result = dict(case=name, rejection_expected=expect_reject)
        try:
            returned = target.historical_document_bytes(requested, now, doc['historical_sha256'], data.__getitem__, check)
        except (ValueError, KeyError) as exc:
            result.update(observed='REJECTED', diagnostic=str(exc), passed=expect_reject)
        else:
            result.update(observed='ACCEPTED', passed=not expect_reject and returned == old)
        results.append(result)

    for doc in manifest['documents']:
        prior = (root / doc['historical_path']).read_bytes()
        assert sha(prior) == doc['historical_sha256']
        assert prior == (baseline / doc['path']).read_bytes(), 'frozen document differs from accepted prior bytes'
        returned = target.historical_document_bytes(doc['path'], (root / doc['path']).read_bytes(),
                                                    doc['historical_sha256'],
                                                    lambda name: (root / name).read_bytes(), check)
        assert returned == prior
    doc = manifest['documents'][0]
    raw = (root / doc['path']).read_bytes()
    prior = (root / doc['historical_path']).read_bytes()
    invoke('current_document_byte_tamper', current=raw + b'\n')
    invoke('frozen_archive_byte_tamper', archive=prior + b'\n')
    invoke('forged_current_SHA_without_matching_edits', current=raw + b'\n',
           transform=lambda mm, now: mm['documents'][0].update(current_sha256=sha(now)))
    invoke('wrong_old_edit_slice', transform=lambda mm, now: mm['documents'][0]['edits'][0].update(old='tampered'))
    invoke('native_source_fallback_forbidden', path='project/rtl/block_v2/block_v2_m.sv')
    invoke('archive_parent_escape_forbidden',
           transform=lambda mm, now: mm['documents'][0].update(historical_path=prefix + '../outside-archive.frozen.txt'))
    invoke('duplicate_registered_document', transform=lambda mm, now: mm['documents'].append(copy.deepcopy(mm['documents'][0])))
    invoke('docs_prefix_cannot_mask_native_path', path='docs/../project/rtl/block_v2/block_v2_m.sv')
    proc = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(source), '--root', str(root)],
                          cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.returncode == 0, proc.stderr.decode('utf8')
    normal = json.loads(proc.stdout.decode('utf8'))
    assert normal['status'] == 'PASS' and normal['checks_passed'] == 525
    assert normal['unchanged_source_locks_verified'] == 22
    assert set(normal['historical_document_transforms_verified']) == {x['path'] for x in manifest['documents']}
    assert source.read_bytes() == raw_source, 'source changed during audit'
    passed = all(x['passed'] for x in results)
    report = dict(status='PASS_INDEPENDENT_W5_HISTORY_AUDIT' if passed else 'FINDINGS_OPEN',
                  checker_sha256=sha(raw_source), audit_sha256=sha(Path(__file__).read_bytes()),
                  manifest_sha256=sha((root / manifest_path).read_bytes()),
                  historical_docs_verified=2, original_checker_lines_retained=True,
                  original_locks_unchanged=unchanged, original_runtime_unchanged=54,
                  baseline_checks=normal['checks_passed'], original_source_locks_verified=22,
                  normal_stdout_bytes=len(proc.stdout), normal_stdout_sha256=sha(proc.stdout),
                  normal_stderr_bytes=len(proc.stderr), normal_stderr_sha256=sha(proc.stderr),
                  tamper_cases=results,
                  prior_finding=dict(source_sha256='d3507e489d7df555de864650c72d19d3e14cef62aeb59dcde85255081c2930eb',
                                     issue='prefix-only archive admission accepted ../outside-archive.frozen.txt with frozen matching bytes',
                                     fixed='two explicit docs and exact archive literal mapping'),
                  limits=['read-only static document/source audit', 'not RTL or numerical execution',
                          'not external PR approval', 'manifest/transform review is source-bound, not an independent cryptographic authority'])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf8'))
    print(json.dumps(dict(status=report['status'], source=report['checker_sha256'],
                          tampers=len(results), failures=[x['case'] for x in results if not x['passed']],
                          checks=525, source_locks=22, old_runtime=54, output=str(output))))
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
