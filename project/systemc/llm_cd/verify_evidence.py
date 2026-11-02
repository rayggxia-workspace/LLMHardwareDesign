"""Independently recompute frozen gates and check downloaded C/D evidence bytes."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, re


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    args = parser.parse_args()
    root = args.evidence
    tools = Path(__file__).resolve().parent.parent / 'llm/tools/assess_numerics.py'
    spec = importlib.util.spec_from_file_location('frozen_numerics', str(tools))
    frozen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frozen)
    suite = json.loads((root / 'suite-final.json').read_bytes())
    seal = json.loads((root / 'sealed-index.json').read_bytes())
    assert sha(Path(__file__).resolve().parent / 'collect_remote.py') == seal['audit_script']['sha256']
    assert suite['passed'] and len(suite['models']) == 7
    assert '|COMPLETED|0:0|' in (root / 'sacct-final.txt').read_text()
    rows = {}
    for name, expected in suite['models'].items():
        run = root / ('run-' + name)
        actual = json.loads((run / 'execution.json').read_bytes())
        assert actual == expected and actual['passed']
        assert actual['binary_sha256'] == seal['binary_sha256']
        assert sha(run / 'execution.json') == seal['models'][name]['execution']['sha256']
        for leaf in ('0.log', '1.log', '2.log', '3.log', 'validation.json',
                     'numerical-gates.json', 'cd-payload.json', 'flow-summary.json'):
            assert (run / leaf).is_file(), (name, leaf, 'missing evidence')
        assert len(actual['commands']) == 4 and all(c['returncode'] == 0 for c in actual['commands'])
        for leaf, record in actual['outputs'].items():
            p = run / leaf
            if p.exists():
                assert p.stat().st_size == record['bytes'] and sha(p) == record['sha256'], (name, leaf)
        gate = frozen.assess(run / 'validation.json')
        assert gate == json.loads((run / 'numerical-gates.json').read_bytes()) == actual['numerical_gate']
        assert gate['accepted'] and gate['steps'] == gate['top1_equal'] == 9 and gate['greedy_equal']
        windows, words, bursts, submitted, completed = map(int, actual['cd_counts'])
        log_counts = re.findall(r'CD_EXECUTED windows=(\d+) words=(\d+) bursts=(\d+) C_submitted=(\d+) C_completed=(\d+)', (run / '0.log').read_text())
        assert log_counts == [tuple(actual['cd_counts'])]
        counts = json.loads((run / 'cd-payload.json').read_bytes())
        assert counts == dict(windows=windows, words=words, bursts=bursts)
        assert windows > 0 and words > 0 and bursts > 0 and submitted == completed == 2 * windows
        for leaf in ('prompt.txt', 'weights.bin', 'weights.index', 'metadata.txt'):
            assert seal['models'][name]['all_checkpoint_files'][leaf]['sha256']
        rows[name] = dict(positions=9, windows=windows, words=words, bursts=bursts,
                          submitted=submitted, completed=completed,
                          logits_relative_l2=gate['worst_logits_relative_l2'],
                          hidden_relative_l2=gate['worst_hidden_relative_l2'])
    for leaf, expected in json.loads((root / 'build-evidence/receipt.json').read_bytes())['outputs'].items():
        assert sha(root / 'build-evidence' / leaf) == expected
    print(json.dumps(dict(passed=True, positions=63, models=rows), indent=2))


if __name__ == '__main__':
    main()
