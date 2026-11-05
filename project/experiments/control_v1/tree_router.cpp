// Multi-terminal negotiated M11/M12 router. Independent Python verification
// checks the returned edges, all landings and global occupancy before use.
#include <algorithm>
#include <chrono>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <numeric>
#include <queue>
#include <random>
#include <sstream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;
struct Item {int64_t priority,cost;int node;bool operator<(const Item& q)const{
 if(priority!=q.priority)return priority>q.priority;
 // On an equal A* score, advance towards the existing tree rather than
 // expanding an arbitrary broad equal-score frontier. Physical checks stay
 // independent of this search-order decision.
 if(cost!=q.cost)return cost<q.cost;
 return node>q.node;
}};
#include "resource_search.h"
#include "ordinary_zero_pattern.h"
#include "ordinary_endpoint_escape.h"
#include "pin_access_reservation.h"
#include "native_prefix_seed.h"
#include "ordinary_coarse_grid.h"
#include "routing_corridor.h"
// Exact XY distance to an existing routed tree is an admissible lower bound:
// it ignores layers, vias, obstacles and congestion. A tree bounding box alone
// gives zero over a large empty area of high-fanout PG/reset trees.
struct TreeDistance {
 vector<array<int,2>> points;
 void build(int lo,int hi,int axis){
  if(lo>=hi)return;int mid=(lo+hi)/2;
  nth_element(points.begin()+lo,points.begin()+mid,points.begin()+hi,[&](auto a,auto b){return a[axis]<b[axis];});
  build(lo,mid,1-axis);build(mid+1,hi,1-axis);
 }
 void search(int lo,int hi,int axis,int x,int y,int& best)const{
  if(lo>=hi)return;int mid=(lo+hi)/2;auto p=points[mid];
  best=min(best,abs(x-p[0])+abs(y-p[1]));if(!best)return;
  int delta=(axis?y:x)-p[axis];
  if(delta<=0){search(lo,mid,1-axis,x,y,best);if(abs(delta)<best)search(mid+1,hi,1-axis,x,y,best);}
  else{search(mid+1,hi,1-axis,x,y,best);if(abs(delta)<best)search(lo,mid,1-axis,x,y,best);}
 }
 int distance(int x,int y)const{int best=numeric_limits<int>::max();search(0,points.size(),0,x,y,best);return best;}
};
// Exact distance to the same XY point set represented by maximal straight
// grid runs. A long routed branch needs a few segments rather than one KD
// entry per grid vertex. The BVH bounds only prune queries; leaf distances
// remain exact. No routed point, detour or via projection is discarded.
struct SegmentDistance {
 struct Box {int x0,y0,x1,y1;};
 struct Node {Box box;int lo,hi,left=-1,right=-1;};
 vector<Box> segments;vector<Node> nodes;
 static int distance(Box b,int x,int y){return max({b.x0-x,0,x-b.x1})+max({b.y0-y,0,y-b.y1});}
 void run(int x0,int y0,int x1,int y1){
  if(x0!=x1&&y0!=y1)throw runtime_error("non-axis-aligned target segment");
  segments.push_back({min(x0,x1),min(y0,y1),max(x0,x1),max(y0,y1)});
 }
 template<class P,class F>void append(const vector<P>& branch,F coord){
  if(branch.empty())throw runtime_error("empty target branch");
  auto first=coord(branch[0]),last=first;int direction=0;
  for(size_t j=1;j<branch.size();++j){auto now=coord(branch[j]);int dx=now[0]-last[0],dy=now[1]-last[1];
   if(abs(dx)+abs(dy)>1)throw runtime_error("non-contiguous target branch");
   int next_direction=dx? (dx>0?1:-1):dy? (dy>0?2:-2):0;
   if(next_direction&&direction&&next_direction!=direction){run(first[0],first[1],last[0],last[1]);first=last;}
   if(next_direction)direction=next_direction;last=now;}
  run(first[0],first[1],last[0],last[1]);
 }
 int build(int lo,int hi){
  if(lo>=hi)throw runtime_error("empty target segment index");
  Box box=segments[lo];for(int i=lo+1;i<hi;++i){auto b=segments[i];box={min(box.x0,b.x0),min(box.y0,b.y0),max(box.x1,b.x1),max(box.y1,b.y1)};}
  int id=nodes.size();nodes.push_back({box,lo,hi});
  if(hi-lo>8){int axis=(box.y1-box.y0)>(box.x1-box.x0),mid=(lo+hi)/2;
   nth_element(segments.begin()+lo,segments.begin()+mid,segments.begin()+hi,[&](Box a,Box b){return axis?a.y0+a.y1<b.y0+b.y1:a.x0+a.x1<b.x0+b.x1;});
   int left=build(lo,mid),right=build(mid,hi);nodes[id].left=left;nodes[id].right=right;}
  return id;
 }
 void build(){nodes.reserve(2*segments.size());build(0,segments.size());}
 void search(int id,int x,int y,int& best)const{
  auto& node=nodes[id];if(distance(node.box,x,y)>=best)return;
  if(node.left<0){for(int i=node.lo;i<node.hi;++i)best=min(best,distance(segments[i],x,y));return;}
  int a=node.left,b=node.right;if(distance(nodes[b].box,x,y)<distance(nodes[a].box,x,y))swap(a,b);
  search(a,x,y,best);search(b,x,y,best);
 }
 int distance(int x,int y)const{int best=numeric_limits<int>::max();search(0,x,y,best);return best;}
};
// Within one branch the target tree and its XY distance are immutable. Both
// layers and repeated neighbour relaxations can reuse the exact same value.
// Epoch invalidation is mandatory whenever that tree grows between branches.
struct XYDistanceCache {
 vector<uint32_t> epochs;vector<int> values;uint32_t epoch=0;
 explicit XYDistanceCache(size_t size):epochs(size),values(size){}
 void next_tree(){if(!++epoch)throw runtime_error("heuristic cache epoch overflow");}
 template<class F>int get(int key,F compute){
  if(epochs[key]!=epoch){values[key]=compute();epochs[key]=epoch;}
  return values[key];
 }
};
// Optional exact two-ended search. Reverse edges charge the original
// destination vertex, and balanced Manhattan potentials make both reduced
// graphs nonnegative. This workspace is never used for finite wire budgets.
struct BidirectionalSearch {
 vector<int64_t>df,db;vector<uint32_t>vf,vb;vector<int>pf,pb;uint32_t epoch=0;
 explicit BidirectionalSearch(size_t size):df(size),db(size),vf(size),vb(size),pf(size),pb(size){}
 template<class Cost,class Allowed>
 vector<int>find(int nx,int ny,int start,int goal,Cost penalty,Allowed allowed,int nonpreferred_cost=2){
  if(nonpreferred_cost!=2&&nonpreferred_cost!=8&&nonpreferred_cost!=32)throw runtime_error("invalid bidirectional direction cost");
  int plane=nx*ny,size=2*plane;const int64_t inf=numeric_limits<int64_t>::max()/4;
  if(!++epoch)throw runtime_error("bidirectional epoch overflow");
  auto coord=[&](int v){return array<int,3>{v%nx,(v%plane)/nx,v/plane};};
  auto s=coord(start),g=coord(goal);
  auto potential=[&](int v){auto p=coord(v);return abs(p[0]-g[0])+abs(p[1]-g[1])-abs(p[0]-s[0])-abs(p[1]-s[1]);};
  priority_queue<Item>qf,qb;qf.push({0,0,start});qb.push({0,0,goal});
  vf[start]=vb[goal]=epoch;df[start]=db[goal]=0;int meeting=-1;int64_t best=inf;
  auto consider=[&](int v){if(vf[v]==epoch&&vb[v]==epoch&&df[v]+db[v]<best){best=df[v]+db[v];meeting=v;}};
  consider(start);
  while(true){
   while(!qf.empty()&&(vf[qf.top().node]!=epoch||df[qf.top().node]!=qf.top().priority))qf.pop();
   while(!qb.empty()&&(vb[qb.top().node]!=epoch||db[qb.top().node]!=qb.top().priority))qb.pop();
   if(qf.empty()||qb.empty())break;
   if(best!=inf&&qf.top().priority+qb.top().priority>=best)break;
   bool reverse=qb.top().priority<qf.top().priority;auto& q=reverse?qb:qf;
   auto& d=reverse?db:df;auto& seen=reverse?vb:vf;auto& parent=reverse?pb:pf;
   auto item=q.top();q.pop();int v=item.node;auto c=coord(v);int x=c[0],y=c[1],l=c[2];
   array<pair<int,int>,5>next{{{v-1,l==0?1:nonpreferred_cost},{v+1,l==0?1:nonpreferred_cost},{v-nx,l==1?1:nonpreferred_cost},{v+nx,l==1?1:nonpreferred_cost},{(1-l)*plane+y*nx+x,3}}};
   for(int i=0;i<5;++i){if(i==4&&(x+y)%2)continue;int w=next[i].first;if(w<0||w>=size)continue;auto p=coord(w);
    if(p[0]<4||p[0]>=nx-4||p[1]<4||p[1]>=ny-4||!allowed(w))continue;
    int64_t cost=next[i].second+penalty(reverse?v:w);
    __int128 reduced=__int128(2)*cost+(reverse?potential(v)-potential(w):potential(w)-potential(v));
    if(reduced<0||__int128(item.priority)+reduced>=inf)throw runtime_error("invalid reduced bidirectional cost");
    int64_t alt=item.priority+int64_t(reduced);
    // Reduced costs can be zero across an empty Manhattan rectangle. The
    // tie key is twice the original accumulated cost, rather than the
    // reduced cost, so equal-score searches advance instead of sweeping
    // that whole rectangle. Distances and termination use reduced costs.
    int64_t original=alt+(reverse?potential(w)-potential(goal):potential(start)-potential(w));
    if(seen[w]!=epoch||alt<d[w]){seen[w]=epoch;d[w]=alt;parent[w]=v;q.push({alt,original,w});consider(w);}
   }
  }
  if(meeting<0)return{};
  vector<int>path{meeting};while(path.back()!=start)path.push_back(pf[path.back()]);reverse(path.begin(),path.end());
  for(int v=meeting;v!=goal;){v=pb[v];path.push_back(v);}return path;
 }
};
#include "weighted_bidirectional.h"
#include "weighted_settled_bidirectional.h"
#include "ordinary_zero_maze.h"
int main(int argc,char**argv){try{
 if(argc==2&&string(argv[1])=="--self-test"){
  mt19937 random(162);int checks=0,cache_checks=0;XYDistanceCache cache(1200*1200);
  for(int t=0;t<250;++t){TreeDistance index;for(int i=0;i<1+t%127;++i)index.points.push_back({int(random()%1024),int(random()%1024)});
   auto original=index.points;index.build(0,index.points.size(),0);cache.next_tree();
   for(int i=0;i<200;++i){int x=random()%1200,y=random()%1200,expected=numeric_limits<int>::max();
    for(auto p:original)expected=min(expected,abs(x-p[0])+abs(y-p[1]));
    if(index.distance(x,y)!=expected)throw runtime_error("tree distance differs from independent exhaustive oracle");++checks;
    for(int repeat=0;repeat<2;++repeat){if(cache.get(y*1200+x,[&]{return index.distance(x,y);})!=expected)throw runtime_error("cached distance differs from exhaustive oracle");++cache_checks;}}
   int before=index.distance(0,0);if(cache.get(0,[&]{return index.distance(0,0);})!=before)throw runtime_error("cache origin differs");++cache_checks;
   index.points.push_back({0,0});index.build(0,index.points.size(),0);cache.next_tree();
   if(cache.get(0,[&]{return index.distance(0,0);})!=0)throw runtime_error("cache survived target-tree change");++cache_checks;}
  int segment_checks=0;
  for(int t=0;t<250;++t){SegmentDistance index;vector<array<int,2>> points;
   for(int j=0;j<1+t%37;++j){int x0=random()%1200,y0=random()%1200,x1=x0,y1=y0;if(random()%2)x1=random()%1200;else y1=random()%1200;
    index.run(x0,y0,x1,y1);for(int x=min(x0,x1);x<=max(x0,x1);++x)for(int y=min(y0,y1);y<=max(y0,y1);++y)points.push_back({x,y});}
   index.build();for(int i=0;i<200;++i){int x=random()%1400,y=random()%1400,expected=numeric_limits<int>::max();
    for(auto p:points)expected=min(expected,abs(x-p[0])+abs(y-p[1]));
    if(index.distance(x,y)!=expected)throw runtime_error("segment distance differs from independent exhaustive grid oracle");++segment_checks;}}
  int branch_checks=0;
  for(int t=0;t<250;++t){SegmentDistance index;vector<array<int,2>> points;
   for(int j=0;j<1+t%13;++j){vector<array<int,2>> branch{{int(random()%1200),int(random()%1200)}};
    for(int k=0;k<500;++k){auto p=branch.back();switch(random()%5){case 0:++p[0];break;case 1:--p[0];break;case 2:++p[1];break;case 3:--p[1];break;default:break;}branch.push_back(p);}
    points.insert(points.end(),branch.begin(),branch.end());index.append(branch,[](auto p){return p;});}
   index.build();for(int i=0;i<200;++i){int x=random()%1400,y=random()%1400,expected=numeric_limits<int>::max();
    for(auto p:points)expected=min(expected,abs(x-p[0])+abs(y-p[1]));
    if(index.distance(x,y)!=expected)throw runtime_error("compressed branch distance differs from exhaustive routed points");++branch_checks;}}
  int bidirectional_checks=0,directional_bidirectional_checks=0,weighted_checks=0;
  for(int nonpreferred_cost:{2,8,32})for(int t=0;t<100;++t){
   int nx=24,ny=26,plane=nx*ny,size=plane*2;BidirectionalSearch bidir(size);
   vector<int>blocked(size),penalty(size);for(int v=0;v<size;++v){blocked[v]=random()%23==0;penalty[v]=random()%41;}
   int start=(5+random()%14)*nx+5+random()%12,goal=(5+random()%14)*nx+5+random()%12;blocked[start]=blocked[goal]=0;
   auto path=bidir.find(nx,ny,start,goal,[&](int v){return penalty[v];},[&](int v){return!blocked[v];},nonpreferred_cost);
   const int64_t inf=numeric_limits<int64_t>::max()/4;vector<int64_t>d(size,inf);d[start]=0;priority_queue<Item>q;q.push({0,0,start});
   while(!q.empty()){auto item=q.top();q.pop();int v=item.node;if(d[v]!=item.cost)continue;int x=v%nx,y=(v%plane)/nx,l=v/plane;
    if(v==goal)break;
    for(auto delta:array<int,5>{-1,1,-nx,nx,(1-2*l)*plane}){int w=v+delta;if(w<0||w>=size)continue;int xx=w%nx,yy=(w%plane)/nx,ll=w/plane;
     if(xx<4||xx>=nx-4||yy<4||yy>=ny-4||blocked[w])continue;
     if(abs(x-xx)+abs(y-yy)+abs(l-ll)!=1||(l!=ll&&(x+y)%2))continue;
     int base=l!=ll?3:((l==0&&y==yy)||(l==1&&x==xx)?1:nonpreferred_cost);int64_t alt=item.cost+base+penalty[w];
     if(alt<d[w]){d[w]=alt;q.push({alt,alt,w});}}
   }
   if((d[goal]==inf)!=path.empty())throw runtime_error("bidirectional reachability differs from independent Dijkstra");
   if(!path.empty()){int64_t cost=0;if(path.front()!=start||path.back()!=goal)throw runtime_error("bidirectional endpoints differ");
    for(size_t j=1;j<path.size();++j){int v=path[j-1],w=path[j],x=v%nx,y=(v%plane)/nx,l=v/plane,xx=w%nx,yy=(w%plane)/nx,ll=w/plane;
     if(abs(x-xx)+abs(y-yy)+abs(l-ll)!=1||blocked[w]||(l!=ll&&(x+y)%2))throw runtime_error("bidirectional invalid edge");
     cost+=(l!=ll?3:((l==0&&y==yy)||(l==1&&x==xx)?1:nonpreferred_cost))+penalty[w];}
    if(cost!=d[goal])throw runtime_error("bidirectional cost differs from independent Dijkstra");}
   for(int weight:{1,4,32,256}){
    auto candidate=weighted_bidirectional(bidir,nx,ny,start,goal,[&](int v){return penalty[v];},[&](int v){return!blocked[v];},nonpreferred_cost,weight);
    if((d[goal]==inf)!=candidate.empty())throw runtime_error("weighted reachability differs from independent Dijkstra");
    if(!candidate.empty()){
     if(candidate.front()!=start||candidate.back()!=goal)throw runtime_error("weighted endpoints differ");
     int64_t cost=0;set<int>vertices;
     for(size_t j=0;j<candidate.size();++j){
      int w=candidate[j];if(!vertices.insert(w).second)throw runtime_error("weighted path repeats vertex");
      if(!j)continue;int v=candidate[j-1],x=v%nx,y=(v%plane)/nx,l=v/plane,xx=w%nx,yy=(w%plane)/nx,ll=w/plane;
      if(abs(x-xx)+abs(y-yy)+abs(l-ll)!=1||blocked[w]||(l!=ll&&(x+y)%2))throw runtime_error("weighted invalid edge");
      cost+=(l!=ll?3:((l==0&&y==yy)||(l==1&&x==xx)?1:nonpreferred_cost))+penalty[w];
     }
     if(cost<d[goal]||(weight==1&&cost!=d[goal]))throw runtime_error("weighted cost contradicts independent oracle");
     if(weight==1&&candidate!=path)throw runtime_error("weight1 fallback differs from exact search");
    }
    ++weighted_checks;
   }
   if(nonpreferred_cost==2)++bidirectional_checks;else ++directional_bidirectional_checks;
  }
  int resource_checks=resource_oracle_test();
  int heap_checks=weighted_heap_order_test();int escape_checks=endpoint_escape_self_test();int maze_checks=zero_maze_self_test();int pin_checks=pin_access_self_test();
  cout<<"{\"independent_resource_product_graph_checks\":"<<resource_checks<<",\"passed\":true,\"exhaustive_distance_checks\":"<<checks<<",\"exact_cache_and_invalidation_checks\":"<<cache_checks<<",\"exhaustive_segment_grid_checks\":"<<segment_checks<<",\"exhaustive_compressed_branch_checks\":"<<branch_checks<<",\"independent_bidirectional_dijkstra_checks\":"<<bidirectional_checks<<",\"independent_directional_bidirectional_dijkstra_checks\":"<<directional_bidirectional_checks<<",\"independent_weighted_bidirectional_path_checks\":"<<weighted_checks<<",\"independent_weighted_heap_order_checks\":"<<heap_checks<<",\"independent_endpoint_escape_checks\":"<<escape_checks<<",\"independent_zero_maze_checks\":"<<maze_checks<<",\"independent_pin_access_matching_checks\":"<<pin_checks<<"}"<<endl;return 0;
 }
 if(argc<3||argc>31)throw runtime_error("input/output arguments required");
 int ordinary_present_growth=0;
 size_t resource_label_limit=4000000;bool label_option=false,critical_first=false,ordinary_zero=false,ordinary_escape=false,weighted_bidir=false,phase_trace=false;int ordinary_congestion_scale=0,ordinary_search_margin=0,weighted_pair_margin=0,threshold_pattern_rounds=0,ordinary_maze_budget=0;
 int ordinary_refresh=0;int ordinary_coarse_rounds=64;bool coarse_rounds_option=false;bool coarse_refine=false;bool weighted_settle_once=false;bool ordinary_coarse_neighbors=false;bool global_batch=false,ordinary_coarse_zero=false,ordinary_coarse_multicast=false,ordinary_coarse_static=false;int global_snapshot=0;bool ordinary_coarse_access=false;int ordinary_coarse=0;int native_refresh=0,native_maze_budget=0;string native_seed_input;bool native_flexible=false,release_pin_reservations=false,native_batch=false,native_prefix_first=false;string pin_policy="none";bool pin_policy_option=false;
 for(int i=3;i<argc;++i){string option=argv[i];
  if(option.rfind("--ordinary-coarse-rounds=",0)==0){if(coarse_rounds_option)throw runtime_error("duplicate coarse round option");coarse_rounds_option=true;string value=option.substr(25);if(value!="8"&&value!="16"&&value!="32"&&value!="64")throw runtime_error("invalid coarse round limit");ordinary_coarse_rounds=stoi(value);}
  else if(option=="--ordinary-present-growth=4"||option=="--ordinary-present-growth=8"){if(ordinary_present_growth)throw runtime_error("duplicate ordinary present growth");ordinary_present_growth=stoi(option.substr(option.find('=')+1));}
  else if(option=="--ordinary-refresh=8"||option=="--ordinary-refresh=16"){if(ordinary_refresh)throw runtime_error("duplicate ordinary refresh");ordinary_refresh=stoi(option.substr(option.find('=')+1));}
  else if(option=="--ordinary-coarse-refine"){if(coarse_refine)throw runtime_error("duplicate coarse refinement option");coarse_refine=true;}
  else if(option=="--weighted-settle-once"){if(weighted_settle_once)throw runtime_error("duplicate weighted settle option");weighted_settle_once=true;}
  else if(option=="--ordinary-coarse-neighbors"){if(ordinary_coarse_neighbors)throw runtime_error("duplicate coarse neighbor option");ordinary_coarse_neighbors=true;}
  else if(option=="--global-batch-ripup"){if(global_batch)throw runtime_error("duplicate global batch option");global_batch=true;}
  else if(option=="--ordinary-coarse-zero"){if(ordinary_coarse_zero)throw runtime_error("duplicate zero coarse option");ordinary_coarse_zero=true;}
  else if(option=="--ordinary-coarse-multicast"){if(ordinary_coarse_multicast)throw runtime_error("duplicate multicast coarse option");ordinary_coarse_multicast=true;}
  else if(option=="--ordinary-coarse-static"){if(ordinary_coarse_static)throw runtime_error("duplicate static coarse option");ordinary_coarse_static=true;}
  else if(option=="--global-route-snapshot=8"||option=="--global-route-snapshot=16"||option=="--global-route-snapshot=32"||option=="--global-route-snapshot=64"){if(global_snapshot)throw runtime_error("duplicate global snapshot option");global_snapshot=stoi(option.substr(option.find('=')+1));}
  else if(option=="--ordinary-coarse-access"){if(ordinary_coarse_access)throw runtime_error("duplicate coarse access option");ordinary_coarse_access=true;}
  else if(option=="--ordinary-coarse=8"||option=="--ordinary-coarse=16"||option=="--ordinary-coarse=32"){if(ordinary_coarse)throw runtime_error("duplicate ordinary coarse option");ordinary_coarse=stoi(option.substr(option.find('=')+1));}
  else if(option=="--native-prefix-flexible"){if(native_flexible)throw runtime_error("duplicate flexible native prefix option");native_flexible=true;}
  else if(option.rfind("--native-prefix-input=",0)==0){if(!native_seed_input.empty())throw runtime_error("duplicate native prefix input");native_seed_input=option.substr(22);if(native_seed_input.empty())throw runtime_error("empty native prefix input");}
  else if(option=="--release-pin-reservations"){if(release_pin_reservations)throw runtime_error("duplicate pin reservation release option");release_pin_reservations=true;}
  else if(option=="--native-refresh=8"||option=="--native-refresh=16"){if(native_refresh)throw runtime_error("duplicate native refresh option");native_refresh=stoi(option.substr(option.find('=')+1));}
  else if(option=="--native-batch-ripup"){if(native_batch)throw runtime_error("duplicate native batch option");native_batch=true;}
  else if(option=="--native-zero-maze=16384"||option=="--native-zero-maze=65536"){if(native_maze_budget)throw runtime_error("duplicate native zero-maze option");native_maze_budget=stoi(option.substr(option.find('=')+1));}
  else if(option=="--native-prefix-first"){if(native_prefix_first)throw runtime_error("duplicate native-prefix option");native_prefix_first=true;}
  else if(option=="--pin-access=all"||option=="--pin-access=after-native"||option=="--pin-access=none"||option=="--pin-access=ordinary-first"){if(pin_policy_option)throw runtime_error("duplicate pin-access policy");pin_policy_option=true;pin_policy=option.substr(option.find('=')+1);}
  else if(option=="--critical-first"){if(critical_first)throw runtime_error("duplicate constrained-priority option");critical_first=true;}
  else if(option=="--ordinary-zero-pattern"){if(ordinary_zero)throw runtime_error("duplicate zero-pattern option");ordinary_zero=true;}
  else if(option=="--ordinary-endpoint-escape"){if(ordinary_escape)throw runtime_error("duplicate endpoint escape option");ordinary_escape=true;}
  else if(option=="--ordinary-zero-maze=16384"||option=="--ordinary-zero-maze=65536"){if(ordinary_maze_budget)throw runtime_error("duplicate zero-maze option");ordinary_maze_budget=stoi(option.substr(option.find('=')+1));}
  else if(option=="--weighted-bidirectional"){if(weighted_bidir)throw runtime_error("duplicate weighted bidirectional option");weighted_bidir=true;}
  else if(option=="--trace-routing-phases"){if(phase_trace)throw runtime_error("duplicate routing phase trace");phase_trace=true;}
  else if(option=="--ordinary-threshold-pattern-rounds=8"||option=="--ordinary-threshold-pattern-rounds=16"){
   if(threshold_pattern_rounds)throw runtime_error("duplicate threshold pattern phase");threshold_pattern_rounds=stoi(option.substr(option.find('=')+1));
  }
  else if(option=="--weighted-pair-margin=4"||option=="--weighted-pair-margin=16"||option=="--weighted-pair-margin=64"||option=="--weighted-pair-margin=256"){
   if(weighted_pair_margin)throw runtime_error("duplicate weighted pair margin");weighted_pair_margin=stoi(option.substr(option.find('=')+1));
  }
  else if(option=="--ordinary-search-margin=4"||option=="--ordinary-search-margin=16"||option=="--ordinary-search-margin=64"||option=="--ordinary-search-margin=256"){
   if(ordinary_search_margin)throw runtime_error("duplicate ordinary search margin");
   ordinary_search_margin=stoi(option.substr(option.find('=')+1));
  }else if(option=="--ordinary-congestion-scale=16"||option=="--ordinary-congestion-scale=64"||option=="--ordinary-congestion-scale=256"){
   if(ordinary_congestion_scale)throw runtime_error("duplicate ordinary congestion option");
   ordinary_congestion_scale=stoi(option.substr(option.find('=')+1));
  }else if(option=="--resource-labels=4000000"||option=="--resource-labels=8000000"){
   if(label_option)throw runtime_error("duplicate memory-envelope option");label_option=true;
   resource_label_limit=option=="--resource-labels=8000000"?8000000:4000000;
  }else throw runtime_error("invalid search option");}
 ifstream in(argv[1]);int nx,ny,count,seed,rounds;in>>nx>>ny>>count>>seed>>rounds;
 string extra;getline(in,extra);int heuristic_weight=1,locked_count=0,wire_limits_present=0,negotiated_priority=0,defer_access_vias=0,congestion_scale=0,history_product=0,initial_order=0,bidirectional_two_terminal=0,adaptive_heuristic=0,nonpreferred_cost=2,pareto_wire_budget=0;
 if(extra.find_first_not_of(" \t\r")!=string::npos){istringstream options(extra);vector<int>values;int value;while(options>>value)values.push_back(value);if(!options.eof()||values.empty()||values.size()>12)throw runtime_error("invalid search options");heuristic_weight=values[0];if(values.size()>1)locked_count=values[1];if(values.size()>2)wire_limits_present=values[2];if(values.size()>3)negotiated_priority=values[3];if(values.size()>4)defer_access_vias=values[4];if(values.size()>5)congestion_scale=values[5];if(values.size()>6)history_product=values[6];if(values.size()>7)initial_order=values[7];if(values.size()>8)bidirectional_two_terminal=values[8];if(values.size()>9)adaptive_heuristic=values[9];if(values.size()>10)nonpreferred_cost=values[10];if(values.size()>11)pareto_wire_budget=values[11];}
 if((pareto_wire_budget!=0&&pareto_wire_budget!=1)||(pareto_wire_budget&&!defer_access_vias))throw runtime_error("invalid finite-resource search option");
 if(ordinary_present_growth&&(!negotiated_priority||!native_prefix_first||!native_flexible||!coarse_refine||history_product||global_batch))throw runtime_error("unsupported ordinary present growth context");
 if(nonpreferred_cost!=2&&nonpreferred_cost!=8&&nonpreferred_cost!=32)throw runtime_error("invalid nonpreferred search cost");
 if(bidirectional_two_terminal!=0&&bidirectional_two_terminal!=1)throw runtime_error("invalid bidirectional search option");
 if(weighted_bidir&&!bidirectional_two_terminal)throw runtime_error("weighted mode requires bidirectional search");
 if(phase_trace&&!weighted_bidir)throw runtime_error("routing phase trace requires weighted mode");
 if(weighted_pair_margin&&!weighted_bidir)throw runtime_error("weighted pair margin requires weighted mode");
 if(ordinary_maze_budget&&(!ordinary_zero||!weighted_bidir))throw runtime_error("zero-maze requires weighted zero-pattern mode");
 if(ordinary_escape&&(!ordinary_zero||!weighted_bidir))throw runtime_error("endpoint escape requires weighted zero-pattern mode");
 if(threshold_pattern_rounds&&(!weighted_bidir||!ordinary_zero))throw runtime_error("threshold pattern phase requires weighted zero-pattern mode");
 if(initial_order<0||initial_order>3)throw runtime_error("invalid initial net ordering");
 if(history_product!=0&&history_product!=1)throw runtime_error("invalid historical congestion strategy");
 if(adaptive_heuristic!=0&&adaptive_heuristic!=1)throw runtime_error("invalid adaptive search schedule");
 if(congestion_scale<0||congestion_scale>32)throw runtime_error("invalid congestion search scale");
 if(negotiated_priority!=0&&negotiated_priority!=1)throw runtime_error("invalid negotiation strategy");
 if(defer_access_vias!=0&&defer_access_vias!=1)throw runtime_error("invalid access strategy");
 if(heuristic_weight<1||(heuristic_weight>32&&heuristic_weight!=64&&heuristic_weight!=128&&heuristic_weight!=256))throw runtime_error("search weight outside explicit range");
 if(critical_first&&(!negotiated_priority||!defer_access_vias||locked_count<=0))throw runtime_error("constrained-priority option requires deferred negotiated finite source routes");
 if(ordinary_congestion_scale&&(!critical_first||!pareto_wire_budget||!negotiated_priority||!defer_access_vias||congestion_scale!=1||bidirectional_two_terminal))throw runtime_error("ordinary scale requires separate scale1 finite-resource routes and original ordinary search");
 if(ordinary_search_margin&&!ordinary_congestion_scale)throw runtime_error("ordinary search margin requires explicit separate ordinary congestion scale");
 if(ordinary_zero&&(!critical_first||!pareto_wire_budget||!negotiated_priority||!defer_access_vias||!bidirectional_two_terminal||ordinary_congestion_scale||ordinary_search_margin))throw runtime_error("zero-pattern prepass requires original finite-priority bidirectional mode without ordinary cost/window overrides");
 if(native_prefix_first&&(!critical_first||!pareto_wire_budget))throw runtime_error("native-prefix requires original finite-priority mode");
 if(weighted_settle_once&&(!weighted_bidir||!native_flexible||!ordinary_coarse_access))throw runtime_error("weighted settle requires weighted flexible native and coarse access mode");
 if(ordinary_refresh&&(!native_flexible||!coarse_refine||global_batch||ordinary_present_growth))throw runtime_error("ordinary refresh requires flexible guided mode without other batch/growth schedules");
 if(coarse_refine&&(!weighted_settle_once||!ordinary_coarse_access||!ordinary_coarse))throw runtime_error("coarse refinement requires settled weighted coarse access mode");
 if(coarse_rounds_option&&!ordinary_coarse)throw runtime_error("coarse round limit requires coarse candidate mode");
 if(ordinary_coarse_neighbors&&!ordinary_coarse_zero)throw runtime_error("coarse neighbors require free coarse local-access mode");
 if(global_batch&&(!ordinary_coarse_zero||!native_flexible))throw runtime_error("global batch requires free coarse and flexible native mode");
 if(ordinary_coarse_zero&&!ordinary_coarse_multicast)throw runtime_error("zero coarse requires multicast static local-access mode");
 if(ordinary_coarse_multicast&&!ordinary_coarse_static)throw runtime_error("multicast coarse requires static local-access mode");
 if(ordinary_coarse_static&&!ordinary_coarse_access)throw runtime_error("static coarse requires local access mode");
 if(global_snapshot&&!native_flexible)throw runtime_error("global snapshot requires flexible native mode");
 if(ordinary_coarse_access&&!ordinary_coarse)throw runtime_error("coarse access requires explicit coarse grid");
 if(ordinary_coarse&&(!native_flexible||!weighted_bidir||!ordinary_zero))throw runtime_error("ordinary coarse requires flexible native and original weighted ordinary prepass mode");
 if(native_flexible&&(!native_prefix_first||pin_policy!="none"))throw runtime_error("flexible native prefix requires native-first and no proxy reservations");
 if(!native_seed_input.empty()&&!native_flexible)throw runtime_error("native seed requires flexible native prefix");
 if(release_pin_reservations&&(!native_prefix_first||pin_policy!="ordinary-first"))throw runtime_error("pin reservation release requires ordinary-first native-prefix mode");
 if(native_refresh&&(!native_prefix_first||!native_batch))throw runtime_error("native refresh requires staged native batch mode");
 if(native_batch&&!native_prefix_first)throw runtime_error("native batch requires staged native-prefix mode");
 if(native_maze_budget&&!native_prefix_first)throw runtime_error("native zero-maze requires staged native-prefix mode");
 if(pin_policy_option&&!native_prefix_first)throw runtime_error("pin-access policy requires native-prefix mode");
 if(locked_count<0||locked_count>count||(wire_limits_present!=0&&wire_limits_present!=1))throw runtime_error("invalid locked source envelope");
 if(!in||nx<16||ny<16||count<1||int64_t(nx)*ny*2>numeric_limits<int>::max())throw runtime_error("invalid input envelope");
 int plane=nx*ny,size=plane*2;
 auto node=[&](int x,int y,int l){return l*plane+y*nx+x;};
 auto coord=[&](int v){return array<int,3>{v%nx,(v%plane)/nx,v/plane};};
 auto inside=[&](int x,int y){return x>=4&&x<nx-4&&y>=4&&y<ny-4;};
 vector<string>names(count);vector<vector<int>>ends(count);vector<int>fixed(size,-1),wire_limits(count,-1);
 for(int n=0;n<count;++n){int k;in>>names[n]>>k;if(!in||k<2)throw runtime_error("invalid net");
  for(int i=0;i<k;++i){int x,y;in>>x>>y;if(!in||!inside(x,y))throw runtime_error("landing outside grid");
   int v=node(x,y,0);if(fixed[v]!=-1)throw runtime_error("overlapping landing");fixed[v]=n;ends[n].push_back(v);}
  if(wire_limits_present){in>>wire_limits[n];if(!in||wire_limits[n]<-1)throw runtime_error("invalid optimistic wire budget");}}
 uint64_t capacity=uint64_t(nx-8)*(ny-8)*2,lower_bound=0;
 for(auto& net:ends){int xlo=nx,xhi=0,ylo=ny,yhi=0;for(int v:net){auto c=coord(v);xlo=min(xlo,c[0]);xhi=max(xhi,c[0]);ylo=min(ylo,c[1]);yhi=max(yhi,c[1]);}lower_bound+=xhi-xlo+yhi-ylo+1;}
 cout<<"{\"grid_cell_capacity\":"<<capacity<<",\"xy_tree_vertex_lower_bound\":"<<lower_bound<<"}"<<endl;
 if(lower_bound>capacity)throw runtime_error("Proven insufficient grid capacity even before access and vias");
 vector<vector<vector<int>>>access(count),branches(count);
 for(int n=0;n<count;++n)for(int v:ends[n]){
  // Every physical M11 landing remains reserved. Reserving an M12 via
  // stub for every pin before any routing is an optional search choice,
  // not a physical requirement. Let the normal layer/via search find the
  // access when dense arrays make those simultaneous stubs obstructive.
  if(defer_access_vias){access[n].push_back({v});continue;}
  auto c=coord(v);int x=c[0],y=c[1];vector<pair<int,int>>sites;
  if((x+y)%2==0)sites={{x,y}};else sites={{x+1,y},{x-1,y},{x,y+1},{x,y-1}};
  bool found=false;for(auto xy:sites){int xx=xy.first,yy=xy.second;if(!inside(xx,yy))continue;
   vector<int>stub{v};if(xx!=x||yy!=y)stub.push_back(node(xx,yy,0));stub.push_back(node(xx,yy,1));
   bool legal=true;for(int w:stub)if(fixed[w]!=-1&&fixed[w]!=n)legal=false;if(!legal)continue;
   for(int w:stub)fixed[w]=n;access[n].push_back(stub);found=true;break;}
  if(!found)throw runtime_error("no reserved access: "+names[n]);
 }
 vector<uint32_t>usage(size),history(size),marked(size),visited(size);
 if(native_prefix_first&&pin_policy=="ordinary-first"){auto r=reserve_pin_access(nx,ny,locked_count,ends,fixed,usage,seed,string(argv[2])+".pin-access.json",true);cout<<"{\"pin_access_policy\":\"ordinary-first\",\"assigned\":"<<r.assigned<<",\"terminals\":"<<r.terminals<<"}"<<endl;}
 if(native_prefix_first&&pin_policy=="all"){auto r=reserve_pin_access(nx,ny,0,ends,fixed,usage,seed,string(argv[2])+".pin-access.json",true);cout<<"{\"pin_access_policy\":\"all\",\"assigned\":"<<r.assigned<<",\"terminals\":"<<r.terminals<<"}"<<endl;}
 vector<int64_t>distance(size);vector<int>parent(size),wire_distance(size);uint32_t epoch=0,search=0;XYDistanceCache heuristic_cache(plane);
 // Allocate the extra workspace only when requested. The old path and all
 // finite-budget paths retain their original search and memory layout.
 BidirectionalSearch bidir(bidirectional_two_terminal?size:0);WeightedSettleState weighted_settle_state;RoutingCorridor routing_corridor;
 uint64_t bidirectional_branches=0,weighted_bidirectional_branches=0;ResourceSearch resource_search;resource_search.label_limit=resource_label_limit;
 vector<vector<int>>trees(count);vector<int>order(count);iota(order.begin(),order.end(),0);mt19937 rng(seed);shuffle(order.begin(),order.end(),rng);
 if(!native_seed_input.empty()){
  uint64_t vertices=import_native_prefix(native_seed_input,nx,ny,locked_count,names,ends,fixed,wire_limits,branches,trees,usage);
  cout<<"{\"native_seed_prefix_loaded\":true,\"nets\":"<<locked_count<<",\"vertices\":"<<vertices<<"}"<<endl;
 }
 // Optional initial routing schedule, based only on the actual terminal
 // geometry. Preserve the shuffled seed order for ties and always retain
 // the original weak-output priority partition. Mode zero is unchanged.
 if(initial_order){
  vector<int>span(count);for(int n=0;n<count;++n){int xlo=nx,xhi=0,ylo=ny,yhi=0;
   for(int v:ends[n]){auto c=coord(v);xlo=min(xlo,c[0]);xhi=max(xhi,c[0]);ylo=min(ylo,c[1]);yhi=max(yhi,c[1]);}span[n]=xhi-xlo+yhi-ylo;}
  stable_sort(order.begin(),order.end(),[&](int a,int b){
   if(initial_order==1)return span[a]<span[b];
   if(initial_order==2)return span[a]>span[b];
   return ends[a].size()>ends[b].size();});
 }
 stable_sort(order.begin(),order.end(),[&](int a,int b){return(a<locked_count)>(b<locked_count);});
 bool complete=false,native_stage=native_prefix_first;uint64_t previous_conflicts=size;
 NativePrefixLog native_log(native_prefix_first,string(argv[2])+".native-prefix.log");
 for(int iteration=0;iteration<rounds;++iteration){
  // Aggressive early ordering must yield to the original admissible search.
  // Keeping a large fixed weight trapped one regression at a single conflict.
  int search_weight=1+((heuristic_weight-1)>>min(iteration/4,8));
  // Optional ordinary-net cost schedule only. Native finite-resource costs
  // and their physical wire budgets remain unchanged. Cap the multiplier
  // at256; the final route still needs independent zero-conflict/RC gates.
  // Reference principle: VPR pres_fac_mult (VTR command_line_usage docs).
  // This integer schedule is a separate experiment, not a VPR port.
  int64_t ordinary_present=int64_t(8+iteration*4)*(ordinary_present_growth?(int64_t(1)<<min(iteration/ordinary_present_growth,8)):1);
  // Optional search speed schedule: high weight while many conflicts remain,
  // full-cost probes every eighth round, original annealing near convergence.
  // Every returned wire/resource/short/geometry/RC gate remains independent.
  if(adaptive_heuristic&&previous_conflicts>uint64_t(max(1,count/8))&&iteration%8!=7)search_weight=heuristic_weight;
  if(adaptive_heuristic)cout<<"{\"round\":"<<iteration<<",\"adaptive_search_weight\":"<<search_weight<<",\"previous_conflicts\":"<<previous_conflicts<<"}"<<endl;
  if(iteration){vector<int>congestion(count);for(int n=0;n<count;++n)for(int v:trees[n])congestion[n]+=max(0,int(usage[v])-1);
   stable_sort(order.begin(),order.end(),[&](int a,int b){
    if(critical_first&&(a<locked_count)!=(b<locked_count))return(a<locked_count)>(b<locked_count);
    return congestion[a]>congestion[b];});}
  if(critical_first){bool regular=false;int prefix=0;
   for(int n:order){if(n<locked_count){if(regular)throw runtime_error("lost constrained-priority partition");++prefix;}else regular=true;}
   if(prefix!=locked_count)throw runtime_error("incomplete constrained-priority partition");
   cout<<"{\"round\":"<<iteration<<",\"constrained_priority_prefix\":"<<prefix<<",\"priority_partition_verified\":true}"<<endl;
  }
  // Snapshot all dirty native trees BEFORE changing occupancy. Remove them
  // together, so another dirty old path cannot trap the first rerouted net.
  // A newly empty tree must never satisfy the clean-tree skip below.
  vector<unsigned char>batch_removed(count,0);int removed=0;
  // Optional software search experiment. Dirty-first ordering was computed
  // above using actual previous occupancy. Periodically release ALL ordinary
  // trees together so clean old routes cannot permanently reserve a corridor.
  // Native trees, real landing ownership, history and finite budgets remain.
  // Disabled mode executes exactly the old path; no acceptance is inferred.
  if(!native_stage&&ordinary_refresh&&iteration&&iteration%ordinary_refresh==0){
   int clean=0,dirty=0;uint64_t vertices=0;
   for(int n=locked_count;n<count;++n){
    if(trees[n].empty())throw runtime_error("missing ordinary tree before refresh");
    bool conflicted=any_of(trees[n].begin(),trees[n].end(),[&](int v){return usage[v]>1;});
    if(conflicted)++dirty;else ++clean;batch_removed[n]=1;
   }
   for(int n=locked_count;n<count;++n){
    for(int v:trees[n]){if(!usage[v])throw runtime_error("ordinary refresh usage underflow");--usage[v];++vertices;}
    trees[n].clear();branches[n].clear();
   }
   cout<<"{\"round\":"<<iteration<<",\"ordinary_refresh_period\":"<<ordinary_refresh<<",\"ordinary_refresh_clean_trees\":"<<clean<<",\"ordinary_refresh_dirty_trees\":"<<dirty<<",\"ordinary_refresh_removed_vertices\":"<<vertices<<",\"native_trees_retained\":"<<locked_count<<"}"<<endl;
  }
  if(!native_stage&&global_batch&&iteration){
   int native_dirty=0,ordinary_dirty=0;uint64_t removed_vertices=0;
   // Snapshot every dirty upper tree before changing usage. This includes
   // weak-output candidates, so removing old ordinary crossings cannot
   // accidentally classify an originally dirty native tree as clean.
   for(int n=0;n<count;++n){
    if(trees[n].empty())throw runtime_error("missing complete tree before global batch");
    if(any_of(trees[n].begin(),trees[n].end(),[&](int v){return usage[v]>1;})){
     batch_removed[n]=1;if(n<locked_count)++native_dirty;else ++ordinary_dirty;
    }
   }
   for(int n=0;n<count;++n)if(batch_removed[n]){
    for(int v:trees[n]){if(!usage[v])throw runtime_error("global batch usage underflow");--usage[v];++removed_vertices;}
    trees[n].clear();branches[n].clear();
   }
   cout<<"{\"round\":"<<iteration<<",\"global_batch_native_trees\":"<<native_dirty<<",\"global_batch_ordinary_trees\":"<<ordinary_dirty<<",\"global_batch_removed_vertices\":"<<removed_vertices<<"}"<<endl;
  }
  if(native_stage&&native_batch&&iteration){
   for(int n=0;n<locked_count;++n){
    if(trees[n].empty())throw runtime_error("missing native tree before batch");
    if((native_refresh&&iteration%native_refresh==0)||any_of(trees[n].begin(),trees[n].end(),[&](int v){return usage[v]>1;})){batch_removed[n]=1;++removed;}
   }
   for(int n=0;n<locked_count;++n)if(batch_removed[n]){
    for(int v:trees[n]){if(!usage[v])throw runtime_error("batch usage underflow");--usage[v];}
    trees[n].clear();branches[n].clear();
   }
   if(native_refresh)cout<<"{\"round\":"<<iteration<<",\"native_refresh_period\":"<<native_refresh<<",\"native_full_refresh\":"<<(iteration%native_refresh==0?"true":"false")<<",\"removed_trees\":"<<removed<<"}"<<endl;
   cout<<"{\"round\":"<<iteration<<",\"native_batch_removed_trees\":"<<removed<<"}"<<endl;
  }
  int number=0;
  uint64_t ordinary_override_penalty_steps=0;
  uint64_t ordinary_box_branches=0,ordinary_box_pruned_neighbors=0;
  uint64_t zero_pattern_attempts=0,zero_pattern_hits=0,zero_pattern_checks=0;
  uint64_t weighted_window_branches=0;
  uint64_t zero_maze_attempts=0,zero_maze_hits=0,zero_maze_expanded=0;
  uint64_t native_maze_attempts=0,native_maze_hits=0,native_maze_rejected=0,native_maze_expanded=0;
  uint64_t endpoint_escape_attempts=0,endpoint_escape_hits=0,endpoint_escape_checks=0,endpoint_escape_calls=0;
  uint64_t coarse_attempts=0,coarse_hits=0,coarse_expanded=0,coarse_checks=0,coarse_multicast_attempts=0,coarse_multicast_hits=0,coarse_zero_attempts=0,coarse_zero_hits=0;
  uint64_t refinement_attempts=0,refinement_changed=0,refinement_vertices=0,refinement_multicast=0;
  uint64_t threshold_pattern_attempts=0,threshold_pattern_calls=0,threshold_pattern_hits=0,threshold_pattern_checks=0;
  for(int n:order){
   if(native_prefix_first&&((native_stage&&n>=locked_count)||(!native_stage&&n<locked_count&&!native_flexible))){++number;continue;}
   if((native_stage&&!native_seed_input.empty()&&!iteration)||(!native_stage&&native_flexible&&!iteration&&n<locked_count)){++number;continue;}
   bool tracing=phase_trace&&number>=max(0,locked_count-32)&&int64_t(number)<int64_t(locked_count)+128;
   if(tracing&&iteration&&n<locked_count&&!negotiated_priority)tracing=false;
   if(tracing&&iteration&&negotiated_priority&&!batch_removed[n]&&all_of(trees[n].begin(),trees[n].end(),[&](int v){return usage[v]<=1;}))tracing=false;
   if(tracing)cout<<R"({"routing_phase_event":"start","round":)"<<iteration<<R"(,"net":")"<<names[n]<<R"(","phase_routed_before":)"<<number<<R"(,"wire_limited":)"<<(n<locked_count&&wire_limits[n]>=0?"true":"false")<<R"(,"terminal_groups":)"<<access[n].size()<<R"(,"phase_search_weight":)"<<search_weight<<R"(,"monotonic_ns":)"<<chrono::duration_cast<chrono::nanoseconds>(chrono::steady_clock::now().time_since_epoch()).count()<<"}"<<endl;
   if(iteration&&n<locked_count&&!negotiated_priority){++number;continue;}
   // Preserve only currently clean trees. Another net can make a tree
   // congested later; the following round will then rip it up normally.
   if(iteration&&negotiated_priority&&!batch_removed[n]&&all_of(trees[n].begin(),trees[n].end(),[&](int v){return usage[v]<=1;})){++number;continue;}
   for(int v:trees[n]){if(!usage[v])throw runtime_error("usage underflow");--usage[v];}
   ++epoch;if(!epoch)throw runtime_error("tree epoch overflow");vector<int>tree;branches[n].clear();
   auto add=[&](int v){if(marked[v]!=epoch){marked[v]=epoch;tree.push_back(v);}};
   for(int v:access[n][0])add(v);branches[n].push_back(access[n][0]);
   int used_wire_edges=0; // Deferred access starts at the real M11 landing.
   vector<int>todo(access[n].size()-1);iota(todo.begin(),todo.end(),1);
   while(!todo.empty()){
    int xlo=nx,xhi=0,ylo=ny,yhi=0;for(int v:tree){auto c=coord(v);xlo=min(xlo,c[0]);xhi=max(xhi,c[0]);ylo=min(ylo,c[1]);yhi=max(yhi,c[1]);}
    SegmentDistance index;if(tree.size()>64){
     for(auto& branch:branches[n])index.append(branch,coord);
     index.build();}
    heuristic_cache.next_tree();
    auto h=[&](int v){return heuristic_cache.get(v%plane,[&]{auto c=coord(v);return index.segments.empty()?max({xlo-c[0],0,c[0]-xhi})+max({ylo-c[1],0,c[1]-yhi}):index.distance(c[0],c[1]);});};
    auto chosen=min_element(todo.begin(),todo.end(),[&](int a,int b){return h(access[n][a].back())<h(access[n][b].back());});
    int k=*chosen;todo.erase(chosen);int start=access[n][k].back(),goal=-1;
    // Optional ordinary-pair software search domain. Native finite-resource
    // routing is untouched. Widen with rounds and restore full grid at64.
    bool pair_window=weighted_pair_margin&&n>=locked_count&&access[n].size()==2;
    int pair_x0=4,pair_x1=nx-5,pair_y0=4,pair_y1=ny-5;
    if(pair_window){
     int margin=iteration>=64?max(nx,ny):weighted_pair_margin*(1+iteration/4);auto s=coord(start);
     pair_x0=max(4,min(xlo,s[0])-margin);pair_x1=min(nx-5,max(xhi,s[0])+margin);
     pair_y0=max(4,min(ylo,s[1])-margin);pair_y1=min(ny-5,max(yhi,s[1])+margin);++weighted_window_branches;
    }
    auto pair_allowed=[&](int v){if(fixed[v]!=-1&&fixed[v]!=n)return false;if(!pair_window)return true;auto c=coord(v);return c[0]>=pair_x0&&c[0]<=pair_x1&&c[1]>=pair_y0&&c[1]<=pair_y1;};
    vector<int>path;
    if(ordinary_zero&&n>=locked_count){
     ++zero_pattern_attempts;
     path=ordinary_zero_pattern(nx,ny,start,tree,
       [&](int v){return !usage[v]&&pair_allowed(v);},
       [&](int v){return marked[v]==epoch;},zero_pattern_checks);
     if(!path.empty())++zero_pattern_hits;
     if(path.empty()&&ordinary_escape&&access[n].size()==2){
      ++endpoint_escape_attempts;path=ordinary_endpoint_escape(nx,ny,start,tree[0],
       [&](int v){return !usage[v]&&pair_allowed(v);},endpoint_escape_checks,endpoint_escape_calls);
      if(!path.empty())++endpoint_escape_hits;
     }
     if(path.empty()&&ordinary_maze_budget){
      ++zero_maze_attempts;path=ordinary_zero_maze(nx,ny,start,
       [&](int v){return !usage[v]&&pair_allowed(v);},[&](int v){return marked[v]==epoch;},h,
       nonpreferred_cost,ordinary_maze_budget,visited,distance,parent,search,zero_maze_expanded);
      if(!path.empty())++zero_maze_hits;
     }
    }
    if(path.empty()&&threshold_pattern_rounds&&iteration<threshold_pattern_rounds&&n>=locked_count&&access[n].size()==2){
     // Reuse the verified geometric generator with a separate bounded,
     // nonzero congestion predicate. These are NOT zero-occupancy hits.
     // Two calls retain the existing65536 vertex-test budget each. Every
     // final route still requires zero conflicts and original physical gates.
     ++threshold_pattern_attempts;int scale=congestion_scale?congestion_scale:(negotiated_priority?heuristic_weight:1);
     for(int multiplier:{2,4}){
      ++threshold_pattern_calls;__int128 limit=__int128(ordinary_present)*scale*multiplier;
      path=ordinary_zero_pattern(nx,ny,start,tree,[&](int v){
       if(!pair_allowed(v))return false;
       __int128 present=ordinary_present*usage[v],accumulated=int64_t(history[v])*4;
       __int128 penalty=(present+accumulated+(history_product?present*accumulated:0))*scale;
       return penalty<=limit;
      },[&](int v){return marked[v]==epoch;},threshold_pattern_checks);
      if(!path.empty()){++threshold_pattern_hits;break;}
     }
    }
    // Bounded strict-zero candidate before the unchanged native finite
    // search. Reject any candidate beyond the actual remaining wire budget.
    // Empty/capped/over-budget paths always yield to the original solver.
    if(path.empty()&&native_stage&&native_maze_budget&&n<locked_count&&wire_limits[n]>=0){
     ++native_maze_attempts;
     path=ordinary_zero_maze(nx,ny,start,[&](int v){return !usage[v]&&(fixed[v]<0||fixed[v]==n);},
       [&](int v){return marked[v]==epoch;},h,nonpreferred_cost,native_maze_budget,
       visited,distance,parent,search,native_maze_expanded);
     if(!path.empty()){
      int wires=0;for(size_t j=1;j<path.size();++j)wires+=path[j-1]/plane==path[j]/plane;
      if(wires<=wire_limits[n]-used_wire_edges)++native_maze_hits;
      else{++native_maze_rejected;path.clear();}
     }
    }
    if(path.empty()&&ordinary_coarse&&(iteration<ordinary_coarse_rounds||coarse_refine)&&previous_conflicts>uint64_t(max(8,count/8))&&n>=locked_count&&(access[n].size()==2||ordinary_coarse_multicast)){
     ++coarse_attempts;int scale=congestion_scale?congestion_scale:(negotiated_priority?heuristic_weight:1);
     auto penalty=[&](int v){__int128 present=ordinary_present*usage[v],accumulated=int64_t(history[v])*4;
      __int128 cost=(present+accumulated+(history_product?present*accumulated:0))*scale;
      if(cost>numeric_limits<int64_t>::max()/16)throw runtime_error("coarse congestion envelope exceeded");return int64_t(cost);};
     uint64_t phase=ordinary_coarse_static?uint32_t(seed):uint32_t(iteration);
     int ox=(uint64_t(n)*7+phase*3)%ordinary_coarse,oy=(uint64_t(n)*11+phase*5)%ordinary_coarse;oy=(oy&~1)|(ox&1);
     int target=tree[0];bool multicast=access[n].size()!=2;
     if(multicast){
      ++coarse_multicast_attempts;auto s=coord(start);
      auto distance_to_start=[&](int v){auto c=coord(v);return abs(c[0]-s[0])+abs(c[1]-s[1])+abs(c[2]-s[2]);};
      target=*min_element(tree.begin(),tree.end(),[&](int a,int b){return distance_to_start(a)<distance_to_start(b);});
     }
     if(ordinary_coarse_zero){
      ++coarse_zero_attempts;
      path=ordinary_coarse_grid(nx,ny,start,target,ordinary_coarse,ox,oy,min(16,search_weight),nonpreferred_cost,
       [&](int){return int64_t(0);},[&](int v){return !usage[v]&&pair_allowed(v);},coarse_expanded,coarse_checks,65536,ordinary_coarse_access,ordinary_coarse_neighbors);
      if(!path.empty()){
       if(any_of(path.begin(),path.end(),[&](int v){return usage[v]!=0;}))throw runtime_error("zero coarse candidate overlaps occupied vertex");
       ++coarse_zero_hits;
      }
     }
     if(path.empty())path=ordinary_coarse_grid(nx,ny,start,target,ordinary_coarse,ox,oy,min(16,search_weight),nonpreferred_cost,penalty,pair_allowed,coarse_expanded,coarse_checks,65536,ordinary_coarse_access,ordinary_coarse_neighbors);
     if(coarse_refine&&!path.empty()&&any_of(path.begin(),path.end(),[&](int v){return usage[v]!=0;})){
      ++refinement_attempts;if(multicast)++refinement_multicast;auto guide=std::move(path);
      routing_corridor.build(nx,ny,guide,4*(1+iteration/16));refinement_vertices+=routing_corridor.vertices;
      path=settled_weighted_bidirectional(bidir,nx,ny,start,target,penalty,
       [&](int v){return pair_allowed(v)&&routing_corridor.contains(v);},nonpreferred_cost,search_weight,weighted_settle_state);
      // The original connected path is inside the guide, so failure must be
      // visible, never silently accepted as a successful fine route.
      if(path.empty())throw runtime_error("coarse-guided fine search disconnected");
      if(path!=guide)++refinement_changed;
      if(search_weight>1)++weighted_bidirectional_branches;
     }
     if(!path.empty()&&multicast){
      auto first=find_if(path.begin(),path.end(),[&](int v){return marked[v]==epoch;});
      if(first==path.end())throw runtime_error("coarse multicast failed to join actual tree");
      path.erase(first+1,path.end());++coarse_multicast_hits;
     }
     if(!path.empty())++coarse_hits;
    }
    if(path.empty()){
    if(pareto_wire_budget&&n<locked_count&&wire_limits[n]>=0){
     int scale=congestion_scale?congestion_scale:(negotiated_priority?heuristic_weight:1);
     auto penalty=[&](int v){__int128 present=int64_t(8+iteration*4)*usage[v],accumulated=int64_t(history[v])*4;
      __int128 cost=(present+accumulated+(history_product?present*accumulated:0))*scale;
      if(cost>numeric_limits<int64_t>::max()/16)throw runtime_error("finite-resource congestion envelope exceeded");return int64_t(cost);};
     path=resource_search.find(nx,ny,start,wire_limits[n]-used_wire_edges,search_weight,nonpreferred_cost,penalty,
       [&](int v){return fixed[v]==-1||fixed[v]==n;},[&](int v){return marked[v]==epoch;},h);
     if(path.empty())throw runtime_error("disconnected finite-resource tree: "+names[n]);
    }else if(bidirectional_two_terminal&&defer_access_vias&&n>=locked_count&&access[n].size()==2){
     int scale=congestion_scale?congestion_scale:(negotiated_priority?heuristic_weight:1);
     auto penalty=[&](int v){__int128 present=ordinary_present*usage[v],accumulated=int64_t(history[v])*4;
      __int128 cost=(present+accumulated+(history_product?present*accumulated:0))*scale;
      if(cost>numeric_limits<int64_t>::max()/16)throw runtime_error("bidirectional congestion cost exceeds envelope");return int64_t(cost);};
     if(weighted_bidir){path=weighted_settle_once?settled_weighted_bidirectional(bidir,nx,ny,start,tree[0],penalty,pair_allowed,nonpreferred_cost,search_weight,weighted_settle_state):weighted_bidirectional(bidir,nx,ny,start,tree[0],penalty,pair_allowed,nonpreferred_cost,search_weight);if(search_weight>1)++weighted_bidirectional_branches;}
     else path=bidir.find(nx,ny,start,tree[0],penalty,[&](int v){return fixed[v]==-1||fixed[v]==n;},nonpreferred_cost);
     if(path.empty())throw runtime_error((pair_window?"weighted pair window search failed; global feasibility unproved: ":"disconnected bidirectional tree: ")+names[n]);++bidirectional_branches;
    }else{
    ++search;if(!search)throw runtime_error("search epoch overflow");visited[start]=search;distance[start]=0;wire_distance[start]=0;
    int box_x0=4,box_x1=nx-5,box_y0=4,box_y1=ny-5;
    if(ordinary_search_margin&&n>=locked_count){
     // Software search window only. Include the entire existing tree and
     // target; widen every four rounds and restore the full grid at64.
     // Native weak-output finite search and every physical gate are separate.
     int margin=iteration>=64?max(nx,ny):ordinary_search_margin*(1+iteration/4);auto s=coord(start);
     box_x0=max(4,min(xlo,s[0])-margin);box_x1=min(nx-5,max(xhi,s[0])+margin);
     box_y0=max(4,min(ylo,s[1])-margin);box_y1=min(ny-5,max(yhi,s[1])+margin);++ordinary_box_branches;
    }
    priority_queue<Item>q;q.push({int64_t(search_weight)*h(start),0,start});
    while(!q.empty()){
     auto item=q.top();q.pop();int v=item.node;if(visited[v]!=search||distance[v]!=item.cost)continue;
     if(marked[v]==epoch){goal=v;break;}
     auto c=coord(v);int x=c[0],y=c[1],l=c[2];
     array<pair<int,int>,5>next{{{v-1,l==0?1:nonpreferred_cost},{v+1,l==0?1:nonpreferred_cost},{v-nx,l==1?1:nonpreferred_cost},{v+nx,l==1?1:nonpreferred_cost},{node(x,y,1-l),3}}};
     for(int i=0;i<5;++i){if(i==4&&(x+y)%2)continue;int w=next[i].first;auto cc=coord(w);
      if(w<0||w>=size||!inside(cc[0],cc[1])||(fixed[w]!=-1&&fixed[w]!=n))continue;
      if(ordinary_search_margin&&n>=locked_count&&(cc[0]<box_x0||cc[0]>box_x1||cc[1]<box_y0||cc[1]>box_y1)){++ordinary_box_pruned_neighbors;continue;}
      if(n<locked_count&&wire_limits[n]>=0){auto s=coord(start);if(abs(s[0]-cc[0])+abs(s[1]-cc[1])+h(w)>wire_limits[n])continue;}
      int wires=wire_distance[v]+(i!=4);
      // A separate physical-length resource, rather than congestion cost.
      // With deferred access each new branch stops on the existing tree,
      // so its new wire edges add to the already committed tree length.
      // This bounded search is not a completeness/optimality proof; the
      // independent edge-set check remains mandatory after routing.
      if(defer_access_vias&&n<locked_count&&wire_limits[n]>=0&&used_wire_edges+wires+h(w)>wire_limits[n])continue;
      // Independent search parameter. Zero exactly preserves prior ordering;
      // positive overrides never alter physical wire limits or verification.
      int scale=congestion_scale?congestion_scale:(negotiated_priority?heuristic_weight:1);
      if(ordinary_congestion_scale&&n>=locked_count){scale=ordinary_congestion_scale;++ordinary_override_penalty_steps;}
      int64_t present=(n>=locked_count?ordinary_present:int64_t(8+iteration*4))*usage[w],accumulated=int64_t(history[w])*4;
      // Optional search comparison: repeatedly occupied historical conflicts
      // cost more than either alone. No physical limit or edge check changes.
      __int128 penalty=__int128(present)+accumulated;
      if(history_product)penalty+=__int128(present)*accumulated;
      __int128 wide_alt=__int128(item.cost)+next[i].second+__int128(scale)*penalty;
      if(wide_alt>numeric_limits<int64_t>::max()/4)throw runtime_error("search cost exceeds checked numeric envelope");
      int64_t alt=int64_t(wide_alt);
      if(visited[w]!=search||alt<distance[w]||(alt==distance[w]&&wires<wire_distance[w])){visited[w]=search;distance[w]=alt;wire_distance[w]=wires;parent[w]=v;q.push({alt+int64_t(search_weight)*h(w),alt,w});}}
    }
    if(goal<0)throw runtime_error((ordinary_search_margin&&n>=locked_count?"ordinary window search failed; global feasibility unproved: ":"disconnected tree: ")+names[n]);
    path={goal};while(path.back()!=start)path.push_back(parent[path.back()]);reverse(path.begin(),path.end());
    }
    }
    vector<int>branch=access[n][k];branch.pop_back();branch.insert(branch.end(),path.begin(),path.end());
    for(int v:branch)add(v);branches[n].push_back(move(branch));
    if(defer_access_vias&&n<locked_count){
     set<pair<int,int>>edge_set;for(auto& b:branches[n])for(size_t j=1;j<b.size();++j)if(b[j-1]/plane==b[j]/plane)edge_set.insert(minmax(b[j-1],b[j]));
     used_wire_edges=edge_set.size();
    }
   }
   if(n<locked_count){
    set<pair<int,int>>wire_edges;
    for(auto& branch:branches[n])for(size_t i=1;i<branch.size();++i){int v=branch[i-1],w=branch[i];if(v/plane==w/plane)wire_edges.insert(minmax(v,w));}
    if(wire_limits[n]>=0&&wire_edges.size()>size_t(wire_limits[n]))throw runtime_error("Locked-source optimistic wire budget exceeded by this search: "+names[n]);
    if(!negotiated_priority)for(int v:tree){if(fixed[v]!=-1&&fixed[v]!=n)throw runtime_error("Locked path overlaps foreign fixed access");fixed[v]=n;}
   }
   trees[n]=move(tree);for(int v:trees[n])++usage[v];++number;
   if(tracing)cout<<R"({"routing_phase_event":"end","round":)"<<iteration<<R"(,"net":")"<<names[n]<<R"(","phase_routed_after":)"<<number<<R"(,"monotonic_ns":)"<<chrono::duration_cast<chrono::nanoseconds>(chrono::steady_clock::now().time_since_epoch()).count()<<"}"<<endl;
   if(number%100==0)cout<<"{\"round\":"<<iteration<<",\"routed\":"<<number<<",\"total\":"<<count<<"}"<<endl;
  }
  uint64_t conflicts=0,excess=0,occupied=0,vertices=0;for(int v=0;v<size;++v){if(usage[v]){++occupied;vertices+=usage[v];}if(usage[v]>1){++conflicts;excess+=usage[v]-1;history[v]+=usage[v]-1;}}
  if(bidirectional_two_terminal)cout<<"{\"round\":"<<iteration<<",\"bidirectional_branches_cumulative\":"<<bidirectional_branches<<"}"<<endl;
  if(weighted_bidir)cout<<"{\"round\":"<<iteration<<",\"weighted_bidirectional_branches_cumulative\":"<<weighted_bidirectional_branches<<",\"weighted_bidirectional_search_weight\":"<<search_weight<<"}"<<endl;
  if(weighted_pair_margin)cout<<"{\"round\":"<<iteration<<",\"weighted_pair_margin\":"<<weighted_pair_margin<<",\"weighted_window_branches\":"<<weighted_window_branches<<",\"effective_pair_margin\":"<<(iteration>=64?max(nx,ny):weighted_pair_margin*(1+iteration/4))<<"}"<<endl;
  if(native_stage&&native_maze_budget)cout<<"{\"round\":"<<iteration<<",\"native_zero_maze_budget\":"<<native_maze_budget<<",\"native_zero_maze_attempts\":"<<native_maze_attempts<<",\"native_zero_maze_hits\":"<<native_maze_hits<<",\"native_zero_maze_wire_rejected\":"<<native_maze_rejected<<",\"native_zero_maze_expanded\":"<<native_maze_expanded<<"}"<<endl;
  if(ordinary_maze_budget)cout<<"{\"round\":"<<iteration<<",\"ordinary_zero_maze_budget\":"<<ordinary_maze_budget<<",\"zero_maze_attempts\":"<<zero_maze_attempts<<",\"zero_maze_hits\":"<<zero_maze_hits<<",\"zero_maze_expanded\":"<<zero_maze_expanded<<"}"<<endl;
  if(ordinary_escape)cout<<"{\"round\":"<<iteration<<",\"endpoint_escape_attempts\":"<<endpoint_escape_attempts<<",\"endpoint_escape_hits\":"<<endpoint_escape_hits<<",\"endpoint_escape_vertex_checks\":"<<endpoint_escape_checks<<",\"endpoint_escape_core_calls\":"<<endpoint_escape_calls<<"}"<<endl;
  if(threshold_pattern_rounds)cout<<"{\"round\":"<<iteration<<",\"ordinary_threshold_pattern_rounds\":"<<threshold_pattern_rounds<<",\"threshold_pattern_phase_active\":"<<(iteration<threshold_pattern_rounds?"true":"false")<<",\"threshold_pattern_attempts\":"<<threshold_pattern_attempts<<",\"threshold_pattern_calls\":"<<threshold_pattern_calls<<",\"threshold_pattern_hits\":"<<threshold_pattern_hits<<",\"threshold_pattern_vertex_checks\":"<<threshold_pattern_checks<<"}"<<endl;
  if(pareto_wire_budget)cout<<"{\"round\":"<<iteration<<",\"finite_resource_calls\":"<<resource_search.calls<<",\"maximum_resource_labels\":"<<resource_search.maximum_labels<<"}"<<endl;
  if(ordinary_present_growth)cout<<"{\"round\":"<<iteration<<",\"ordinary_present_growth_period\":"<<ordinary_present_growth<<",\"ordinary_present_coefficient\":"<<ordinary_present<<",\"native_present_coefficient\":"<<(8+iteration*4)<<"}"<<endl;
  if(ordinary_congestion_scale)cout<<"{\"round\":"<<iteration<<",\"ordinary_congestion_scale\":"<<ordinary_congestion_scale<<",\"finite_congestion_scale\":"<<congestion_scale<<",\"ordinary_override_penalty_steps\":"<<ordinary_override_penalty_steps<<"}"<<endl;
  if(ordinary_search_margin)cout<<"{\"round\":"<<iteration<<",\"ordinary_search_margin\":"<<ordinary_search_margin<<",\"effective_margin\":"<<(iteration>=64?max(nx,ny):ordinary_search_margin*(1+iteration/4))<<",\"ordinary_box_branches\":"<<ordinary_box_branches<<",\"ordinary_box_pruned_neighbors\":"<<ordinary_box_pruned_neighbors<<"}"<<endl;
  if(weighted_settle_once)cout<<"{\"round\":"<<iteration<<",\"weighted_settle_once\":true,\"weighted_settle_branches\":"<<weighted_settle_state.branches<<",\"weighted_settle_expanded\":"<<weighted_settle_state.expanded<<"}"<<endl;
  if(coarse_refine)cout<<"{\"round\":"<<iteration<<",\"coarse_refinement_attempts\":"<<refinement_attempts<<",\"coarse_refinement_changed\":"<<refinement_changed<<",\"coarse_refinement_multicast\":"<<refinement_multicast<<",\"coarse_refinement_xy_vertices\":"<<refinement_vertices<<",\"coarse_refinement_radius\":"<<4*(1+iteration/16)<<"}"<<endl;
  if(coarse_rounds_option)cout<<"{\"round\":"<<iteration<<",\"coarse_round_limit\":"<<ordinary_coarse_rounds<<",\"coarse_phase_active\":"<<(iteration<ordinary_coarse_rounds?"true":"false")<<",\"coarse_attempts\":"<<coarse_attempts<<"}"<<endl;
  if(ordinary_coarse_neighbors)cout<<"{\"round\":"<<iteration<<",\"coarse_neighbor_tracks\":true,\"coarse_neighbor_attempts\":"<<coarse_attempts<<"}"<<endl;
  if(ordinary_coarse_zero)cout<<"{\"round\":"<<iteration<<",\"coarse_zero_attempts\":"<<coarse_zero_attempts<<",\"coarse_zero_hits\":"<<coarse_zero_hits<<"}"<<endl;
  if(ordinary_coarse_multicast)cout<<"{\"round\":"<<iteration<<",\"coarse_multicast_attempts\":"<<coarse_multicast_attempts<<",\"coarse_multicast_hits\":"<<coarse_multicast_hits<<"}"<<endl;
  if(ordinary_coarse_static)cout<<"{\"round\":"<<iteration<<",\"coarse_static_grid\":true,\"grid_phase\":"<<uint32_t(seed)<<"}"<<endl;
  if(ordinary_coarse_access)cout<<"{\"round\":"<<iteration<<",\"coarse_local_access\":true,\"coarse_settle_once\":true}"<<endl;
  if(ordinary_coarse)cout<<"{\"round\":"<<iteration<<",\"ordinary_coarse_stride\":"<<ordinary_coarse<<",\"coarse_attempts\":"<<coarse_attempts<<",\"coarse_hits\":"<<coarse_hits<<",\"coarse_expanded\":"<<coarse_expanded<<",\"coarse_point_checks\":"<<coarse_checks<<"}"<<endl;
  if(ordinary_zero)cout<<"{\"round\":"<<iteration<<",\"zero_pattern_attempts\":"<<zero_pattern_attempts<<",\"zero_pattern_hits\":"<<zero_pattern_hits<<",\"zero_pattern_fallbacks\":"<<zero_pattern_attempts-zero_pattern_hits<<",\"zero_pattern_point_checks\":"<<zero_pattern_checks<<"}"<<endl;
  cout<<"{\"round\":"<<iteration<<",\"conflict_nodes\":"<<conflicts<<",\"excess_occupancy\":"<<excess<<",\"occupied_cells\":"<<occupied<<",\"summed_tree_vertices\":"<<vertices<<",\"grid_cell_capacity\":"<<capacity<<"}"<<endl;
  if(global_snapshot&&!native_stage&&iteration+1==global_snapshot){
   ofstream diagnostic(string(argv[2])+".global-round-"+to_string(global_snapshot)+".txt");diagnostic<<count<<'\n';
   for(int n=0;n<count;++n){diagnostic<<names[n]<<' '<<branches[n].size()<<'\n';for(auto&branch:branches[n]){
    diagnostic<<branch.size();for(int v:branch){auto c=coord(v);diagnostic<<' '<<c[0]<<' '<<c[1]<<' '<<c[2];}diagnostic<<'\n';}}
   if(!diagnostic)throw runtime_error("cannot write diagnostic global snapshot");diagnostic.close();
   cout<<"{\"round\":"<<iteration<<",\"global_snapshot_round\":"<<global_snapshot<<",\"global_snapshot_nets\":"<<count<<",\"diagnostic_only\":true}"<<endl;
  }
  previous_conflicts=conflicts;
  if(!conflicts&&native_stage){
   // Freeze only a fully disjoint native prefix; full routing still has to
   // converge and pass the original independent gates before any success.
   for(int n=0;n<locked_count;++n){if(trees[n].empty())throw runtime_error("missing native prefix tree");
    for(int v:trees[n]){if(usage[v]!=1||(fixed[v]>=0&&fixed[v]!=n))throw runtime_error("native freeze ownership conflict");if(!native_flexible)fixed[v]=n;}}
   ofstream prefix(string(argv[2])+".native-prefix-paths.txt");prefix<<locked_count<<'\n';
   for(int n=0;n<locked_count;++n){prefix<<names[n]<<' '<<branches[n].size()<<'\n';for(auto&branch:branches[n]){
    prefix<<branch.size();for(int v:branch){auto c=coord(v);prefix<<' '<<c[0]<<' '<<c[1]<<' '<<c[2];}prefix<<'\n';}}
   if(!prefix)throw runtime_error("cannot write frozen native prefix");prefix.close();native_log.release();
   if(native_flexible)cout<<"{\"native_prefix_stage_passed\":true,\"native_rounds\":"<<iteration+1<<",\"frozen_nets\":0,\"warm_started_nets\":"<<locked_count<<"}"<<endl;
   else cout<<"{\"native_prefix_stage_passed\":true,\"native_rounds\":"<<iteration+1<<",\"frozen_nets\":"<<locked_count<<"}"<<endl;
   if(pin_policy=="after-native"){auto r=reserve_pin_access(nx,ny,locked_count,ends,fixed,usage,seed,string(argv[2])+".pin-access.json",false);
    cout<<"{\"pin_access_policy\":\"after-native\",\"assigned\":"<<r.assigned<<",\"terminals\":"<<r.terminals<<"}"<<endl;}
   if(release_pin_reservations){
    // These are search reservations, not fabricated wires. Once the real
    // native paths are frozen, retain those paths and every original M11
    // landing, and let ordinary nets negotiate actual wire occupancy.
    uint64_t cleared=0,landings=0;
    for(int v=0;v<size;++v)if(fixed[v]>=locked_count){fixed[v]=-1;++cleared;}
    for(int n=locked_count;n<count;++n)for(int v:ends[n]){
     if(fixed[v]>=0&&fixed[v]!=n)throw runtime_error("landing lost during reservation release");
     fixed[v]=n;++landings;
    }
    for(int n=0;n<locked_count;++n)for(int v:trees[n])
     if(fixed[v]!=n||usage[v]!=1)throw runtime_error("native freeze changed during reservation release");
    if(cleared<landings)throw runtime_error("invalid released reservation count");
    cout<<"{\"unwired_search_reservations_released\":"<<cleared-landings<<",\"actual_m11_landings_restored\":"<<landings<<",\"frozen_native_paths_unchanged\":true}"<<endl;
   }
   for(int n=locked_count;n<count;++n)for(int v:ends[n]){auto c=coord(v);bool legal=false;
    for(int w:{v-1,v+1,v-nx,v+nx}){if(w<0||w>=plane)continue;auto d=coord(w);if(inside(d[0],d[1])&&(fixed[w]<0||fixed[w]==n))legal=true;}
    if((c[0]+c[1])%2==0&&(fixed[v+plane]<0||fixed[v+plane]==n))legal=true;
    if(!legal)throw runtime_error("frozen native prefix blocks an ordinary terminal; retry required");}
   native_stage=false;fill(history.begin(),history.end(),0);previous_conflicts=size;iteration=-1;continue;
  }
  if(!conflicts){complete=true;break;}
 }
 native_log.release();
 if(!complete)throw runtime_error(native_stage?"native-prefix negotiation did not converge; global feasibility unproved":"negotiation did not converge");
 ofstream out(argv[2]);out<<count<<'\n';
 for(int n=0;n<count;++n){out<<names[n]<<' '<<branches[n].size()<<'\n';
  for(auto& branch:branches[n]){out<<branch.size();for(int v:branch){auto c=coord(v);out<<' '<<c[0]<<' '<<c[1]<<' '<<c[2];}out<<'\n';}}
 if(!out)throw runtime_error("cannot write complete route");return 0;
}catch(const exception&e){cerr<<e.what()<<endl;return 1;}}
