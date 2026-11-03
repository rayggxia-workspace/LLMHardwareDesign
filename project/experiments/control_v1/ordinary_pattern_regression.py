"""Actual bounded ordinary prepass checks; never physical qualification."""
import hashlib,json,subprocess
from pathlib import Path
from tree_router_cpp import route

UNIT=r'''
#include <bits/stdc++.h>
using namespace std;
#include "ordinary_zero_pattern.h"
int main(){
 mt19937 rng(162);int successes=0,fallbacks=0;
 const int nx=32,ny=32,plane=nx*ny,size=2*plane;
 for(int c=0;c<320;++c){
  vector<int>occupied(size),foreign(size);int start=6+(c%2)+6*nx,goal=24+24*nx+(c%2)*plane;
  for(int v=0;v<size;++v){occupied[v]=c%10?rng()%6==0:0;foreign[v]=c%10?rng()%19==0:0;}
  occupied[start]=occupied[goal]=foreign[start]=foreign[goal]=0;
  if(c%20==0){for(int v:{start-1,start+1,start-nx,start+nx,start+plane})occupied[v]=1;}
  auto free=[&](int v){return !occupied[v]&&!foreign[v];};
  uint64_t checks=0;auto path=ordinary_zero_pattern(nx,ny,start,vector<int>{goal},free,[&](int v){return v==goal;},checks);
  if(checks>65537)throw runtime_error("unbounded zero-pattern work");
  // Independent exhaustive reachability on the complete legal two-layer
  // graph. The incomplete prepass may fall back even when BFS finds a path.
  vector<int>seen(size);queue<int>q;seen[start]=1;q.push(start);
  while(!q.empty()){
   int v=q.front();q.pop();int x=v%nx,y=(v%plane)/nx,l=v/plane;
   for(int w:{v-1,v+1,v-nx,v+nx,(1-l)*plane+y*nx+x}){
    if(w<0||w>=size)continue;int xx=w%nx,yy=(w%plane)/nx,ll=w/plane;
    if(xx<4||xx>=nx-4||yy<4||yy>=ny-4||abs(x-xx)+abs(y-yy)+abs(l-ll)!=1)continue;
    if(l!=ll&&(x+y)%2)continue;
    if(free(w)&&!seen[w]){seen[w]=1;q.push(w);}
   }
  }
  if(path.empty()){++fallbacks;continue;}
  if(path.front()!=start||path.back()!=goal||!seen[goal])throw runtime_error("false zero-pattern reachability");
  for(size_t i=0;i<path.size();++i){
   int v=path[i];if(v<0||v>=size||!free(v))throw runtime_error("occupied zero-pattern vertex");
   int x=v%nx,y=(v%plane)/nx,l=v/plane;if(x<4||x>=nx-4||y<4||y>=ny-4)throw runtime_error("zero-pattern out of bounds");
   if(i){int w=path[i-1],xx=w%nx,yy=(w%plane)/nx,ll=w/plane;
    if(abs(x-xx)+abs(y-yy)+abs(l-ll)!=1||(l!=ll&&(x+y)%2))throw runtime_error("invalid zero-pattern edge/via");}
  }
  ++successes;
 }
 if(successes<16||!fallbacks)throw runtime_error("unexercised prepass or fallback");
 cout<<"{\"passed\":true,\"independent_bfs_cases\":320,\"successes\":"<<successes<<",\"fallbacks\":"<<fallbacks<<"}"<<endl;
}
'''


def run(out,baseline_binary):
    out.mkdir();source=Path(__file__).parent
    cpp=out/'independent-pattern.cpp';cpp.write_text(UNIT)
    binary=out/'independent-pattern'
    subprocess.run(['g++','-std=c++17','-O2','-I'+str(source),str(cpp),'-o',str(binary)],check=True)
    with(out/'independent-pattern.json').open('w')as f:subprocess.run([str(binary)],stdout=f,check=True)
    unit=json.loads((out/'independent-pattern.json').read_text());assert unit['passed']and unit['independent_bfs_cases']==320
    cases=[];fallbacks=0
    for mode in range(3):
        folder=out/('pattern-on-'+str(mode));folder.mkdir()
        terminals={'weak0':[(6,6),(10,6)],'weak1':[(6,8),(10,8)]}
        if mode==0:terminals.update({'bus'+str(i):[(8+2*i,14),(38-2*i,30)]for i in range(12)})
        elif mode==1:
            terminals.update({'bus'+str(i):[(8+2*i,14),(38-2*i,30),(8+2*i,32)]for i in range(10)})
        else:
            terminals['pg']=[(42,42)]+[(12+4*i,36+4*j)for i in range(7)for j in range(2)]
            terminals.update({'bus'+str(i):[(8+2*i,14),(38-2*i,30)]for i in range(10)})
        kwargs=dict(heuristic_weight=16,locked_names=['weak0','weak1'],wire_limits={'weak0':16,'weak1':16},negotiated_priority=True,defer_access_vias=True,congestion_scale=1,bidirectional_two_terminal=True,pareto_wire_budget=True,resource_label_limit=8000000,critical_first=True)
        _,proof=route(terminals,48,48,162+mode,160,folder,ordinary_zero_pattern=True,**kwargs)
        trace=proof['ordinary_zero_pattern_trace'];assert trace and sum(x['zero_pattern_hits']for x in trace)>0
        assert all(x['zero_pattern_hits']+x['zero_pattern_fallbacks']==x['zero_pattern_attempts']for x in trace)
        assert proof['final_conflicts']==0 and proof['independent_cross_net_occupancy']and proof['independent_tree_flood']
        assert all(x['constrained_priority_prefix']==2 and x['priority_partition_verified']for x in proof['priority_partitions'])
        cases.append(proof);fallbacks+=sum(x['zero_pattern_fallbacks']for x in trace)
        if mode==0:
            off=out/'pattern-off';off.mkdir();route(terminals,48,48,162,160,off,**kwargs)
            with(out/'baseline-off.log').open('w')as f:subprocess.run([str(baseline_binary),str(off/'router-input.txt'),str(out/'baseline-off.txt'),'--resource-labels=8000000','--critical-first'],stdout=f,check=True)
            assert(off/'router-output.txt').read_bytes()==(out/'baseline-off.txt').read_bytes()
            assert(off/'router.log').read_bytes()==(out/'baseline-off.log').read_bytes()
    rejected=[]
    good=out/'pattern-on-0/router-input.txt'
    for label,flags in [('missing-critical',['--ordinary-zero-pattern']),('duplicate',['--critical-first','--ordinary-zero-pattern','--ordinary-zero-pattern']),('mixed-ordinary-scale',['--critical-first','--ordinary-zero-pattern','--ordinary-congestion-scale=64']),('unknown-value',['--critical-first','--ordinary-zero-pattern=1'])]:
        target=out/('reject-'+label);r=subprocess.run([str(out/'pattern-on-0/router'),str(good),str(target),*flags],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert r.returncode!=0 and not target.exists();rejected.append(dict(case=label,rejected=True))
    return dict(passed=True,unit=unit,cases=cases,rejected=rejected,actual_fallbacks=fallbacks,disabled_bidirectional_default_replay_exact=True,header_sha256=hashlib.sha256((source/'ordinary_zero_pattern.h').read_bytes()).hexdigest(),whole_system_qualified=False)
