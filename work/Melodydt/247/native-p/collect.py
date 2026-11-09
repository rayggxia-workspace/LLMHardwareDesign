"""Collect terminal Issue247 runs, preserving partial failures honestly.

Run locally in the authorized server run directory; this program has no SSH,
upload, publish, cancellation, or source modification capability. All result
files are SHA-256 hashed, including excluded objects/binaries/large JSONL.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile


PARENT = Path('/public/home/yuzelu/Melodydt/issue247-area-speed')
TERMINAL = {'COMPLETED', 'FAILED', 'CANCELLED', 'TIMEOUT', 'OUT_OF_MEMORY',
            'NODE_FAIL', 'PREEMPTED', 'BOOT_FAIL', 'DEADLINE', 'REVOKED'}
LIGHT_SUFFIXES = {'.json', '.log', '.txt', '.sha256', '.md', '.csv', '.sv', '.jsonl'}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    state = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            state.update(block)
    return state.hexdigest()


def parse_status(text, job):
    matches = []
    for line in text.splitlines():
        fields = line.split('|')
        if len(fields) >= 6 and fields[0] == str(job):
            matches.append(fields[:6])
    require(len(matches) == 1, 'need exactly one pipe-delimited sacct main-job row')
    row = dict(zip(('job_id', 'job_name', 'state', 'exit_code', 'elapsed', 'nodes'), matches[0]))
    row['state'] = row['state'].split()[0].rstrip('+')
    require(row['state'] in TERMINAL, 'job is not terminal: ' + row['state'])
    return row


def exclusion(path, relative, max_bytes):
    if any(part == 'obj' or part.startswith(('obj-', 'obj_')) for part in relative.parts):
        return 'object_directory'
    if path.stat().st_size > max_bytes:
        return 'size_limit_retained_on_server'
    if path.suffix.lower() not in LIGHT_SUFFIXES:
        return 'binary_or_generated_source_retained_on_server'
    return None


def collect(root, job, status_text, expected_parent=PARENT, max_bytes=16 * 1024 * 1024):
    root, expected_parent = Path(root).resolve(), Path(expected_parent).resolve()
    require(root.parent == expected_parent and re.fullmatch(r'run\d+', root.name),
            'run directory is outside the explicitly selected task parent')
    require(root.is_dir() and (root / 'results').is_dir(), 'missing run/results directory')
    status = parse_status(status_text, job)
    outputs_path = root / 'output-files.sha256'
    report_path = root / 'collection.json'
    archive_path = root / 'receipts.tar'
    summary_path = root / 'receipts.summary.json'
    for target in (outputs_path, report_path, archive_path, summary_path):
        require(not target.exists(), 'refuse to replace existing evidence: ' + str(target))
    status_path = root / ('collection-sacct.txt' if (root / 'sacct.txt').exists() else 'sacct.txt')
    require(not status_path.exists(), 'refuse to replace existing status receipt')
    status_path.write_bytes(status_text.encode('utf-8'))
    manifest_path = root / 'inputs.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    source_commit = manifest.get('source_commit')
    warnings = []
    if not isinstance(source_commit, str) or not re.fullmatch('[0-9a-f]{40}', source_commit):
        warnings.append('missing_or_invalid_manifest_source_commit')
    selected, excluded, file_hashes, components = [], [], {}, []
    for path in sorted((root / 'results').rglob('*')):
        require(not path.is_symlink(), 'refuse result symlink: ' + str(path))
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        before = path.stat()
        digest = sha(path)
        after = path.stat()
        require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
                'result changed while hashing: ' + str(relative))
        file_hashes[relative.as_posix()] = digest
        reason = exclusion(path, relative.relative_to('results'), max_bytes)
        if reason:
            excluded.append(dict(path=relative.as_posix(), bytes=before.st_size,
                                 sha256=digest, reason=reason))
        else:
            selected.append(path)
        if path.name == 'result.json' and not any(
                part == 'obj' or part.startswith(('obj-', 'obj_')) for part in relative.parts):
            component = dict(path=relative.as_posix(), sha256=digest)
            try:
                value = json.loads(path.read_text(encoding='utf-8'))
                component.update(passed=value.get('passed'), source_commit=value.get('source_commit'),
                                 scope=value.get('scope'), error=value.get('error'))
                if component['source_commit'] is not None and component['source_commit'] != source_commit:
                    warnings.append('component_source_commit_mismatch:' + relative.as_posix())
            except (ValueError, UnicodeError) as error:
                component.update(passed=None, error='invalid/incomplete JSON: ' + str(error))
            components.append(component)
    outputs_path.write_bytes(''.join(digest + '  ' + name + '\n'
                                    for name, digest in sorted(file_hashes.items())).encode())
    main = next((entry for entry in components if entry['path'] == 'results/result.json'), None)
    whole_passed = (status['state'] == 'COMPLETED' and status['exit_code'] == '0:0' and
                    main is not None and main.get('passed') is True and not warnings)
    metadata = ['allocation.txt', 'sacct.txt', 'collection-sacct.txt', 'tools.sha256',
                'source-files.sha256', 'input-files.sha256', 'inputs.json', 'job.sh',
                'payload.sha256', 'slurm-' + str(job) + '.log', 'output-files.sha256']
    missing_metadata = [name for name in metadata if not (root / name).is_file()]
    for name in metadata:
        path = root / name
        if path.is_file():
            require(not path.is_symlink(), 'refuse metadata symlink')
            selected.append(path)
    selected = sorted(set(selected))
    report = dict(schema_version=1, run=root.name, run_root=str(root), job=status,
                  collection_succeeded=True, whole_run_passed=whole_passed,
                  classification='complete_pass' if whole_passed else 'partial_or_failed_run',
                  source_commit=source_commit, input_manifest_sha256=sha(manifest_path) if manifest_path.exists() else None,
                  main_result=main, component_receipts=components, warnings=warnings,
                  total_result_files_hashed=len(file_hashes), result_files_selected=sum(
                      p.relative_to(root).parts[0] == 'results' for p in selected),
                  all_results_sha256_manifest='output-files.sha256',
                  collected_files=[p.relative_to(root).as_posix() for p in selected] + ['collection.json'],
                  omitted_files=excluded, missing_optional_metadata=missing_metadata,
                  policy='hash all regular results; omit obj/obj-*/obj_*, binaries and files above size limit; '
                         'retain successful subcomponents without claiming a failed parent passed',
                  max_selected_result_bytes=max_bytes)
    report_path.write_bytes((json.dumps(report, indent=2) + '\n').encode())
    with tarfile.open(archive_path, 'x') as archive:
        for path in selected + [report_path]:
            archive.add(path, arcname=path.relative_to(root).as_posix(), recursive=False)
    summary = dict(job=job, run=root.name, whole_run_passed=whole_passed,
                   classification=report['classification'], source_commit=source_commit,
                   total_outputs_hashed=len(file_hashes), collected_files=len(selected) + 1,
                   omitted_files=len(excluded), receipts_sha256=sha(archive_path),
                   collection_sha256=sha(report_path),
                   main_result_sha256=main['sha256'] if main else None,
                   successful_component_paths=[c['path'] for c in components if c.get('passed') is True])
    summary_path.write_bytes((json.dumps(summary, indent=2) + '\n').encode())
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('job', type=int)
    parser.add_argument('--run-root', type=Path, default=Path.cwd())
    parser.add_argument('--expected-parent', type=Path, default=PARENT)
    parser.add_argument('--status-file', type=Path,
                        help='read already captured sacct -n -P text; otherwise query local sacct')
    parser.add_argument('--max-result-mib', type=int, default=16)
    args = parser.parse_args()
    require(args.job > 0 and args.max_result_mib > 0, 'invalid job/size parameter')
    status = args.status_file.read_text(encoding='utf-8') if args.status_file else subprocess.check_output(
        ['sacct', '-j', str(args.job), '-X', '-n', '-P',
         '--format=JobIDRaw,JobName,State,ExitCode,Elapsed,NodeList'], universal_newlines=True)
    print(json.dumps(collect(args.run_root, args.job, status, args.expected_parent,
                             args.max_result_mib * 1024 * 1024), indent=2))


if __name__ == '__main__':
    main()
