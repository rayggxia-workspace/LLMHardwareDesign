
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
