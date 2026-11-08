"""Read measured M descriptor timings without extrapolating absent descriptors.

The grid qualifies the standalone accepted M netlist, not S/LC/DMA service
latency, model accuracy, or energy. Three initialization runs must agree.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path


KEYS = ('wide_a', 'wide_b', 'rows', 'tiles', 'last_k', 'columns')
TIMES = ('load_cycles', 'execute_with_response_cycles', 'read_all_s64_cycles')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_grid(paths):
    expected = set(itertools.product(range(2), range(2), range(1, 9),
                                    range(1, 5), range(1, 9), range(1, 9)))
    reference = None
    if len(paths) != 3:
        raise ValueError('three initialization profiles required')
    for path in paths:
        rows = {}
        for line in path.read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            if set(row) != set(KEYS + TIMES):
                raise ValueError('unexpected descriptor fields')
            if any(type(row[k]) is not int for k in KEYS + TIMES):
                raise ValueError('integer fields required')
            key = tuple(row[k] for k in KEYS)
            if key in rows or key not in expected:
                raise ValueError('duplicate/unsupported descriptor')
            if any(row[k] <= 0 for k in TIMES):
                raise ValueError('positive measured cycles required')
            rows[key] = tuple(row[k] for k in TIMES)
        if set(rows) != expected:
            raise ValueError('incomplete descriptor coverage')
        if reference is not None and rows != reference:
            raise ValueError('initialization-dependent timing')
        reference = rows
    return reference


def main():
    p = argparse.ArgumentParser()
    p.add_argument('directory', type=Path)
    p.add_argument('cached_model_receipt', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    names = ('profile-1-143', 'profile-2-143', 'profile-2-144')
    paths = [a.directory / (name + '.jsonl') for name in names]
    grid = load_grid(paths)
    # Functional assertions live in the frozen driver; retain its terminal
    # summary and complete raw logs alongside the timing table.
    summaries = []
    for name in names:
        log = a.directory / (name + '.log')
        entries = [json.loads(s[8:]) for s in log.read_text(encoding='utf-8').splitlines()
                   if s.startswith('PROFILE ')]
        if len(entries) != 1 or entries[0].get('descriptors_checked') != len(grid) or \
                entries[0].get('exact_s64_passed') is not True:
            raise ValueError('functional terminal receipt missing')
        summaries.append(entries[0])
    files = paths + [a.directory / (name + '.log') for name in names]
    files += [a.directory / s for s in ('m_profile.cpp', 'm_activity.cpp', 'm-tile-0.tsv')]
    files += [a.cached_model_receipt]
    receipt = {
        'scope': 'standalone accepted M netlist descriptor timing and direct S64 checks',
        'descriptor_count': len(grid), 'initializations': list(names),
        'identical_timings': True, 'functional_summaries': summaries,
        'files_sha256': {str(f): digest(f) for f in files},
        'sample_timings': [{'descriptor': dict(zip(KEYS, key)),
                           **dict(zip(TIMES, grid[key]))}
                          for key in ((1, 1, 1, 1, 1, 1), (1, 1, 1, 4, 8, 8),
                                      (1, 1, 8, 4, 8, 8), (0, 0, 8, 4, 8, 8))],
        'excluded': ['S32 decomposition/reconstruction', 'S feeder and bank contention',
                     'LC/MC issue', 'DMA and wires', 'energy', 'full-model numerics'],
        'full_model_qualified': False,
    }
    a.output.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: receipt[k] for k in ('descriptor_count', 'identical_timings',
                                            'full_model_qualified')}))


if __name__ == '__main__':
    main()
