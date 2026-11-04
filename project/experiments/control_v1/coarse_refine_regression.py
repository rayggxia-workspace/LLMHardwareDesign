"""Coarse-to-fine search-guide regression, not full physical qualification.

Reference principle only: https://github.com/cuhk-eda/cu-gr (connected rectangle
guides to a detailed router). No CUGR implementation or qualification reused.
"""
from pathlib import Path
import concurrent.futures,json,os,subprocess
from coarse_access_regression import sha
from global_snapshot_analysis import inputs
from router_conflict_snapshot import inspect
from tree_router_cpp import route


def run(config,out):
    config=Path(config);cfg=json.loads(config.read_text());out=Path(out);out.mkdir()
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))==16
    here=Path(__file__).parent;baseline=Path(cfg['baseline_source']);prior=Path(cfg['previous_resource'])
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
    def guided(pair):
        cost,number=pair;name='guided-cost-'+str(cost)+'-seed-'+str(number);target=out/name;target.mkdir();failed=False
        try:_,proof=route(tm,40,40,number,80,target,adaptive_heuristic=True,nonpreferred_cost=cost,coarse_refine=True,**kwargs)
        except subprocess.CalledProcessError:failed=True;proof=None
        trace=[json.loads(l)for l in(target/'router.log').read_text().splitlines()if l.startswith('{')]
        refined=[r for r in trace if'coarse_refinement_attempts'in r]
        attempts=sum(r['coarse_refinement_attempts']for r in refined);changed=sum(r['coarse_refinement_changed']for r in refined)
        final=None
        if not failed:
            final=inspect(target/'router-output.txt',tm,40,40,lm)
            assert final['conflict_nodes']==0 and final['all_trees_flood_verified']and final['all_wire_budgets_verified']
        else:assert not(target/'router-output.txt').exists()
        return dict(cost=cost,seed=number,failed=failed,refinement_attempts=attempts,refinement_changed=changed,refined_after_original_cutoff=any(r['round']>=16 and r['coarse_refinement_attempts']for r in refined),proof=proof,independent_final=final,guide_trace=refined)
    with concurrent.futures.ThreadPoolExecutor(max_workers=16)as pool:cases=list(pool.map(guided,[(c,n)for c in(2,8)for n in range(971,979)]))
    (out/'attempts.json').write_text(json.dumps(cases,indent=2)+'\n')
    for c in(2,8):assert any(not r['failed']and r['refinement_changed']>0 for r in cases if r['cost']==c),('No actual successful fine refinement',c)
    assert any(r['refined_after_original_cutoff']for r in cases),'Missing actual post-cutoff guidance coverage'
    rejected=[]
    for name,flags in [('cpp-no-context',['--ordinary-coarse-refine']),('cpp-duplicate',['--ordinary-coarse-refine','--ordinary-coarse-refine'])]:
        target=out/name;default=out/'unchanged-default'
        p=subprocess.run([str(default/'router'),str(default/'router-input.txt'),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        (out/(name+'.stderr')).write_bytes(p.stderr)
        assert p.returncode and not target.exists();rejected.append(dict(name=name,returncode=p.returncode))
    for name,flags in [('no-settled',[]),('no-coarse',['--route-weighted-settle-once'])]:
        target=out/('rejected-'+name)
        cmd=[__import__('sys').executable,str(here/'system_upper.py'),'--manifest',str(out/'absent-manifest.json'),'--graph',str(out/'absent-graph.json'),'--out',str(target),'--route-ordinary-coarse-refine',*flags]
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE);(out/(name+'.stderr')).write_bytes(p.stderr)
        assert p.returncode and b'AssertionError'in p.stderr and not target.exists();rejected.append(dict(name=name,returncode=p.returncode))
    failed=out/'guided-one-round-failure';failed.mkdir()
    try:route(tm,40,40,971,1,failed,coarse_refine=True,adaptive_heuristic=True,**kwargs)
    except subprocess.CalledProcessError:assert not(failed/'router-output.txt').exists()
    else:raise AssertionError('Conflicted guided single round incorrectly accepted')
    result=dict(passed=True,whole_system_qualified=False,stage='coarse-guided-fine-regression-only',component=component,defaults=defaults,cases=cases,rejected=rejected,one_round_failure_rejected=True,inputs={str(p):sha(p)for p in[config,Path(__file__),here/'routing_corridor.h',here/'tree_router.cpp',here/'tree_router_cpp.py',here/'system_upper.py',prior/'receipt.json',manifest,fixture,Path(seed['prefix']),*[here/n for n in unchanged]]},scope='Optional actual coarse path used only as XY search guide for ordinary two-terminal fine routing. Both layers, all fixed ownership, unit edges/vias/flood/budgets and original final gates retained. Native search/default18executions unchanged. Actual guide membership, epoch and failures plus16complete real small attempts retained. Component/small route evidence only; no new hardware, macro change or full system physical qualification.')
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result
