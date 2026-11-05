from pathlib import Path
p=Path('project/experiments/control_v1')
(p/'pin_access_reservation.h').write_bytes(r'''// Optional search constraints: reserve a globally matched one-step pin exit.
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
 ofstream out(path);out<<"{\"terminals\":"<<result.terminals<<",\"assigned\":"<<result.assigned
  <<",\"unassigned\":"<<result.terminals-result.assigned<<",\"direct\":"<<result.direct
  <<",\"odd\":"<<result.odd<<",\"same_net_aliases\":"<<result.aliases<<",\"plan\":[";
 bool comma=false;for(auto row:plan){if(comma)out<<',';comma=true;out<<'['<<row[0]<<','<<row[1]<<','<<row[2]<<']';}out<<"]}\n";
 if(!out)throw runtime_error("cannot write pin access plan");out.close();
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
'''.encode())
# All substitutions are exact and single occurrence; default disabled code retains existing flow.
f=p/'tree_router.cpp';s=f.read_text(encoding='utf-8')
def sub(a,z):
 global s
 assert s.count(a)==1,a;s=s.replace(a,z,1)
sub('#include "ordinary_endpoint_escape.h"','#include "ordinary_endpoint_escape.h"\n#include "pin_access_reservation.h"')
sub('if(argc<3||argc>12)','if(argc<3||argc>14)')
sub(' for(int i=3;i<argc;++i){string option=argv[i];',' bool native_prefix_first=false;string pin_policy="none";bool pin_policy_option=false;\n for(int i=3;i<argc;++i){string option=argv[i];')
sub('  if(option=="--critical-first")','  if(option=="--native-prefix-first"){if(native_prefix_first)throw runtime_error("duplicate native-prefix option");native_prefix_first=true;}\n  else if(option=="--pin-access=all"||option=="--pin-access=after-native"||option=="--pin-access=none"){if(pin_policy_option)throw runtime_error("duplicate pin-access policy");pin_policy_option=true;pin_policy=option.substr(option.find(\'=\')+1);}\n  else if(option=="--critical-first")')
sub(' if(locked_count<0||locked_count>count', ' if(native_prefix_first&&(!critical_first||!pareto_wire_budget))throw runtime_error("native-prefix requires original finite-priority mode");\n if(pin_policy_option&&!native_prefix_first)throw runtime_error("pin-access policy requires native-prefix mode");\n if(locked_count<0||locked_count>count')
sub(' vector<int64_t>distance(size);',' if(native_prefix_first&&pin_policy=="all"){auto r=reserve_pin_access(nx,ny,0,ends,fixed,usage,seed,string(argv[2])+".pin-access.json",true);cout<<"{\\\"pin_access_policy\\\":\\\"all\\\",\\\"assigned\\\":"<<r.assigned<<",\\\"terminals\\\":"<<r.terminals<<"}"<<endl;}\n vector<int64_t>distance(size);')
sub(' bool complete=false;uint64_t previous_conflicts=size;',' bool complete=false,native_stage=native_prefix_first;uint64_t previous_conflicts=size;\n NativePrefixLog native_log(native_prefix_first,string(argv[2])+".native-prefix.log");')
sub('  for(int n:order){\n   bool tracing=', '  for(int n:order){\n   if(native_prefix_first&&((native_stage&&n>=locked_count)||(!native_stage&&n<locked_count))){++number;continue;}\n   bool tracing=')
sub('  if(!conflicts){complete=true;break;}',r'''  if(!conflicts&&native_stage){
   // Freeze only a fully disjoint native prefix; full routing still has to
   // converge and pass the original independent gates before any success.
   for(int n=0;n<locked_count;++n){if(trees[n].empty())throw runtime_error("missing native prefix tree");
    for(int v:trees[n]){if(usage[v]!=1||(fixed[v]>=0&&fixed[v]!=n))throw runtime_error("native freeze ownership conflict");fixed[v]=n;}}
   ofstream prefix(string(argv[2])+".native-prefix-paths.txt");prefix<<locked_count<<'\n';
   for(int n=0;n<locked_count;++n){prefix<<names[n]<<' '<<branches[n].size()<<'\n';for(auto&branch:branches[n]){
    prefix<<branch.size();for(int v:branch){auto c=coord(v);prefix<<' '<<c[0]<<' '<<c[1]<<' '<<c[2];}prefix<<'\n';}}
   if(!prefix)throw runtime_error("cannot write frozen native prefix");prefix.close();native_log.release();
   cout<<"{\"native_prefix_stage_passed\":true,\"native_rounds\":"<<iteration+1<<",\"frozen_nets\":"<<locked_count<<"}"<<endl;
   if(pin_policy=="after-native"){auto r=reserve_pin_access(nx,ny,locked_count,ends,fixed,usage,seed,string(argv[2])+".pin-access.json",false);
    cout<<"{\"pin_access_policy\":\"after-native\",\"assigned\":"<<r.assigned<<",\"terminals\":"<<r.terminals<<"}"<<endl;}
   for(int n=locked_count;n<count;++n)for(int v:ends[n]){auto c=coord(v);bool legal=false;
    for(int w:{v-1,v+1,v-nx,v+nx}){if(w<0||w>=plane)continue;auto d=coord(w);if(inside(d[0],d[1])&&(fixed[w]<0||fixed[w]==n))legal=true;}
    if((c[0]+c[1])%2==0&&(fixed[v+plane]<0||fixed[v+plane]==n))legal=true;
    if(!legal)throw runtime_error("frozen native prefix blocks an ordinary terminal; retry required");}
   native_stage=false;fill(history.begin(),history.end(),0);previous_conflicts=size;iteration=-1;continue;
  }
  if(!conflicts){complete=true;break;}''')
sub(' if(!complete)throw runtime_error("negotiation did not converge");',' native_log.release();\n if(!complete)throw runtime_error(native_stage?"native-prefix negotiation did not converge; global feasibility unproved":"negotiation did not converge");')
f.write_bytes(s.encode())
