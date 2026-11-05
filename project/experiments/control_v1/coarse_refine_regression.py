"""Coarse-to-fine search-guide regression, not full physical qualification.

Reference principle only: https://github.com/cuhk-eda/cu-gr (connected rectangle
guides to a detailed router). No CUGR implementation or qualification reused.
"""
from pathlib import Path
import concurrent.futures,json,os,subprocess,random
from coarse_access_regression import sha
from global_snapshot_analysis import inputs
from router_conflict_snapshot import inspect
from tree_router_cpp import route


def run(config,out):
    config=Path(config);cfg=json.loads(config.read_text());out=Path(out);out.mkdir()
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))==16
    here=Path(__file__).parent;baseline=Path(cfg['baseline_source']);prior=Path(cfg['previous_resource'])
    guided_adaptive=cfg.get('guided_adaptive',True);assert isinstance(guided_adaptive,bool)
    guided_history_product=cfg.get('guided_history_product',False);assert isinstance(guided_history_product,bool)
    guided_global_batch=cfg.get('guided_global_batch',False);assert isinstance(guided_global_batch,bool)
    guided_costs=cfg.get('guided_costs',[2,8]);assert guided_costs in ([2,8],[2,8,32])
    guided_present_growth=cfg.get('guided_present_growth',0);assert guided_present_growth in (0,4,8)
    guided_refresh=cfg.get('guided_refresh',0);assert guided_refresh in (0,8,16)
    guided_pin_access=cfg.get('guided_pin_access','none');assert guided_pin_access in ('none','after-native','after-native-m12')
    assert not guided_refresh or(not guided_present_growth and not guided_global_batch)
    assert not guided_present_growth or(not guided_history_product and not guided_global_batch)
    assert json.loads((prior/'receipt.json').read_text())['passed']
    unchanged=['resource_search.h','weighted_settled_bidirectional.h','weighted_bidirectional.h','ordinary_coarse_grid.h','system_geometry.py','system_sta.py','system_accept.py','final_composition.py','native_pin_load.py','native_cap_residual.py','upper_cap_bound.py','steiner_wire_bound.py','placement_residual_budget.py']
    for n in unchanged:assert sha(here/n)==sha(baseline/n),n
    harness=r'''
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <limits>
#include <random>
#include <stdexcept>
#include <vector>
#include "routing_corridor.h"
int main(){
 std::mt19937 rng(1621368);RoutingCorridor guide;uint64_t checks=0;
 for(int t=0;t<120;++t){
  int nx=16+rng()%33,ny=16+rng()%33,plane=nx*ny,radius=t%9;
  int x=4+rng()%(nx-8),y=4+rng()%(ny-8),l=t%2;std::vector<int>path{l*plane+y*nx+x};
  for(int i=0;i<60;++i){int d=rng()%5;
   if(d==0&&x>4)--x;else if(d==1&&x<nx-5)++x;
   else if(d==2&&y>4)--y;else if(d==3&&y<ny-5)++y;else if(d==4&&(x+y)%2==0)l=1-l;
   path.push_back(l*plane+y*nx+x);
  }
  if(t%7==0)guide.epoch=std::numeric_limits<uint32_t>::max();
  guide.build(nx,ny,path,radius);uint64_t expected_count=0;
  for(int v=0;v<2*plane;++v){int xx=v%nx,yy=(v%plane)/nx;bool expected=false;
   if(xx>=4&&xx<nx-4&&yy>=4&&yy<ny-4)
    for(int p:path)if(std::max(abs(xx-p%nx),abs(yy-(p%plane)/nx))<=radius){expected=true;break;}
   if(guide.contains(v)!=expected)return 2;
   if(v<plane)expected_count+=expected;++checks;
  }
  if(guide.vertices!=expected_count||guide.contains(-1)||guide.contains(2*plane))return 3;
 }
 guide.build(16,16,std::vector<int>{4*16+4},0);
 guide.epoch=std::numeric_limits<uint32_t>::max();
 guide.build(16,16,std::vector<int>{5*16+5},0);
 if(guide.contains(4*16+4)||!guide.contains(5*16+5))return 5;
 checks+=2;int rejects=0;
 for(int t=0;t<3;++t)try{
  guide.build(t==0?8:16,16,t==1?std::vector<int>{}:std::vector<int>{999999},4);
 }catch(const std::runtime_error&){++rejects;}
 if(rejects!=3)return 4;
 std::cout<<"{\"passed\":true,\"independent_membership_checks\":"<<checks<<",\"invalid_rejections\":"<<rejects<<",\"epoch_wrap_and_size_reuse\":true}"<<std::endl;
}
'''
    (out/'corridor-test.cpp').write_text(harness)
    subprocess.run(['g++','-std=c++17','-O2','-I',str(here),str(out/'corridor-test.cpp'),'-o',str(out/'corridor-test')],check=True)
    with(out/'corridor-test.json').open('w')as f:subprocess.run([str(out/'corridor-test')],stdout=f,check=True)
    component=json.loads((out/'corridor-test.json').read_text());assert component['passed']and component['independent_membership_checks']>100000
    manifest=Path(cfg['fixture_manifest']);seed=json.loads(manifest.read_text());fixture=Path(seed['input'])
    assert sha(fixture)==seed['input_sha256']and sha(seed['prefix'])==seed['prefix_sha256']
    h,tm,lm=inputs(fixture);assert h[:2]==[40,40]
    kwargs=dict(heuristic_weight=256,locked_names=list(tm)[:8],wire_limits={n:v for n,v in lm.items()if v>=0},negotiated_priority=True,defer_access_vias=True,congestion_scale=1,bidirectional_two_terminal=True,weighted_bidirectional=True,ordinary_zero_pattern=True,pareto_wire_budget=True,critical_first=True,native_prefix_first=True,native_prefix_flexible=True,native_prefix_input=manifest,ordinary_coarse_grid_stride=16,ordinary_coarse_access=True,ordinary_coarse_static=True,ordinary_coarse_multicast=True,ordinary_coarse_zero=True,ordinary_coarse_rounds=16,weighted_settle_once=True)
    def replay(pair):
        cost,number,adaptive,rounds,name=pair;target=out/name;target.mkdir();failed=False
        try:route(tm,40,40,number,rounds,target,adaptive_heuristic=adaptive,nonpreferred_cost=cost,**kwargs)
        except subprocess.CalledProcessError:failed=True
        expected=prior/name;files={}
        for n in ['router-output.txt','router-output.txt.native-prefix.log','router-output.txt.native-prefix-paths.txt','router.log']:
            a=target/n;b=expected/n;assert a.exists()==b.exists(),(name,n)
            if a.exists():assert a.read_bytes()==b.read_bytes(),(name,n);files[n]=sha(a)
        assert failed==(not(expected/'router-output.txt').exists())
        return dict(name=name,failed=failed,byteexact=files)
    pairs=[(c,n,True,80,'cost-'+str(c)+'-seed-'+str(n))for c in(2,8)for n in range(971,979)]
    pairs +=[(2,972,False,80,'unchanged-default'),(2,971,True,1,'one-round-failure')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=16)as pool:defaults=list(pool.map(replay,pairs))
    guided_defaults=[]
    if guided_present_growth:
        previous_guided=Path(cfg['previous_guided']);assert json.loads((previous_guided/'receipt.json').read_text())['passed']
        def guided_replay(pair):
            cost,number=pair;name='guided-cost-'+str(cost)+'-seed-'+str(number);target=out/('disabled-'+name);target.mkdir();failed=False
            try:route(tm,40,40,number,80,target,adaptive_heuristic=guided_adaptive,history_product=False,global_batch_ripup=False,nonpreferred_cost=cost,coarse_refine=True,**kwargs)
            except subprocess.CalledProcessError:failed=True
            expected=previous_guided/name;files={}
            for n in ['router-output.txt','router-output.txt.native-prefix.log','router-output.txt.native-prefix-paths.txt','router.log']:
                a=target/n;b=expected/n;assert a.exists()==b.exists(),(name,n)
                if a.exists():assert a.read_bytes()==b.read_bytes(),(name,n);files[n]=sha(a)
            assert failed==(not(expected/'router-output.txt').exists())
            return dict(name=name,failed=failed,byteexact=files)
        with concurrent.futures.ThreadPoolExecutor(max_workers=16)as pool:guided_defaults=list(pool.map(guided_replay,[(c,n)for c in guided_costs for n in range(971,979)]))
    dense_manifest=None
    if guided_present_growth or guided_refresh:
        # Deliberately over-capacity negative fixture keeps late refinement
        # active. Original24-net fixture/budgets/cutoff gates remain unchanged.
        dense_tm=dict(tm);dense_lm=dict(lm);used={p for ps in tm.values()for p in ps}
        used|={(x+dx,y+dy)for x,y in list(used)for dx,dy in[(1,0),(-1,0),(0,1),(0,-1)]}
        with Path(seed['prefix']).open()as f:
            for _ in range(int(f.readline())):
                for _ in range(int(f.readline().split()[1])):
                    raw=list(map(int,f.readline().split()))
                    for j in range(1,len(raw),3):
                        x,y,l=raw[j:j+3]
                        if l==0:used.add((x,y))
        left=sorted((x,y)for x in range(4,19)for y in range(4,36)if(x+y)%2==0 and(x,y)not in used)
        right=sorted(((x,y)for x in range(21,36)for y in range(4,36)if(x+y)%2==0 and(x,y)not in used),reverse=True)
        assert min(len(left),len(right))>=96;left=left[:96];right=right[:96];random.Random(1621514).shuffle(right)
        negative_vertex_lower_bound=sum(abs(a[0]-b[0])+abs(a[1]-b[1])+1 for a,b in zip(left,right))
        assert negative_vertex_lower_bound>2048
        for i in range(96):dense_tm['late_cross_'+str(i)]=[left[i],right[i]];dense_lm['late_cross_'+str(i)]=-1
        dense_input=out/'dense-input.txt';dh=list(h);dh[2]=len(dense_tm)
        dense_input.write_text(' '.join(map(str,dh))+'\n'+''.join(n+' '+str(len(ps))+' '+' '.join(str(v)for xy in ps for v in xy)+' '+str(dense_lm[n])+'\n'for n,ps in dense_tm.items()))
        dense_manifest=out/'dense-manifest.json';dense_manifest.write_text(json.dumps(dict(prefix=seed['prefix'],prefix_sha256=seed['prefix_sha256'],input=str(dense_input),input_sha256=sha(dense_input))))
        # Keep the proven-negative fixture and its early capacity rejection.
        # A distinct near-capacity fixture is needed to enter actual rounds.
        pressure_tm=dict(tm);pressure_lm=dict(lm)
        pressure_lower_bound=sum(max(x for x,y in ps)-min(x for x,y in ps)+max(y for x,y in ps)-min(y for x,y in ps)+1 for ps in tm.values())
        for n,ps in dense_tm.items():
            if n in tm:continue
            extra=abs(ps[0][0]-ps[1][0])+abs(ps[0][1]-ps[1][1])+1
            if pressure_lower_bound+extra>1850:continue
            pressure_tm[n]=ps;pressure_lm[n]=-1;pressure_lower_bound+=extra
        assert 1750<pressure_lower_bound<=1850<2048
        pressure_input=out/'pressure-input.txt';ph=list(h);ph[2]=len(pressure_tm)
        pressure_input.write_text(' '.join(map(str,ph))+'\n'+''.join(n+' '+str(len(ps))+' '+' '.join(str(v)for xy in ps for v in xy)+' '+str(pressure_lm[n])+'\n'for n,ps in pressure_tm.items()))
        pressure_manifest=out/'pressure-manifest.json';pressure_manifest.write_text(json.dumps(dict(prefix=seed['prefix'],prefix_sha256=seed['prefix_sha256'],input=str(pressure_input),input_sha256=sha(pressure_input))))
    def verify_pin_plan(target,nets):
        path=target/'router-output.txt.pin-access.json'
        if not path.exists():return None
        plan=json.loads(path.read_text());items=list(nets.items());plane=40*40
        landings={x+40*y:n for n,(_,ps)in enumerate(items)for x,y in ps}
        native_file=target/'router-output.txt.native-prefix-paths.txt';native=set()
        with native_file.open()as f:
            assert int(f.readline())==8
            for index in range(8):
                fields=f.readline().split();assert fields[0]==items[index][0]
                for _ in range(int(fields[1])):
                    raw=list(map(int,f.readline().split()));assert len(raw)==1+3*raw[0]
                    native.update(raw[j]+40*raw[j+1]+plane*raw[j+2]for j in range(1,len(raw),3))
            assert not f.read().strip()
        assert native_file.read_bytes()==(out/'unchanged-default/router-output.txt.native-prefix-paths.txt').read_bytes()
        claims={};seen=set()
        for n,pin,site in plan['plan']:
            assert 8<=n<len(items)and(pin%40,pin//40)in items[n][1]and(n,pin)not in seen;seen.add((n,pin))
            assert 4<=site%40<36 and 4<=site//40<36 and(site%40+site//40)%2==0
            if(pin%40+pin//40)%2==0:assert site==pin
            else:assert abs(pin%40-site%40)+abs(pin//40-site//40)==1
            for v in {pin,site,site+plane}:
                assert v not in native and(v>=plane or landings.get(v,n)==n)
                assert claims.get(v,n)==n;claims[v]=n
        assert plan['terminals']==sum(len(ps)for _,ps in items[8:])and plan['assigned']==len(seen)<=plan['terminals']
        assert plan['assigned']+plan['unassigned']==plan['terminals']and plan['assigned']==plan['direct']+plan['odd']
        result=dict(assigned=plan['assigned'],terminals=plan['terminals'],unassigned=plan['unassigned'],claims_checked=len(claims),native_prefix_byteexact=True,plan_sha256=sha(path))
        if guided_pin_access=='after-native-m12':
            events=[json.loads(line)for line in(target/'router.log').read_text().splitlines()if '"m11_proxy_reservations_released"'in line]
            expected=dict(m11_proxy_reservations_released=sum(v<plane and v not in landings for v in claims),physical_m11_landings_preserved=plan['terminals'],m12_proxy_reservations_retained=sum(v>=plane for v in claims),native_prefix_unchanged=True)
            assert events==[expected];result['actual_m12_only']=expected
            final=target/'router-output.txt'
            if final.exists():
                with final.open()as f:
                    assert int(f.readline())==len(items)
                    for n,(name,_)in enumerate(items):
                        fields=f.readline().split();assert fields[0]==name
                        for _ in range(int(fields[1])):
                            raw=list(map(int,f.readline().split()));assert len(raw)==1+3*raw[0]
                            for j in range(1,len(raw),3):
                                v=raw[j]+40*raw[j+1]+plane*raw[j+2]
                                assert (landings if v<plane else claims).get(v,n)==n
                    assert not f.read().strip()
                result['actual_final_landing_and_m12_ownership_checked']=True
        return result
    def guided(pair):
        cost,number=pair[:2];negative=len(pair)==3 and pair[2]is True;pressure=len(pair)==3 and pair[2]=='pressure';dense=negative or pressure;name=('pressure-'if pressure else'dense-'if negative else'')+'guided-cost-'+str(cost)+'-seed-'+str(number);target=out/name;target.mkdir();failed=False
        nets=pressure_tm if pressure else dense_tm if negative else tm;limits=pressure_lm if pressure else dense_lm if negative else lm;options=dict(kwargs)
        if dense:options['native_prefix_input']=pressure_manifest if pressure else dense_manifest
        options['pin_access_policy']=guided_pin_access
        try:_,proof=route(nets,40,40,number,80,target,adaptive_heuristic=guided_adaptive,history_product=guided_history_product,global_batch_ripup=guided_global_batch,nonpreferred_cost=cost,coarse_refine=True,ordinary_present_growth=guided_present_growth,ordinary_refresh=guided_refresh,**options)
        except subprocess.CalledProcessError:failed=True;proof=None
        if negative:assert failed,'Over-capacity negative fixture incorrectly accepted'
        trace=[json.loads(l)for l in(target/'router.log').read_text().splitlines()if l.startswith('{')]
        refined=[r for r in trace if'coarse_refinement_attempts'in r]
        attempts=sum(r['coarse_refinement_attempts']for r in refined);changed=sum(r['coarse_refinement_changed']for r in refined)
        final=None
        if not failed:
            final=inspect(target/'router-output.txt',nets,40,40,limits)
            assert final['conflict_nodes']==0 and final['all_trees_flood_verified']and final['all_wire_budgets_verified']
        else:assert not(target/'router-output.txt').exists()
        return dict(cost=cost,seed=number,dense_fixture=dense,failed=failed,refinement_attempts=attempts,refinement_changed=changed,refinement_multicast=sum(r['coarse_refinement_multicast']for r in refined),refined_after_original_cutoff=any(r['round']>=16 and r['coarse_refinement_attempts']for r in refined),proof=proof,independent_final=final,guide_trace=refined,global_batch_trace=[r for r in trace if 'global_batch_native_trees'in r],ordinary_present_trace=[r for r in trace if 'ordinary_present_growth_period'in r],ordinary_refresh_trace=[r for r in trace if 'ordinary_refresh_period'in r],pin_access_assignment=verify_pin_plan(target,nets)if guided_pin_access in ('after-native','after-native-m12')else None)
    guided_pairs=[(c,n)for c in guided_costs for n in range(971,979)]+([(2,1300,True),(8,1301,True),(2,1302,'pressure'),(8,1303,'pressure')]if (guided_present_growth or guided_refresh) else[])
    with concurrent.futures.ThreadPoolExecutor(max_workers=16)as pool:cases=list(pool.map(guided,guided_pairs))
    (out/'attempts.json').write_text(json.dumps(cases,indent=2)+'\n')
    if guided_pin_access in ('after-native','after-native-m12'):
        plans=[r['pin_access_assignment']for r in cases if r['pin_access_assignment']is not None]
        assert plans and all(p['native_prefix_byteexact']for p in plans)and any(p['assigned']>0 for p in plans)
    prior_pin_replays=[]
    if guided_pin_access=='after-native-m12':
        assert any(p['actual_m12_only']['m11_proxy_reservations_released']>0 for p in plans)
        assert any(p.get('actual_final_landing_and_m12_ownership_checked')for p in plans)
        prior_pin=Path(cfg['previous_pin_guided']);pr=json.loads((prior_pin/'receipt.json').read_text())
        assert pr['passed']and pr['guided_pin_access']=='after-native'and pr['guided_refresh']==guided_refresh and pr['guided_costs']==guided_costs and pr['guided_present_growth']==guided_present_growth
        assert pr['guided_adaptive']==guided_adaptive and pr['guided_history_product']==guided_history_product and pr['guided_global_batch']==guided_global_batch and len(pr['cases'])==len(guided_pairs)
        replay_root=out/'prior-pin-policy-replay';replay_root.mkdir()
        def prior_policy(pair):
            cost,number=pair[:2];kind=pair[2]if len(pair)==3 else None
            name=('dense-'if kind is True else'pressure-'if kind=='pressure'else'')+'guided-cost-'+str(cost)+'-seed-'+str(number)
            target=replay_root/name;target.mkdir();expected=prior_pin/name;options=dict(kwargs,pin_access_policy='after-native')
            nets,limits=(dense_tm,dense_lm)if kind is True else(pressure_tm,pressure_lm)if kind=='pressure'else(tm,lm)
            if kind:options['native_prefix_input']=dense_manifest if kind is True else pressure_manifest
            failed=False
            try:route(nets,40,40,number,80,target,adaptive_heuristic=guided_adaptive,history_product=guided_history_product,global_batch_ripup=guided_global_batch,nonpreferred_cost=cost,coarse_refine=True,ordinary_present_growth=guided_present_growth,ordinary_refresh=guided_refresh,**options)
            except subprocess.CalledProcessError:failed=True
            files={}
            for name in ['router-output.txt','router-output.txt.native-prefix.log','router-output.txt.native-prefix-paths.txt','router-output.txt.pin-access.json','router.log']:
                a=target/name;b=expected/name;assert a.exists()==b.exists(),(target,name)
                if a.exists():assert a.read_bytes()==b.read_bytes(),(target,name);files[name]=sha(a)
            assert failed==(not(expected/'router-output.txt').exists())
            return dict(case=target.name,failed=failed,byteexact=files)
        with concurrent.futures.ThreadPoolExecutor(max_workers=16)as pool:prior_pin_replays=list(pool.map(prior_policy,guided_pairs))
    for c in guided_costs:assert any(not r['failed']and r['refinement_changed']>0 and r['refinement_multicast']>0 for r in cases if r['cost']==c),('No actual successful fine and multicast refinement',c)
    assert any(r['refined_after_original_cutoff']for r in cases),'Missing actual post-cutoff guidance coverage'
    if guided_present_growth:
        assert any(t['ordinary_present_coefficient']>t['native_present_coefficient']for r in cases for t in r['ordinary_present_trace']),'No actual amplified ordinary occupancy cost'
    if guided_refresh:
        refreshed=[t for r in cases for t in r['ordinary_refresh_trace']]
        assert refreshed and all(t['round']%guided_refresh==0 and t['native_trees_retained']==8 and t['ordinary_refresh_clean_trees']+t['ordinary_refresh_dirty_trees']>=16 for t in refreshed)
        assert any(t['ordinary_refresh_clean_trees']>0 for t in refreshed),'No actual previously clean ordinary tree released'
        assert any(t['ordinary_refresh_dirty_trees']>0 for t in refreshed),'No actual dirty ordinary tree released'
    if guided_global_batch:
        assert any(t['global_batch_native_trees']>0 and t['global_batch_ordinary_trees']>0 for r in cases for t in r['global_batch_trace']),'Missing actual combined native/ordinary batch ripup'
    rejected=[]
    if guided_refresh:
        for name,flags in [('refresh-no-context',['--ordinary-refresh=8']),('refresh-duplicate',['--ordinary-refresh=8','--ordinary-refresh=8']),('refresh-invalid',['--ordinary-refresh=4'])]:
            target=out/name;default=out/'unchanged-default';p=subprocess.run([str(default/'router'),str(default/'router-input.txt'),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE);(out/(name+'.stderr')).write_bytes(p.stderr)
            assert p.returncode and not target.exists();rejected.append(dict(name=name,returncode=p.returncode))
        target=out/'refresh-cli-no-context';p=subprocess.run([__import__('sys').executable,str(here/'system_upper.py'),'--manifest',str(out/'absent-manifest.json'),'--graph',str(out/'absent-graph.json'),'--out',str(target),'--route-ordinary-refresh','8'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert p.returncode and b'AssertionError'in p.stderr and not target.exists();rejected.append(dict(name='refresh-cli-no-context',returncode=p.returncode))
    for name,flags in [('cpp-no-context',['--ordinary-coarse-refine']),('cpp-duplicate',['--ordinary-coarse-refine','--ordinary-coarse-refine'])]:
        target=out/name;default=out/'unchanged-default'
        p=subprocess.run([str(default/'router'),str(default/'router-input.txt'),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        (out/(name+'.stderr')).write_bytes(p.stderr)
        assert p.returncode and not target.exists();rejected.append(dict(name=name,returncode=p.returncode))
    if guided_present_growth:
        for name,flags in [('growth-no-context',['--ordinary-present-growth=4']),('growth-duplicate',['--ordinary-present-growth=4','--ordinary-present-growth=4']),('growth-invalid',['--ordinary-present-growth=16'])]:
            target=out/name;default=out/'unchanged-default';p=subprocess.run([str(default/'router'),str(default/'router-input.txt'),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE);(out/(name+'.stderr')).write_bytes(p.stderr)
            assert p.returncode and not target.exists();rejected.append(dict(name=name,returncode=p.returncode))
    for name,flags in [('no-settled',[]),('no-coarse',['--route-weighted-settle-once'])]:
        target=out/('rejected-'+name)
        cmd=[__import__('sys').executable,str(here/'system_upper.py'),'--manifest',str(out/'absent-manifest.json'),'--graph',str(out/'absent-graph.json'),'--out',str(target),'--route-ordinary-coarse-refine',*flags]
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE);(out/(name+'.stderr')).write_bytes(p.stderr)
        assert p.returncode and b'AssertionError'in p.stderr and not target.exists();rejected.append(dict(name=name,returncode=p.returncode))
    failed=out/'guided-one-round-failure';failed.mkdir()
    try:route(tm,40,40,971,1,failed,coarse_refine=True,adaptive_heuristic=guided_adaptive,history_product=guided_history_product,global_batch_ripup=guided_global_batch,**kwargs)
    except subprocess.CalledProcessError:assert not(failed/'router-output.txt').exists()
    else:raise AssertionError('Conflicted guided single round incorrectly accepted')
    result=dict(passed=True,whole_system_qualified=False,stage='coarse-guided-fine-regression-only',guided_adaptive=guided_adaptive,component=component,defaults=defaults,cases=cases,rejected=rejected,one_round_failure_rejected=True,inputs={str(p):sha(p)for p in[config,Path(__file__),here/'routing_corridor.h',here/'tree_router.cpp',here/'tree_router_cpp.py',here/'system_upper.py',prior/'receipt.json',manifest,fixture,Path(seed['prefix']),*[here/n for n in unchanged]]},scope='Optional actual coarse path used only as XY search guide for ordinary pair and multicast branches. Multicast targets an existing actual tree point then truncates at its first actual tree join. Both layers, all fixed ownership, unit edges/vias/flood/budgets and original final gates retained. Native search/default18executions unchanged. Actual guide membership, epoch and failures plus16complete real small attempts retained; both costs require successful actual multicast refinement. Component/small route evidence only; no new hardware, macro change or full system physical qualification.')
    result['guided_history_product']=guided_history_product
    result['guided_global_batch']=guided_global_batch
    result['guided_costs']=guided_costs
    result['guided_refresh']=guided_refresh
    result['guided_pin_access']=guided_pin_access
    result['prior_pin_policy_replays']=prior_pin_replays
    if prior_pin_replays:result['inputs'][str(prior_pin/'receipt.json')]=sha(prior_pin/'receipt.json')
    result['guided_present_growth']=guided_present_growth
    result['guided_disabled_defaults']=guided_defaults
    if guided_present_growth:result['inputs'][str(previous_guided/'receipt.json')]=sha(previous_guided/'receipt.json')
    if dense_manifest:
        for p in [dense_manifest,dense_input]:result['inputs'][str(p)]=sha(p)
        result['negative_fixture_vertex_lower_bound']=negative_vertex_lower_bound
        result['negative_fixture_vertex_capacity']=2048
        for p in [pressure_manifest,pressure_input]:result['inputs'][str(p)]=sha(p)
        result['pressure_fixture_vertex_lower_bound']=pressure_lower_bound
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result
