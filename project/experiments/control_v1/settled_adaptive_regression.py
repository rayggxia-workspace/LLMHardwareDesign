"""Exercise the existing adaptive schedule with settled weighted candidates."""
from pathlib import Path
import concurrent.futures,json,os,subprocess,sys
from coarse_access_regression import sha
from global_snapshot_analysis import inputs
from router_conflict_snapshot import inspect
from tree_router_cpp import route


def run(config,out):
    config=Path(config);cfg=json.loads(config.read_text());out=Path(out);out.mkdir()
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))==16
    prior=Path(cfg['previous_settled']);old=json.loads((prior/'receipt.json').read_text());assert old['passed']
    baseline=Path(cfg['baseline_source']);here=Path(__file__).parent
    # This adds a supported combination, not a new path finder or physical gate.
    unchanged=['tree_router.cpp','tree_router_cpp.py','weighted_settled_bidirectional.h','weighted_bidirectional.h','resource_search.h','system_geometry.py','system_sta.py','system_accept.py','final_composition.py']
    for n in unchanged:assert sha(here/n)==sha(baseline/n)
    manifest=Path(cfg['fixture_manifest']);seed=json.loads(manifest.read_text());fixture=Path(seed['input']);assert sha(fixture)==seed['input_sha256']and sha(seed['prefix'])==seed['prefix_sha256']
    h,tm,lm=inputs(fixture);assert h[:2]==[40,40]
    kwargs=dict(heuristic_weight=256,locked_names=list(tm)[:8],wire_limits={n:v for n,v in lm.items()if v>=0},negotiated_priority=True,defer_access_vias=True,congestion_scale=1,bidirectional_two_terminal=True,weighted_bidirectional=True,ordinary_zero_pattern=True,pareto_wire_budget=True,critical_first=True,native_prefix_first=True,native_prefix_flexible=True,native_prefix_input=manifest,ordinary_coarse_grid_stride=16,ordinary_coarse_access=True,ordinary_coarse_static=True,ordinary_coarse_multicast=True,ordinary_coarse_zero=True,ordinary_coarse_rounds=16,weighted_settle_once=True)
    default=out/'unchanged-default';default.mkdir();_,proof=route(tm,40,40,972,80,default,**kwargs)
    for name in ['router-output.txt','router-output.txt.native-prefix.log','router-output.txt.native-prefix-paths.txt','router.log']:
        assert(default/name).read_bytes()==(prior/'settled-16-972'/name).read_bytes(),name

    def case(pair):
        cost,number=pair;target=out/('cost-'+str(cost)+'-seed-'+str(number));target.mkdir()
        try:_,p=route(tm,40,40,number,80,target,adaptive_heuristic=True,nonpreferred_cost=cost,**kwargs)
        except subprocess.CalledProcessError as error:
            assert not(target/'router-output.txt').exists()
            return dict(cost=cost,seed=number,full_route=False,returncode=error.returncode,log_sha256=sha(target/'router.log'))
        independent=inspect(target/'router-output.txt',tm,40,40,lm);assert independent['conflict_nodes']==0 and independent['all_trees_flood_verified']and independent['all_wire_budgets_verified']
        trace=[json.loads(l)for l in(target/'router.log').read_text().splitlines()if l.startswith('{')]
        schedule=[r for r in trace if'adaptive_search_weight'in r]
        for r in schedule:
            annealed=1+((255)>>min(r['round']//4,8));expected=256 if r['previous_conflicts']>max(1,len(tm)//8)and r['round']%8!=7 else annealed
            assert r['adaptive_search_weight']==expected
        override=any(r['round']>=16 and r['round']%8!=7 and r['adaptive_search_weight']==256 for r in schedule)
        exact_probes=any(r['round']>=16 and r['round']%8==7 and r['adaptive_search_weight']<256 for r in schedule)
        used=p['weighted_settle_trace'][-1]['weighted_settle_branches']>0
        return dict(cost=cost,seed=number,full_route=True,crossed_and_overrode=override,periodic_original_probe=exact_probes,used_settled=used,proof=p,independent_final=independent,adaptive_schedule=schedule)

    pairs=[(cost,number)for cost in (2,8)for number in range(971,979)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=16)as pool:cases=list(pool.map(case,pairs))
    (out/'attempts.json').write_text(json.dumps(cases,indent=2)+'\n')
    covered=[]
    for cost in (2,8):
        eligible=[r for r in cases if r['cost']==cost and r['full_route']and r['crossed_and_overrode']and r['periodic_original_probe']and r['used_settled']]
        assert eligible,('No complete actual adaptive/settled/transition/periodic-probe coverage',cost)
        covered.append(dict(cost=cost,seeds=[r['seed']for r in eligible]))
    rejected=[]
    for name,flags in [('plain-bidirectional',[]),('weighted-without-settle',['--route-weighted-bidirectional'])]:
        target=out/('rejected-'+name)
        cmd=[sys.executable,str(here/'system_upper.py'),'--manifest',str(out/'absent-manifest.json'),'--graph',str(out/'absent-graph.json'),'--out',str(target),'--route-adaptive-heuristic','--bidirectional-two-terminal','--defer-access-vias','--negotiate-priority-routes',*flags]
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE);(out/(name+'.stderr')).write_bytes(p.stderr)
        assert p.returncode and b'AssertionError'in p.stderr and not target.exists()
        rejected.append(dict(case=name,returncode=p.returncode,stderr_sha256=sha(out/(name+'.stderr'))))
    failed=out/'one-round-failure';failed.mkdir()
    try:route(tm,40,40,971,1,failed,adaptive_heuristic=True,**kwargs)
    except subprocess.CalledProcessError:assert not(failed/'router-output.txt').exists()
    else:raise AssertionError('Conflicted single round incorrectly accepted')
    result=dict(passed=True,whole_system_qualified=False,stage='settled-adaptive-combination-regression-only',unchanged_default_byteexact=True,covered=covered,cases=cases,rejected=rejected,one_round_failure_rejected=True,inputs={str(p):sha(p)for p in [config,Path(__file__),here/'system_upper.py',prior/'receipt.json',manifest,fixture,Path(seed['prefix']),*[here/n for n in unchanged]]},scope='Existing adaptive schedule and existing settled weighted candidate combination only. Original core/search/exact/native/physical gates byteexact to source1250; default full small route/native/log bytes replayed. Sixteen real complete small attempts retain failures; each cost must actually cross dense16, execute adaptive override and original periodic probe, use settled branches and independently reach zero/flood/via/budget. Does not grant whole composition physical qualification.')
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result
