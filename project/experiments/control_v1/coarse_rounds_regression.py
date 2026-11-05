"""Earlier ordinary dense transition; independent final checks stay mandatory."""
from pathlib import Path
import json,subprocess
from coarse_access_regression import sha
from coarse_neighbors_regression import run as previous_run
from global_snapshot_analysis import inputs
from router_conflict_snapshot import inspect
from tree_router_cpp import route


def run(config,out):
    config=Path(config);cfg=json.loads(config.read_text());out=Path(out);out.mkdir()
    previous=Path(cfg['previous_neighbors']);prior=json.loads((previous/'receipt.json').read_text())
    assert prior['passed']and prior['stage']=='ordinary-coarse-neighbors-focused-regression-only'
    reused=previous_run(cfg['neighbors_config'],out/'unchanged-neighbors');assert reused['passed']
    for seed in (971,972):
        for suffix in ('','.native-prefix.log','.native-prefix-paths.txt','.global-round-8.txt'):
            assert Path(str(previous/'coarse-neighbors'/('full-'+str(seed))/'router-output.txt')+suffix).read_bytes()==Path(str(out/'unchanged-neighbors'/('full-'+str(seed))/'router-output.txt')+suffix).read_bytes()
        assert(previous/'coarse-neighbors'/('full-'+str(seed))/'router.log').read_bytes()==(out/'unchanged-neighbors'/('full-'+str(seed))/'router.log').read_bytes()
    manifest=out/'unchanged-neighbors/unchanged-batch/unchanged-zero/unchanged-multicast/multicast-seed.json'
    fixture=Path(json.loads(manifest.read_text())['input']);header,tm,lm=inputs(fixture);assert header[:3]==[40,40,24]
    kwargs=dict(heuristic_weight=256,locked_names=list(tm)[:8],wire_limits={n:v for n,v in lm.items()if v>=0},negotiated_priority=True,defer_access_vias=True,congestion_scale=1,bidirectional_two_terminal=True,weighted_bidirectional=True,ordinary_zero_pattern=True,pareto_wire_budget=True,critical_first=True,native_prefix_first=True,native_prefix_flexible=True,native_prefix_input=manifest,ordinary_coarse_grid_stride=16,ordinary_coarse_access=True,ordinary_coarse_static=True,ordinary_coarse_multicast=True,ordinary_coarse_zero=True)
    positives=[];attempts=[]
    for cutoff in (8,16):
        found=False
        for seed in range(971,979):
            target=out/('cutoff-'+str(cutoff)+'-seed-'+str(seed));target.mkdir()
            try:_,proof=route(tm,40,40,seed,80,target,ordinary_coarse_rounds=cutoff,**kwargs)
            except subprocess.CalledProcessError as error:
                assert not(target/'router-output.txt').exists();attempts.append(dict(cutoff=cutoff,seed=seed,returned=error.returncode,output=str(target),full_route=False));continue
            final=inspect(target/'router-output.txt',tm,40,40,lm)
            assert final['conflict_nodes']==0 and final['all_trees_flood_verified']and final['all_wire_budgets_verified']
            trace=proof['coarse_round_limit_trace'];assert trace and all(r['coarse_phase_active']==(r['round']<cutoff)for r in trace)
            assert all(r['coarse_attempts']==0 for r in trace if r['round']>=cutoff)
            attempts.append(dict(cutoff=cutoff,seed=seed,output=str(target),full_route=True,actual_transition=any(r['round']>=cutoff for r in trace)))
            if not attempts[-1]['actual_transition']:continue
            positives.append(dict(cutoff=cutoff,seed=seed,proof=proof,independent_final=final));found=True;break
        assert found,('No completed full-route transition for cutoff',cutoff)
    router=out/('cutoff-8-seed-'+str(positives[0]['seed']))/'router';inp=router.parent/'router-input.txt';rejected=[]
    for name,flags in [('context',['--ordinary-coarse-rounds=8']),('duplicate',['--ordinary-coarse-rounds=8']*2),('invalid',['--ordinary-coarse-rounds=7']),('suffix',['--ordinary-coarse-rounds=8x'])]:
        target=out/('invalid-'+name);p=subprocess.run([str(router),str(inp),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert p.returncode and not target.exists();rejected.append(dict(case=name,stderr=p.stderr.decode()))
    failed=out/'one-round-failure';failed.mkdir()
    try:route(tm,40,40,971,1,failed,ordinary_coarse_rounds=8,**kwargs)
    except subprocess.CalledProcessError:assert not(failed/'router-output.txt').exists()
    else:raise AssertionError('A partial conflicted first round incorrectly grants full success')
    result=dict(passed=True,whole_system_qualified=False,stage='ordinary-coarse-rounds-focused-regression-only',inputs={**reused['inputs'],str(config):sha(config),str(Path(__file__)):sha(__file__),str(manifest):sha(manifest),str(fixture):sha(fixture)},full_route_positives=positives,attempts=attempts,rejected=rejected,one_round_global_failure_rejected=True,scope='Original default64 full neighbors routes/main/native/path/snapshot byteexact; all nested prior real regressions. Cutoffs8/16 actually enter original dense phase and complete independently checked zero-conflict unit-edge/via/flood/finite-budget trees. All unsuccessful or pre-transition attempts retained. Four illegal contexts/values rejected and actual conflicted one-round run yields no final output. Only ordinary candidate schedule changes; original heuristic annealing/native finite solver/physical grid/M1-M10/geometry/PG/3RC300MHz gates unchanged. No fullscene qualification inferred.')
    (out/'receipt.json').write_text(json.dumps(result,indent=2));return result
