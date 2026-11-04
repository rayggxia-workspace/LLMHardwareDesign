#include <unordered_set>
// Observation only: no search arrays, routing choices or reservations change.
void write_pin_exit_probe(const string& path,const string& stage,int nx,int ny,
                         int locked_count,const vector<vector<int>>& ends,
                         const vector<int>& fixed,const vector<vector<int>>& trees,
                         const vector<uint32_t>& usage){
 const int plane=nx*ny;uint64_t terminals=0,isolated=0,isolated_nets=0,odd_isolated=0,even_isolated=0,even_foreign_m12=0,static_no_exit=0;
 array<uint64_t,6> histogram{};vector<int> samples;
 for(int n=locked_count;n<int(ends.size());++n){
  unordered_set<int> own(trees[n].begin(),trees[n].end());bool bad=false;
  for(int v:ends[n]){
   ++terminals;int x=v%nx,y=(v%plane)/nx;int clean=0,legal=0;
   for(int i=0;i<5;++i){
    if(i==4&&(x+y)%2)continue;
    int w=i==0?v-1:i==1?v+1:i==2?v-nx:i==3?v+nx:v+plane;
    if(w<0||w>=2*plane)continue;int xx=w%nx,yy=(w%plane)/nx;
    if(xx<4||xx>=nx-4||yy<4||yy>=ny-4||(fixed[w]!=-1&&fixed[w]!=n))continue;
    ++legal;uint32_t own_use=own.count(w)?1:0;if(usage[w]<own_use)throw runtime_error("pin-exit own usage underflow");
    if(usage[w]==own_use)++clean;
    if(i==4&&usage[w]>own_use)++even_foreign_m12;
   }
   if(!legal)++static_no_exit;++histogram[clean];
   if(!clean){++isolated;bad=true;if((x+y)%2)++odd_isolated;else ++even_isolated;}
  }
  if(bad){++isolated_nets;if(samples.size()<40)samples.push_back(n);}
 }
 uint64_t occupied=0,conflicts=0,excess=0,vertices=0;
 for(auto u:usage){occupied+=u!=0;vertices+=u;if(u>1){++conflicts;excess+=u-1;}}
 ofstream out(path);out<<"{\"stage\":\""<<stage<<"\",\"ordinary_terminals\":"<<terminals<<",\"isolated_terminals\":"<<isolated<<",\"isolated_nets\":"<<isolated_nets<<",\"odd_isolated\":"<<odd_isolated<<",\"even_isolated\":"<<even_isolated<<",\"even_foreign_m12_occupied\":"<<even_foreign_m12<<",\"static_no_legal_exit\":"<<static_no_exit<<",\"occupied_cells\":"<<occupied<<",\"conflict_nodes\":"<<conflicts<<",\"excess_occupancy\":"<<excess<<",\"summed_tree_vertices\":"<<vertices<<",\"free_exit_histogram\":[";
 for(int i=0;i<6;++i){if(i)out<<',';out<<histogram[i];}out<<"],\"sample_net_indices\":[";
 for(size_t i=0;i<samples.size();++i){if(i)out<<',';out<<samples[i];}out<<"],\"scope\":\"Observation relative to all other current net trees held fixed; own tree use subtracted. A zero-exit endpoint cannot use a strict-zero reroute at this snapshot. Does not prove global infeasibility or describe every earlier search call. No physical qualification.\"}\n";
 if(!out)throw runtime_error("cannot write pin-exit observation");
}
