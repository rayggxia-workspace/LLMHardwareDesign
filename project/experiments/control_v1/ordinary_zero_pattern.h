// Optional bounded, zero-occupancy ordinary-net prepass. An empty result
// always yields to the original search. This is neither a feasibility nor
// optimality proof; the independent route/physical/RC gates remain mandatory.
template<class Free,class Goal>
vector<int> ordinary_zero_pattern(int nx,int ny,int start,const vector<int>& tree,
                                 Free free_vertex,Goal is_goal,uint64_t& checks){
 const int plane=nx*ny;const uint64_t limit=65536;uint64_t local_checks=0;
 auto xyz=[&](int v){return array<int,3>{v%nx,(v%plane)/nx,v/plane};};
 auto id=[&](int x,int y,int l){return l*plane+y*nx+x;};
 auto s=xyz(start);int target=-1,best=numeric_limits<int>::max();
 for(int v:tree){auto p=xyz(v);int d=abs(p[0]-s[0])+abs(p[1]-s[1]);
  if(d<best||(d==best&&v<target)){best=d;target=v;}}
 if(target<0)return{};
 auto t=xyz(target);
 auto available=[&](int v){
  ++checks;if(++local_checks>limit)return false;
  if(v<0||v>=2*plane)return false;auto p=xyz(v);
  return p[0]>=4&&p[0]<nx-4&&p[1]>=4&&p[1]<ny-4&&free_vertex(v);
 };
 if(!available(start))return{};
 if(is_goal(start))return{start};
 for(int orientation=0;orientation<2;++orientation){
  int a=s[orientation],b=t[orientation],middle=(a+b)/2;vector<int> mids;
  auto add=[&](int v){int bound=orientation?ny:nx;
   if(v>=4&&v<bound-4&&find(mids.begin(),mids.end(),v)==mids.end())mids.push_back(v);};
  add(middle);add((3*a+b)/4);add((a+3*b)/4);add(a);add(b);
  for(int d=1;d<=16;++d){add(middle-d);add(middle+d);}
  for(int d:{2,4,8,16,32,64}){add(min(a,b)-d);add(max(a,b)+d);}
  for(int mid:mids){
   array<array<int,2>,4> points;
   if(!orientation)points={{{s[0],s[1]},{mid,s[1]},{mid,t[1]},{t[0],t[1]}}};
   else points={{{s[0],s[1]},{s[0],mid},{t[0],mid},{t[0],t[1]}}};
   // Prefer the usual alternating direction layers, but permit both
   // directions on both layers just as the original physical grid does.
   array<int,8> masks=orientation?array<int,8>{5,2,0,7,1,3,4,6}:array<int,8>{2,5,0,7,1,3,4,6};
   for(int mask:masks){
    vector<int> path{start};auto current=s;bool valid=true,done=false;
    auto append=[&](int x,int y,int l){
     int v=id(x,y,l);if(!available(v)){valid=false;return;}
     path.push_back(v);current={x,y,l};if(is_goal(v))done=true;
    };
    auto layer=[&](int wanted){
     if(current[2]!=wanted){
      if((current[0]+current[1])%2){valid=false;return;}
      append(current[0],current[1],wanted);
     }
    };
    for(int segment=0;segment<3&&valid&&!done;++segment){
     layer((mask>>segment)&1);
     auto end=points[segment+1];
     while(valid&&!done&&(current[0]!=end[0]||current[1]!=end[1])){
      int dx=(end[0]>current[0])-(end[0]<current[0]);
      int dy=(end[1]>current[1])-(end[1]<current[1]);
      if(dx&&dy)throw runtime_error("nonorthogonal zero-pattern segment");
      append(current[0]+dx,current[1]+dy,current[2]);
     }
    }
    if(valid&&!done)layer(t[2]);
    if(valid&&done)return path;
    if(local_checks>limit)return{};
   }
  }
 }
 return{};
}
