"""Prefer presently free compressed candidates; retain full conflict acceptance."""
from pathlib import Path
import json,subprocess
from coarse_multicast_regression import run as multicast_run
from coarse_access_regression import sha
from router_conflict_snapshot import inputs,inspect
from tree_router_cpp import route


def run(config,out):
    config=Path(config);cfg=json.loads(config.read_text());out=Path(out);out.mkdir()
    previous=Path(cfg['previous_multicast']);prior=json.loads((previous/'receipt.json').read_text())
    assert prior['passed']and prior['stage']=='ordinary-coarse-multicast-focused-regression-only'
    old=Path(next(k for k in prior['inputs']if k.endswith('/system_upper.py'))).parent
    assert sha(old/'coarse_multicast_regression.py')==sha(Path(__file__).with_name('coarse_multicast_regression.py'))
    reused=multicast_run(cfg['multicast_config'],out/'unchanged-multicast');assert reused['passed']
    for seed in (971,972):
        for suffix in ('','.native-prefix.log','.native-prefix-paths.txt','.global-round-8.txt'):
            assert Path(str(previous/'coarse-multicast'/('full-'+str(seed))/'router-output.txt')+suffix).read_bytes()==Path(str(out/'unchanged-multicast'/('full-'+str(seed))/'router-output.txt')+suffix).read_bytes()
        assert(previous/'coarse-multicast'/('full-'+str(seed))/'router.log').read_bytes()==(out/'unchanged-multicast'/('full-'+str(seed))/'router.log').read_bytes()
    manifest=out/'unchanged-multicast/multicast-seed.json';fixture=Path(json.loads(manifest.read_text())['input']);header,tm,lm=inputs(fixture)
    assert header[:3]==[40,40,24]and header[6]==8 and [len(x)for x in list(tm.values())[8:10]]==[3,6]
    kwargs=dict(heuristic_weight=256,locked_names=list(tm)[:8],wire_limits={n:v for n,v in lm.items()if v>=0},negotiated_priority=True,defer_access_vias=True,congestion_scale=1,bidirectional_two_terminal=True,weighted_bidirectional=True,ordinary_zero_pattern=True,pareto_wire_budget=True,critical_first=True,native_prefix_first=True,native_prefix_flexible=True,native_prefix_input=manifest,ordinary_coarse_grid_stride=16,ordinary_coarse_access=True,ordinary_coarse_static=True,ordinary_coarse_multicast=True,ordinary_coarse_zero=True,global_snapshot_round=8)
    positives=[]
    for seed in (971,972):
        target=out/('full-'+str(seed));target.mkdir();_,proof=route(tm,40,40,seed,80,target,**kwargs)
        assert proof['final_conflicts']==0 and proof['independent_tree_flood']and proof['independent_cross_net_occupancy']
        assert proof['coarse_zero_trace']and sum(r['coarse_zero_hits']for r in proof['coarse_zero_trace'])>0
        assert all(0<=r['coarse_zero_hits']<=r['coarse_zero_attempts']for r in proof['coarse_zero_trace'])
        final=inspect(target/'router-output.txt',tm,40,40,lm)
        assert final['conflict_nodes']==0 and final['all_trees_flood_verified']and final['all_wire_budgets_verified']
        snapshot=target/'router-output.txt.global-round-8.txt';diagnostic=inspect(snapshot,tm,40,40,lm)
        expected=next(json.loads(l)for l in(target/'router.log').read_text().splitlines()if l.startswith('{')and '"conflict_nodes"'in l and json.loads(l)['round']==7)
        for key in ('conflict_nodes','excess_occupancy','occupied_cells','summed_tree_vertices','grid_cell_capacity'):assert diagnostic[key]==expected[key]
        positives.append(dict(seed=seed,proof=proof,independent_final=final,snapshot_sha256=sha(snapshot),snapshot_diagnostic=diagnostic))
    rejected=[];router=out/'full-971/router';inp=out/'full-971/router-input.txt'
    for name,flags in [('context',['--ordinary-coarse-zero']),('duplicate',['--ordinary-coarse-zero']*2)]:
        target=out/('invalid-'+name);p=subprocess.run([str(router),str(inp),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert p.returncode and not target.exists();rejected.append(dict(case=name,stderr=p.stderr.decode()))
    failed=out/'coarse-zero-global-failure';failed.mkdir()
    try:route(tm,40,40,993,80,failed,**kwargs)
    except subprocess.CalledProcessError:assert not(failed/'router-output.txt').exists()and(failed/'router-output.txt.global-round-8.txt').exists()
    else:raise AssertionError('Free candidate prepass incorrectly grants full success')
    result=dict(passed=True,whole_system_qualified=False,route_qualified=False,stage='ordinary-coarse-zero-focused-regression-only',inputs={**reused['inputs'],str(config):sha(config),str(Path(__file__)):sha(__file__),str(manifest):sha(manifest),str(fixture):sha(fixture)},full_route_positives=positives,rejected=rejected,coarse_zero_global_failure_rejected=True,scope='Two full synthetic24net routes with3/6terminal ordinary nets and8finite native nets; actual strictly free coarse hits each audited against current occupancy in C++. Independent final tree/budget/occupancy and round8 replay. Earlier two multicast paths/main/native/snapshot byteexact and nested actual104oracle/earlier replays retained. Free at selection time does not imply final zero conflicts; actual globalfailure remains rejected. Production floorplan/native solver/finalphysicalgates unchanged.')
    (out/'receipt.json').write_text(json.dumps(result,indent=2));return result
