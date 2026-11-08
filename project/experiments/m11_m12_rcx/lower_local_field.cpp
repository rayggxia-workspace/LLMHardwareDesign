// SPDX-License-Identifier: BSD-3-Clause
// Existing WOS solver on exact local conductor geometry; reports its own
// conservative window-leakage estimate and expands inadequate windows.
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
#include "fsv/Solver.h"
using namespace fsv;
template<class T>T rd(std::ifstream&f){T v{};f.read(reinterpret_cast<char*>(&v),sizeof(v));if(!f)throw std::runtime_error("truncated record");return v;}
struct Master{uint32_t id;Box bounds;uint64_t boxes;double volume;};
int main(int argc,char**argv){try{
 if(argc!=10)throw std::runtime_error("tiles masters threads min_walks offset margin max_margin seed tol");
 std::filesystem::path root(argv[1]);std::ifstream mf(argv[2],std::ios::binary);std::vector<Master>masters;
 while(mf.peek()!=EOF){Master m;m.id=rd<uint32_t>(mf);for(auto&v:m.bounds.lo)v=rd<double>(mf);for(auto&v:m.bounds.hi)v=rd<double>(mf);m.boxes=rd<uint64_t>(mf);m.volume=rd<double>(mf);masters.push_back(m);}
 int threads=std::stoi(argv[3]);int64_t minimum=std::stoll(argv[4]);double offset=std::stod(argv[5]),initial_margin=std::stod(argv[6]),max_margin=std::stod(argv[7]),tol=std::stod(argv[9]);
 uint64_t seed=std::stoull(argv[8]);std::ifstream cfg(root/"runtime.txt");double tile,eps,capture_abs;cfg>>tile>>eps>>capture_abs;if(!cfg)throw std::runtime_error("tile runtime config");
 std::map<std::pair<int,int>,uint64_t>tile_counts;std::ifstream ti(root/"tiles.tsv");int tx,ty;uint64_t tc;while(ti>>tx>>ty>>tc)tile_counts[{tx,ty}]=tc;
 std::cout<<std::setprecision(17);
 for(const Master&m:masters){
  std::cerr<<"MASTER "<<m.id<<std::endl;
  bool accepted=false;double margin=initial_margin;
  while(true){
   Box window{{std::floor(m.bounds.lo[0]/tile)*tile-margin,std::floor(m.bounds.lo[1]/tile)*tile-margin,0},
              {(std::floor((m.bounds.hi[0]-1e-9)/tile)+1)*tile+margin,(std::floor((m.bounds.hi[1]-1e-9)/tile)+1)*tile+margin,1e9}};
   Geometry before,after;for(auto*g:{&before,&after}){g->addNet("TARGET");g->addNet("QUIET_NATIVE");g->addNet("QUIET_UPPER");g->setGrounded(1);g->setWindow({{window.lo[0],window.lo[1]},{window.hi[0],window.hi[1]}});}
   uint64_t native_parts=0,upper_parts=0,master_parts=0;double master_volume=0;
   int x0=std::floor(window.lo[0]/tile),x1=std::floor((window.hi[0]-1e-9)/tile),y0=std::floor(window.lo[1]/tile),y1=std::floor((window.hi[1]-1e-9)/tile);
   for(int x=x0;x<=x1;++x)for(int y=y0;y<=y1;++y){auto entry=tile_counts.find({x,y});if(entry==tile_counts.end())continue;
    auto file=root/"tiles"/(std::to_string(x)+"_"+std::to_string(y)+".bin");
    if(std::filesystem::file_size(file)!=entry->second*56)throw std::runtime_error("tile missing or truncated");
    std::ifstream f(file,std::ios::binary);if(!f)throw std::runtime_error("expected tile missing");
    while(f.peek()!=EOF){int net=rd<int32_t>(f),owner=rd<int32_t>(f);Box b;for(auto&v:b.lo)v=rd<double>(f);for(auto&v:b.hi)v=rd<double>(f);
     if(owner==0){if(net==int(m.id))throw std::runtime_error("native target unexpectedly upper-connected");after.addBox(2,b);++upper_parts;}
     else {int local=net==int(m.id)?0:1;before.addBox(local,b);after.addBox(local,b);++native_parts;
      if(local==0){++master_parts;double v=1;for(int d=0;d<3;++d)v*=b.hi[d]-b.lo[d];master_volume+=v;}}
    }
   }
   if(!master_parts)throw std::runtime_error("missing complete native target");
   if(std::abs(master_volume-m.volume)>1e-8*m.volume+1e-16)throw std::runtime_error("native target volume changed");
   // Tile-aligned windows contain every original target box by construction.
   for(int d=0;d<2;++d)if(!(window.lo[d]<m.bounds.lo[d]&&m.bounds.hi[d]<window.hi[d]))throw std::runtime_error("target clipped by window");
   // Match the global solver's counter-based stream after remapping its
   // global master ID to local TARGET=0.
   constexpr uint64_t salt=0x9E3779B97F4A7C15ull;
   Solver solver({.threads=threads,.seed=seed^(salt*(uint64_t(m.id)+1))^salt});
   SolveOptions o;o.min_walks=minimum;o.max_walks=std::max<int64_t>(16*minimum,16777216);o.gauss_offset=offset;o.tol_total=tol;o.tol_coupling=tol;
   Scene bscene(before,eps),ascene(after,eps);auto ob=o,oa=o;ob.capture_rel=capture_abs/bscene.minDimension();oa.capture_rel=capture_abs/ascene.minDimension();
   auto b=solver.solve(bscene,0,ob),a=solver.solve(ascene,0,oa);
   double leak=b.window_leakage+a.window_leakage;
   bool stat=b.sigma[0]<=.003*b.cap[0]&&a.sigma[0]<=.003*a.cap[0];
   accepted=stat&&leak<=.003*std::min(b.cap[0],a.cap[0]);
   if(!accepted&&margin<max_margin){margin*=2;continue;}
   std::cout<<"{\"master\":"<<m.id<<",\"before_ff\":"<<b.cap[0]<<",\"before_sigma_ff\":"<<b.sigma[0]<<",\"after_ff\":"<<a.cap[0]<<",\"after_sigma_ff\":"<<a.sigma[0]
     <<",\"before_window_leakage_ff\":"<<b.window_leakage<<",\"after_window_leakage_ff\":"<<a.window_leakage
     <<",\"upper_mutual_ff\":"<<-a.cap[2]<<",\"upper_mutual_sigma_ff\":"<<a.sigma[2]<<",\"native_parts\":"<<native_parts<<",\"upper_parts\":"<<upper_parts
     <<",\"target_parts\":"<<master_parts<<",\"target_volume_um3\":"<<master_volume<<",\"margin_um\":"<<margin
     <<",\"before_walks\":"<<b.walks<<",\"after_walks\":"<<a.walks<<",\"offset\":"<<offset<<",\"statistical_gate\":"<<(stat?"true":"false")
     <<",\"window_gate\":"<<(leak<=.003*std::min(b.cap[0],a.cap[0])?"true":"false")<<",\"qualified\":"<<(accepted?"true":"false")<<"}"<<std::endl;
   break;
  }
 }
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
