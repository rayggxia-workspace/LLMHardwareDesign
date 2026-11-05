// Optional zero-occupancy ordinary-pair prepass. Escape an odd M11 landing
// by one legal M11 edge before its even-parity via. At most four unchanged
// geometric-generator calls; failure always yields to the original search.
template<class Free>
vector<int> ordinary_endpoint_escape(int nx,int ny,int start,int goal,
                                    Free free_vertex,uint64_t& checks,uint64_t& core_calls){
 const int plane=nx*ny;
 auto xyz=[&](int v){return array<int,3>{v%nx,(v%plane)/nx,v/plane};};
 auto available=[&](int v){
  ++checks;if(v<0||v>=2*plane)return false;auto p=xyz(v);
  return p[0]>=4&&p[0]<nx-4&&p[1]>=4&&p[1]<ny-4&&free_vertex(v);
 };
 if(start/plane||goal/plane)throw runtime_error("endpoint escape requires M11 terminals");
 if(!available(start)||!available(goal))return{};
 auto prefixes=[&](int v){
  auto p=xyz(v);vector<vector<int>> result;vector<int> candidates;
  if((p[0]+p[1])%2)candidates={v+1,v-1,v+nx,v-nx};else candidates={v};
  for(int w:candidates){
   auto q=xyz(w);
   if(abs(q[0]-p[0])+abs(q[1]-p[1])>1)continue;
   if(w!=v&&!available(w))continue;
   if(!available(w+plane))continue;
   vector<int> path{v};if(w!=v)path.push_back(w);path.push_back(w+plane);result.push_back(path);
  }
  return result;
 };
 auto sources=prefixes(start),targets=prefixes(goal);
 vector<array<int,3>> pairs;
 for(int i=0;i<int(sources.size());++i)for(int j=0;j<int(targets.size());++j){
  auto s=xyz(sources[i].back()),t=xyz(targets[j].back());pairs.push_back({abs(s[0]-t[0])+abs(s[1]-t[1]),i,j});
 }
 sort(pairs.begin(),pairs.end());int tried=0;
 for(auto choice:pairs){
  if(tried++==4)break;
  const auto& prefix=sources[choice[1]];const auto& suffix=targets[choice[2]];
  if(prefix.back()==suffix.back()){
   // Shared even M11 proxy needs no redundant up/down via.
   vector<int> path(prefix.begin(),prefix.end()-1);
   for(int j=int(suffix.size())-3;j>=0;--j)path.push_back(suffix[j]);return path;
  }
  auto clear_core=[&](int v){
   if(find(prefix.begin(),prefix.end()-1,v)!=prefix.end()-1)return false;
   if(find(suffix.begin(),suffix.end()-1,v)!=suffix.end()-1)return false;
   return free_vertex(v);
  };
  ++core_calls;
  auto core=ordinary_zero_pattern(nx,ny,prefix.back(),vector<int>{suffix.back()},
        clear_core,[&](int v){return v==suffix.back();},checks);
  if(core.empty())continue;
  vector<int> path=prefix;path.insert(path.end(),core.begin()+1,core.end());
  for(int j=int(suffix.size())-2;j>=0;--j)path.push_back(suffix[j]);return path;
 }
 return{};
}

inline int endpoint_escape_self_test(){
 const int nx=24,ny=26,plane=nx*ny;mt19937 random(809);int tested=0;
 auto verify=[&](int start,int goal,const vector<unsigned char>& blocked,int exact_size=0){
  uint64_t checks=0,calls=0;auto path=ordinary_endpoint_escape(nx,ny,start,goal,
     [&](int v){return !blocked[v];},checks,calls);
  if(calls>4||checks>262166)throw runtime_error("endpoint escape budget exceeded");
  if(exact_size&&int(path.size())!=exact_size)throw runtime_error("endpoint escape shared proxy mismatch");
  if(!path.empty()){
   if(path.front()!=start||path.back()!=goal)throw runtime_error("endpoint escape endpoints mismatch");
   for(size_t j=0;j<path.size();++j){
    int v=path[j],x=v%nx,y=(v%plane)/nx,l=v/plane;
    if(v<0||v>=2*plane||x<4||x>=nx-4||y<4||y>=ny-4||blocked[v])throw runtime_error("endpoint escape blocked vertex");
    if(!j)continue;int w=path[j-1],xx=w%nx,yy=(w%plane)/nx,ll=w/plane;
    if(l==ll){if(abs(x-xx)+abs(y-yy)!=1)throw runtime_error("endpoint escape nonunit edge");}
    else if(x!=xx||y!=yy||(x+y)%2)throw runtime_error("endpoint escape illegal via");
   }
  }
  ++tested;return path;
 };
 vector<unsigned char> open(2*plane);
 verify(6+6*nx,7+6*nx,open,2);verify(7+6*nx,9+6*nx,open,3);
 if(verify(7+7*nx,14+15*nx,open).empty())throw runtime_error("endpoint escape open mixed parity failed");
 auto blocked_source=open;blocked_source[6+6*nx]=1;
 if(!verify(6+6*nx,12+12*nx,blocked_source).empty())throw runtime_error("endpoint escape occupied source accepted");
 for(int i=0;i<128;++i){
  auto blocked=open;if(i%2)for(auto& v:blocked)v=random()%5==0;
  int sx=5+random()%14,sy=5+random()%16,gx=5+random()%14,gy=5+random()%16;
  int start=sx+sy*nx,goal=gx+gy*nx;if(start==goal)goal=5+5*nx;
  if(start==goal)goal=6+5*nx;blocked[start]=blocked[goal]=0;
  auto path=verify(start,goal,blocked);
  if(!(i%2)&&path.empty())throw runtime_error("endpoint escape open static case failed");
 }
 return tested;
}
