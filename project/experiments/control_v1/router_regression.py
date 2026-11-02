"""Independent route edge/flood/occupancy checks on actual C++ searches."""
import concurrent.futures,json,subprocess
from pathlib import Path
from tree_router_cpp import route


def run(out):
    def case(pair):
        mode,weight,lock,negotiate=pair;folder=out/('case-%d-w%d-lock%d-negotiate%d'%(mode,weight,lock,negotiate));folder.mkdir()
        if mode==0:
            terminals={'bus_'+str(i):[(8,8+2*i),(38,34-2*i)]for i in range(12)}
        elif mode==1:
            terminals={'VDD':[(8,8)]+[(12+4*i,12+4*j)for i in range(7)for j in range(7)if(i+j)%2==0],
                       'VSS':[(40,40)]+[(12+4*i,14+4*j)for i in range(7)for j in range(7)if(i+j)%2==1]}
        else:
            terminals={'bus_'+str(i):[(8+2*i,8),(38-2*i,38),(8+2*i,40)]for i in range(10)}
        locked=list(terminals)[:1]if lock else[]
        _,proof=route(terminals,48,48,162+mode,40,folder,heuristic_weight=weight,locked_names=locked,negotiated_priority=bool(negotiate))
        assert proof['final_conflicts']==0 and proof['independent_tree_flood']and proof['independent_cross_net_occupancy']
        return dict(case=mode,weight=weight,lock=lock,negotiate=negotiate,proof=proof)
    with concurrent.futures.ThreadPoolExecutor(max_workers=15)as pool:
        records=list(pool.map(case,[(mode,weight,lock,negotiate)for mode in range(3)for weight in (1,4,8,16,32)for lock in (0,1)for negotiate in (0,1)]))
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
    result=dict(passed=True,cases=records,negative_fixed_landing_overlap_rejected=rejected,
        negative_impossible_wire_budget_rejected=budget_rejected,
        positive_finite_wire_budget=finite,
        positive_negotiated_finite_wire_budget=finite_negotiated,
        scope='Small actual C++ routing searches with independent Python grid-edge, checkerboard-via, sink-flood and global short checks. Search ordering regression only; no declared full-system qualification.')
    (out/'router-search-regression.json').write_text(json.dumps(result,indent=2)+'\n');return result
