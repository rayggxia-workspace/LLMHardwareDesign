// Optional bounded strict-zero maze prepass for ordinary pair/multi-terminal
// branches. Reuses the original generic search arrays; no new grid workspace.
// An empty result is inconclusive and always yields to the original search.
template<class Allowed,class Goal,class Heuristic>
vector<int> ordinary_zero_maze(int nx,int ny,int start,Allowed allowed,Goal is_goal,
                              Heuristic heuristic,int direction_cost,size_t budget,
                              vector<uint32_t>& visited,vector<int64_t>& distance,
                              vector<int>& parent,uint32_t& epoch,uint64_t& expanded){
 if(!budget||budget>65536)throw runtime_error("invalid zero-maze expansion budget");
 if(direction_cost!=2&&direction_cost!=8&&direction_cost!=32)throw runtime_error("invalid zero-maze direction cost");
 const int plane=nx*ny,size=2*plane;
 if(visited.size()!=size||distance.size()!=size||parent.size()!=size)throw runtime_error("zero-maze workspace size mismatch");
 if(!allowed(start))return{};
 if(!++epoch)throw runtime_error("zero-maze search epoch overflow");
 WeightedFourHeap queue;visited[start]=epoch;distance[start]=0;queue.push({int64_t(8)*heuristic(start),0,start});
 size_t local=0;
 while(!queue.empty()){
  auto item=queue.top();queue.pop();int v=item.node;
  if(visited[v]!=epoch||distance[v]!=item.cost)continue;
  if(is_goal(v)){
   vector<int>path{v};while(path.back()!=start)path.push_back(parent[path.back()]);reverse(path.begin(),path.end());return path;
  }
  if(local==budget)return{};++local;++expanded;
  int x=v%nx,y=(v%plane)/nx,layer=v/plane;
  array<pair<int,int>,5> next{{{v-1,layer==0?1:direction_cost},{v+1,layer==0?1:direction_cost},{v-nx,layer==1?1:direction_cost},{v+nx,layer==1?1:direction_cost},{(1-layer)*plane+y*nx+x,3}}};
  for(int i=0;i<5;++i){
   if(i==4&&(x+y)%2)continue;int w=next[i].first;if(w<0||w>=size)continue;
   int xx=w%nx,yy=(w%plane)/nx;
   if(xx<4||xx>=nx-4||yy<4||yy>=ny-4||!allowed(w))continue;
   int64_t alt=item.cost+next[i].second;
   if(visited[w]!=epoch||alt<distance[w]){
    visited[w]=epoch;distance[w]=alt;parent[w]=v;queue.push({alt+int64_t(8)*heuristic(w),alt,w});
   }
  }
 }
 return{};
}

inline int zero_maze_self_test(){
 const int nx=16,ny=18,plane=nx*ny,size=2*plane;mt19937 random(828);int checks=0;
 vector<uint32_t>visited(size);vector<int64_t>distance(size);vector<int>parent(size);uint32_t epoch=0;
 for(int trial=0;trial<200;++trial){
  vector<unsigned char> blocked(size),goal(size);vector<int> targets;
  if(trial%4)for(auto& v:blocked)v=random()%4==0;
  int start=(5+random()%6)+(5+random()%8)*nx;
  for(int j=0;j<2;++j){int v=(5+random()%6)+(5+random()%8)*nx+(random()%2)*plane;targets.push_back(v);goal[v]=1;blocked[v]=0;}
  blocked[start]=trial==0;
  auto allowed=[&](int v){return !blocked[v];};auto is_goal=[&](int v){return bool(goal[v]);};
  auto heuristic=[&](int v){int x=v%nx,y=(v%plane)/nx,best=size;for(int t:targets)best=min(best,abs(x-t%nx)+abs(y-(t%plane)/nx));return best;};
  // Independent breadth-first reachability on the exact two-layer graph.
  vector<unsigned char> seen(size);vector<int> todo;if(!blocked[start]){seen[start]=1;todo.push_back(start);}bool reachable=false;
  for(size_t j=0;j<todo.size();++j){int v=todo[j],x=v%nx,y=(v%plane)/nx,l=v/plane;if(goal[v])reachable=true;
   for(int w:array<int,5>{v-1,v+1,v-nx,v+nx,(1-l)*plane+y*nx+x}){
    if(w<0||w>=size)continue;int xx=w%nx,yy=(w%plane)/nx,ll=w/plane;
    if(xx<4||xx>=nx-4||yy<4||yy>=ny-4||blocked[w]||seen[w])continue;
    if(ll!=l&&(x+y)%2)continue;seen[w]=1;todo.push_back(w);
   }
  }
  for(size_t budget:{1,8,64,16384}){
   uint64_t expanded=0;auto path=ordinary_zero_maze(nx,ny,start,allowed,is_goal,heuristic,2,budget,visited,distance,parent,epoch,expanded);
   if(expanded>budget)throw runtime_error("zero-maze expansion budget exceeded");
   if(expanded<budget&&(!path.empty())!=reachable)throw runtime_error("zero-maze completed tiny-grid BFS mismatch");
   if(trial&&trial%4==0&&budget==16384&&path.empty())throw runtime_error("zero-maze open grid failed");
   if(!path.empty()){
    if(!reachable||path.front()!=start||!goal[path.back()])throw runtime_error("zero-maze incorrect endpoint/reachability");
    for(size_t j=0;j<path.size();++j){int v=path[j],x=v%nx,y=(v%plane)/nx,l=v/plane;
     if(x<4||x>=nx-4||y<4||y>=ny-4||blocked[v])throw runtime_error("zero-maze blocked vertex");
     if(!j)continue;int w=path[j-1],xx=w%nx,yy=(w%plane)/nx,ll=w/plane;
     if(l==ll){if(abs(x-xx)+abs(y-yy)!=1)throw runtime_error("zero-maze nonunit edge");}
     else if(x!=xx||y!=yy||(x+y)%2)throw runtime_error("zero-maze illegal via");
    }
   }++checks;
  }
 }
 return checks;
}
