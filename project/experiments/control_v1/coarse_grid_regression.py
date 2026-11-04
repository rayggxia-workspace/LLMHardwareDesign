"""Independent fine-grid cost oracle and complete routes for coarse candidates."""
from pathlib import Path
import hashlib,heapq,json,random,subprocess
from native_warm_regression import run as warm_run
from pin_release_regression import parse
from tree_router_cpp import route


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def oracle(nx,ny,start,goal,penalty,blocked):
    plane=nx*ny;d={start:0};q=[(0,start)]
    while q:
        cost,v=heapq.heappop(q)
        if d[v]!=cost:continue
        if v==goal:return cost
        x,y,l=v%nx,(v%plane)//nx,v//plane
        for xx,yy,ll,base in [(x-1,y,l,1 if l==0 else 2),(x+1,y,l,1 if l==0 else 2),(x,y-1,l,1 if l==1 else 2),(x,y+1,l,1 if l==1 else 2)]+([(x,y,1-l,3)]if(x+y)%2==0 else[]):
            w=ll*plane+yy*nx+xx
            if not(4<=xx<nx-4 and 4<=yy<ny-4)or w in blocked:continue
            alt=cost+base+penalty[w]
            if alt<d.get(w,10**30):d[w]=alt;heapq.heappush(q,(alt,w))
    return None


def run(config,out):
    config=Path(config);cfg=json.loads(config.read_text());out=Path(out);out.mkdir()
    previous=Path(cfg['previous_warm']);prior=json.loads((previous/'receipt.json').read_text());assert prior['passed']and prior['stage']=='native-warm-focused-regression-only'
    old=Path(next(k for k in prior['inputs']if k.endswith('/system_upper.py'))).parent
    assert sha(old/'native_warm_regression.py')==sha(Path(__file__).with_name('native_warm_regression.py'))
    reused=warm_run(cfg['warm_config'],out/'unchanged-warm');assert reused['passed']
    for seed in (977,979):
        for suffix in ('','.native-prefix.log','.native-prefix-paths.txt'):
            assert Path(str(previous/'native-warm'/('full-'+str(seed))/'router-output.txt')+suffix).read_bytes()==Path(str(out/'unchanged-warm'/('full-'+str(seed))/'router-output.txt')+suffix).read_bytes()
        assert(previous/'native-warm'/('full-'+str(seed))/'router.log').read_bytes()==(out/'unchanged-warm'/('full-'+str(seed))/'router.log').read_bytes()
    header=Path(__file__).with_name('ordinary_coarse_grid.h');harness=out/'coarse-harness.cpp'
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
'''+ '#include "'+header.name+'"\n'+'''int main(){int n;cin>>n;while(n--){int nx,ny,s,g,stride,weight,cap;cin>>nx>>ny>>s>>g>>stride>>weight>>cap;vector<int>cost(nx*ny*2),blocked(cost.size());for(int&v:cost)cin>>v;for(int&v:blocked)cin>>v;uint64_t expanded=0,checks=0;auto path=ordinary_coarse_grid(nx,ny,s,g,stride,0,0,weight,2,[&](int v){return cost[v];},[&](int v){return !blocked[v];},expanded,checks,cap);cout<<path.size()<<' '<<expanded<<' '<<checks;for(int v:path)cout<<' '<<v;cout<<'\\n';}}
''')
    binary=out/'coarse-harness';subprocess.run(['g++','-std=c++17','-O2',str(harness),'-I',str(header.parent),'-o',str(binary)],check=True)
    rng=random.Random(162);cases=[]
    for index in range(88):
        nx=ny=20 if index<64 else 40;plane=nx*ny
        start=5*nx+5;goal=(ny-6)*nx+nx-6+(plane if index%2 else 0)
        blocked={v for v in range(2*plane)if rng.random()<.12};blocked-={start,goal};penalty=[rng.randrange(8)for _ in range(2*plane)]
        stride=1 if index<64 else (8,16,32)[(index-64)//8]
        cases.append(dict(nx=nx,ny=ny,start=start,goal=goal,stride=stride,weight=1,cap=100000,blocked=sorted(blocked),penalty=penalty))
    capped=dict(cases[0]);capped['cap']=1;cases.append(capped)
    data=[str(len(cases))]
    for c in cases:
        data+=[' '.join(str(c[k])for k in ['nx','ny','start','goal','stride','weight','cap']),' '.join(map(str,c['penalty'])),' '.join('1'if v in set(c['blocked'])else'0'for v in range(c['nx']*c['ny']*2))]
    inputs=out/'oracle-input.txt';inputs.write_text('\n'.join(data)+'\n');raw=subprocess.check_output([str(binary)],input=inputs.read_bytes());(out/'oracle-output.txt').write_bytes(raw);lines=raw.decode().splitlines();assert len(lines)==len(cases);checks=[]
    for i,(c,line)in enumerate(zip(cases,lines)):
        row=list(map(int,line.split()));length,expanded,points=row[:3];path=row[3:];assert len(path)==length;nx,ny=c['nx'],c['ny'];plane=nx*ny;blocked=set(c['blocked']);best=oracle(nx,ny,c['start'],c['goal'],c['penalty'],blocked)
        if i==88:assert not path and expanded==2
        elif i<64:assert bool(path)==(best is not None)
        if path:
            assert path[0]==c['start']and path[-1]==c['goal']and len(path)==len(set(path));cost=0
            for v in path:assert 4<=v%nx<nx-4 and 4<=(v%plane)//nx<ny-4 and v not in blocked
            for v,w in zip(path,path[1:]):
                x,y,l=v%nx,(v%plane)//nx,v//plane;xx,yy,ll=w%nx,(w%plane)//nx,w//plane;assert abs(x-xx)+abs(y-yy)+abs(l-ll)==1 and(l==ll or(x+y)%2==0)
                base=3 if l!=ll else (1 if((x!=xx and l==0)or(y!=yy and l==1))else 2);cost+=base+c['penalty'][w]
            assert cost>=best
            if i<64:assert cost==best
        checks.append(dict(index=i,stride=c['stride'],returned_vertices=length,expanded=expanded,point_checks=points,independent_minimum_cost=best,exact_full_grid_oracle=i<64))
    fixture=out/'unchanged-warm/unchanged-release/same-prefix-release-proxy/router-input.txt';_,tm,lm=parse(fixture.read_text());manifest=out/'unchanged-warm/seed.json';positives=[]
    kwargs=dict(heuristic_weight=256,locked_names=list(tm)[:8],wire_limits=lm,negotiated_priority=True,defer_access_vias=True,congestion_scale=1,bidirectional_two_terminal=True,weighted_bidirectional=True,ordinary_zero_pattern=True,pareto_wire_budget=True,critical_first=True,native_prefix_first=True,native_prefix_flexible=True,native_prefix_input=manifest,ordinary_coarse_grid_stride=16)
    for seed in (975,976):
        target=out/('full-'+str(seed));target.mkdir();_,proof=route(tm,24,24,seed,80,target,**kwargs)
        assert proof['final_conflicts']==0 and proof['independent_tree_flood']and proof['independent_cross_net_occupancy']and any(x['coarse_hits']>0 for x in proof['ordinary_coarse_trace'])
        positives.append(dict(seed=seed,proof=proof))
    rejected=[];router=out/'full-975/router';input_path=out/'full-975/router-input.txt'
    for name,flags in [('context',['--ordinary-coarse=16']),('value',['--ordinary-coarse=4']),('duplicate',['--ordinary-coarse=16','--ordinary-coarse=16'])]:
        target=out/('invalid-'+name);p=subprocess.run([str(router),str(input_path),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE);assert p.returncode and not target.exists();rejected.append(dict(case=name,stderr=p.stderr.decode()))
    failed=out/'coarse-full-failure';failed.mkdir()
    try:route(tm,24,24,971,80,failed,**kwargs)
    except subprocess.CalledProcessError:assert not(failed/'router-output.txt').exists()
    else:raise AssertionError('Coarse candidate incorrectly grants full success')
    inputs_map=dict(reused['inputs'])
    for p in [config,Path(__file__),header,harness,inputs,out/'oracle-output.txt',out/'unchanged-warm/receipt.json']:inputs_map[str(p)]=sha(p)
    result=dict(passed=True,whole_system_qualified=False,route_qualified=False,stage='ordinary-coarse-focused-regression-only',inputs=inputs_map,scope='Independent64 fine-grid cost oracles,24 valid coarse cases,one capped fallback;2complete routes actually use coarse candidates and all original edge/via/flood/occupancy/wire checks. Old warm2 routes/main/native logs byte-identical and old71/release/refresh helpers rerun. No whole-scene physical acceptance inferred.',oracle_checks=checks,full_route_positives=positives,rejected=rejected,coarse_full_failure_rejected=True)
    (out/'receipt.json').write_text(json.dumps(result,indent=2));return result
