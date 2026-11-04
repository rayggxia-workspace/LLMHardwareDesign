"""Bounded software diagnostic on an actual frame; never grants route qualification."""
from pathlib import Path
import concurrent.futures,json,os,subprocess,time
from coarse_access_regression import sha
from global_snapshot_analysis import inputs
from router_conflict_snapshot import inspect


def run(config,out):
    config=Path(config);cfg=json.loads(config.read_text());out=Path(out);out.mkdir()
    assert cfg['schema']=='weighted-reopen-probe-v1'
    source=Path(__file__).parent;cpp=source/'tree_router.cpp';header=source/'weighted_bidirectional.h'
    paths={k:Path(cfg[k])for k in ('input','snapshot','graph')}
    for k,p in paths.items():assert sha(p)==cfg[k+'_sha256']
    graph=json.loads(paths['graph'].read_text());assert len(graph['instances'])==345 and'macro_r'in graph['instances']
    h,tm,lm=inputs(paths['input']);assert h[:3]==[2345,2345,11149]
    diagnostic=inspect(paths['snapshot'],tm,*h[:2],lm)
    assert diagnostic['all_trees_flood_verified']and diagnostic['all_wire_budgets_verified']
    original=header.read_text();function=original[original.index('template<class Workspace,class Cost,class Allowed>'):]
    edits=[
        ('weighted_bidirectional(', 'probe_weighted_bidirectional('),
        ('Cost penalty,Allowed allowed,int direction_cost,int weight){','Cost penalty,Allowed allowed,int direction_cost,int weight,bool settle,vector<uint32_t>&cf,vector<uint32_t>&cb,Stats& stats){'),
        ('work.df[qf.top().node]!=qf.top().cost)', 'work.df[qf.top().node]!=qf.top().cost||(settle&&cf[qf.top().node]==epoch))'),
        ('work.db[qb.top().node]!=qb.top().cost)', 'work.db[qb.top().node]!=qb.top().cost||(settle&&cb[qb.top().node]==epoch))'),
        ('auto& seen=reverse?work.vb:work.vf;auto& parent=reverse?work.pb:work.pf;', 'auto& seen=reverse?work.vb:work.vf;auto& parent=reverse?work.pb:work.pf;auto& closed=reverse?cb:cf;'),
        ('int v=item.node;auto c=coord(v);', 'int v=item.node;++stats.expanded;if(closed[v]==epoch)++stats.reopened;else ++stats.unique;closed[v]=epoch;auto c=coord(v);'),
        ('if(p[0]<4||p[0]>=nx-4||p[1]<4||p[1]>=ny-4||!allowed(w))continue;', 'if(p[0]<4||p[0]>=nx-4||p[1]<4||p[1]>=ny-4||!allowed(w))continue;if(settle&&closed[w]==epoch)continue;')]
    probe=function
    for old,new in edits:assert probe.count(old)==1,old;probe=probe.replace(old,new)
    reverse=probe
    for old,new in reversed(edits):assert reverse.count(new)==1,new;reverse=reverse.replace(new,old)
    assert reverse==function
    (out/'baseline-weighted.h').write_bytes(header.read_bytes());(out/'probe-weighted.h').write_text(probe)
    text=cpp.read_text();item=text[text.index('struct Item {'):text.index('#include "resource_search.h"')]
    workspace=text[text.index('struct BidirectionalSearch {'):text.index('#include "weighted_bidirectional.h"')]
    code='#include <bits/stdc++.h>\nusing namespace std;\n'+item+workspace+'\n#include "baseline-weighted.h"\nstruct Stats{uint64_t expanded=0,reopened=0,unique=0;};\n#include "probe-weighted.h"\n'
    code+=r'''
int64_t valid_path(const vector<int>&path,int nx,int ny,int start,int goal,int np,const vector<int>&fixed,int owner,const vector<int>&usage){
 if(path.empty())throw runtime_error("empty path");int plane=nx*ny;int64_t cost=0;
 if(path.front()!=start||path.back()!=goal)throw runtime_error("endpoints");
 for(size_t j=1;j<path.size();++j){int a=path[j-1],b=path[j],x=a%nx,y=(a%plane)/nx,l=a/plane,xx=b%nx,yy=(b%plane)/nx,ll=b/plane;
  if(b<0||b>=2*plane||xx<4||xx>=nx-4||yy<4||yy>=ny-4||abs(x-xx)+abs(y-yy)+abs(l-ll)!=1||(l!=ll&&(x+y)%2)||(fixed[b]>=0&&fixed[b]!=owner))throw runtime_error("unit edge/fixed landing");
  cost+=(l!=ll?3:(x!=xx?(l==0?1:np):(l==1?1:np)))+int64_t(64)*usage[b];
 }return cost;
}
int main(int argc,char**argv){try{
 if(argc==2&&string(argv[1])=="--self-test"){
  mt19937 random(1240);int checks=0,baseline_replays=0;uint64_t reopens=0;
  for(int i=0;i<96;++i){int nx=24,ny=26,plane=nx*ny,size=2*plane,np=i%2?8:2,weight= i%3==0?4:i%3==1?16:64;
   BidirectionalSearch work(size);vector<uint32_t>cf(size),cb(size);vector<int>fixed(size,-1),usage(size);
   for(int v=0;v<size;++v){if(random()%23==0)fixed[v]=1;usage[v]=random()%5;}int start=5+random()%12+nx*(5+random()%14),goal=5+random()%12+nx*(5+random()%14);fixed[start]=fixed[goal]=-1;
   auto penalty=[&](int v){return int64_t(64)*usage[v];};auto allowed=[&](int v){return fixed[v]<0;};
   auto baseline=weighted_bidirectional(work,nx,ny,start,goal,penalty,allowed,np,weight);Stats a;
   auto measured=probe_weighted_bidirectional(work,nx,ny,start,goal,penalty,allowed,np,weight,false,cf,cb,a);if(baseline!=measured)throw runtime_error("instrumentation changed baseline path");++baseline_replays;reopens+=a.reopened;
   Stats b;auto settled=probe_weighted_bidirectional(work,nx,ny,start,goal,penalty,allowed,np,weight,true,cf,cb,b);if(b.reopened)throw runtime_error("settled vertex reopened");
   const int64_t inf=numeric_limits<int64_t>::max()/4;vector<int64_t>d(size,inf);priority_queue<pair<int64_t,int>,vector<pair<int64_t,int>>,greater<pair<int64_t,int>>>q;d[start]=0;q.push({0,start});
   while(!q.empty()){auto [cost,v]=q.top();q.pop();if(cost!=d[v])continue;if(v==goal)break;int x=v%nx,y=(v%plane)/nx,l=v/plane;
    for(int delta:array<int,5>{-1,1,-nx,nx,(1-2*l)*plane}){int w=v+delta;if(w<0||w>=size)continue;int xx=w%nx,yy=(w%plane)/nx,ll=w/plane;
     if(xx<4||xx>=nx-4||yy<4||yy>=ny-4||!allowed(w)||(ll!=l&&(x+y)%2))continue;
     int64_t alt=cost+(ll!=l?3:(x!=xx?(l==0?1:np):(l==1?1:np)))+penalty(w);if(alt<d[w]){d[w]=alt;q.push({alt,w});}
    }
   }
   for(auto&path:array<vector<int>,2>{measured,settled}){if(path.empty()){if(d[goal]!=inf)throw runtime_error("reachable graph rejected");}else if(d[goal]==inf||valid_path(path,nx,ny,start,goal,np,fixed,0,usage)<d[goal])throw runtime_error("independent weighted path check");++checks;}
  }
  cout<<"{\"passed\":true,\"independent_path_checks\":"<<checks<<",\"baseline_exact_path_replays\":"<<baseline_replays<<",\"observed_synthetic_reopens\":"<<reopens<<"}"<<endl;return 0;
 }
 if(argc!=7)throw runtime_error("input/snapshot/net/weight/mode/output required");ifstream f(argv[1]);string line;getline(f,line);istringstream hs(line);vector<int>h;int value;while(hs>>value)h.push_back(value);if(h.size()!=17)throw runtime_error("header");
 int nx=h[0],ny=h[1],count=h[2],plane=nx*ny,size=plane*2,target=-1,weight=stoi(argv[4]);bool settle=stoi(argv[5]);if((weight!=16&&weight!=64)||(string(argv[5])!="0"&&string(argv[5])!="1"))throw runtime_error("probe options");
 vector<string>names(count);vector<vector<int>>pins(count),trees(count);vector<int>fixed(size,-1),usage(size);
 for(int n=0;n<count;++n){int k,x,y,limit;f>>names[n]>>k;for(int j=0;j<k;++j){f>>x>>y;int q=y*nx+x;pins[n].push_back(q);if(fixed[q]>=0&&fixed[q]!=n)throw runtime_error("foreign pin collision");fixed[q]=n;}f>>limit;if(names[n]==argv[3]){if(n<h[6]||k!=2||limit!=-1)throw runtime_error("not ordinary pair");target=n;}}
 if(target<0)throw runtime_error("unknown probe net");ifstream dump(argv[2]);int total;dump>>total;if(total!=count)throw runtime_error("snapshot count");
 for(int n=0;n<count;++n){string name;int branches;dump>>name>>branches;if(name!=names[n])throw runtime_error("snapshot net order");auto&tree=trees[n];for(int j=0;j<branches;++j){int k;dump>>k;for(int q=0;q<k;++q){int x,y,l;dump>>x>>y>>l;tree.push_back(l*plane+y*nx+x);}}sort(tree.begin(),tree.end());tree.erase(unique(tree.begin(),tree.end()),tree.end());for(int v:tree)++usage[v];}
 for(int v:trees[target])--usage[v];BidirectionalSearch work(size);vector<uint32_t>cf(size),cb(size);Stats stats;
 auto penalty=[&](int v){return int64_t(64)*usage[v];};auto allowed=[&](int v){return fixed[v]<0||fixed[v]==target;};auto before=chrono::steady_clock::now();
 auto path=probe_weighted_bidirectional(work,nx,ny,pins[target][1],pins[target][0],penalty,allowed,8,weight,settle,cf,cb,stats);
 auto elapsed=chrono::duration_cast<chrono::microseconds>(chrono::steady_clock::now()-before).count();auto cost=valid_path(path,nx,ny,pins[target][1],pins[target][0],8,fixed,target,usage);
 if(settle&&stats.reopened)throw runtime_error("settled actual vertex reopened");ofstream result(argv[6]);result<<"{\"passed\":true,\"net\":\""<<names[target]<<"\",\"weight\":"<<weight<<",\"settle\":"<<(settle?"true":"false")<<",\"expanded\":"<<stats.expanded<<",\"unique_expanded\":"<<stats.unique<<",\"reopened\":"<<stats.reopened<<",\"microseconds_search_only\":"<<elapsed<<",\"vertices\":"<<path.size()<<",\"cost\":"<<cost<<",\"path\":[";for(size_t j=0;j<path.size();++j){if(j)result<<',';result<<path[j];}result<<"]}"<<endl;return 0;
 }catch(const exception&e){cerr<<e.what()<<endl;return 1;}}
'''
    harness=out/'probe.cpp';harness.write_text(code);binary=out/'probe'
    subprocess.run(['g++','-std=c++17','-O2',str(harness),'-o',str(binary)],check=True)
    p=subprocess.run([str(binary),'--self-test'],stdout=subprocess.PIPE,stderr=subprocess.PIPE);(out/'self-test.stdout').write_bytes(p.stdout);(out/'self-test.stderr').write_bytes(p.stderr);assert p.returncode==0
    selftest=json.loads(p.stdout);assert selftest['passed']and selftest['independent_path_checks']==192 and selftest['baseline_exact_path_replays']==96
    ordinary=[n for i,(n,ends)in enumerate(tm.items())if i>=h[6]and len(ends)==2];selected=[]
    for name in ['net_8437','net_2555','net_1668','net_1730']+[ordinary[(len(ordinary)-1)*i//15]for i in range(16)]:
        if name in ordinary and name not in selected:selected.append(name)
    selected=selected[:16];assert len(selected)==16
    def trial(case):
        name,weight,settle=case;target=out/(name+'-w'+str(weight)+'-s'+str(int(settle)));command=[str(binary),str(paths['input']),str(paths['snapshot']),name,str(weight),str(int(settle)),str(target)+'.json'];before=time.monotonic()
        try:
            p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90);timed_out=False
        except subprocess.TimeoutExpired as error:
            p=None;timed_out=True;stdout=error.stdout or b'';stderr=error.stderr or b''
        if p is not None:stdout=p.stdout;stderr=p.stderr
        target.with_suffix('.stdout').write_bytes(stdout);target.with_suffix('.stderr').write_bytes(stderr)
        r=dict(net=name,weight=weight,settle=settle,timed_out=timed_out,wall_seconds=time.monotonic()-before,command=command,returncode=None if p is None else p.returncode)
        if p is not None and p.returncode==0:
            d=json.loads(Path(str(target)+'.json').read_text());assert d['passed']and(not settle or d['reopened']==0);r['result']={k:v for k,v in d.items()if k!='path'};r['output_sha256']=sha(str(target)+'.json')
        return r
    workers=min(16,len(os.sched_getaffinity(0)));assert 1<=workers<=16
    cases=[(n,w,s)for n in selected for w in (16,64)for s in (False,True)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers)as pool:results=list(pool.map(trial,cases))
    # A bounded timeout or probe failure is retained, never converted into a
    # route result or a physical infeasibility conclusion.
    result=dict(passed=True,whole_system_qualified=False,route_qualified=False,stage='weighted-reopen-probe-only',selftest=selftest,diagnostic=diagnostic,workers=workers,cases=results,inputs={str(p):sha(p)for p in [config,Path(__file__),cpp,header,harness,out/'baseline-weighted.h',out/'probe-weighted.h',*paths.values()]},scope='Diagnostic own-scratch instrumented ordinary weighted search and settle-once candidate. Production C++/headers and all running sources unchanged.96 baseline path byte replays/192 independent synthetic Dijkstra path checks; actual full frame flood/unit edges/finite budgets independently checked.64 bounded actual-pair runs with artificial64*occupancy penalties after removing own tree;not actual accumulated history or full rerouting.90s own-probe child timeouts retained;no global convergence/performance/physical qualification inferred.')
    (out/'receipt.json').write_text(json.dumps(result,indent=2));return result
