"""Unit-edge pin access, independent costs, settled-graph bounds and full routes."""
from pathlib import Path
import hashlib,json,random,subprocess
from coarse_grid_regression import run as coarse_run, oracle
from pin_release_regression import parse
from tree_router_cpp import route


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(config,out):
    config=Path(config);cfg=json.loads(config.read_text());out=Path(out);out.mkdir()
    previous=Path(cfg['previous_coarse']);prior=json.loads((previous/'receipt.json').read_text());assert prior['passed']and prior['stage']=='ordinary-coarse-focused-regression-only'
    old=Path(next(k for k in prior['inputs']if k.endswith('/system_upper.py'))).parent
    assert sha(old/'coarse_grid_regression.py')==sha(Path(__file__).with_name('coarse_grid_regression.py'))
    reused=coarse_run(cfg['coarse_config'],out/'unchanged-coarse');assert reused['passed']
    for seed in (975,976):
        for suffix in ('','.native-prefix.log','.native-prefix-paths.txt'):
            assert Path(str(previous/'coarse-grid'/('full-'+str(seed))/'router-output.txt')+suffix).read_bytes()==Path(str(out/'unchanged-coarse'/('full-'+str(seed))/'router-output.txt')+suffix).read_bytes()
        assert(previous/'coarse-grid'/('full-'+str(seed))/'router.log').read_bytes()==(out/'unchanged-coarse'/('full-'+str(seed))/'router.log').read_bytes()
    assert(previous/'coarse-grid/oracle-output.txt').read_bytes()==(out/'unchanged-coarse/oracle-output.txt').read_bytes()
    header=Path(__file__).with_name('ordinary_coarse_grid.h');harness=out/'access-harness.cpp'
    harness.write_text('''#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <limits>
#include <queue>
#include <stdexcept>
#include <vector>
using namespace std;
struct Item{int64_t priority,cost;int node;bool operator<(const Item&q)const{return priority!=q.priority?priority>q.priority:cost!=q.cost?cost>q.cost:node>q.node;}};
#include "ordinary_coarse_grid.h"
int main(){int n;cin>>n;while(n--){int nx,ny,s,g,stride,weight,cap,local;cin>>nx>>ny>>s>>g>>stride>>weight>>cap>>local;vector<int>cost(nx*ny*2),blocked(cost.size());for(int&v:cost)cin>>v;for(int&v:blocked)cin>>v;uint64_t expanded=0,checks=0;auto path=ordinary_coarse_grid(nx,ny,s,g,stride,0,0,weight,2,[&](int v){return cost[v];},[&](int v){return !blocked[v];},expanded,checks,cap,local);cout<<path.size()<<' '<<expanded<<' '<<checks;for(int v:path)cout<<' '<<v;cout<<char(10);}}
''')
    binary=out/'access-harness';subprocess.run(['g++','-std=c++17','-O2',str(harness),'-I',str(header.parent),'-o',str(binary)],check=True)
    rng=random.Random(162);cases=[]
    for i in range(88):
        nx=ny=20 if i<64 else 40;plane=nx*ny;start=5*nx+5;goal=(ny-6)*nx+nx-6+(plane if i%2 else 0)
        blocked={v for v in range(2*plane)if rng.random()<.12};blocked-={start,goal}
        cases.append(dict(nx=nx,ny=ny,start=start,goal=goal,stride=1 if i<64 else (8,16,32)[(i-64)//8],weight=1 if i<64 else 16,cap=1 if i<64 else 65536,local=1,blocked=sorted(blocked),penalty=[rng.randrange(8)for _ in range(2*plane)]))
    for stride in (16,32):
        for x in (11,13,15,17):
            nx=ny=40;start=10*nx+x;goal=30*nx+30;blocked=[10*nx+x-2,10*nx+x+2,8*nx+x,12*nx+x]
            for local in (0,1):cases.append(dict(nx=nx,ny=ny,start=start,goal=goal,stride=stride,weight=16,cap=65536,local=local,blocked=blocked,penalty=[0]*(2*nx*ny),fence=True))
    data=[str(len(cases))]
    for c in cases:
        blocked=set(c['blocked']);data+=[' '.join(str(c[k])for k in ['nx','ny','start','goal','stride','weight','cap','local']),' '.join(map(str,c['penalty'])),' '.join('1'if v in blocked else'0'for v in range(c['nx']*c['ny']*2))]
    inputs=out/'access-input.txt';inputs.write_text('\n'.join(data)+'\n');raw=subprocess.check_output([str(binary)],input=inputs.read_bytes());(out/'access-output.txt').write_bytes(raw);lines=raw.decode().splitlines();assert len(lines)==len(cases)==104;checks=[]
    for i,(c,line)in enumerate(zip(cases,lines)):
        row=list(map(int,line.split()));length,expanded,points=row[:3];path=row[3:];assert len(path)==length;nx,ny=c['nx'],c['ny'];plane=nx*ny;blocked=set(c['blocked']);best=oracle(nx,ny,c['start'],c['goal'],c['penalty'],blocked)
        if i<64:assert bool(path)==(best is not None)
        if c.get('fence'):assert bool(path)==bool(c['local'])and best is not None
        sx,sy=c['start']%nx,(c['start']%plane)//nx;gx,gy=c['goal']%nx,(c['goal']%plane)//nx
        xs={4,nx-5,sx,gx,*range(4,nx-4,c['stride'])};ys={4,ny-5,sy,gy,*range(4,ny-4,c['stride'])}
        if c['local']:
            xs.update(x for x in [sx-1,sx+1,gx-1,gx+1]if 4<=x<nx-4);ys.update(y for y in [sy-1,sy+1,gy-1,gy+1]if 4<=y<ny-4)
            assert expanded<=2*len(xs)*len(ys)
        if path:
            assert path[0]==c['start']and path[-1]==c['goal']and len(path)==len(set(path));cost=0
            for v in path:assert 4<=v%nx<nx-4 and 4<=(v%plane)//nx<ny-4 and v not in blocked
            for v,w in zip(path,path[1:]):
                x,y,l=v%nx,(v%plane)//nx,v//plane;xx,yy,ll=w%nx,(w%plane)//nx,w//plane;assert abs(x-xx)+abs(y-yy)+abs(l-ll)==1 and(l==ll or(x+y)%2==0)
                base=3 if l!=ll else (1 if((x!=xx and l==0)or(y!=yy and l==1))else 2);cost+=base+c['penalty'][w]
            assert cost>=best
            if i<64:assert cost==best
        checks.append(dict(index=i,stride=c['stride'],local_access=bool(c['local']),returned_vertices=length,expanded=expanded,graph_states=2*len(xs)*len(ys),point_checks=points,independent_minimum_cost=best,exact_cost_oracle=i<64,endpoint_fence=bool(c.get('fence'))))
    fixture=out/'unchanged-coarse/unchanged-warm/unchanged-release/same-prefix-release-proxy/router-input.txt';_,tm,lm=parse(fixture.read_text());manifest=out/'unchanged-coarse/unchanged-warm/seed.json';positives=[]
    kwargs=dict(heuristic_weight=256,locked_names=list(tm)[:8],wire_limits=lm,negotiated_priority=True,defer_access_vias=True,congestion_scale=1,bidirectional_two_terminal=True,weighted_bidirectional=True,ordinary_zero_pattern=True,pareto_wire_budget=True,critical_first=True,native_prefix_first=True,native_prefix_flexible=True,native_prefix_input=manifest,ordinary_coarse_grid_stride=16,ordinary_coarse_access=True)
    for seed in (971,972):
        target=out/('full-'+str(seed));target.mkdir();_,proof=route(tm,24,24,seed,80,target,**kwargs)
        assert proof['final_conflicts']==0 and proof['independent_tree_flood']and proof['independent_cross_net_occupancy']and proof['coarse_access_trace']and any(x['coarse_hits']>0 for x in proof['ordinary_coarse_trace']);positives.append(dict(seed=seed,proof=proof))
    rejected=[];router=out/'full-971/router';input_path=out/'full-971/router-input.txt'
    for name,flags in [('context',['--ordinary-coarse-access']),('duplicate',['--ordinary-coarse-access','--ordinary-coarse-access'])]:
        target=out/('invalid-'+name);p=subprocess.run([str(router),str(input_path),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE);assert p.returncode and not target.exists();rejected.append(dict(case=name,stderr=p.stderr.decode()))
    failed=out/'access-global-failure';failed.mkdir()
    try:route(tm,24,24,975,80,failed,**kwargs)
    except subprocess.CalledProcessError:assert not(failed/'router-output.txt').exists()
    else:raise AssertionError('Access candidate incorrectly grants full success')
    inputs_map=dict(reused['inputs'])
    for p in [config,Path(__file__),header,harness,inputs,out/'access-output.txt',out/'unchanged-coarse/receipt.json']:inputs_map[str(p)]=sha(p)
    result=dict(passed=True,whole_system_qualified=False,route_qualified=False,stage='ordinary-coarse-access-focused-regression-only',inputs=inputs_map,scope='64 independent full-grid minimum costs,24 weighted coarse legality/bound checks,8 same-input blocked-endpoint failure/success pairs. Settled nodes bounded by compressed graph states.2actualfull routes plusglobalfailure/controlrejects; oldcoarse2 route/main/native artifacts and89oraclebytes identical, allold71/warm/release/refresh actual helperreplays retained. No fullscene physical acceptance inferred.',oracle_checks=checks,full_route_positives=positives,rejected=rejected,access_global_failure_rejected=True)
    (out/'receipt.json').write_text(json.dumps(result,indent=2));return result
