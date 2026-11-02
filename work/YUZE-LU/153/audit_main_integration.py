"""Audit the integrated index and generated C/D source without rerunning models.

Historical evidence stays byte-exact. Generated sources report exact matches
separately from checkout CRLF-to-LF differences; this is not binary equivalence.
Run after staging the integration; --out must name a new report.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OLD = '6093daab79b538c72a7ee2735ece319fb42883ae'
MAIN = '4b1df2c7cbdaa0fa6f9f468f2b5b854cec875609'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=str(ROOT))


def tree(ref, paths):
    records = git('ls-tree', '-rz', ref, '--', *paths).split(b'\0')
    return {name.decode('utf-8'): metadata.split()[2].decode('ascii')
            for record in records if record
            for metadata, name in [record.split(b'\t', 1)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    indexed = {}
    for record in git('ls-files', '-s', '-z').split(b'\0'):
        if record:
            metadata, name = record.split(b'\t', 1)
            indexed[name.decode('utf-8')] = metadata.split()[1].decode('ascii')

    protected = ['project/rtl', 'project/experiments', 'work/YUZE-LU/143/release-six']
    frozen = tree(MAIN, protected)
    actual = {name: sha for name, sha in indexed.items()
              if any(name.startswith(prefix + '/') for prefix in protected)}
    assert actual == frozen, 'main RTL/physical tree changed'

    history = tree(OLD, ['project/systemc/llm/results',
                         'project/systemc/llm_cd/results', 'work/YUZE-LU/153'])
    # The task README intentionally receives the new integration progress entry.
    history.pop('work/YUZE-LU/153/README.md', None)
    for name, sha in history.items():
        assert indexed.get(name) == sha, ('historical evidence changed', name)

    evidence = ROOT / 'project/systemc/llm_cd/results/seven-cd-03'
    seal = json.loads((evidence / 'sealed-index.json').read_bytes())
    generated = ROOT / '.systemc-build-cd-main/source'
    source_rows = {}
    for name, expected in seal['compiled_source_files'].items():
        raw = (generated / name).read_bytes()
        found = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        exact = found == expected
        if not exact:
            normalized = raw.replace(b'\r\n', b'\n')
            found_lf = dict(bytes=len(normalized), sha256=hashlib.sha256(normalized).hexdigest())
            assert found_lf == expected, ('source differs beyond checkout line endings', name)
        source_rows[name] = dict(actual=found, sealed=expected,
                                 comparison='exact' if exact else 'CRLF-to-LF only')

    module_path = ROOT / 'project/systemc/llm/tools/assess_numerics.py'
    spec = importlib.util.spec_from_file_location('frozen_numerics', str(module_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite = json.loads((evidence / 'suite-final.json').read_bytes())
    rows = {}
    for name, record in suite['models'].items():
        run = evidence / ('run-' + name)
        gate = module.assess(run / 'validation.json')
        assert gate == record['numerical_gate']
        assert gate == json.loads((run / 'numerical-gates.json').read_bytes())
        assert gate['accepted'] and gate['steps'] == gate['top1_equal'] == 9
        windows, words, bursts, submitted, completed = map(int, record['cd_counts'])
        assert submitted == completed == 2 * windows
        rows[name] = dict(positions=gate['steps'], top1=gate['top1_equal'],
                          greedy_equal=gate['greedy_equal'], windows=windows,
                          submitted=submitted, completed=completed)
    assert len(rows) == 7
    result = dict(passed=True, main=MAIN, historical_head=OLD,
                  protected_files=len(frozen), unchanged_evidence_blobs=len(history),
                  generated_source_files=len(source_rows),
                  source_comparison='exact or explicitly CRLF-to-LF only; no other byte differences',
                  generated_source_exact=sum(v['comparison'] == 'exact' for v in source_rows.values()),
                  generated_source_newline_only=sum(v['comparison'] != 'exact' for v in source_rows.values()),
                  generated_sources=source_rows, models=rows, positions=63,
                  pretrained_models_rerun=False, physical_validation=False)
    with args.out.open('x', encoding='utf-8') as output:
        output.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'generated_sources'}, indent=2))


if __name__ == '__main__':
    main()
