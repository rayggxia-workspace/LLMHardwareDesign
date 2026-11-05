"""Actual compute-node congestion-scale preflight; no physical qualification."""
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
    assert 'SLURM_JOB_ID' in os.environ and 15 <= len(os.sched_getaffinity(0)) <= 16
    args.out.mkdir()
    source = Path(__file__).parent
    receipt = dict(passed=False, whole_system_qualified=False,
                   stage='ordinary-pattern-scale-regression-only',
                   job=os.environ['SLURM_JOB_ID'], inputs={})
    for name in ('pattern_scale_regression.py', 'tree_router_cpp.py', 'tree_router.cpp',
                 'resource_search.h', 'ordinary_zero_pattern.h'):
        receipt['inputs'][str(source/name)] = hashlib.sha256((source/name).read_bytes()).hexdigest()
    try:
        def case(pair):
            scale, mode = pair
            folder = args.out / ('scale%d-mode%d' % pair)
            folder.mkdir()
            terminals = {'weak0': [(6, 6), (10, 6)], 'weak1': [(6, 8), (10, 8)]}
            for i in range(12 if mode == 0 else 10):
                terminals['bus'+str(i)] = [(8+2*i, 14), (38-2*i, 30)]
                if mode == 1:
                    terminals['bus'+str(i)].append((8+2*i, 32))
            if mode == 2:
                terminals['pg'] = [(42, 42)] + [(12+4*i, 36+4*j)
                                               for i in range(7) for j in range(2)]
            _, proof = route(terminals, 48, 48, 162+mode, 160, folder,
                             heuristic_weight=256, locked_names=['weak0', 'weak1'],
                             wire_limits={'weak0': 16, 'weak1': 16},
                             negotiated_priority=True, defer_access_vias=True,
                             congestion_scale=scale, bidirectional_two_terminal=True,
                             nonpreferred_cost=2, pareto_wire_budget=True,
                             resource_label_limit=8000000, critical_first=True,
                             ordinary_zero_pattern=True)
            assert proof['final_conflicts'] == 0 and proof['congestion_scale_override'] == scale
            assert proof['congestion_scale'] == (scale or 256)
            assert proof['independent_cross_net_occupancy'] and proof['independent_tree_flood']
            assert proof['distance_oracle']['independent_bidirectional_dijkstra_checks'] == 100
            assert proof['distance_oracle']['independent_directional_bidirectional_dijkstra_checks'] == 200
            assert all(x['constrained_priority_prefix'] == 2 and x['priority_partition_verified']
                       for x in proof['priority_partitions'])
            return dict(scale=scale, mode=mode, proof=proof)

        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as pool:
            rows = list(pool.map(case, [(scale, mode) for scale in (0, 1, 4, 8, 16, 32)
                                       for mode in range(3)]))
        receipt.update(passed=True, cases=rows,
                       scope='18 actual global congestion-scale0/1/4/8/16/32 and two-ended/multi-ended/PG-like cases, fixed initial weight256/cost2/bidirectional/zero-pattern. Existing default0 means effective256 here, explicitly verified; it does not mean zero penalty. Cost scale affects constrained and ordinary search penalties, never physical wire budgets. Original independent edges/vias/occupancy/flood/wire bounds and100+200 Dijkstra/120 resource/50000 distance checks retained. Search preflight only, no speed/convergence or full physical qualification.')
    except BaseException as exc:
        receipt.update(error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        (args.out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')


if __name__ == '__main__':
    main()
