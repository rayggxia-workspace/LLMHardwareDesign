"""Real search comparisons and independent edge checks; no physical qualification."""
import concurrent.futures
import hashlib
import json
import subprocess
from pathlib import Path

from tree_router_cpp import route


def run(out, baseline_source):
    assert baseline_source and Path(baseline_source).is_file()
    binary = out / 'previous-router'
    subprocess.run(['g++', '-std=c++17', '-O2', str(baseline_source), '-o', str(binary)], check=True)

    def case(pair):
        mode, cost = pair
        folder = out / ('mode%d-cost%d' % pair)
        folder.mkdir()
        if mode == 0:
            terminals = {'bus_'+str(i): [(8, 8+2*i), (38, 34-2*i)] for i in range(12)}
        elif mode == 1:
            terminals = {'p': [(8, 8)]+[(12+4*i, 12+4*j) for i in range(7) for j in range(7) if (i+j)%2 == 0],
                         'q': [(40, 40)]+[(12+4*i, 14+4*j) for i in range(7) for j in range(7) if (i+j)%2 == 1]}
        else:
            terminals = {'bus_'+str(i): [(8+2*i, 8), (38-2*i, 38), (8+2*i, 40)] for i in range(10)}
        _, proof = route(terminals, 48, 48, 162+mode, 80, folder,
                         negotiated_priority=True, defer_access_vias=True, nonpreferred_cost=cost)
        assert proof['final_conflicts'] == 0 and proof['independent_tree_flood'] and proof['independent_cross_net_occupancy']
        assert proof['nonpreferred_search_cost'] == cost
        identical = None
        if cost == 2:
            old = folder / 'previous-output.txt'
            result = subprocess.run([str(binary), str(folder/'router-input.txt'), str(old)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            assert not result.stderr and result.stdout == (folder/'router.log').read_bytes()
            assert old.read_bytes() == (folder/'router-output.txt').read_bytes()
            identical = True
        return dict(mode=mode, cost=cost, default_route_and_log_bytes_identical=identical, proof=proof)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(case, [(mode, cost) for mode in range(3) for cost in (2, 8, 32)]))
    negatives = []
    for cost in (8, 32):
        for kind in ('overlap', 'wire-budget'):
            folder = out / ('negative-%s-%d' % (kind, cost))
            folder.mkdir()
            terminals = {'a': [(8, 8), (32, 32)]}
            if kind == 'overlap':
                terminals['b'] = [(8, 8), (34, 34)]
            try:
                route(terminals, 48, 48, 162, 2, folder, locked_names=['a'],
                      wire_limits={'a': 1} if kind == 'wire-budget' else {},
                      negotiated_priority=True, defer_access_vias=True, nonpreferred_cost=cost)
            except subprocess.CalledProcessError:
                negatives.append(dict(kind=kind, cost=cost, rejected=True))
            else:
                raise AssertionError('Directional search bypassed original %s check' % kind)
    executable = out/'mode0-cost8/router'
    original = (out/'mode0-cost8/router-input.txt').read_text()
    for cost, bidir in ((-1, 0), (0, 0), (3, 0), (33, 0), (8, 1)):
        header, body = original.split('\n', 1)
        values = header.split()
        values[13], values[15] = str(bidir), str(cost)
        path = out / ('negative-header-%d-%d.txt' % (cost, bidir))
        path.write_text(' '.join(values)+'\n'+body)
        result = subprocess.run([str(executable), str(path), str(path)+'.output'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert result.returncode != 0 and not Path(str(path)+'.output').exists()
        negatives.append(dict(kind='header', cost=cost, bidirectional=bidir, rejected=True))
    resource_cases = []
    for cost in (2, 8, 32):
        folder = out / ('finite-resource-%d' % cost)
        folder.mkdir()
        terminals = {'bus_'+str(i): [(8, 8+2*i), (38, 34-2*i)] for i in range(12)}
        _, proof = route(terminals, 48, 48, 162, 80, folder,
                         locked_names=list(terminals), wire_limits={n: 80 for n in terminals},
                         negotiated_priority=True, defer_access_vias=True,
                         nonpreferred_cost=cost, pareto_wire_budget=True)
        assert proof['pareto_wire_budget'] and proof['final_conflicts'] == 0
        assert proof['distance_oracle']['independent_resource_product_graph_checks'] == 120
        resource_cases.append(proof)
    for kind in ('overlap', 'wire-budget'):
        folder = out / ('negative-resource-'+kind)
        folder.mkdir()
        terminals = {'a': [(8, 8), (32, 32)]}
        if kind == 'overlap':
            terminals['b'] = [(8, 8), (34, 34)]
        try:
            route(terminals, 48, 48, 162, 2, folder, locked_names=['a'],
                  wire_limits={'a': 1} if kind == 'wire-budget' else {'a': 80},
                  negotiated_priority=True, defer_access_vias=True, pareto_wire_budget=True)
        except subprocess.CalledProcessError:
            negatives.append(dict(kind='finite-resource-'+kind, rejected=True))
        else:
            raise AssertionError('Finite-resource search bypassed original '+kind)
    return dict(passed=True, cases=rows, resource_cases=resource_cases, rejected=negatives,
                baseline_source=str(baseline_source), baseline_sha256=hashlib.sha256(Path(baseline_source).read_bytes()).hexdigest(),
                whole_system_qualified=False, scope='Search ordering/cost comparisons only; independent original edge/flood/occupancy/wire-limit checks retained; all final geometry/PG/RC/300MHz gates still required')
