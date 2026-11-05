#include <bits/stdc++.h>
#include <omp.h>
using namespace std;
#include "ordinary_zero_pattern.h"
#include "ordinary_endpoint_escape.h"
int main(int argc,char**argv){try{
 if(argc!=3)throw runtime_error("input/output required");
 ifstream in(argv[1]);int nx,ny,count,seed,rounds,weight,locked;in>>nx>>ny>>count>>seed>>rounds>>weight>>locked;string rest;getline(in,rest);
 int plane=nx*ny;vector<int>fixed(2*plane,-1);vector<string>names(count);vector<vector<int>>pins(count);
 for(int n=0;n<count;++n){int k,limit;in>>names[n]>>k;for(int j=0;j<k;++j){int x,y;in>>x>>y;int v=y*nx+x;if(fixed[v]!=-1)throw runtime_error("duplicate input landing");fixed[v]=n;pins[n].push_back(v);}in>>limit;}
 if(!in)throw runtime_error("input parse failed");
 struct Result{bool tested=false,original=false,escaped=false;uint64_t old_checks=0,new_checks=0,calls=0,vertices=0;string error;};vector<Result>rows(count);
 int direct_checks=endpoint_escape_self_test();
 #pragma omp parallel for schedule(dynamic,1) num_threads(16)
 for(int n=locked;n<count;++n){
  if(pins[n].size()!=2)continue;auto& r=rows[n];r.tested=true;
  try{
   int goal=pins[n][0],start=pins[n][1];auto free_vertex=[&](int v){return fixed[v]==-1||fixed[v]==n;};
   auto path=ordinary_zero_pattern(nx,ny,start,vector<int>{goal},free_vertex,[&](int v){return v==goal;},r.old_checks);r.original=!path.empty();
   if(path.empty()){path=ordinary_endpoint_escape(nx,ny,start,goal,free_vertex,r.new_checks,r.calls);r.escaped=!path.empty();}
   if(r.old_checks>65537||r.new_checks>262166||r.calls>4)throw runtime_error("prepass budget violation");
   if(!path.empty()){
    if(path.front()!=start||path.back()!=goal)throw runtime_error("wrong endpoint");
    for(size_t i=0;i<path.size();++i){int v=path[i],x=v%nx,y=(v%plane)/nx,l=v/plane;
     if(v<0||v>=2*plane||x<4||x>=nx-4||y<4||y>=ny-4||!free_vertex(v))throw runtime_error("bounds/foreign landing violation");
     if(i){int w=path[i-1],xx=w%nx,yy=(w%plane)/nx,ll=w/plane;
      if(l==ll){if(abs(x-xx)+abs(y-yy)!=1)throw runtime_error("nonunit edge");}
      else if(x!=xx||y!=yy||(x+y)%2)throw runtime_error("illegal via");
     }
    }r.vertices=path.size();
   }
  }catch(const exception& e){r.error=e.what();}
 }
 int tested=0,original=0,escaped=0,failed=0;uint64_t vertices=0,checks=0;
 for(auto& r:rows){if(!r.error.empty())throw runtime_error(r.error);if(!r.tested)continue;++tested;original+=r.original;escaped+=r.escaped;failed+=!r.original&&!r.escaped;vertices+=r.vertices;checks+=r.old_checks+r.new_checks;}
 ofstream out(argv[2]);out<<"{\"passed\":true,\"scope\":\"Actual input static pin-only bounded candidates; no dynamic occupancy/history, simultaneous routing, congestion convergence or physical qualification. Every returned path independently unit-edge/via/bounds/foreign-pin checked.\",\"pairs\":"<<tested<<",\"original_capped_hits\":"<<original<<",\"escape_additional_hits\":"<<escaped<<",\"still_no_candidate\":"<<failed<<",\"validated_vertices\":"<<vertices<<",\"candidate_vertex_checks\":"<<checks<<",\"direct_candidate_selfchecks\":"<<direct_checks<<",\"unresolved\":[";
 bool first=true;for(int n=0;n<count;++n)if(rows[n].tested&&!rows[n].original&&!rows[n].escaped){if(!first)out<<',';first=false;out<<'"'<<names[n]<<'"';}out<<"]}\n";
 cout<<"pairs="<<tested<<" original="<<original<<" additional_escape="<<escaped<<" unresolved="<<failed<<endl;return 0;
}catch(const exception& e){cerr<<e.what()<<endl;return 1;}}
