"""Optional weighted candidate search: independent legality and full-route tests."""
from pathlib import Path
import array,json,subprocess
from coarse_access_regression import sha
from coarse_rounds_regression import run as previous_run
from global_snapshot_analysis import inputs
from router_conflict_snapshot import inspect
from tree_router_cpp import route


def verify_probe(root):
    root=Path(root);receipt=root/'receipt.json';r=json.loads(receipt.read_text())
    assert r['passed'] and r['stage']=='weighted-reopen-probe-only'
    for p,digest in r['inputs'].items():assert sha(p)==digest
    cfg=json.loads(next(Path(p).read_text()for p in r['inputs']if Path(p).name.startswith('config')))
    h,tm,lm=inputs(cfg['input']);nx,ny=h[:2];plane=nx*ny
    selected={c['net']for c in r['cases']};own={};usage=array.array('I',[0])*(2*plane)
    fixed={y*nx+x:n for n,points in tm.items()for x,y in points}
    with Path(cfg['snapshot']).open()as f:
        assert int(f.readline())==len(tm)
        for n in tm:
            row=f.readline().split();assert row[0]==n;points=set()
            for _ in range(int(row[1])):
                raw=list(map(int,f.readline().split()));assert len(raw)==1+3*raw[0]
                points.update(raw[j+2]*plane+raw[j+1]*nx+raw[j]for j in range(1,len(raw),3))
            for v in points:usage[v]+=1
            if n in selected:own[n]=points
        assert not f.read().strip()
    checks=[];timeouts=[]
    for case in r['cases']:
        if case['timed_out']:
            assert not case['settle'] and case['returncode'] is None
            timeouts.append({k:case[k]for k in ('net','weight','settle')});continue
        assert case['returncode']==0
        pathfile=Path(case['command'][-1]);assert sha(pathfile)==case['output_sha256']
        d=json.loads(pathfile.read_text());path=d['path'];n=case['net']
        assert d['passed'] and d['expanded']==d['unique_expanded']+d['reopened']
        if case['settle']:assert d['reopened']==0
        assert len(path)==d['vertices'] and path[0]==tm[n][1][1]*nx+tm[n][1][0] and path[-1]==tm[n][0][1]*nx+tm[n][0][0]
        total=0
        for a,b in zip(path,path[1:]):
            x,y,l=a%nx,(a%plane)//nx,a//plane;xx,yy,ll=b%nx,(b%plane)//nx,b//plane
            assert 4<=xx<nx-4 and 4<=yy<ny-4 and ll in (0,1)
            assert abs(x-xx)+abs(y-yy)+abs(l-ll)==1 and (l==ll or (x+y)%2==0)
            assert b not in fixed or fixed[b]==n
            total+=(3 if l!=ll else (1 if (l==0 and x!=xx)or(l==1 and y!=yy)else 8))+64*(usage[b]-(b in own[n]))
        assert total==d['cost'];checks.append({k:d[k]for k in d if k!='path'})
    assert len(r['cases'])==64 and sum(c['settle']for c in checks)==32
    return dict(receipt=str(receipt),receipt_sha256=sha(receipt),checked_paths=checks,timeouts=timeouts,artificial_occupancy_cost_only=True)


def production_selftest(root,out):
    root=Path(root);out=Path(out);out.mkdir()
    for name in ('baseline-weighted.h','probe-weighted.h'):(out/name).write_bytes((root/name).read_bytes())
    header=Path(__file__).with_name('weighted_settled_bidirectional.h')
    (out/header.name).write_bytes(header.read_bytes())
    code=(root/'probe.cpp').read_text()
    old='Stats b;auto settled=probe_weighted_bidirectional(work,nx,ny,start,goal,penalty,allowed,np,weight,true,cf,cb,b);'
    new=old+'WeightedSettleState state;auto actual=settled_weighted_bidirectional(work,nx,ny,start,goal,penalty,allowed,np,weight,state);if(actual!=settled||state.expanded!=b.expanded||state.branches!=1)throw runtime_error("production candidate mismatch");auto exact=settled_weighted_bidirectional(work,nx,ny,start,goal,penalty,allowed,np,1,state);if(state.branches!=1)throw runtime_error("weight1 mutated settled state");auto expected=work.find(nx,ny,start,goal,penalty,allowed,np);if(exact!=expected)throw runtime_error("weight1 exact dispatch mismatch");state.last_epoch=work.epoch+100;actual=settled_weighted_bidirectional(work,nx,ny,start,goal,penalty,allowed,np,weight,state);if(actual!=settled)throw runtime_error("epoch reset mismatch");'
    assert code.count(old)==1;code=code.replace(old,new)
    assert code.count('#include "probe-weighted.h"')==1
    code=code.replace('#include "probe-weighted.h"','#include "probe-weighted.h"\n#include "weighted_settled_bidirectional.h"')
    cpp=out/'test.cpp';cpp.write_text(code);binary=out/'test'
    subprocess.run(['g++','-std=c++17','-O2',str(cpp),'-o',str(binary)],check=True)
    p=subprocess.run([str(binary),'--self-test'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (out/'stdout').write_bytes(p.stdout);(out/'stderr').write_bytes(p.stderr);assert p.returncode==0
    result=json.loads(p.stdout);assert result['passed']and result['independent_path_checks']==192
    return dict(**result,production_paths_byteexact_to_candidate=96,weight1_exact_replays=96,epoch_reset_replays=96,header_sha256=sha(header))


def run(config,out):
    config=Path(config);cfg=json.loads(config.read_text());out=Path(out);out.mkdir()
    probes=[verify_probe(p)for p in cfg['probe_roots']];assert len(probes)==2
    selftest=production_selftest(cfg['probe_roots'][0],out/'production-selftest')
    reused=previous_run(cfg['rounds_config'],out/'unchanged-rounds');assert reused['passed']
    previous=Path(cfg['previous_rounds'])
    old=json.loads((previous/'receipt.json').read_text());assert old['passed']
    for case in old['full_route_positives']:
        name='cutoff-'+str(case['cutoff'])+'-seed-'+str(case['seed'])
        for suffix in ('','.native-prefix.log','.native-prefix-paths.txt'):
            assert Path(str(previous/name/'router-output.txt')+suffix).read_bytes()==Path(str(out/'unchanged-rounds'/name/'router-output.txt')+suffix).read_bytes()
        assert(previous/name/'router.log').read_bytes()==(out/'unchanged-rounds'/name/'router.log').read_bytes()
    manifest=out/'unchanged-rounds/unchanged-neighbors/unchanged-batch/unchanged-zero/unchanged-multicast/multicast-seed.json'
    fixture=Path(json.loads(manifest.read_text())['input']);h,tm,lm=inputs(fixture)
    kwargs=dict(heuristic_weight=256,locked_names=list(tm)[:8],wire_limits={n:v for n,v in lm.items()if v>=0},negotiated_priority=True,defer_access_vias=True,congestion_scale=1,bidirectional_two_terminal=True,weighted_bidirectional=True,ordinary_zero_pattern=True,pareto_wire_budget=True,critical_first=True,native_prefix_first=True,native_prefix_flexible=True,native_prefix_input=manifest,ordinary_coarse_grid_stride=16,ordinary_coarse_access=True,ordinary_coarse_static=True,ordinary_coarse_multicast=True,ordinary_coarse_zero=True,weighted_settle_once=True)
    positives=[];attempts=[]
    for cutoff in (8,16):
        for seed in range(971,983):
            target=out/('settled-'+str(cutoff)+'-'+str(seed));target.mkdir()
            try:_,proof=route(tm,40,40,seed,80,target,ordinary_coarse_rounds=cutoff,**kwargs)
            except subprocess.CalledProcessError as error:
                assert not(target/'router-output.txt').exists();attempts.append(dict(cutoff=cutoff,seed=seed,full_route=False,returncode=error.returncode));continue
            final=inspect(target/'router-output.txt',tm,40,40,lm)
            assert final['conflict_nodes']==0 and final['all_trees_flood_verified']and final['all_wire_budgets_verified']
            trace=proof['weighted_settle_trace'];assert trace
            used=trace[-1]['weighted_settle_branches']>0
            crossed=any(r['round']>=cutoff for r in trace)
            attempts.append(dict(cutoff=cutoff,seed=seed,full_route=True,used_settled=used,crossed=crossed))
            if not(used and crossed):continue
            positives.append(dict(cutoff=cutoff,seed=seed,proof=proof,independent_final=final));break
        else:raise AssertionError(('No actual full-route transition with settled branches',cutoff))
    folder=out/('settled-8-'+str(positives[0]['seed']));router=folder/'router';inp=folder/'router-input.txt';rejected=[]
    for name,flags in [('context',['--weighted-settle-once']),('duplicate',['--weighted-settle-once']*2)]:
        target=out/('invalid-'+name);p=subprocess.run([str(router),str(inp),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert p.returncode and not target.exists();rejected.append(dict(case=name,stderr=p.stderr.decode()))
    failed=out/'one-round-failure';failed.mkdir()
    try:route(tm,40,40,971,1,failed,ordinary_coarse_rounds=8,**kwargs)
    except subprocess.CalledProcessError:assert not(failed/'router-output.txt').exists()
    else:raise AssertionError('Partial first round incorrectly grants success')
    result=dict(passed=True,whole_system_qualified=False,stage='weighted-settle-focused-regression-only',probes=probes,selftest=selftest,full_route_positives=positives,attempts=attempts,rejected=rejected,one_round_global_failure_rejected=True,inputs={str(config):sha(config),str(Path(__file__)):sha(__file__)},scope='Optional ordinary weighted settle-once candidate only. Two actual frames independently replayed under artificial64occupancy cost, not actual history or full-scene speedup. Production candidate matches96 independently checked scratch paths, exact weight1 and epoch-reset replays. Original default complete small routes/native logs/paths byteexact and nested prior regressions executed. New cutoff8/16 full small routes require actual settled branches and independent zero-conflict/edge/via/flood/budget checks. All production full-scene geometry/PG/three-RC300MHz gates remain required.')
    (out/'receipt.json').write_text(json.dumps(result,indent=2));return result
