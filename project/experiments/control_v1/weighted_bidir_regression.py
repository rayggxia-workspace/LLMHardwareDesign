"""Opt-in ordinary weighted search checks; independent physical checks retained."""
import concurrent.futures
import hashlib
import json
import subprocess
from pathlib import Path

from tree_router_cpp import route


def run(out, baseline_binary):
    out.mkdir()

    def case(key, tracing=False, margin=0):
        weight, scale, mode, cost, pattern = key
        folder = out / (('trace-' if tracing else '') + ('window%d-' % margin if margin else '') + 'weight%d-scale%d-mode%d-cost%d-pattern%d' % key)
        folder.mkdir()
        terminals = {'weak0': [(6, 6), (10, 6)], 'weak1': [(6, 8), (10, 8)]}
        for i in range(10):
            terminals['bus'+str(i)] = [(8+2*i, 14), (38-2*i, 30)]
            if mode == 1:
                terminals['bus'+str(i)].append((8+2*i, 32))
        if mode == 1:
            terminals['pair'] = [(10, 12), (40, 36)]
        if mode == 2:
            terminals['pg'] = [(42, 42)] + [(12+4*i, 36+4*j)
                                           for i in range(7) for j in range(2)]
        _, proof = route(terminals, 48, 48, 162+mode, 160, folder,
                         heuristic_weight=weight, locked_names=['weak0', 'weak1'],
                         wire_limits={'weak0': 16, 'weak1': 16},
                         negotiated_priority=True, defer_access_vias=True,
                         congestion_scale=scale, bidirectional_two_terminal=True,
                         nonpreferred_cost=cost, pareto_wire_budget=True,
                         resource_label_limit=8000000, critical_first=True,
                         ordinary_zero_pattern=bool(pattern), weighted_bidirectional=True,
                         trace_routing_phases=tracing, weighted_pair_margin=margin)
        assert proof['final_conflicts'] == 0 and proof['weighted_bidirectional']
        assert proof['independent_cross_net_occupancy'] and proof['independent_tree_flood']
        assert proof['distance_oracle']['independent_weighted_bidirectional_path_checks'] == 1200
        assert proof['distance_oracle']['independent_weighted_heap_order_checks'] >= 100000
        if margin:
            assert proof['weighted_pair_margin'] == margin
            assert sum(x['weighted_window_branches'] for x in proof['weighted_pair_window_trace']) > 0
        trace = proof['weighted_bidirectional_trace']
        assert trace and all(x['weighted_bidirectional_search_weight'] ==
                             1+((weight-1) >> min(x['round']//4, 8)) for x in trace)
        exercised = trace[-1]['weighted_bidirectional_branches_cumulative']
        if weight > 1 and not pattern:
            assert exercised > 0
        exact = None
        phase_exact = None
        # Preserve every routed byte and ordering counter against source735's
        # original std::priority_queue, including ties and window variants.
        heap_flags = ['--resource-labels=8000000', '--critical-first', '--weighted-bidirectional']
        if pattern:
            heap_flags.append('--ordinary-zero-pattern')
        if margin:
            heap_flags.append('--weighted-pair-margin='+str(margin))
        with (folder/'std-heap.log').open('w') as log:
            subprocess.run([str(baseline_binary), str(folder/'router-input.txt'),
                            str(folder/'std-heap-output.txt'), *heap_flags], stdout=log, check=True)
        assert (folder/'std-heap-output.txt').read_bytes() == (folder/'router-output.txt').read_bytes()
        heap_filtered = b''.join(line for line in (folder/'router.log').read_bytes().splitlines(keepends=True)
                                 if b'routing_phase_event' not in line)
        assert heap_filtered == (folder/'std-heap.log').read_bytes()
        if tracing:
            phases = proof['routing_phase_trace']; assert phases and len(phases) % 2 == 0
            for start, end in zip(phases[::2], phases[1::2]):
                assert start['routing_phase_event'] == 'start' and end['routing_phase_event'] == 'end'
                assert (start['round'], start['net']) == (end['round'], end['net'])
                assert end['monotonic_ns'] >= start['monotonic_ns']
            flags = ['--resource-labels=8000000', '--critical-first', '--weighted-bidirectional']
            if pattern:
                flags.append('--ordinary-zero-pattern')
            with (folder/'untraced.log').open('w') as log:
                subprocess.run([str(baseline_binary), str(folder/'router-input.txt'),
                                str(folder/'untraced-output.txt'), *flags], stdout=log, check=True)
            assert (folder/'untraced-output.txt').read_bytes() == (folder/'router-output.txt').read_bytes()
            filtered = b''.join(line for line in (folder/'router.log').read_bytes().splitlines(keepends=True)
                                if b'routing_phase_event' not in line)
            assert filtered == (folder/'untraced.log').read_bytes()
            phase_exact = True
        if weight == 1:
            assert exercised == 0
            flags = ['--resource-labels=8000000', '--critical-first']
            with (folder/'baseline.log').open('w') as log:
                subprocess.run([str(baseline_binary), str(folder/'router-input.txt'),
                                str(folder/'baseline-output.txt'), *flags], stdout=log, check=True)
            assert (folder/'baseline-output.txt').read_bytes() == (folder/'router-output.txt').read_bytes()
            filtered = b''.join(line for line in (folder/'router.log').read_bytes().splitlines(keepends=True)
                                if b'weighted_bidirectional_branches_cumulative' not in line)
            assert filtered == (folder/'baseline.log').read_bytes()
            exact = True
        return dict(weight=weight, scale=scale, mode=mode, direction_cost=cost,
                    zero_pattern=bool(pattern), proof=proof, tracing=tracing, margin=margin,
                    phase_only_exact_replay=phase_exact,
                    std_heap_route_and_filtered_log_exact_replay=True,
                    actual_weighted_branches=exercised, weight1_exact_replay=exact)

    keys = [(weight, scale, mode, 2, 0) for weight in (32, 256)
            for scale in (1, 0) for mode in range(3)]
    keys += [(256, 1, mode, 32, 1) for mode in range(3)]
    keys += [(256, scale, mode, 2, 1) for scale in (1, 0) for mode in range(3)]
    keys += [(1, 1, mode, 2, 0) for mode in range(3)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(case, keys))
    assert len(rows) == 24 and sum(x['actual_weighted_branches'] for x in rows) > 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows += list(pool.map(lambda mode: case((256, 1, mode, 2, 1), tracing=True), range(3)))
    assert len(rows) == 27 and sum(x['phase_only_exact_replay'] is True for x in rows) == 3
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        rows += list(pool.map(lambda pair: case((256, 1, pair[0], 2, 1), margin=pair[1]),
                              [(mode, margin) for mode in range(3) for margin in (4, 16)]))
    assert len(rows) == 33
    assert all(x['std_heap_route_and_filtered_log_exact_replay'] for x in rows)
    first = out/'weight32-scale1-mode0-cost2-pattern0'
    good = first/'router-input.txt'
    header, body = good.read_text().split('\n', 1)
    fields = header.split(); assert fields[13] == '1'; fields[13] = '0'
    invalid = out/'no-bidirectional-input.txt'; invalid.write_text(' '.join(fields)+'\n'+body)
    rejected = []
    for label, inp, flags in [
        ('missing-mode', invalid, ['--weighted-bidirectional']),
        ('duplicate', good, ['--weighted-bidirectional', '--weighted-bidirectional']),
        ('unsupported-value', good, ['--weighted-bidirectional=4'])]:
        target = out/('invalid-'+label)
        result = subprocess.run([str(first/'router'), str(inp), str(target), *flags],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert result.returncode != 0 and not target.exists()
        rejected.append(dict(case=label, returncode=result.returncode,
                             stderr=result.stderr.decode(), rejected=True))
    folder = out/'invalid-python-context'; folder.mkdir()
    try:
        route({'net': [(6, 6), (10, 10)]}, 24, 24, 162, 10, folder,
              weighted_bidirectional=True)
    except AssertionError:
        assert not list(folder.iterdir())
        rejected.append(dict(case='python-missing-bidirectional', rejected=True))
    else:
        raise AssertionError('Invalid Python weighted context accepted')
    for label, flags in [
        ('phase-missing-weighted', ['--trace-routing-phases']),
        ('phase-duplicate', ['--weighted-bidirectional', '--trace-routing-phases', '--trace-routing-phases']),
        ('phase-unsupported-value', ['--trace-routing-phases=8'])]:
        target = out/('invalid-'+label)
        result = subprocess.run([str(first/'router'), str(good), str(target), *flags],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert result.returncode != 0 and not target.exists()
        rejected.append(dict(case=label, returncode=result.returncode,
                             stderr=result.stderr.decode(), rejected=True))
    folder = out/'invalid-python-phase-context'; folder.mkdir()
    try:
        route({'net': [(6, 6), (10, 10)]}, 24, 24, 162, 10, folder, trace_routing_phases=True)
    except AssertionError:
        assert not list(folder.iterdir())
        rejected.append(dict(case='python-phase-missing-weighted', rejected=True))
    else:
        raise AssertionError('Invalid Python phase context accepted')
    for label, flags in [
        ('window-missing-weighted', ['--weighted-pair-margin=4']),
        ('window-duplicate', ['--weighted-bidirectional', '--weighted-pair-margin=4', '--weighted-pair-margin=4']),
        ('window-unsupported-value', ['--weighted-bidirectional', '--weighted-pair-margin=8'])]:
        target = out/('invalid-'+label)
        result = subprocess.run([str(first/'router'), str(good), str(target), *flags],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert result.returncode != 0 and not target.exists()
        rejected.append(dict(case=label, returncode=result.returncode,
                             stderr=result.stderr.decode(), rejected=True))
    folder = out/'invalid-python-window-context'; folder.mkdir()
    try:
        route({'net': [(6, 6), (10, 10)]}, 24, 24, 162, 10, folder, weighted_pair_margin=4)
    except AssertionError:
        assert not list(folder.iterdir())
        rejected.append(dict(case='python-window-missing-weighted', rejected=True))
    else:
        raise AssertionError('Invalid Python window context accepted')
    return dict(passed=True, cases=rows, rejected=rejected, whole_system_qualified=False,
                helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                scope='All33 weighted/trace/window route outputs and filtered logs replay byte-exact against source735 std heap; original3 trace and3 weight1 replays retained. Every binary independently checks100000-plus mixed/tied/extreme heap operations against std::priority_queue,1200 weighted paths and original exact/resource/distance oracles. Twelve invalid contexts retained. Heap arity changes only software storage/sift depth, not keys, ordering, search space, finite branch or physical gates. No speed/convergence/physical qualification claim.')
