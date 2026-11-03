"""Independent route edge/flood/occupancy checks on actual C++ searches."""
import concurrent.futures,json,subprocess
from pathlib import Path
from tree_router_cpp import route


def run(out,baseline_source=None):
    def case(pair):
        mode,weight,lock,negotiate,defer=pair;folder=out/('case-%d-w%d-lock%d-negotiate%d-defer%d'%(mode,weight,lock,negotiate,defer));folder.mkdir()
        if mode==0:
            terminals={'bus_'+str(i):[(8,8+2*i),(38,34-2*i)]for i in range(12)}
        elif mode==1:
            terminals={'VDD':[(8,8)]+[(12+4*i,12+4*j)for i in range(7)for j in range(7)if(i+j)%2==0],
                       'VSS':[(40,40)]+[(12+4*i,14+4*j)for i in range(7)for j in range(7)if(i+j)%2==1]}
        else:
            terminals={'bus_'+str(i):[(8+2*i,8),(38-2*i,38),(8+2*i,40)]for i in range(10)}
        locked=list(terminals)[:1]if lock else[]
        _,proof=route(terminals,48,48,162+mode,40,folder,heuristic_weight=weight,locked_names=locked,negotiated_priority=bool(negotiate),defer_access_vias=bool(defer))
        assert proof['final_conflicts']==0 and proof['independent_tree_flood']and proof['independent_cross_net_occupancy']
        return dict(case=mode,weight=weight,lock=lock,negotiate=negotiate,defer=defer,proof=proof)
    with concurrent.futures.ThreadPoolExecutor(max_workers=15)as pool:
        records=list(pool.map(case,[(mode,weight,lock,negotiate,defer)for mode in range(3)for weight in (1,4,8,16,32)for lock in (0,1)for negotiate in (0,1)for defer in (0,1)]))
    bad=out/'negative-overlapping-native-landings';bad.mkdir()
    try:route({'a':[(8,8),(32,32)],'b':[(8,8),(34,34)]},48,48,162,2,bad,heuristic_weight=16)
    except subprocess.CalledProcessError:rejected=True
    else:raise AssertionError('Router accepted cross-net fixed landing overlap')
    budget=out/'negative-impossible-locked-wire-budget';budget.mkdir()
    try:route({'a':[(8,8),(32,32)]},48,48,162,2,budget,heuristic_weight=16,locked_names=['a'],wire_limits={'a':1})
    except subprocess.CalledProcessError:budget_rejected=True
    else:raise AssertionError('Router accepted impossible locked wire budget')
    good=out/'positive-finite-locked-wire-budget';good.mkdir()
    _,finite=route({'a':[(8,8),(32,32)]},48,48,162,10,good,heuristic_weight=16,locked_names=['a'],wire_limits={'a':60})
    assert finite['final_conflicts']==0 and finite['optimistic_locked_wire_limits_grid_edges']=={'a':60}
    negotiated=out/'positive-negotiated-finite-wire-budget';negotiated.mkdir()
    _,finite_negotiated=route({'a':[(8,8),(32,32)]},48,48,162,10,negotiated,heuristic_weight=16,
        locked_names=['a'],wire_limits={'a':60},negotiated_priority=True)
    assert finite_negotiated['final_conflicts']==0 and finite_negotiated['prioritized_source_nets']==['a']
    assert not finite_negotiated['locked_source_nets'] and finite_negotiated['optimistic_locked_wire_limits_grid_edges']=={'a':60}
    # All actual M11 terminals are identical in these two attempts. Eagerly
    # reserving M12 at every surrounding terminal traps the centre landing;
    # choosing vias during routing must recover a physically checked route.
    dense={'centre':[(24,24),(8,8)],'ring':[(x,y)for x in range(22,27)for y in range(22,27)
        if (x+y)%2==0 and (x,y)!=(24,24)]+[(40,40)]}
    eager=out/'dense-eager-access-rejection';eager.mkdir()
    try:route(dense,48,48,162,40,eager,locked_names=['centre'])
    except subprocess.CalledProcessError:dense_eager_rejected=True
    else:raise AssertionError('Eager dense fixture unexpectedly escaped reserved via enclosure')
    deferred=out/'dense-deferred-access-positive';deferred.mkdir()
    _,dense_proof=route(dense,48,48,162,40,deferred,locked_names=['centre'],defer_access_vias=True)
    assert dense_proof['final_conflicts']==0 and dense_proof['independent_tree_flood']
    tight=out/'positive-tight-deferred-wire-resource';tight.mkdir()
    _,tight_proof=route({'a':[(8,8),(32,32)]},48,48,162,10,tight,heuristic_weight=1,
        locked_names=['a'],wire_limits={'a':48},negotiated_priority=True,defer_access_vias=True)
    assert tight_proof['final_conflicts']==0 and tight_proof['optimistic_locked_wire_limits_grid_edges']=={'a':48}
    def separate(pair):
        mode,weight=pair;folder=out/('independent-congestion-mode%d-weight%d'%(mode,weight));folder.mkdir()
        terminals=({'bus_'+str(i):[(8,8+2*i),(38,34-2*i)]for i in range(12)}if mode==0 else dense)
        priority=list(terminals)[:1]
        _,proof=route(terminals,48,48,162+mode,40,folder,heuristic_weight=weight,
            locked_names=priority,negotiated_priority=True,defer_access_vias=True,congestion_scale=1)
        assert proof['final_conflicts']==0 and proof['independent_tree_flood']and proof['independent_cross_net_occupancy']
        assert proof['congestion_scale']==1 and proof['congestion_scale_override']==1
        return proof
    with concurrent.futures.ThreadPoolExecutor(max_workers=8)as pool:
        separate_costs=list(pool.map(separate,[(mode,weight)for mode in (0,1)for weight in (1,4,8,16)]))
    negative=out/'negative-separate-cost-impossible-wire-budget';negative.mkdir()
    try:route({'a':[(8,8),(32,32)]},48,48,162,2,negative,heuristic_weight=4,locked_names=['a'],wire_limits={'a':1},negotiated_priority=True,defer_access_vias=True,congestion_scale=1)
    except subprocess.CalledProcessError:separate_budget_rejected=True
    else:raise AssertionError('Search override bypassed physical wire budget')
    def product(pair):
        mode,weight=pair;folder=out/('product-history-mode%d-weight%d'%(mode,weight));folder.mkdir()
        terminals=({'bus_'+str(i):[(8,8+2*i),(38,34-2*i)]for i in range(12)}if mode==0 else dense)
        _,proof=route(terminals,48,48,162+mode,40,folder,heuristic_weight=weight,
            locked_names=list(terminals)[:1],negotiated_priority=True,defer_access_vias=True,
            congestion_scale=1,history_product=True)
        assert proof['final_conflicts']==0 and proof['independent_tree_flood']and proof['independent_cross_net_occupancy']
        assert proof['multiplicative_congestion_history']
        return proof
    with concurrent.futures.ThreadPoolExecutor(max_workers=8)as pool:
        product_cases=list(pool.map(product,[(mode,weight)for mode in (0,1)for weight in (1,4,8,16)]))
    negative_product=out/'negative-product-history-impossible-budget';negative_product.mkdir()
    try:route({'a':[(8,8),(32,32)]},48,48,162,2,negative_product,heuristic_weight=4,
        locked_names=['a'],wire_limits={'a':1},negotiated_priority=True,defer_access_vias=True,congestion_scale=1,history_product=True)
    except subprocess.CalledProcessError:product_budget_rejected=True
    else:raise AssertionError('History product bypassed physical wire budget')
    def ordered(pair):
        mode,order=pair;folder=out/('initial-order-mode%d-order%d'%(mode,order));folder.mkdir()
        terminals=({'bus_'+str(i):[(8,8+2*i),(38,34-2*i)]for i in range(12)}if mode==0 else
                   {'VDD':[(8,8)]+[(12+4*i,12+4*j)for i in range(7)for j in range(7)if(i+j)%2==0],
                    'VSS':[(40,40)]+[(12+4*i,14+4*j)for i in range(7)for j in range(7)if(i+j)%2==1]}if mode==1 else
                   {'bus_'+str(i):[(8+2*i,8),(38-2*i,38),(8+2*i,40)]for i in range(10)})
        _,proof=route(terminals,48,48,162+mode,40,folder,locked_names=list(terminals)[:1],
                      negotiated_priority=True,defer_access_vias=True,initial_order=order)
        assert proof['final_conflicts']==0 and proof['independent_tree_flood']and proof['independent_cross_net_occupancy']
        return dict(mode=mode,order=order,proof=proof)
    with concurrent.futures.ThreadPoolExecutor(max_workers=9)as pool:
        initial_orders=list(pool.map(ordered,[(mode,order)for mode in range(3)for order in (1,2,3)]))
    # This is an actual replay of the previous immutable executable, rather
    # than an assertion that the disabled new sort ought to be equivalent.
    default_replay=[]
    if baseline_source:
        binary=out/'previous-router';subprocess.run(['g++','-std=c++17','-O2',str(baseline_source),'-o',str(binary)],check=True)
        for mode in range(3):
            folder=out/('case-%d-w1-lock0-negotiate0-defer0'%mode)
            previous=out/('previous-route-%d.txt'%mode)
            old=subprocess.run([str(binary),str(folder/'router-input.txt'),str(previous)],capture_output=True,check=True)
            assert old.stdout==(folder/'router.log').read_bytes()and not old.stderr
            assert previous.read_bytes()==(folder/'router-output.txt').read_bytes()
            default_replay.append(dict(mode=mode,route_bytes_identical=True,log_bytes_identical=True))
    negative_orders=[]
    for order in (1,2,3):
        folder=out/('negative-order%d-wire-budget'%order);folder.mkdir()
        try:route({'a':[(8,8),(32,32)]},48,48,162,2,folder,locked_names=['a'],wire_limits={'a':1},negotiated_priority=True,defer_access_vias=True,initial_order=order)
        except subprocess.CalledProcessError:negative_orders.append(order)
        else:raise AssertionError('Initial ordering bypassed physical wire budget')
    result=dict(passed=True,cases=records,initial_order_cases=initial_orders,default_previous_source_byte_replay=default_replay,
        initial_order_impossible_wire_budget_rejected=negative_orders,negative_fixed_landing_overlap_rejected=rejected,
        negative_impossible_wire_budget_rejected=budget_rejected,
        positive_finite_wire_budget=finite,
        positive_negotiated_finite_wire_budget=finite_negotiated,
        dense_eager_access_rejected=dense_eager_rejected,dense_deferred_access=dense_proof,
        tight_deferred_wire_resource=tight_proof,independent_congestion_cases=separate_costs,
        independent_congestion_impossible_budget_rejected=separate_budget_rejected,
        product_history_cases=product_cases,product_history_impossible_budget_rejected=product_budget_rejected,
        scope='Small actual C++ routing searches with independent Python grid-edge, checkerboard-via, sink-flood and global short checks. Search ordering regression only; no declared full-system qualification.')
    (out/'router-search-regression.json').write_text(json.dumps(result,indent=2)+'\n');return result
