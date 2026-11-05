"""Exact old/new finite-resource search replay; never physical qualification."""
from pathlib import Path
import concurrent.futures,json,os,subprocess,time
from coarse_access_regression import sha
from global_snapshot_analysis import inputs
from router_conflict_snapshot import inspect
from tree_router_cpp import route


def run(config,out):
    config=Path(config);cfg=json.loads(config.read_text());out=Path(out);out.mkdir()
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))==16
    here=Path(__file__).parent;old=Path(cfg['baseline_source']);prior=Path(cfg['previous_adaptive'])
    assert json.loads((prior/'receipt.json').read_text())['passed']
    unchanged=['tree_router.cpp','tree_router_cpp.py','weighted_settled_bidirectional.h','weighted_bidirectional.h','settled_adaptive_regression.py','system_geometry.py','system_sta.py','system_accept.py','final_composition.py']
    for n in unchanged:assert sha(here/n)==sha(old/n),n
    # Both implementations are compiled into one translation unit. Rename only
    # the baseline type; the independent full-state oracle is exercised too.
    base=(old/'resource_search.h').read_text().replace('ResourceSearch','BaselineResourceSearch').replace('resource_oracle_test','baseline_resource_oracle_test')
    (out/'baseline.h').write_text(base)
    harness=r'''
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <limits>
#include <queue>
#include <random>
#include <stdexcept>
#include <vector>
using namespace std;
struct Item {int64_t priority,cost;int node;bool operator<(const Item&q)const{
 if(priority!=q.priority)return priority>q.priority;
 if(cost!=q.cost)return cost<q.cost;return node>q.node;}};
#include "baseline.h"
#include "resource_search.h"
int main(){
 if(resource_oracle_test()!=120||baseline_resource_oracle_test()!=120)return 2;
 mt19937 rng(1621340);int checks=0,failures=0;
 for(int trial=0;trial<2400;++trial){
  int nx=24,ny=24,plane=nx*ny,size=2*plane;
  vector<int>blocked(size),penalty(size);
  for(int v=0;v<size;++v){blocked[v]=rng()%19==0;penalty[v]=rng()%501;}
  int start=(4+rng()%16)*nx+4+rng()%16,goal=(4+rng()%16)*nx+4+rng()%16;
  blocked[start]=blocked[goal]=0;
  int budget=rng()%80,weight=array<int,8>{1,4,8,16,32,64,128,256}[trial%8],cost=array<int,3>{2,8,32}[trial%3];
  BaselineResourceSearch a;ResourceSearch b;
  a.label_limit=b.label_limit=trial%4?8000000:array<int,5>{1,2,16,64,256}[trial%5];
  auto h=[&](int v){return abs(v%nx-goal%nx)+abs((v%plane)/nx-(goal%plane)/nx);};
  vector<int>pa,pb;string ea,eb;
  try{pa=a.find(nx,ny,start,budget,weight,cost,[&](int v){return penalty[v];},[&](int v){return !blocked[v];},[&](int v){return v==goal;},h);}catch(const runtime_error&e){ea=e.what();}
  try{pb=b.find(nx,ny,start,budget,weight,cost,[&](int v){return penalty[v];},[&](int v){return !blocked[v];},[&](int v){return v==goal;},h);}catch(const runtime_error&e){eb=e.what();}
  if(pa!=pb||ea!=eb||a.calls!=b.calls||a.maximum_labels!=b.maximum_labels)return 3;
  failures+=!ea.empty();++checks;
 }
 cout<<"{\"passed\":true,\"exact_path_and_label_checks\":"<<checks<<",\"identical_cap_failures\":"<<failures<<",\"independent_oracles\":240}"<<endl;
}
'''
    (out/'component.cpp').write_text(harness)
    subprocess.run(['g++','-std=c++17','-O2','-I',str(here),str(out/'component.cpp'),'-o',str(out/'component')],check=True)
    with(out/'component.json').open('w')as f:subprocess.run([str(out/'component')],stdout=f,check=True,timeout=600)
    component=json.loads((out/'component.json').read_text());assert component['passed']and component['identical_cap_failures']>0
    manifest=Path(cfg['fixture_manifest']);seed=json.loads(manifest.read_text());fixture=Path(seed['input'])
    assert sha(fixture)==seed['input_sha256']and sha(seed['prefix'])==seed['prefix_sha256']
    h,tm,lm=inputs(fixture);assert h[:2]==[40,40]
    kwargs=dict(heuristic_weight=256,locked_names=list(tm)[:8],wire_limits={n:v for n,v in lm.items()if v>=0},negotiated_priority=True,defer_access_vias=True,congestion_scale=1,bidirectional_two_terminal=True,weighted_bidirectional=True,ordinary_zero_pattern=True,pareto_wire_budget=True,critical_first=True,native_prefix_first=True,native_prefix_flexible=True,native_prefix_input=manifest,ordinary_coarse_grid_stride=16,ordinary_coarse_access=True,ordinary_coarse_static=True,ordinary_coarse_multicast=True,ordinary_coarse_zero=True,ordinary_coarse_rounds=16,weighted_settle_once=True)
    def case(pair):
        cost,number,adaptive,rounds,name=pair;target=out/name;target.mkdir();expected=prior/name
        before=time.monotonic();failed=False
        try:route(tm,40,40,number,rounds,target,adaptive_heuristic=adaptive,nonpreferred_cost=cost,**kwargs)
        except subprocess.CalledProcessError:failed=True
        files=['router-output.txt','router-output.txt.native-prefix.log','router-output.txt.native-prefix-paths.txt','router.log']
        replay={}
        for n in files:
            a=target/n;b=expected/n;assert a.exists()==b.exists(),(name,n)
            if a.exists():assert a.read_bytes()==b.read_bytes(),(name,n);replay[n]=sha(a)
        assert failed==(not(expected/'router-output.txt').exists())
        final=None
        if not failed:
            final=inspect(target/'router-output.txt',tm,40,40,lm)
            assert final['conflict_nodes']==0 and final['all_trees_flood_verified']and final['all_wire_budgets_verified']
        return dict(name=name,failed=failed,byteexact=replay,independent_final=final,elapsed_seconds=time.monotonic()-before)
    pairs=[(c,n,True,80,'cost-'+str(c)+'-seed-'+str(n))for c in(2,8)for n in range(971,979)]
    pairs +=[(2,972,False,80,'unchanged-default'),(2,971,True,1,'one-round-failure')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=16)as pool:cases=list(pool.map(case,pairs))
    result=dict(passed=True,whole_system_qualified=False,stage='resource-front-exact-replay-only',component=component,cases=cases,inputs={str(p):sha(p)for p in[config,Path(__file__),here/'resource_search.h',old/'resource_search.h',prior/'receipt.json',manifest,fixture,Path(seed['prefix']),*[here/n for n in unchanged]]},scope='Only unlink inactive dominance lookup entries. All label records/IDs/parents/cap/heap ordering and physical gates retained. Baseline/new exact paths, counts and exceptions plus 18 original full small executions byteexact, including failures. No speedup or full physical qualification inferred.')
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result
