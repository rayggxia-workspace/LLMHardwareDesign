#pragma once
#include <unordered_set>
// Search seed only. No imported path grants full routing/physical acceptance.
// Every actual landing, edge, via, sink, wire limit and cross-net owner is
// checked here; the Python caller independently checks the same raw snapshot.
inline uint64_t import_native_prefix(const string& path,int nx,int ny,int locked,
 const vector<string>&names,const vector<vector<int>>&ends,const vector<int>&fixed,
 const vector<int>&wire_limits,vector<vector<vector<int>>>&branches,
 vector<vector<int>>&trees,vector<uint32_t>&usage){
 const int plane=nx*ny,size=plane*2;ifstream in(path);int count=-1;in>>count;
 if(!in||count!=locked)throw runtime_error("seed native count mismatch");
 uint64_t total=0;
 for(int n=0;n<locked;++n){string name;int k=-1;in>>name>>k;
  if(!in||name!=names[n]||k!=int(ends[n].size()))throw runtime_error("seed native name/branch mismatch");
  unordered_set<int>seen;unordered_set<uint64_t>wires;
  for(int j=0;j<k;++j){int length=-1;in>>length;
   if(!in||length<1||length>size)throw runtime_error("seed native branch length");
   vector<int>points;unordered_set<int>unique;
   for(int i=0;i<length;++i){int x=-1,y=-1,l=-1;in>>x>>y>>l;
    if(!in||x<4||x>=nx-4||y<4||y>=ny-4||l<0||l>1)throw runtime_error("seed native point outside grid");
    int v=l*plane+y*nx+x;
    if((fixed[v]>=0&&fixed[v]!=n)||!unique.insert(v).second)throw runtime_error("seed native foreign landing or repeated point");
    if(!points.empty()){int w=points.back(),xx=w%nx,yy=(w%plane)/nx,ll=w/plane;
     if(abs(x-xx)+abs(y-yy)+abs(l-ll)!=1||(l!=ll&&(x+y)%2))throw runtime_error("seed native edge/via invalid");
     if(l==ll)wires.insert(uint64_t(min(v,w))*uint64_t(size)+max(v,w));
    }
    points.push_back(v);
   }
   if(j==0){if(points!=vector<int>{ends[n][0]})throw runtime_error("seed native driver access mismatch");}
   else if(!seen.count(points.back()))throw runtime_error("seed native branch disconnected");
   for(int v:points)if(seen.insert(v).second)trees[n].push_back(v);
   branches[n].push_back(move(points));
  }
  for(int v:ends[n])if(!seen.count(v))throw runtime_error("seed native missing sink");
  if(wire_limits[n]>=0&&wires.size()>uint64_t(wire_limits[n]))throw runtime_error("seed native wire budget exceeded");
  for(int v:trees[n]){if(usage[v])throw runtime_error("seed native cross-net short");++usage[v];++total;}
 }
 string trailing;if(in>>trailing)throw runtime_error("seed native trailing data");
 return total;
}
