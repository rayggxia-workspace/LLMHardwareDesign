// Multi-terminal negotiated M11/M12 router. Independent Python verification
// checks the returned edges, all landings and global occupancy before use.
#include <algorithm>
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
 vector<int>find(int nx,int ny,int start,int goal,Cost penalty,Allowed allowed){
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
   array<pair<int,int>,5>next{{{v-1,l==0?1:2},{v+1,l==0?1:2},{v-nx,l==1?1:2},{v+nx,l==1?1:2},{(1-l)*plane+y*nx+x,3}}};
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
  int bidirectional_checks=0;
  for(int t=0;t<100;++t){
   int nx=24,ny=26,plane=nx*ny,size=plane*2;BidirectionalSearch bidir(size);
   vector<int>blocked(size),penalty(size);for(int v=0;v<size;++v){blocked[v]=random()%23==0;penalty[v]=random()%41;}
   int start=(5+random()%14)*nx+5+random()%12,goal=(5+random()%14)*nx+5+random()%12;blocked[start]=blocked[goal]=0;
   auto path=bidir.find(nx,ny,start,goal,[&](int v){return penalty[v];},[&](int v){return!blocked[v];});
   const int64_t inf=numeric_limits<int64_t>::max()/4;vector<int64_t>d(size,inf);d[start]=0;priority_queue<Item>q;q.push({0,0,start});
   while(!q.empty()){auto item=q.top();q.pop();int v=item.node;if(d[v]!=item.cost)continue;int x=v%nx,y=(v%plane)/nx,l=v/plane;
    if(v==goal)break;
    for(auto delta:array<int,5>{-1,1,-nx,nx,(1-2*l)*plane}){int w=v+delta;if(w<0||w>=size)continue;int xx=w%nx,yy=(w%plane)/nx,ll=w/plane;
     if(xx<4||xx>=nx-4||yy<4||yy>=ny-4||blocked[w])continue;
     if(abs(x-xx)+abs(y-yy)+abs(l-ll)!=1||(l!=ll&&(x+y)%2))continue;
     int base=l!=ll?3:((l==0&&y==yy)||(l==1&&x==xx)?1:2);int64_t alt=item.cost+base+penalty[w];
     if(alt<d[w]){d[w]=alt;q.push({alt,alt,w});}}
   }
   if((d[goal]==inf)!=path.empty())throw runtime_error("bidirectional reachability differs from independent Dijkstra");
   if(!path.empty()){int64_t cost=0;if(path.front()!=start||path.back()!=goal)throw runtime_error("bidirectional endpoints differ");
    for(size_t j=1;j<path.size();++j){int v=path[j-1],w=path[j],x=v%nx,y=(v%plane)/nx,l=v/plane,xx=w%nx,yy=(w%plane)/nx,ll=w/plane;
     if(abs(x-xx)+abs(y-yy)+abs(l-ll)!=1||blocked[w]||(l!=ll&&(x+y)%2))throw runtime_error("bidirectional invalid edge");
     cost+=(l!=ll?3:((l==0&&y==yy)||(l==1&&x==xx)?1:2))+penalty[w];}
    if(cost!=d[goal])throw runtime_error("bidirectional cost differs from independent Dijkstra");}
   ++bidirectional_checks;
  }
  int resource_checks=resource_oracle_test();
  cout<<"{\"independent_resource_product_graph_checks\":"<<resource_checks<<",\"passed\":true,\"exhaustive_distance_checks\":"<<checks<<",\"exact_cache_and_invalidation_checks\":"<<cache_checks<<",\"exhaustive_segment_grid_checks\":"<<segment_checks<<",\"exhaustive_compressed_branch_checks\":"<<branch_checks<<",\"independent_bidirectional_dijkstra_checks\":"<<bidirectional_checks<<"}"<<endl;return 0;
 }
 if(argc<3||argc>7)throw runtime_error("input/output arguments required");
 size_t resource_label_limit=4000000;bool label_option=false,critical_first=false,ordinary_zero=false;int ordinary_congestion_scale=0,ordinary_search_margin=0;
 for(int i=3;i<argc;++i){string option=argv[i];
  if(option=="--critical-first"){if(critical_first)throw runtime_error("duplicate constrained-priority option");critical_first=true;}
  else if(option=="--ordinary-zero-pattern"){if(ordinary_zero)throw runtime_error("duplicate zero-pattern option");ordinary_zero=true;}
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
 if(nonpreferred_cost!=2&&nonpreferred_cost!=8&&nonpreferred_cost!=32)throw runtime_error("invalid nonpreferred search cost");
 if(nonpreferred_cost!=2&&bidirectional_two_terminal)throw runtime_error("directional cost requires original unidirectional search");
 if(bidirectional_two_terminal!=0&&bidirectional_two_terminal!=1)throw runtime_error("invalid bidirectional search option");
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
 vector<int64_t>distance(size);vector<int>parent(size),wire_distance(size);uint32_t epoch=0,search=0;XYDistanceCache heuristic_cache(plane);
 // Allocate the extra workspace only when requested. The old path and all
 // finite-budget paths retain their original search and memory layout.
 BidirectionalSearch bidir(bidirectional_two_terminal?size:0);
 uint64_t bidirectional_branches=0;ResourceSearch resource_search;resource_search.label_limit=resource_label_limit;
 vector<vector<int>>trees(count);vector<int>order(count);iota(order.begin(),order.end(),0);mt19937 rng(seed);shuffle(order.begin(),order.end(),rng);
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
 bool complete=false;uint64_t previous_conflicts=size;
 for(int iteration=0;iteration<rounds;++iteration){
  // Aggressive early ordering must yield to the original admissible search.
  // Keeping a large fixed weight trapped one regression at a single conflict.
  int search_weight=1+((heuristic_weight-1)>>min(iteration/4,8));
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
  int number=0;
  uint64_t ordinary_override_penalty_steps=0;
  uint64_t ordinary_box_branches=0,ordinary_box_pruned_neighbors=0;
  uint64_t zero_pattern_attempts=0,zero_pattern_hits=0,zero_pattern_checks=0;
  for(int n:order){
   if(iteration&&n<locked_count&&!negotiated_priority){++number;continue;}
   // Preserve only currently clean trees. Another net can make a tree
   // congested later; the following round will then rip it up normally.
   if(iteration&&negotiated_priority&&all_of(trees[n].begin(),trees[n].end(),[&](int v){return usage[v]<=1;})){++number;continue;}
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
    vector<int>path;
    if(ordinary_zero&&n>=locked_count){
     ++zero_pattern_attempts;
     path=ordinary_zero_pattern(nx,ny,start,tree,
       [&](int v){return !usage[v]&&(fixed[v]==-1||fixed[v]==n);},
       [&](int v){return marked[v]==epoch;},zero_pattern_checks);
     if(!path.empty())++zero_pattern_hits;
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
     auto penalty=[&](int v){__int128 present=int64_t(8+iteration*4)*usage[v],accumulated=int64_t(history[v])*4;
      __int128 cost=(present+accumulated+(history_product?present*accumulated:0))*scale;
      if(cost>numeric_limits<int64_t>::max()/16)throw runtime_error("bidirectional congestion cost exceeds envelope");return int64_t(cost);};
     path=bidir.find(nx,ny,start,tree[0],penalty,[&](int v){return fixed[v]==-1||fixed[v]==n;});
     if(path.empty())throw runtime_error("disconnected bidirectional tree: "+names[n]);++bidirectional_branches;
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
      int64_t present=int64_t(8+iteration*4)*usage[w],accumulated=int64_t(history[w])*4;
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
   if(number%100==0)cout<<"{\"round\":"<<iteration<<",\"routed\":"<<number<<",\"total\":"<<count<<"}"<<endl;
  }
  uint64_t conflicts=0,excess=0,occupied=0,vertices=0;for(int v=0;v<size;++v){if(usage[v]){++occupied;vertices+=usage[v];}if(usage[v]>1){++conflicts;excess+=usage[v]-1;history[v]+=usage[v]-1;}}
  if(bidirectional_two_terminal)cout<<"{\"round\":"<<iteration<<",\"bidirectional_branches_cumulative\":"<<bidirectional_branches<<"}"<<endl;
  if(pareto_wire_budget)cout<<"{\"round\":"<<iteration<<",\"finite_resource_calls\":"<<resource_search.calls<<",\"maximum_resource_labels\":"<<resource_search.maximum_labels<<"}"<<endl;
  if(ordinary_congestion_scale)cout<<"{\"round\":"<<iteration<<",\"ordinary_congestion_scale\":"<<ordinary_congestion_scale<<",\"finite_congestion_scale\":"<<congestion_scale<<",\"ordinary_override_penalty_steps\":"<<ordinary_override_penalty_steps<<"}"<<endl;
  if(ordinary_search_margin)cout<<"{\"round\":"<<iteration<<",\"ordinary_search_margin\":"<<ordinary_search_margin<<",\"effective_margin\":"<<(iteration>=64?max(nx,ny):ordinary_search_margin*(1+iteration/4))<<",\"ordinary_box_branches\":"<<ordinary_box_branches<<",\"ordinary_box_pruned_neighbors\":"<<ordinary_box_pruned_neighbors<<"}"<<endl;
  if(ordinary_zero)cout<<"{\"round\":"<<iteration<<",\"zero_pattern_attempts\":"<<zero_pattern_attempts<<",\"zero_pattern_hits\":"<<zero_pattern_hits<<",\"zero_pattern_fallbacks\":"<<zero_pattern_attempts-zero_pattern_hits<<",\"zero_pattern_point_checks\":"<<zero_pattern_checks<<"}"<<endl;
  cout<<"{\"round\":"<<iteration<<",\"conflict_nodes\":"<<conflicts<<",\"excess_occupancy\":"<<excess<<",\"occupied_cells\":"<<occupied<<",\"summed_tree_vertices\":"<<vertices<<",\"grid_cell_capacity\":"<<capacity<<"}"<<endl;
  previous_conflicts=conflicts;
  if(!conflicts){complete=true;break;}
 }
 if(!complete)throw runtime_error("negotiation did not converge");
 ofstream out(argv[2]);out<<count<<'\n';
 for(int n=0;n<count;++n){out<<names[n]<<' '<<branches[n].size()<<'\n';
  for(auto& branch:branches[n]){out<<branch.size();for(int v:branch){auto c=coord(v);out<<' '<<c[0]<<' '<<c[1]<<' '<<c[2];}out<<'\n';}}
 if(!out)throw runtime_error("cannot write complete route");return 0;
}catch(const exception&e){cerr<<e.what()<<endl;return 1;}}
