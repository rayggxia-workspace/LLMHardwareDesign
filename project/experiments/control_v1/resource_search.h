// Per-branch finite-wire search. Cost and wire length are separate resources.
// Immutable parent labels prevent later node relaxations changing a returned
// path's length. This is not a globally optimal multi-terminal tree solver.
#include <unordered_map>
struct ResourceSearch {
 struct Label {int node,wire,parent,next;int64_t cost;bool active;};
 uint64_t calls=0,maximum_labels=0;
 template<class Penalty,class Allowed,class Goal,class Heuristic>
 vector<int> find(int nx,int ny,int start,int budget,int weight,int nonpreferred,
                  Penalty penalty,Allowed allowed,Goal goal,Heuristic h){
  ++calls;if(budget<0||h(start)>budget)return{};
  int plane=nx*ny,size=2*plane;vector<Label>labels;unordered_map<int,int>head;
  priority_queue<Item>q;
  auto insert=[&](int node,int wire,int parent,int64_t cost){
   auto found=head.find(node);int first=found==head.end()?-1:found->second;
   for(int id=first;id>=0;id=labels[id].next){auto& old=labels[id];
    if(old.active&&old.wire<=wire&&old.cost<=cost)return;}
   for(int id=first;id>=0;id=labels[id].next){auto& old=labels[id];
    if(old.active&&wire<=old.wire&&cost<=old.cost)old.active=false;}
   if(labels.size()>=4000000)throw runtime_error("finite-resource search label memory envelope exhausted");
   int id=labels.size();labels.push_back({node,wire,parent,first,cost,true});head[node]=id;
   q.push({cost+int64_t(weight)*h(node),cost,id});
  };
  insert(start,0,-1,0);
  while(!q.empty()){
   int id=q.top().node;q.pop();auto label=labels[id];if(!label.active)continue;
   int v=label.node,x=v%nx,y=(v%plane)/nx,l=v/plane;
   if(goal(v)){
    maximum_labels=max(maximum_labels,uint64_t(labels.size()));vector<int>path;
    for(int p=id;p>=0;p=labels[p].parent)path.push_back(labels[p].node);
    reverse(path.begin(),path.end());return path;
   }
   array<pair<int,int>,5>next{{{v-1,l==0?1:nonpreferred},{v+1,l==0?1:nonpreferred},
      {v-nx,l==1?1:nonpreferred},{v+nx,l==1?1:nonpreferred},{(1-l)*plane+y*nx+x,3}}};
   for(int i=0;i<5;++i){
    if(i==4&&(x+y)%2)continue;int w=next[i].first;
    if(w<0||w>=size)continue;int xx=w%nx,yy=(w%plane)/nx,ll=w/plane;
    if(xx<4||xx>=nx-4||yy<4||yy>=ny-4||abs(x-xx)+abs(y-yy)+abs(l-ll)!=1||!allowed(w))continue;
    int wire=label.wire+(i!=4);if(wire+h(w)>budget)continue;
    __int128 cost=__int128(label.cost)+next[i].second+penalty(w);
    if(cost>numeric_limits<int64_t>::max()/4)throw runtime_error("finite-resource search cost overflow");
    insert(w,wire,id,int64_t(cost));
   }
  }
  maximum_labels=max(maximum_labels,uint64_t(labels.size()));return{};
 }
};

// A separate full (vertex,wire) product graph is the oracle. No dominance
// pruning, heuristic, immutable-label machinery or search code is reused.
inline int resource_oracle_test(){
 mt19937 random(162400);int checks=0;const int64_t inf=numeric_limits<int64_t>::max()/4;
 for(int trial=0;trial<120;++trial){
  int nx=16,ny=16,plane=nx*ny,size=2*plane,budget=random()%36,nonpreferred=array<int,3>{2,8,32}[trial%3];
  vector<int>blocked(size),penalty(size);for(int v=0;v<size;++v){blocked[v]=random()%17==0;penalty[v]=random()%41;}
  int start=(4+random()%8)*nx+4+random()%8,goal=(4+random()%8)*nx+4+random()%8;blocked[start]=blocked[goal]=0;
  auto h=[&](int v){return abs(v%nx-goal%nx)+abs((v%plane)/nx-(goal%plane)/nx);};
  ResourceSearch search;auto path=search.find(nx,ny,start,budget,1,nonpreferred,[&](int v){return penalty[v];},[&](int v){return!blocked[v];},[&](int v){return v==goal;},h);
  vector<int64_t>distance(size*(budget+1),inf);priority_queue<Item>q;distance[start]=0;q.push({0,0,start});int64_t best=inf;
  while(!q.empty()){
   auto item=q.top();q.pop();int state=item.node,v=state%size,wire=state/size;
   if(item.cost!=distance[state])continue;if(v==goal){best=item.cost;break;}
   int x=v%nx,y=(v%plane)/nx,l=v/plane;
   for(int delta:array<int,5>{-1,1,-nx,nx,(1-2*l)*plane}){
    int w=v+delta;if(w<0||w>=size)continue;int xx=w%nx,yy=(w%plane)/nx,ll=w/plane;
    if(xx<4||xx>=nx-4||yy<4||yy>=ny-4||blocked[w]||abs(x-xx)+abs(y-yy)+abs(l-ll)!=1||(l!=ll&&(x+y)%2))continue;
    int next_wire=wire+(l==ll);if(next_wire>budget)continue;
    int base=l!=ll?3:((l==0&&y==yy)||(l==1&&x==xx)?1:nonpreferred);
    int next=next_wire*size+w;int64_t cost=item.cost+base+penalty[w];
    if(cost<distance[next]){distance[next]=cost;q.push({cost,cost,next});}
   }
  }
  if(path.empty()!=(best==inf))throw runtime_error("finite-resource reachability differs from independent full-state oracle");
  if(!path.empty()){
   if(path.front()!=start||path.back()!=goal)throw runtime_error("finite-resource endpoints differ");
   int wire=0;int64_t cost=0;
   for(size_t j=1;j<path.size();++j){int v=path[j-1],w=path[j],x=v%nx,y=(v%plane)/nx,l=v/plane,xx=w%nx,yy=(w%plane)/nx,ll=w/plane;
    if(abs(x-xx)+abs(y-yy)+abs(l-ll)!=1||blocked[w]||(l!=ll&&(x+y)%2))throw runtime_error("finite-resource invalid returned edge");
    wire+=l==ll;cost+=(l!=ll?3:((l==0&&y==yy)||(l==1&&x==xx)?1:nonpreferred))+penalty[w];}
   if(wire>budget||cost!=best)throw runtime_error("finite-resource returned length/cost differs from independent oracle");
  }
  ++checks;
 }
 return checks;
}
