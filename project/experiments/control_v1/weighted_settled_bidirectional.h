#pragma once

// Optional ordinary weighted search only. Each side expands a vertex once;
// this changes candidate paths and makes no shortest-path guarantee.
// Software scratch is allocated lazily, never hardware state or route evidence.
struct WeightedSettleState {
 std::vector<uint32_t> closed_f,closed_b;
 const void* owner=nullptr;uint32_t last_epoch=0;
 uint64_t branches=0,expanded=0;
 void prepare(size_t size,const void* workspace,uint32_t epoch){
  if(closed_f.size()!=size||owner!=workspace||epoch<=last_epoch){
   closed_f.assign(size,0);closed_b.assign(size,0);
  }
  owner=workspace;last_epoch=epoch;
 }
};

template<class Workspace,class Cost,class Allowed>
std::vector<int> settled_weighted_bidirectional(Workspace& work,int nx,int ny,int start,int goal,
                                      Cost penalty,Allowed allowed,int direction_cost,int weight,WeightedSettleState& state){
 if(weight<1||weight>256)throw std::runtime_error("invalid weighted bidirectional weight");
 if(direction_cost!=2&&direction_cost!=8&&direction_cost!=32)throw std::runtime_error("invalid weighted direction cost");
 if(weight==1)return work.find(nx,ny,start,goal,penalty,allowed,direction_cost);
 const int plane=nx*ny,size=2*plane;const int64_t inf=std::numeric_limits<int64_t>::max()/4;
 if(!++work.epoch)throw std::runtime_error("weighted bidirectional epoch overflow");
 const auto epoch=work.epoch;state.prepare(size,&work,epoch);++state.branches;
 auto coord=[&](int v){return std::array<int,3>{v%nx,(v%plane)/nx,v/plane};};
 auto distance=[&](int a,int b){auto x=coord(a),y=coord(b);return abs(x[0]-y[0])+abs(x[1]-y[1]);};
 WeightedFourHeap qf,qb;qf.push({int64_t(weight)*distance(start,goal),0,start});qb.push({int64_t(weight)*distance(goal,start),0,goal});
 work.vf[start]=work.vb[goal]=epoch;work.df[start]=work.db[goal]=0;
 int meeting=start==goal?start:-1;bool tie_reverse=false;
 while(meeting<0){
  while(!qf.empty()&&(work.vf[qf.top().node]!=epoch||work.df[qf.top().node]!=qf.top().cost||state.closed_f[qf.top().node]==epoch))qf.pop();
  while(!qb.empty()&&(work.vb[qb.top().node]!=epoch||work.db[qb.top().node]!=qb.top().cost||state.closed_b[qb.top().node]==epoch))qb.pop();
  if(qf.empty()||qb.empty())break;
  bool reverse=qb.top().priority<qf.top().priority;
  if(qb.top().priority==qf.top().priority){reverse=tie_reverse;tie_reverse=!tie_reverse;}
  auto& queue=reverse?qb:qf;auto& dist=reverse?work.db:work.df;
  auto& seen=reverse?work.vb:work.vf;auto& parent=reverse?work.pb:work.pf;auto& closed=reverse?state.closed_b:state.closed_f;
  auto item=queue.top();queue.pop();int v=item.node;closed[v]=epoch;++state.expanded;auto c=coord(v);int x=c[0],y=c[1],layer=c[2];
  std::array<std::pair<int,int>,5>next{{{v-1,layer==0?1:direction_cost},{v+1,layer==0?1:direction_cost},{v-nx,layer==1?1:direction_cost},{v+nx,layer==1?1:direction_cost},{(1-layer)*plane+y*nx+x,3}}};
  for(int i=0;i<5;++i){
   if(i==4&&(x+y)%2)continue;int w=next[i].first;if(w<0||w>=size)continue;auto p=coord(w);
   if(p[0]<4||p[0]>=nx-4||p[1]<4||p[1]>=ny-4||!allowed(w)||closed[w]==epoch)continue;
   // Reverse traversal charges the original edge destination, as exact mode.
   __int128 alt=__int128(item.cost)+next[i].second+penalty(reverse?v:w);
   __int128 score=alt+int64_t(weight)*distance(w,reverse?start:goal);
   if(alt<0||score>=inf)throw std::runtime_error("weighted bidirectional cost exceeds envelope");
   if(seen[w]!=epoch||alt<dist[w]){
    seen[w]=epoch;dist[w]=int64_t(alt);parent[w]=v;queue.push({int64_t(score),int64_t(alt),w});
    if(work.vf[w]==epoch&&work.vb[w]==epoch){meeting=w;break;}
   }
  }
 }
 if(meeting<0)return{};
 std::vector<int>path{meeting};while(path.back()!=start)path.push_back(work.pf[path.back()]);std::reverse(path.begin(),path.end());
 for(int v=meeting;v!=goal;){v=work.pb[v];path.push_back(v);}return path;
}
