#pragma once

// Same fully ordered Item keys as std::priority_queue; four children reduce
// sift depth in the profiled ordinary-pair hot loop. No routing keys change.
struct WeightedFourHeap {
 std::vector<Item> items;
 bool empty()const{return items.empty();}
 size_t size()const{return items.size();}
 const Item& top()const{return items.front();}
 void push(Item value){
  size_t position=items.size();items.push_back(value);
  while(position){size_t parent=(position-1)/4;if(!(items[parent]<value))break;items[position]=items[parent];position=parent;}
  items[position]=value;
 }
 void pop(){
  Item value=items.back();items.pop_back();if(items.empty())return;size_t position=0;
  for(;;){size_t first=position*4+1;if(first>=items.size())break;size_t best=first;
   for(size_t child=first+1;child<std::min(first+4,items.size());++child)if(items[best]<items[child])best=child;
   if(!(value<items[best]))break;items[position]=items[best];position=best;
  }items[position]=value;
 }
};

inline int weighted_heap_order_test(){
 WeightedFourHeap actual;std::priority_queue<Item>expected;std::mt19937 random(776);int checks=0;
 auto verify=[&](){if(actual.size()!=expected.size())throw std::runtime_error("weighted heap size mismatch");
  if(!expected.empty()){auto a=actual.top(),e=expected.top();if(a.priority!=e.priority||a.cost!=e.cost||a.node!=e.node)throw std::runtime_error("weighted heap ordering mismatch");}++checks;};
 std::vector<Item>extremes{{std::numeric_limits<int64_t>::min(),std::numeric_limits<int64_t>::max(),0},
  {std::numeric_limits<int64_t>::max(),std::numeric_limits<int64_t>::min(),1},{0,0,0},{0,0,0},{0,1,0},{0,1,1}};
 for(auto item:extremes){actual.push(item);expected.push(item);verify();}
 for(int i=0;i<100000;++i){
  if(expected.empty()||random()%3){Item item{int64_t(random()%101)-50,int64_t(random()%101)-50,int(random()%101)};actual.push(item);expected.push(item);}
  else{verify();actual.pop();expected.pop();}verify();
 }
 while(!expected.empty()){verify();actual.pop();expected.pop();}verify();return checks;
}

// Optional first-meeting weighted search for ordinary two-terminal nets.
// Reuses the exact search workspace. This does not claim shortest paths.
// Weight1 dispatches to the unchanged exact balanced-potential search.
template<class Workspace,class Cost,class Allowed>
std::vector<int> weighted_bidirectional(Workspace& work,int nx,int ny,int start,int goal,
                                      Cost penalty,Allowed allowed,int direction_cost,int weight){
 if(weight<1||weight>256)throw std::runtime_error("invalid weighted bidirectional weight");
 if(direction_cost!=2&&direction_cost!=8&&direction_cost!=32)throw std::runtime_error("invalid weighted direction cost");
 if(weight==1)return work.find(nx,ny,start,goal,penalty,allowed,direction_cost);
 const int plane=nx*ny,size=2*plane;const int64_t inf=std::numeric_limits<int64_t>::max()/4;
 if(!++work.epoch)throw std::runtime_error("weighted bidirectional epoch overflow");
 const auto epoch=work.epoch;
 auto coord=[&](int v){return std::array<int,3>{v%nx,(v%plane)/nx,v/plane};};
 auto distance=[&](int a,int b){auto x=coord(a),y=coord(b);return abs(x[0]-y[0])+abs(x[1]-y[1]);};
 WeightedFourHeap qf,qb;qf.push({int64_t(weight)*distance(start,goal),0,start});qb.push({int64_t(weight)*distance(goal,start),0,goal});
 work.vf[start]=work.vb[goal]=epoch;work.df[start]=work.db[goal]=0;
 int meeting=start==goal?start:-1;bool tie_reverse=false;
 while(meeting<0){
  while(!qf.empty()&&(work.vf[qf.top().node]!=epoch||work.df[qf.top().node]!=qf.top().cost))qf.pop();
  while(!qb.empty()&&(work.vb[qb.top().node]!=epoch||work.db[qb.top().node]!=qb.top().cost))qb.pop();
  if(qf.empty()||qb.empty())break;
  bool reverse=qb.top().priority<qf.top().priority;
  if(qb.top().priority==qf.top().priority){reverse=tie_reverse;tie_reverse=!tie_reverse;}
  auto& queue=reverse?qb:qf;auto& dist=reverse?work.db:work.df;
  auto& seen=reverse?work.vb:work.vf;auto& parent=reverse?work.pb:work.pf;
  auto item=queue.top();queue.pop();int v=item.node;auto c=coord(v);int x=c[0],y=c[1],layer=c[2];
  std::array<std::pair<int,int>,5>next{{{v-1,layer==0?1:direction_cost},{v+1,layer==0?1:direction_cost},{v-nx,layer==1?1:direction_cost},{v+nx,layer==1?1:direction_cost},{(1-layer)*plane+y*nx+x,3}}};
  for(int i=0;i<5;++i){
   if(i==4&&(x+y)%2)continue;int w=next[i].first;if(w<0||w>=size)continue;auto p=coord(w);
   if(p[0]<4||p[0]>=nx-4||p[1]<4||p[1]>=ny-4||!allowed(w))continue;
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
