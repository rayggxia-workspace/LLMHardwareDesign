"""Collect terminal conditional width-study evidence; I/O postprocessing, never EDA."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def member(base, name):
    rel = PurePosixPath(name)
    if rel.is_absolute() or '..' in rel.parts or '\\' in name or not rel.parts:
        raise ValueError('unsafe manifest path: ' + name)
    path = base / name
    if path.is_symlink() or not path.is_file() or base not in path.resolve().parents:
        raise ValueError('missing or escaping manifest member: ' + name)
    return path


def main():
    root = Path.cwd().resolve()
    if root.parent != Path('/public/home/yuzelu/Melodydt/issue247-area-speed') or not re.fullmatch(r'run\d+', root.name):
        raise ValueError('outside the authorized run directory')
    if len(sys.argv) != 2 or not re.fullmatch(r'\d+', sys.argv[1]):
        raise ValueError('usage: collect_server.py SLURM_JOB_ID')
    job = int(sys.argv[1])
    status = subprocess.check_output(['sacct', '-j', str(job), '-X', '--noheader', '--parsable2',
        '--format=JobID,JobName,State,ExitCode,Elapsed,NodeList'], universal_newlines=True, timeout=30)
    rows = [line.split('|') for line in status.splitlines() if line.split('|')[0] == str(job)]
    terminal = ('COMPLETED', 'FAILED', 'TIMEOUT', 'OUT_OF_MEMORY', 'CANCELLED', 'NODE_FAIL', 'PREEMPTED', 'BOOT_FAIL', 'DEADLINE')
    if len(rows) != 1 or rows[0][2].split()[0] not in terminal:
        raise ValueError('job is not in an inspected terminal state: ' + status)
    if not rows[0][1].startswith('mdt-'):
        raise ValueError('unexpected job owner/name contract: ' + rows[0][1])
    if (root/'receipts.tar').exists():
        raise ValueError('refuse to overwrite an existing collection')
    manifest = json.loads((root/'inputs.json').read_text(encoding='utf-8'))
    if not re.fullmatch(r'[0-9a-f]{40}', manifest.get('source_commit', '')):
        raise ValueError('real source commit missing')
    for name, digest in manifest['code_sha256'].items():
        if sha(member(root/'source', name)) != digest:
            raise ValueError('deployed source drift: ' + name)
    for name, digest in manifest['input_sha256'].items():
        if sha(member(root, name)) != digest:
            raise ValueError('deployed input drift: ' + name)
    results = root/'results'
    if results.is_symlink():
        raise ValueError('unexpected results symlink')
    all_paths = sorted(results.rglob('*'))
    if any(path.is_symlink() for path in all_paths):
        raise ValueError('unexpected output symlink')
    outputs = [path for path in all_paths if path.is_file()]
    if any(results not in path.resolve().parents for path in outputs):
        raise ValueError('output escaped result directory')
    selected = [path for path in outputs if path.suffix in ('.json', '.log', '.ys', '.v')
                and not any(part.startswith('obj') for part in path.relative_to(results).parts)]
    result_path = results/'result.json'
    result = json.loads(result_path.read_text(encoding='utf-8')) if result_path.is_file() else {}
    if result.get('source_commit') not in (None, manifest['source_commit']):
        raise ValueError('result source commit differs from deployment')
    for job_field in ('job', 'slurm_job_id'):
        if job_field in result and str(result[job_field]) != str(job):
            raise ValueError('result ' + job_field + ' differs from requested Slurm job')
    (root/'sacct.txt').write_text(status, encoding='utf-8')
    (root/'output-files.sha256').write_text(''.join(sha(path)+'  '+path.relative_to(root).as_posix()+'\n' for path in outputs), encoding='utf-8')
    record = dict(run=root.name, job=job, run_root=str(root), source_commit=manifest['source_commit'],
        terminal_state=rows[0][2], exit_code=rows[0][3], node=rows[0][5], elapsed=rows[0][4],
        collection_succeeded=True,
        whole_run_passed=rows[0][2]=='COMPLETED' and rows[0][3]=='0:0' and result.get('passed') is True,
        functional_passed=result.get('functional_passed'),
        total_result_files_hashed=len(outputs), result_files_selected=len(selected),
        source_files_verified=len(manifest['code_sha256']), input_files_verified=len(manifest['input_sha256']),
        classification='conditional_SystemC_prefill_width',
        limits='No full-model token/s, placement/routing, timing or chip-area qualification.')
    (root/'collection.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    metadata = ['allocation.txt', 'sacct.txt', 'tools.sha256', 'source-files.sha256', 'input-files.sha256',
                'inputs.json', 'job.sh', f'slurm-{job}.log', 'output-files.sha256', 'collection.json']
    selected += [root/name for name in metadata if (root/name).is_file()]
    if any(path.is_symlink() for path in selected):
        raise ValueError('unexpected selected metadata symlink')
    with tarfile.open(root/'receipts.tar', 'x') as archive:
        for path in selected:
            archive.add(path, arcname=path.relative_to(root).as_posix(), recursive=False)
    print(json.dumps(dict(record, collected_files=len(selected), receipts_sha256=sha(root/'receipts.tar'),
        result_sha256=sha(result_path) if result_path.is_file() else None)))


if __name__ == '__main__':
    main()
