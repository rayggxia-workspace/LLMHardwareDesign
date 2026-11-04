// Optional search constraints: reserve a globally matched one-step pin exit.
// These reservations are not fabricated wires/vias; actual returned paths
// still undergo the independent occupancy, connectivity and physical gates.
#include <functional>
#include <map>
struct PinAccessResult {int terminals=0,assigned=0,direct=0,odd=0,aliases=0;};
inline PinAccessResult reserve_pin_access(int nx,int ny,int first,
 const vector<vector<int>>&ends,vector<int>&fixed,const vector<uint32_t>&usage,
 uint32_t seed,const string&path,bool require_complete){
 const int plane=nx*ny;PinAccessResult result;
 struct Left {int net,pin;vector<int>sites;};vector<Left>left;
 vector<array<int,3>>plan;mt19937 random(seed^0x6d2b79f5U);
 auto allowed=[&](int v,int n){return !usage[v]&&(fixed[v]<0||fixed[v]==n);};
 auto inside=[&](int v){int x=v%nx,y=v/nx;return x>=4&&x<nx-4&&y>=4&&y<ny-4;};
 // Even landing owners have first claim on their own vertical exit.
 for(int n=first;n<int(ends.size());++n)for(int pin:ends[n]){
  ++result.terminals;int x=pin%nx,y=pin/nx;
  if((x+y)%2)continue;
  if(allowed(pin+plane,n)){fixed[pin+plane]=n;++result.assigned;++result.direct;plan.push_back({n,pin,pin});}
 }
 for(int n=first;n<int(ends.size());++n)for(int pin:ends[n]){
  int x=pin%nx,y=pin/nx;if(!((x+y)%2))continue;Left item{n,pin,{}};
  for(int site:{pin-1,pin+1,pin-nx,pin+nx})
   if(inside(site)&&allowed(site,n)&&allowed(site+plane,n))item.sites.push_back(site);
  shuffle(item.sites.begin(),item.sites.end(),random);
  auto alias=find_if(item.sites.begin(),item.sites.end(),[&](int site){return fixed[site+plane]==n;});
  if(alias!=item.sites.end()){
   fixed[*alias]=n;++result.assigned;++result.odd;++result.aliases;plan.push_back({n,pin,*alias});
  }else left.push_back(move(item));
 }
 // Maximum bipartite matching, rather than greedy pin-by-pin reservation.
 // Only O(terminals) state: no additional grid-sized workspace.
 map<int,int>resource;for(auto&item:left)for(int site:item.sites)resource.emplace(site,0);
 int next=0;for(auto&entry:resource)entry.second=next++;
 vector<vector<int>>edges(left.size());vector<int>site_by_id(resource.size());
 for(auto&entry:resource)site_by_id[entry.second]=entry.first;
 for(size_t i=0;i<left.size();++i)for(int site:left[i].sites)edges[i].push_back(resource.at(site));
 vector<int>match_left(left.size(),-1),match_right(resource.size(),-1),level(left.size());
 vector<int>order(left.size());iota(order.begin(),order.end(),0);shuffle(order.begin(),order.end(),random);
 for(;;){queue<int>q;fill(level.begin(),level.end(),-1);bool reachable=false;
  for(int i:order)if(match_left[i]<0){level[i]=0;q.push(i);}
  while(!q.empty()){int i=q.front();q.pop();for(int r:edges[i]){
   int j=match_right[r];if(j<0)reachable=true;else if(level[j]<0){level[j]=level[i]+1;q.push(j);}
  }}
  if(!reachable)break;
  function<bool(int)>augment=[&](int i){for(int r:edges[i]){int j=match_right[r];
   if(j<0||(level[j]==level[i]+1&&augment(j))){match_left[i]=r;match_right[r]=i;return true;}
  }level[i]=-1;return false;};
  int progress=0;for(int i:order)if(match_left[i]<0&&augment(i))++progress;
  if(!progress)throw runtime_error("pin matching invariant failed");
 }
 for(size_t i=0;i<left.size();++i)if(match_left[i]>=0){int site=site_by_id[match_left[i]],n=left[i].net;
  if(!allowed(site,n)||!allowed(site+plane,n))throw runtime_error("matched pin exit overlaps occupied/fixed owner");
  fixed[site]=n;fixed[site+plane]=n;++result.assigned;++result.odd;plan.push_back({n,left[i].pin,site});
 }
 if(!path.empty()){ofstream out(path);out<<"{\"terminals\":"<<result.terminals<<",\"assigned\":"<<result.assigned
  <<",\"unassigned\":"<<result.terminals-result.assigned<<",\"direct\":"<<result.direct
  <<",\"odd\":"<<result.odd<<",\"same_net_aliases\":"<<result.aliases<<",\"plan\":[";
 bool comma=false;for(auto row:plan){if(comma)out<<',';comma=true;out<<'['<<row[0]<<','<<row[1]<<','<<row[2]<<']';}out<<"]}\n";
 if(!out)throw runtime_error("cannot write pin access plan");out.close();}
 if(require_complete&&result.assigned!=result.terminals)
  throw runtime_error("bounded one-step pin assignment incomplete; global feasibility unproved");
 return result;
}
// Isolate prefix-only progress from the ordinary/full routing log. Restore
// cout even when any original finite-resource search throws an exception.
struct NativePrefixLog {
 ofstream file;streambuf*previous=nullptr;
 NativePrefixLog(bool enabled,const string&path){if(enabled){file.open(path);if(!file)throw runtime_error("cannot open native prefix log");previous=cout.rdbuf(file.rdbuf());}}
 void release(){if(previous){cout.flush();cout.rdbuf(previous);previous=nullptr;file.close();}}
 ~NativePrefixLog(){release();}
};

// Independent exhaustive assignment oracle on small random pin neighbourhoods.
// The oracle enumerates resource subsets; it does not reuse the matcher.
inline int pin_access_self_test(){
 mt19937 random(0x162849U);int checks=0;const int nx=20,ny=20,plane=400;
 for(int trial=0;trial<200;++trial){
  vector<vector<int>>ends(6);vector<int>fixed(2*plane,-1);vector<uint32_t>usage(2*plane);
  vector<int>pool;for(int y=6;y<12;++y)for(int x=6;x<12;++x)pool.push_back(y*nx+x);
  shuffle(pool.begin(),pool.end(),random);
  for(int n=0;n<6;++n){ends[n]={pool[n]};fixed[pool[n]]=n;}
  for(int j=0;j<25;++j){int v=(6+random()%6)*nx+6+random()%6+(random()%2)*plane;if(fixed[v]<0)fixed[v]=99;}
  auto before=fixed;vector<vector<int>>legal(6);int direct=0;
  for(int n=0;n<6;++n){int pin=ends[n][0],x=pin%nx,y=pin/nx;
   if((x+y)%2==0){if(before[pin+plane]<0||before[pin+plane]==n)++direct;continue;}
   for(int site:{pin-1,pin+1,pin-nx,pin+nx})if((before[site]<0||before[site]==n)&&(before[site+plane]<0||before[site+plane]==n))legal[n].push_back(site);
  }
  // Odd neighbours may not consume an even landing's reserved M12 point.
  for(int n=0;n<6;++n)for(int m=0;m<6;++m){int pin=ends[m][0];if((pin%nx+pin/nx)%2==0)
   legal[n].erase(remove(legal[n].begin(),legal[n].end(),pin),legal[n].end());}
  set<int>used;function<int(int)>enumerate=[&](int n){if(n==6)return 0;int best=enumerate(n+1);
   for(int site:legal[n])if(used.insert(site).second){best=max(best,1+enumerate(n+1));used.erase(site);}return best;};
  int expected=direct+enumerate(0);auto got=reserve_pin_access(nx,ny,0,ends,fixed,usage,trial,"",false);
  if(got.assigned!=expected||got.terminals!=6)throw runtime_error("pin matching disagrees with independent exhaustive oracle");
  for(size_t v=0;v<fixed.size();++v)if(before[v]>=0&&fixed[v]!=before[v])throw runtime_error("pin matching overwrote foreign fixed owner");
  ++checks;
 }
 return checks;
}
