// SPDX-License-Identifier: BSD-3-Clause
// Three source-origin bins: above M10, shared landing, other native metal.
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include "fsv/Solver.h"
template<class T>T rd(std::ifstream&f){T v{};f.read(reinterpret_cast<char*>(&v),sizeof(v));if(!f)throw std::runtime_error("truncated scene");return v;}
int main(int argc,char**argv){try{
 if(argc!=7)throw std::runtime_error("scene masters threads walks offset seed");
 std::ifstream in(argv[1],std::ios::binary);char magic[8];in.read(magic,8);if(std::string(magic,8)!="NATIVE22")throw std::runtime_error("scene format");
 auto n=rd<uint32_t>(in);auto count=rd<uint64_t>(in);double eps=rd<double>(in);fsv::Geometry g;
 for(uint32_t i=0;i<n;++i){auto len=rd<uint32_t>(in);std::string name(len,' ');in.read(name.data(),len);auto ground=rd<uint8_t>(in);if(g.addNet(name)!=int(i))throw std::runtime_error("duplicate electrode name");if(ground)g.setGrounded(i);}
 std::vector<int>groups;groups.reserve(count);
 for(uint64_t i=0;i<count;++i){int net=rd<int32_t>(in),owner=rd<int32_t>(in);fsv::Box b;for(auto&v:b.lo)v=rd<double>(in);for(auto&v:b.hi)v=rd<double>(in);
  g.addBox(net,b);groups.push_back(owner==1?2:(b.hi[2]<=12.09+1e-10?1:0));}
 if(in.peek()!=EOF)throw std::runtime_error("trailing scene");
 fsv::Scene scene(g,eps);fsv::Solver solver({.threads=std::stoi(argv[3]),.seed=std::stoull(argv[6])});fsv::SolveOptions o;
 o.min_walks=std::stoll(argv[4]);o.max_walks=16*o.min_walks;o.tol_total=.002;o.tol_coupling=.002;o.gauss_offset=std::stod(argv[5]);o.origin_box_groups=groups;
 std::ifstream masters(argv[2]);int master;std::cout<<std::setprecision(17);
 while(masters>>master){std::cerr<<"MASTER "<<master<<std::endl;auto r=solver.solve(scene,master,o);
  if(r.partial_cap.size()!=3)throw std::runtime_error("missing three source bins");
  std::cout<<"{\"master\":"<<master<<",\"net\":\""<<g.netName(master)<<"\",\"walks\":"<<r.walks<<",\"hops\":"<<r.hops<<",\"total_ff\":"<<r.cap[master]
    <<",\"sigma_ff\":"<<r.sigma[master]<<",\"ground\":["<<r.ground<<','<<r.ground_sigma<<"],\"values\":[";
  for(uint32_t j=0;j<=n;++j){double v=j==n?r.ground:r.cap[j],s=j==n?r.ground_sigma:r.sigma[j],sum=0;for(int k=0;k<3;++k)sum+=r.partial_cap[k][j];
   if(std::abs(sum-v)>1e-9*std::max(1.,std::abs(v)))throw std::runtime_error("partition sum");
   if(j)std::cout<<',';std::cout<<'['<<v<<','<<s;for(int k=0;k<3;++k)std::cout<<','<<r.partial_cap[k][j]<<','<<r.partial_sigma[k][j];std::cout<<']';}
  std::cout<<"]}"<<std::endl;
 }
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
