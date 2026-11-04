#pragma once
// Optional candidate generator for unconstrained ordinary pairs only.
// A compressed two-layer graph expands to real unit edges. All foreign
// landings and checkerboard vias remain obstacles. Failure/cap uses the
// unchanged dense search; only independent full zero occupancy grants success.
template<class Penalty,class Allowed>
vector<int> ordinary_coarse_grid(int nx,int ny,int start,int goal,int stride,
 int offset_x,int offset_y,int weight,int nonpreferred,Penalty penalty,Allowed allowed,
 uint64_t&expanded,uint64_t&point_checks,int expansion_limit=65536,bool local_access=false,bool neighbor_tracks=false){
 if(neighbor_tracks&&!local_access)throw runtime_error("neighbor tracks require local access");
 const int plane=nx*ny;auto xyz=[&](int v){return array<int,3>{v%nx,(v%plane)/nx,v/plane};};
 auto s=xyz(start),g=xyz(goal);
 if(!allowed(start)||!allowed(goal))return{};
 vector<int>xs{4,nx-5,s[0],g[0]},ys{4,ny-5,s[1],g[1]};
 if(local_access){
  for(int x:{s[0]-1,s[0]+1,g[0]-1,g[0]+1})if(x>=4&&x<nx-4)xs.push_back(x);
  for(int y:{s[1]-1,s[1]+1,g[1]-1,g[1]+1})if(y>=4&&y<ny-4)ys.push_back(y);
 }
 for(int x=4+offset_x;x<nx-4;x+=stride){xs.push_back(x);if(neighbor_tracks)for(int d:{-1,1})if(x+d>=4&&x+d<nx-4)xs.push_back(x+d);}
 for(int y=4+offset_y;y<ny-4;y+=stride){ys.push_back(y);if(neighbor_tracks)for(int d:{-1,1})if(y+d>=4&&y+d<ny-4)ys.push_back(y+d);}
 auto compact=[](vector<int>&a){sort(a.begin(),a.end());a.erase(unique(a.begin(),a.end()),a.end());};compact(xs);compact(ys);
 const int cx=xs.size(),cy=ys.size(),size=2*cx*cy;
 auto node=[&](int x,int y,int l){return l*plane+y*nx+x;};
 auto physical=[&](int v){return node(xs[v%cx],ys[(v/cx)%cy],v/(cx*cy));};
 auto locate=[&](array<int,3>a){return int(lower_bound(xs.begin(),xs.end(),a[0])-xs.begin())+cx*(int(lower_bound(ys.begin(),ys.end(),a[1])-ys.begin())+cy*a[2]);};
 int source=locate(s),target=locate(g);const int64_t inf=numeric_limits<int64_t>::max()/4;
 vector<int64_t>d(size,inf);vector<int>parent(size,-1);priority_queue<Item>queue;
 vector<uint8_t>closed(local_access?size:0,0);
 // Settled weighted candidates need no optimality claim. At weight1 the
 // Manhattan heuristic is consistent, checked by the independent oracle.
 if(local_access)expansion_limit=max(expansion_limit,size);
 auto h=[&](int v){auto a=xyz(physical(v));return abs(a[0]-g[0])+abs(a[1]-g[1]);};
 d[source]=0;queue.push({int64_t(weight)*h(source),0,source});int steps=0;
 while(!queue.empty()){
  Item item=queue.top();queue.pop();int v=item.node;if(d[v]!=item.cost)continue;
  if(local_access){if(closed[v])continue;closed[v]=1;}
  if(v==target){
   vector<int>chain;for(int w=v;w!=-1;w=parent[w])chain.push_back(physical(w));reverse(chain.begin(),chain.end());
   vector<int>path{start};for(size_t j=1;j<chain.size();++j){auto a=xyz(chain[j-1]),b=xyz(chain[j]);
    while(a!=b){if(a[0]!=b[0])a[0]+=a[0]<b[0]?1:-1;else if(a[1]!=b[1])a[1]+=a[1]<b[1]?1:-1;else a[2]=b[2];path.push_back(node(a[0],a[1],a[2]));}}
   return path;
  }
  ++expanded;if(++steps>expansion_limit)return{};
  int i=v%cx,j=(v/cx)%cy,l=v/(cx*cy);auto a=xyz(physical(v));
  array<int,5>next{{i? v-1:-1,i+1<cx?v+1:-1,j?v-cx:-1,j+1<cy?v+cx:-1,((a[0]+a[1])%2)?-1:v+(l?-cx*cy:cx*cy)}};
  for(int w:next){if(w<0||(local_access&&closed[w]))continue;auto b=xyz(physical(w)),p=a;int64_t cost=0;bool legal=true;
   while(p!=b){int old_layer=p[2],base=3;if(p[0]!=b[0]){p[0]+=p[0]<b[0]?1:-1;base=old_layer==0?1:nonpreferred;}
    else if(p[1]!=b[1]){p[1]+=p[1]<b[1]?1:-1;base=old_layer==1?1:nonpreferred;}else p[2]=b[2];
    int q=node(p[0],p[1],p[2]);++point_checks;if(!allowed(q)){legal=false;break;}
    int64_t extra=penalty(q);if(extra<0||extra>inf/8||cost>inf-base-extra)throw runtime_error("coarse-grid cost overflow");cost+=base+extra;
   }
   if(!legal)continue;if(item.cost>inf-cost)throw runtime_error("coarse-grid accumulated cost overflow");int64_t alt=item.cost+cost;
   if(alt<d[w]){d[w]=alt;parent[w]=v;queue.push({alt+int64_t(weight)*h(w),alt,w});}
  }
 }
 return{};
}
