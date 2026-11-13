"""Collect only this task's completed runs, including failed attempts and SHA."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
REMOTE = 'yuzelu@10.129.166.172'
BASE = '/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search'
JOBS = [99897, 99898, 99900, 99901, 99903, 99904, 99905, 99906, 99907, 99908, 99909, 99910, 99911, 99912, 99913, 99914, 99915]


def main():
    py = '/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python'
    code = r'''
import hashlib, json, shutil, subprocess, tarfile
from pathlib import Path
base = Path(BASE)
out = base / 'algorithm-fix-delivery-02'
out.mkdir(exist_ok=False)
raw = subprocess.check_output(['sacct', '-n', '-P', '-j', ','.join(map(str, JOBS)), '--format=JobIDRaw,JobName,State,ExitCode,Elapsed,AllocCPUS,NodeList,Timelimit']).decode()
states = {r.split('|')[0]: r.split('|')[2] for r in raw.splitlines() if r.strip()}
for job in (99897, 99913, 99914, 99915):
    assert states[str(job)] == 'COMPLETED', (job, states.get(str(job)))
(out / 'slurm.psv').write_text(raw)
files = {}
def take(src, dst):
    src = base / src
    target = out / dst
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, target)
    files[dst] = {'server_path': str(src), 'bytes': src.stat().st_size,
                  'sha256': hashlib.sha256(src.read_bytes()).hexdigest()}
take('algorithm-fix-15-test/tests.log', 'tests.log')
take('algorithm-fix-15-test/input.sha256', 'test-source.sha256')
take('algorithm-fix-17-rows/input.sha256', 'native-source.sha256')
take('algorithm-fix-16-evaluate/input.sha256', 'evaluation-source.sha256')
take('algorithm-fix-17-rows/generation.log', 'native/generation.log')
take('algorithm-fix-17-rows/output.sha256', 'native/server-output.sha256')
for f in sorted((base / 'algorithm-fix-17-rows/result').iterdir()):
    take(str(f.relative_to(base)), 'native/' + f.name)
for f in sorted((base / 'algorithm-fix-16-evaluate/result').rglob('*.json')):
    take(str(f.relative_to(base)), 'evaluation/' + str(f.relative_to(base / 'algorithm-fix-16-evaluate/result')))
log = (base / 'algorithm-fix-17-rows/native.log').read_bytes()
assert log.count(b'NATIVE_ROWS_PASS') == 3
(out / 'native/replay-summary.log').write_text('\n'.join(l for l in log.decode().splitlines() if 'NATIVE_ROWS_PASS' in l) + '\n')
files['native/full-log'] = {'server_path': str(base / 'algorithm-fix-17-rows/native.log'),
    'bytes': len(log), 'sha256': hashlib.sha256(log).hexdigest(), 'kept_server': True}
take('algorithm-fix-01-qualify/instrumented/instrumentation.json', 'qualification-instrumentation.json')
qlog = (base / 'algorithm-fix-01-qualify/native.log').read_bytes()
(out / 'qualification-profiles.log').write_text('\n'.join(l for l in qlog.decode().splitlines() if l.startswith('PROFILE') or 'PASS U native' in l) + '\n')
files['qualification/full-log'] = {'server_path': str(base / 'algorithm-fix-01-qualify/native.log'),
    'sha256': hashlib.sha256(qlog).hexdigest(), 'kept_server': True}
take('dependencies/pr182-test_dma.cpp', 'pr182-test_dma.cpp')
for job, folder in [(99908,'algorithm-fix-10-test'),(99909,'algorithm-fix-11-evaluate')]:
    for name in ('tests.log','evaluation.log'):
        f = base / folder / name
        if f.exists(): take(str(f.relative_to(base)), 'failures/' + str(job) + '-' + name)
receipt = {'jobs': JOBS, 'final_test_job': 99913, 'final_native_job': 99915, 'final_evaluation_job': 99914,
           'test_count': 34, 'outputs': files,
           'scope': 'algorithm with virtual external memory; no physical/native-DMA/control-image prerequisite',
           'native_scope': '2048 RMS + residual ADD and 16 Softmax; three-initial-state U client replay',
           'full_model_scope': 'full Qwen2.5-3B import and detailed software coverage; full native lowering not completed',
           'failures': {'99908': 'unit fixture used wrong input key; older test expected only CP history',
                        '99909': 'new parallel constructor did not prefilter combined wire budget; fixed'}}
(out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
with tarfile.open(base / 'algorithm-fix-delivery-02.tar.gz', 'w:gz') as tar:
    for f in sorted(out.rglob('*')):
        if f.is_file(): tar.add(f, arcname=str(f.relative_to(out)))
print(json.dumps({'files': len(files), 'archive_bytes': (base / 'algorithm-fix-delivery-02.tar.gz').stat().st_size}))
'''.replace('BASE', repr(BASE)).replace('JOBS', repr(JOBS))
    # Substitute only unique identifiers above; never interpolate shell code.
    result = subprocess.run(['ssh', REMOTE, py, '-B', '-'], input=code.encode(), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=60)
    if result.returncode:
        raise RuntimeError(result.stderr.decode())
    print(result.stdout.decode().strip())
    archive = Path.home() / 'AppData/Local/Codex/algorithm-fix-delivery-02.tar.gz'
    subprocess.run(['scp', REMOTE + ':' + BASE + '/algorithm-fix-delivery-02.tar.gz', str(archive)], check=True, timeout=60)
    out = ROOT / 'work/YUZE-LU/219/results/fix-v2'
    out.mkdir(exist_ok=False)
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            target = (out / member.name).resolve()
            if not target.is_relative_to(out.resolve()) or not member.isfile():
                raise ValueError('archive path/type rejected')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(tar.extractfile(member).read())
    receipt = json.loads((out / 'receipt.json').read_text())
    for name, row in receipt['outputs'].items():
        if not row.get('kept_server'):
            assert hashlib.sha256((out / name).read_bytes()).hexdigest() == row['sha256'], name
    matches = set()
    for manifest in ('test-source.sha256', 'native-source.sha256', 'evaluation-source.sha256'):
        for line in (out / manifest).read_text().splitlines():
            sha, name = line.split(maxsplit=1)
            if '/' in name:
                continue
            f = ROOT / 'project/experiments/block_synthesis' / name
            assert hashlib.sha256(f.read_bytes()).hexdigest() == sha, (manifest, name)
            matches.add(name)
    (out / 'source-verification.json').write_text(json.dumps({'passed': True, 'files': sorted(matches)}, indent=2) + '\n')
    print(json.dumps({'verified_source_files': len(matches), 'output': str(out)}))


if __name__ == '__main__':
    main()
