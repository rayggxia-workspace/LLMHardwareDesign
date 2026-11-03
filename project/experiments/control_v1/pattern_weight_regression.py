"""Actual compute-node preflight of ordinary pattern/weight combinations."""
import argparse
import concurrent.futures
import hashlib
import json
import os
import traceback
from pathlib import Path

from tree_router_cpp import route


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    assert 'SLURM_JOB_ID' in os.environ
    assert len(os.sched_getaffinity(0)) <= 16
    args.out.mkdir()
    source = Path(__file__).parent
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    receipt = dict(passed=False, whole_system_qualified=False,
                   stage='ordinary-pattern-weight-regression-only',
                   job=os.environ['SLURM_JOB_ID'], inputs={})
    for name in ('pattern_weight_regression.py', 'tree_router_cpp.py',
                 'tree_router.cpp', 'resource_search.h', 'ordinary_zero_pattern.h'):
        receipt['inputs'][str(source/name)] = sha(source/name)
    try:
        def case(pair):
            weight, mode = pair
            folder = args.out / ('weight%d-mode%d' % pair)
            folder.mkdir()
            terminals = {'weak0': [(6, 6), (10, 6)], 'weak1': [(6, 8), (10, 8)]}
            count = 12 if mode == 0 else 10
            for i in range(count):
                terminals['bus'+str(i)] = [(8+2*i, 14), (38-2*i, 30)]
                if mode == 1:
                    terminals['bus'+str(i)].append((8+2*i, 32))
            if mode == 2:
                terminals['pg'] = [(42, 42)] + [(12+4*i, 36+4*j)
                                               for i in range(7) for j in range(2)]
            _, proof = route(terminals, 48, 48, 162+mode, 160, folder,
                             heuristic_weight=weight, locked_names=['weak0', 'weak1'],
                             wire_limits={'weak0': 16, 'weak1': 16},
                             negotiated_priority=True, defer_access_vias=True,
                             congestion_scale=1, bidirectional_two_terminal=True,
                             pareto_wire_budget=True, resource_label_limit=8000000,
                             critical_first=True, ordinary_zero_pattern=True)
            assert proof['final_conflicts'] == 0
            assert proof['independent_cross_net_occupancy'] and proof['independent_tree_flood']
            assert all(x['constrained_priority_prefix'] == 2 and x['priority_partition_verified']
                       for x in proof['priority_partitions'])
            assert sum(x['zero_pattern_hits'] for x in proof['ordinary_zero_pattern_trace']) > 0
            return dict(weight=weight, mode=mode, proof=proof)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            rows = list(pool.map(case, [(weight, mode) for weight in (64, 128, 256)
                                       for mode in range(3)]))
        receipt.update(passed=True, cases=rows,
                       scope='Nine actual two-ended/multi-ended/PG-like small cases at64/128/256 initial weights, same finite constraints and zero-pattern fallback. Original independent edge/via/occupancy/flood/wire-budget checks retained. Does not qualify a full physical composition or claim speed/convergence.')
    except BaseException as exc:
        receipt.update(error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        (args.out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')


if __name__ == '__main__':
    main()
