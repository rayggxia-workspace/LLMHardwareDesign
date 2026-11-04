"""Check fixed candidate lattices and diagnostic snapshots without granting acceptance."""
from pathlib import Path
import json,subprocess
from coarse_access_regression import run as access_run,sha
from pin_release_regression import parse
from router_conflict_snapshot import inspect,inputs
from tree_router_cpp import route


def run(config,out):
    config=Path(config);cfg=json.loads(config.read_text());out=Path(out);out.mkdir()
    previous=Path(cfg['previous_access']);prior=json.loads((previous/'receipt.json').read_text())
    assert prior['passed']and prior['stage']=='ordinary-coarse-access-focused-regression-only'
    old=Path(next(k for k in prior['inputs']if k.endswith('/system_upper.py'))).parent
    assert sha(old/'coarse_access_regression.py')==sha(Path(__file__).with_name('coarse_access_regression.py'))
    reused=access_run(cfg['access_config'],out/'unchanged-access');assert reused['passed']
    for seed in (971,972):
        for suffix in ('','.native-prefix.log','.native-prefix-paths.txt'):
            assert Path(str(previous/'coarse-access'/('full-'+str(seed))/'router-output.txt')+suffix).read_bytes()==Path(str(out/'unchanged-access'/('full-'+str(seed))/'router-output.txt')+suffix).read_bytes()
        assert(previous/'coarse-access'/('full-'+str(seed))/'router.log').read_bytes()==(out/'unchanged-access'/('full-'+str(seed))/'router.log').read_bytes()
    assert(previous/'coarse-access/access-output.txt').read_bytes()==(out/'unchanged-access/access-output.txt').read_bytes()
    fixture=out/'unchanged-access/unchanged-coarse/unchanged-warm/unchanged-release/same-prefix-release-proxy/router-input.txt'
    _,tm,lm=parse(fixture.read_text());manifest=out/'unchanged-access/unchanged-coarse/unchanged-warm/seed.json'
    kwargs=dict(heuristic_weight=256,locked_names=list(tm)[:8],wire_limits=lm,negotiated_priority=True,defer_access_vias=True,congestion_scale=1,bidirectional_two_terminal=True,weighted_bidirectional=True,ordinary_zero_pattern=True,pareto_wire_budget=True,critical_first=True,native_prefix_first=True,native_prefix_flexible=True,native_prefix_input=manifest,ordinary_coarse_grid_stride=16,ordinary_coarse_access=True,ordinary_coarse_static=True,global_snapshot_round=8)
    positives=[]
    for seed in (972,980):
        target=out/('full-'+str(seed));target.mkdir();_,proof=route(tm,24,24,seed,80,target,**kwargs)
        assert proof['final_conflicts']==0 and proof['independent_tree_flood']and proof['independent_cross_net_occupancy']
        assert proof['coarse_static_trace']and all(r['grid_phase']==seed for r in proof['coarse_static_trace'])
        snapshot=target/'router-output.txt.global-round-8.txt';h,nets,limits=inputs(target/'router-input.txt')
        diagnostic=inspect(snapshot,nets,*h[:2],limits)
        trace=[json.loads(l)for l in(target/'router.log').read_text().splitlines()if l.startswith('{')]
        expected=next(r for r in trace if r.get('round')==7 and 'conflict_nodes'in r)
        for key in ('conflict_nodes','excess_occupancy','occupied_cells','summed_tree_vertices','grid_cell_capacity'):assert diagnostic[key]==expected[key]
        assert diagnostic['conflict_nodes']>0
        positives.append(dict(seed=seed,proof=proof,snapshot_sha256=sha(snapshot),diagnostic=diagnostic))
    rejected=[];router=out/'full-972/router';input_path=out/'full-972/router-input.txt'
    for name,flags in [('static-context',['--ordinary-coarse-static']),('static-duplicate',['--ordinary-coarse-static']*2),('snapshot-context',['--global-route-snapshot=8']),('snapshot-duplicate',['--global-route-snapshot=8']*2),('snapshot-invalid',['--global-route-snapshot=7'])]:
        target=out/('invalid-'+name);p=subprocess.run([str(router),str(input_path),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert p.returncode and not target.exists();rejected.append(dict(case=name,stderr=p.stderr.decode()))
    failed=out/'static-global-failure';failed.mkdir()
    try:route(tm,24,24,971,80,failed,**kwargs)
    except subprocess.CalledProcessError:assert not(failed/'router-output.txt').exists()and(failed/'router-output.txt.global-round-8.txt').exists()
    else:raise AssertionError('Diagnostic snapshot incorrectly grants full success')
    result=dict(passed=True,whole_system_qualified=False,route_qualified=False,stage='static-coarse-grid-focused-regression-only',inputs={str(config):sha(config),str(Path(__file__)):sha(__file__),**reused['inputs']},full_route_positives=positives,rejected=rejected,static_global_failure_rejected=True,scope='Two complete small routes with constant trial-specific lattice phase; independent round8 complete-tree/budget/occupancy replay. Diagnostic snapshots contain conflicts and cannot grant acceptance. Previous access104 oracle bytes and both complete route/main/native artifacts identical; nested earlier actual regressions retained. Large composition and first-trial-only process policy require separate evidence.')
    (out/'receipt.json').write_text(json.dumps(result,indent=2));return result
