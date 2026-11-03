"""Actual directional bidirectional checks; no physical qualification."""
import concurrent.futures
import hashlib
import json
import subprocess
from pathlib import Path

from tree_router_cpp import route


def run(out, baseline_binary):
    out.mkdir()

    def case(key):
        cost, mode, pattern = key
        folder = out / ('cost%d-mode%d-pattern%d' % key)
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
                         heuristic_weight=16, locked_names=['weak0', 'weak1'],
                         wire_limits={'weak0': 16, 'weak1': 16},
                         negotiated_priority=True, defer_access_vias=True,
                         congestion_scale=1, bidirectional_two_terminal=True,
                         nonpreferred_cost=cost, pareto_wire_budget=True,
                         resource_label_limit=8000000, critical_first=True,
                         ordinary_zero_pattern=bool(pattern))
        assert proof['final_conflicts'] == 0
        assert proof['independent_cross_net_occupancy'] and proof['independent_tree_flood']
        assert proof['distance_oracle']['independent_bidirectional_dijkstra_checks'] == 100
        assert proof['distance_oracle']['independent_directional_bidirectional_dijkstra_checks'] == 200
        assert all(x['constrained_priority_prefix'] == 2 and x['priority_partition_verified']
                   for x in proof['priority_partitions'])
        trace = [json.loads(x) for x in (folder/'router.log').read_text().splitlines()
                 if x.startswith('{')]
        branches = [x['bidirectional_branches_cumulative'] for x in trace
                    if 'bidirectional_branches_cumulative' in x]
        assert branches
        if not pattern and mode != 1:
            assert branches[-1] > 0
        exact = None
        if cost == 2:
            flags = ['--resource-labels=8000000', '--critical-first']
            if pattern:
                flags.append('--ordinary-zero-pattern')
            with (folder/'baseline.log').open('w') as log:
                subprocess.run([str(baseline_binary), str(folder/'router-input.txt'),
                                str(folder/'baseline-output.txt'), *flags],
                               stdout=log, check=True)
            assert (folder/'baseline.log').read_bytes() == (folder/'router.log').read_bytes()
            assert (folder/'baseline-output.txt').read_bytes() == (folder/'router-output.txt').read_bytes()
            exact = True
        return dict(cost=cost, mode=mode, pattern=bool(pattern), proof=proof,
                    actual_bidirectional_branches=branches[-1],
                    original_cost2_route_and_log_exact=exact)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(case, [(cost, mode, pattern) for cost in (2, 8, 32)
                                   for mode in range(3) for pattern in (0, 1)]))
    assert len(rows) == 18
    assert sum(x['actual_bidirectional_branches'] for x in rows if x['cost'] != 2) > 0
    return dict(passed=True, cases=rows, whole_system_qualified=False,
                helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                scope='18 actual direction-cost2/8/32 two-ended/multi-ended/PG-like cases with optional prepass on/off. Each actual binary checks original100 Dijkstra cases plus200 new directional cases, original120 resource and50000 distance cases. Six cost2 route/log byte replays against prior source remain exact. Independent original physical edge/via/occupancy/flood/wire-budget checks retained. Search regression only, no full physical or convergence claim.')
