"""Seal small evidence after a completed seven-model suite; keep large data remote."""
from pathlib import Path
import argparse, hashlib, json, subprocess, tarfile


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return {'bytes': path.stat().st_size, 'sha256': h.hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--job', required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    suite = json.loads((root / 'suite-final.json').read_text())
    assert suite['passed'] and len(suite['models']) == 7, 'suite has not passed'
    acct = subprocess.check_output(
        ['sacct', '-X', '-j', args.job, '-n', '-P',
         '--format=JobID,State,ExitCode,Elapsed,NodeList,AllocCPUS'],
        universal_newlines=True)
    assert '|COMPLETED|0:0|' in acct, 'allocation has not completed successfully'
    (root / 'sacct-final.txt').write_text(acct)
    index = {'job': args.job, 'root': str(root), 'large_files_remain_remote': True,
             'source_archive': digest(root / 'source.tar.gz'),
             'audit_script': digest(Path(__file__).resolve()), 'models': {}}
    binaries = set()
    for name, result in suite['models'].items():
        assert result['passed'] and result['numerical_gate']['steps'] == 9
        binaries.add(result['binary_sha256'])
        run = root / ('run-' + name)
        for leaf, expected in result['outputs'].items():
            assert digest(run / leaf) == expected, (name, leaf, 'output changed')
        cp = Path(result['checkpoint'])
        index['models'][name] = {
            'checkpoint': str(cp),
            # Include prompt and binary references omitted by the initial runner filter.
            'all_checkpoint_files': {p.name: digest(p) for p in cp.iterdir() if p.is_file()},
            'execution': digest(run / 'execution.json')}
    assert len(binaries) == 1
    index['binary_sha256'] = binaries.pop()
    assert digest(root / 'experiment/build/llm_cd_bench')['sha256'] == index['binary_sha256']
    staged = root / 'experiment/source'
    index['compiled_source_files'] = {
        str(p.relative_to(staged)): digest(p) for p in staged.rglob('*')
        if p.is_file() and p.suffix in ('.hpp', '.cpp', '.txt')}
    (root / 'sealed-index.json').write_text(json.dumps(index, indent=2) + '\n')
    files = [root / n for n in ('suite-final.json', 'suite-progress.json',
             'upload.sha256', 'sacct-final.txt', 'sealed-index.json')]
    files += list(root.glob('slurm-*.log'))
    files += [p for p in (root / 'build-evidence').rglob('*') if p.is_file()]
    for name in suite['models']:
        run = root / ('run-' + name)
        files += [p for p in run.iterdir() if p.is_file() and
                  (p.suffix == '.log' or p.name in (
                      'execution.json', 'validation.json', 'numerical-gates.json',
                      'cd-payload.json', 'systemc_receipt.json', 'flow-summary.json',
                      'flow-controls.jsonl', 'tensor-link.json'))]
    with tarfile.open(str(root / 'evidence.tar.gz'), 'x:gz') as archive:
        for p in sorted(set(files)):
            archive.add(str(p), arcname=str(p.relative_to(root)))
    print(json.dumps(digest(root / 'evidence.tar.gz')))


if __name__ == '__main__':
    main()
