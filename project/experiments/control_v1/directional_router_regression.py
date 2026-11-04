"""Real search comparisons and independent edge checks; no physical qualification."""
import concurrent.futures
import hashlib
import json
import subprocess
import sys
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
    for cost, bidir in ((-1, 0), (0, 0), (3, 0), (33, 0), (8, 2)):
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
    # Actual finite-budget C++ success and exhausted failure through the pool,
    # in addition to subprocess scheduler tests that force a mid-flight refill.
    pool_test=subprocess.run([sys.executable,'-m','unittest','test_router_trial_pool'],cwd=str(Path(__file__).parent),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True)
    (out/'dynamic-pool-subprocess-tests.log').write_bytes(pool_test.stdout)
    pool_cases=[]
    folder=out/'dynamic-pool-real-success';folder.mkdir()
    _,proof=route({'a':[(8,8),(32,32)]},48,48,162,10,folder,
        trials=2,trial_attempts=4,locked_names=['a'],wire_limits={'a':80},
        negotiated_priority=True,defer_access_vias=True,pareto_wire_budget=True)
    assert proof['final_conflicts']==0 and proof['trial_search']['dynamic_failed_attempt_refill']
    pool_cases.append(dict(kind='actual-routed-finite-budget',proof=proof))
    folder=out/'dynamic-pool-real-failure';folder.mkdir()
    try:
        route({'a':[(8,8),(32,32)]},48,48,162,2,folder,
            trials=2,trial_attempts=4,locked_names=['a'],wire_limits={'a':1},
            negotiated_priority=True,defer_access_vias=True,pareto_wire_budget=True)
    except AssertionError as exc:
        assert str(exc)=='All independent own search trials failed'
        failed=json.loads((folder/'trial-index.json').read_text())
        assert failed['attempts_started']==4 and failed['winner']is None and failed['maximum_active']==2
        assert all(row['returncode']!=0 for row in failed['records'].values())
        assert not(folder/'router-output.txt').exists()
        pool_cases.append(dict(kind='actual-finite-budget-rejection-all4-attempts',proof=failed))
    else:raise AssertionError('Dynamic pool accepted impossible wire budget')
    memory_cases=[]
    for limit in (4000000,8000000):
        folder=out/('resource-memory-'+str(limit));folder.mkdir()
        _,proof=route({'a':[(8,8),(32,32)]},48,48,162,10,folder,
            trials=2,trial_attempts=4,locked_names=['a'],wire_limits={'a':80},
            negotiated_priority=True,defer_access_vias=True,pareto_wire_budget=True,resource_label_limit=limit)
        assert proof['final_conflicts']==0 and proof['finite_resource_label_memory_envelope']==limit
        commands=proof['trial_search']['records'].values()
        assert all(('--resource-labels=8000000'in row['command'])==(limit==8000000)for row in commands)
        memory_cases.append(proof)
    for option in ('--resource-labels=0','--resource-labels=7999999','--other-option'):
        result=subprocess.run([str(executable),str(out/'mode0-cost8/router-input.txt'),str(out/'invalid-memory-output'),option],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert result.returncode!=0 and not(out/'invalid-memory-output').exists()
        negatives.append(dict(kind='memory-envelope-cli',option=option,rejected=True))
    critical_cases=[]
    for limit in (4000000,8000000):
        folder=out/('critical-mixed-'+str(limit));folder.mkdir()
        terminals={'bus_'+str(i):[(8+2*i,8),(38-2*i,38),(8+2*i,40)]for i in range(10)}
        locked=list(terminals)[:4]
        _,proof=route(terminals,48,48,162,80,folder,
            heuristic_weight=16,locked_names=locked,wire_limits={n:100 for n in locked},
            negotiated_priority=True,defer_access_vias=True,nonpreferred_cost=32,
            pareto_wire_budget=True,resource_label_limit=limit,critical_first=True)
        assert proof['final_conflicts']==0 and proof['priority_partition_each_round']
        assert len(proof['priority_partitions'])==len(proof['rounds'])
        assert all(r['constrained_priority_prefix']==4 and r['priority_partition_verified']for r in proof['priority_partitions'])
        critical_cases.append(proof)
    for flags in [('--critical-first',),('--critical-first','--critical-first'),('--resource-labels=8000000','--resource-labels=8000000')]:
        result=subprocess.run([str(executable),str(out/'mode0-cost8/router-input.txt'),str(out/'invalid-critical-output'),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert result.returncode!=0 and not(out/'invalid-critical-output').exists()
        negatives.append(dict(kind='critical-context-or-duplicate-option',flags=flags,rejected=True))
    high_weight_cases=[]
    for weight in (64,128,256):
        folder=out/('high-weight-'+str(weight));folder.mkdir()
        terminals={'bus_'+str(i):[(8+2*i,8),(38-2*i,38),(8+2*i,40)]for i in range(10)}
        locked=list(terminals)[:4]
        _,proof=route(terminals,48,48,162,80,folder,heuristic_weight=weight,
            locked_names=locked,wire_limits={n:100 for n in locked},
            negotiated_priority=True,defer_access_vias=True,nonpreferred_cost=8,
            pareto_wire_budget=True,resource_label_limit=8000000,critical_first=True)
        assert proof['final_conflicts']==0 and proof['heuristic_weight']==weight
        high_weight_cases.append(proof)
    original=(out/'mode0-cost8/router-input.txt').read_text()
    header,body=original.split('\n',1)
    for weight in (63,65,257):
        fields=header.split();fields[5]=str(weight);bad=out/('invalid-high-weight-'+str(weight)+'.txt');bad.write_text(' '.join(fields)+'\n'+body)
        target=out/('invalid-high-output-'+str(weight))
        result=subprocess.run([str(executable),str(bad),str(target)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert result.returncode!=0 and not target.exists()
        negatives.append(dict(kind='high-search-weight-envelope',weight=weight,rejected=True))
    ordinary_scale_cases=[]
    for scale in (16,64,256):
        folder=out/('ordinary-scale-'+str(scale));folder.mkdir()
        terminals={'bus_'+str(i):[(8+2*i,8),(38-2*i,38),(8+2*i,40)]for i in range(10)}
        locked=list(terminals)[:4]
        _,proof=route(terminals,48,48,162,160,folder,heuristic_weight=16,
            locked_names=locked,wire_limits={n:100 for n in locked},
            negotiated_priority=True,defer_access_vias=True,congestion_scale=1,
            pareto_wire_budget=True,resource_label_limit=8000000,critical_first=True,
            ordinary_congestion_scale=scale)
        assert proof['final_conflicts']==0 and proof['ordinary_congestion_scale_override']==scale
        trace=proof['ordinary_congestion_trace'];assert trace and all(r['ordinary_congestion_scale']==scale and r['finite_congestion_scale']==1 for r in trace)
        assert sum(r['ordinary_override_penalty_steps']for r in trace)>0
        assert all(c['priority_partition_verified']and c['constrained_priority_prefix']==4 for c in proof['priority_partitions'])
        ordinary_scale_cases.append(proof)
    good=out/'ordinary-scale-64/router-input.txt'
    for label,flags,input_path in [
        ('zero',('--ordinary-congestion-scale=0',),good),
        ('eight',('--ordinary-congestion-scale=8',),good),
        ('outside',('--ordinary-congestion-scale=257',),good),
        ('duplicate',('--critical-first','--ordinary-congestion-scale=64','--ordinary-congestion-scale=64'),good),
        ('missing-critical',('--ordinary-congestion-scale=64',),good),
        ('wrong-context',('--critical-first','--ordinary-congestion-scale=64'),out/'mode0-cost8/router-input.txt')]:
        target=out/('invalid-ordinary-scale-'+label)
        result=subprocess.run([str(executable),str(input_path),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert result.returncode!=0 and not target.exists()
        negatives.append(dict(kind='ordinary-scale-envelope-or-context',case=label,rejected=True))
    ordinary_window_cases=[]
    for margin in (4,16,64,256):
        folder=out/('ordinary-window-'+str(margin));folder.mkdir()
        terminals={'bus_'+str(i):[(8+2*i,16),(30-2*i,24),(8+2*i,28)]for i in range(10)}
        locked=list(terminals)[:4]
        _,proof=route(terminals,48,48,162,160,folder,heuristic_weight=16,
            locked_names=locked,wire_limits={n:100 for n in locked},
            negotiated_priority=True,defer_access_vias=True,congestion_scale=1,
            pareto_wire_budget=True,resource_label_limit=8000000,critical_first=True,
            ordinary_congestion_scale=64,ordinary_search_margin=margin)
        assert proof['final_conflicts']==0 and proof['ordinary_search_margin']==margin
        trace=proof['ordinary_window_trace'];assert trace and sum(r['ordinary_box_branches']for r in trace)>0
        assert all(r['effective_margin']==(48 if r['round']>=64 else margin*(1+r['round']//4))for r in trace)
        ordinary_window_cases.append(proof)
    assert sum(r['ordinary_box_pruned_neighbors']for proof in ordinary_window_cases for r in proof['ordinary_window_trace'])>0
    for label,flags in [
        ('zero',('--ordinary-search-margin=0',)),
        ('two',('--ordinary-search-margin=2',)),
        ('outside',('--ordinary-search-margin=257',)),
        ('missing-cost',('--critical-first','--ordinary-search-margin=64')),
        ('duplicate',('--critical-first','--ordinary-congestion-scale=64','--ordinary-search-margin=64','--ordinary-search-margin=64'))]:
        target=out/('invalid-ordinary-window-'+label)
        result=subprocess.run([str(executable),str(good),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert result.returncode!=0 and not target.exists()
        negatives.append(dict(kind='ordinary-window-envelope-or-context',case=label,rejected=True))
    from ordinary_pattern_regression import run as pattern_run
    pattern=pattern_run(out/'ordinary-zero-pattern',out/'previous-router')
    from directional_bidir_regression import run as directional_bidir_run
    directional_bidir=directional_bidir_run(out/'directional-bidirectional',out/'previous-router')
    from weighted_bidir_regression import run as weighted_bidir_run
    weighted_bidir=weighted_bidir_run(out/'weighted-bidirectional',out/'previous-router')
    return dict(passed=True, weighted_bidirectional_cases=weighted_bidir, cases=rows, resource_cases=resource_cases, dynamic_pool_cases=pool_cases,resource_memory_cases=memory_cases,critical_partition_cases=critical_cases,high_weight_cases=high_weight_cases,ordinary_scale_cases=ordinary_scale_cases,ordinary_window_cases=ordinary_window_cases,ordinary_zero_pattern_cases=pattern,directional_bidirectional_cases=directional_bidir,dynamic_pool_subprocess_tests_sha256=hashlib.sha256(pool_test.stdout).hexdigest(),rejected=negatives,
                baseline_source=str(baseline_source), baseline_sha256=hashlib.sha256(Path(baseline_source).read_bytes()).hexdigest(),
                whole_system_qualified=False, scope='Search ordering/cost comparisons only; independent original edge/flood/occupancy/wire-limit checks retained; all final geometry/PG/RC/300MHz gates still required')
