"""Adjacent candidate tracks: independent graph costs and unchanged final gates."""
from pathlib import Path
import heapq,json,random,subprocess
from coarse_access_regression import sha
from global_batch_regression import run as previous_run
from global_snapshot_analysis import inputs
from router_conflict_snapshot import inspect
from tree_router_cpp import route


def oracle(c,neighbors):
    nx,ny=c['nx'],c['ny'];plane=nx*ny
    def xyz(v):return v%nx,(v%plane)//nx,v//plane
    sx,sy,_=xyz(c['start']);gx,gy,_=xyz(c['goal'])
    xs={4,nx-5,sx,gx};ys={4,ny-5,sy,gy}
    for values,n,offset in [(xs,nx,c['ox']),(ys,ny,c['oy'])]:
        for v in range(4+offset,n-4,c['stride']):
            values.update(v+d for d in ((-1,0,1)if neighbors else(0,))if 4<=v+d<n-4)
    xs.update(v for v in (sx-1,sx+1,gx-1,gx+1)if 4<=v<nx-4)
    ys.update(v for v in (sy-1,sy+1,gy-1,gy+1)if 4<=v<ny-4)
    xs=sorted(xs);ys=sorted(ys);xi={v:i for i,v in enumerate(xs)};yi={v:i for i,v in enumerate(ys)}
    blocked=set(c['blocked']);best={c['start']:0};queue=[(0,c['start'])]
    while queue:
        cost,v=heapq.heappop(queue)
        if best.get(v)!=cost:continue
        if v==c['goal']:return cost,2*len(xs)*len(ys)
        x,y,l=xyz(v);i,j=xi[x],yi[y];targets=[]
        if i:targets.append((xs[i-1],y,l))
        if i+1<len(xs):targets.append((xs[i+1],y,l))
        if j:targets.append((x,ys[j-1],l))
        if j+1<len(ys):targets.append((x,ys[j+1],l))
        if (x+y)%2==0:targets.append((x,y,1-l))
        for xx,yy,ll in targets:
            px,py,pl=x,y,l;extra=0;legal=True
            while (px,py,pl)!=(xx,yy,ll):
                if px!=xx:px+=1 if px<xx else-1;base=1 if pl==0 else c['nonpreferred']
                elif py!=yy:py+=1 if py<yy else-1;base=1 if pl==1 else c['nonpreferred']
                else:pl=ll;base=3
                w=pl*plane+py*nx+px
                if w in blocked:legal=False;break
                extra+=base+c['penalty'][w]
            if legal and cost+extra<best.get(w,10**30):best[w]=cost+extra;heapq.heappush(queue,(cost+extra,w))
    return None,2*len(xs)*len(ys)


def candidate_checks(out):
    out=Path(out);out.mkdir();header=Path(__file__).with_name('ordinary_coarse_grid.h');harness=out/'harness.cpp'
    harness.write_text('''#include <bits/stdc++.h>
using namespace std;
struct Item{int64_t priority,cost;int node;bool operator<(const Item&q)const{return priority!=q.priority?priority>q.priority:cost!=q.cost?cost>q.cost:node>q.node;}};
#include "ordinary_coarse_grid.h"
int main(){int n;cin>>n;while(n--){int nx,ny,s,g,stride,ox,oy,weight,np,neighbor;cin>>nx>>ny>>s>>g>>stride>>ox>>oy>>weight>>np>>neighbor;vector<int>cost(nx*ny*2),blocked(cost.size());for(int&v:cost)cin>>v;for(int&v:blocked)cin>>v;uint64_t expanded=0,checks=0;auto path=ordinary_coarse_grid(nx,ny,s,g,stride,ox,oy,weight,np,[&](int v){return cost[v];},[&](int v){return !blocked[v];},expanded,checks,65536,true,neighbor);cout<<path.size()<<' '<<expanded<<' '<<checks;for(int v:path)cout<<' '<<v;cout<<char(10);}}
''')
    binary=out/'harness';subprocess.run(['g++','-std=c++17','-O2',str(harness),'-I',str(header.parent),'-o',str(binary)],check=True)
    rng=random.Random(1621183);cases=[];data=['144']
    for i in range(72):
        nx=ny=40;plane=nx*ny;start=5*nx+5;goal=34*nx+34+(plane if i%2 else 0);blocked={v for v in range(2*plane)if rng.random()<.08};blocked-={start,goal}
        c=dict(nx=nx,ny=ny,start=start,goal=goal,stride=(8,16,32)[i%3],ox=i%4,oy=(i*3)%4,weight=1 if i<48 else 16,nonpreferred=(2,8,32)[i%3],blocked=sorted(blocked),penalty=[rng.randrange(8)for _ in range(2*plane)]);cases.append(c)
        for neighbors in (False,True):data+=[' '.join(str(c[k])for k in ['nx','ny','start','goal','stride','ox','oy','weight','nonpreferred'])+' '+str(int(neighbors)),' '.join(map(str,c['penalty'])),' '.join('1'if v in blocked else'0'for v in range(2*plane))]
    inp=out/'input.txt';inp.write_text('\n'.join(data)+'\n');raw=subprocess.check_output([str(binary)],input=inp.read_bytes());(out/'output.txt').write_bytes(raw);lines=raw.decode().splitlines();assert len(lines)==144;checks=[]
    for i,c in enumerate(cases):
        costs=[]
        for neighbor in (False,True):
            row=list(map(int,lines[2*i+neighbor].split()));length,expanded,points=row[:3];path=row[3:];assert len(path)==length;best,states=oracle(c,neighbor);assert bool(path)==(best is not None)and expanded<=states;cost=0;nx,ny=c['nx'],c['ny'];plane=nx*ny;blocked=set(c['blocked'])
            if path:
                assert path[0]==c['start']and path[-1]==c['goal']and len(path)==len(set(path))
                for v in path:assert v not in blocked and 4<=v%nx<nx-4 and 4<=(v%plane)//nx<ny-4
                for v,w in zip(path,path[1:]):
                    x,y,l=v%nx,(v%plane)//nx,v//plane;xx,yy,ll=w%nx,(w%plane)//nx,w//plane;assert abs(x-xx)+abs(y-yy)+abs(l-ll)==1 and(l==ll or(x+y)%2==0)
                    cost+=(3 if l!=ll else 1 if((x!=xx and l==0)or(y!=yy and l==1))else c['nonpreferred'])+c['penalty'][w]
                assert cost>=best
                if c['weight']==1:assert cost==best
            costs.append(best);checks.append(dict(case=i,neighbors=neighbor,weight=c['weight'],independent_cost=best,returned_cost=cost if path else None,vertices=length,expanded=expanded,states=states,point_checks=points))
        if costs[0]is not None:assert costs[1]is not None and costs[1]<=costs[0]
    (out/'checks.json').write_text(json.dumps(checks,indent=2))
    return dict(passed=True,checks=checks,inputs={str(p):sha(p)for p in [header,harness,inp,out/'output.txt',out/'checks.json']})


def run(config,out):
    config=Path(config);cfg=json.loads(config.read_text());out=Path(out);out.mkdir();previous=Path(cfg['previous_batch']);prior=json.loads((previous/'receipt.json').read_text());assert prior['passed']and prior['stage']=='global-dirty-batch-focused-regression-only'
    reused=previous_run(cfg['batch_config'],out/'unchanged-batch');assert reused['passed']
    for seed in (971,972):
        for suffix in ('','.native-prefix.log','.native-prefix-paths.txt','.global-round-8.txt'):assert Path(str(previous/'global-batch'/('full-'+str(seed))/'router-output.txt')+suffix).read_bytes()==Path(str(out/'unchanged-batch'/('full-'+str(seed))/'router-output.txt')+suffix).read_bytes()
        assert(previous/'global-batch'/('full-'+str(seed))/'router.log').read_bytes()==(out/'unchanged-batch'/('full-'+str(seed))/'router.log').read_bytes()
    checked=candidate_checks(out/'candidate-checks');manifest=out/'unchanged-batch/unchanged-zero/unchanged-multicast/multicast-seed.json';fixture=Path(json.loads(manifest.read_text())['input']);header,tm,lm=inputs(fixture);assert header[:3]==[40,40,24]and header[6]==8
    kwargs=dict(heuristic_weight=256,locked_names=list(tm)[:8],wire_limits={n:v for n,v in lm.items()if v>=0},negotiated_priority=True,defer_access_vias=True,congestion_scale=1,bidirectional_two_terminal=True,weighted_bidirectional=True,ordinary_zero_pattern=True,pareto_wire_budget=True,critical_first=True,native_prefix_first=True,native_prefix_flexible=True,native_prefix_input=manifest,ordinary_coarse_grid_stride=16,ordinary_coarse_access=True,ordinary_coarse_static=True,ordinary_coarse_multicast=True,ordinary_coarse_zero=True,ordinary_coarse_neighbors=True,global_snapshot_round=8)
    positives=[]
    for seed in (971,972):
        target=out/('full-'+str(seed));target.mkdir();_,proof=route(tm,40,40,seed,80,target,**kwargs);assert proof['final_conflicts']==0 and proof['coarse_neighbors_trace']and sum(r['coarse_neighbor_attempts']for r in proof['coarse_neighbors_trace'])>0
        final=inspect(target/'router-output.txt',tm,40,40,lm);assert final['conflict_nodes']==0 and final['all_trees_flood_verified']and final['all_wire_budgets_verified'];snapshot=target/'router-output.txt.global-round-8.txt';diagnostic=inspect(snapshot,tm,40,40,lm)
        expected=next(json.loads(l)for l in(target/'router.log').read_text().splitlines()if l.startswith('{')and '"conflict_nodes"'in l and json.loads(l)['round']==7)
        for key in ('conflict_nodes','excess_occupancy','occupied_cells','summed_tree_vertices','grid_cell_capacity'):assert diagnostic[key]==expected[key]
        positives.append(dict(seed=seed,proof=proof,independent_final=final,snapshot_sha256=sha(snapshot),snapshot_diagnostic=diagnostic))
    rejected=[];router=out/'full-971/router';inp=out/'full-971/router-input.txt'
    for name,flags in [('context',['--ordinary-coarse-neighbors']),('duplicate',['--ordinary-coarse-neighbors']*2)]:
        target=out/('invalid-'+name);p=subprocess.run([str(router),str(inp),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE);assert p.returncode and not target.exists();rejected.append(dict(case=name,stderr=p.stderr.decode()))
    failed=out/'coarse-neighbors-failure';failed.mkdir()
    try:route(tm,40,40,974,80,failed,**kwargs)
    except subprocess.CalledProcessError:assert not(failed/'router-output.txt').exists()and(failed/'router-output.txt.global-round-8.txt').exists()
    else:raise AssertionError('Neighbor candidates incorrectly grant full success')
    result=dict(passed=True,whole_system_qualified=False,route_qualified=False,stage='ordinary-coarse-neighbors-focused-regression-only',inputs={**reused['inputs'],**checked['inputs'],str(config):sha(config),str(Path(__file__)):sha(__file__),str(manifest):sha(manifest),str(fixture):sha(fixture)},candidate_checks=checked['checks'],full_route_positives=positives,rejected=rejected,coarse_neighbors_global_failure_rejected=True,scope='144 independent candidate graph comparisons(96exactcost/48weighted),adjacent-track graph superset reachability/cost and physical unit edges checked. Two full synthetic routes and independently recomputed final trees/budgets/occupancy and round8. Global failure with diagnostic but no final output rejected. Oldbatch routes/main/native/path/snapshot byteexact and allnestedactualoldregressions. No physical grid/pitch or finite native solver/budget/gate change;no fullscene qualification inferred.')
    (out/'receipt.json').write_text(json.dumps(result,indent=2));return result
