// SPDX-License-Identifier: BSD-3-Clause
// Sparse reporting client for the already verified, unchanged field solver.
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include "fsv/Solver.h"

template<class T>T read(std::ifstream& f){T v{};f.read(reinterpret_cast<char*>(&v),sizeof(v));if(!f)throw std::runtime_error("truncated scene");return v;}

int main(int argc,char**argv){try{
  if(argc!=7)throw std::runtime_error("scene masters threads walks offset seed");
  std::ifstream input(argv[1],std::ios::binary);char magic[8];input.read(magic,8);
  if(std::string(magic,8)!="NATIVE22")throw std::runtime_error("scene format");
  auto count=read<uint32_t>(input);auto boxes=read<uint64_t>(input);auto eps=read<double>(input);
  fsv::Geometry geometry;
  for(uint32_t i=0;i<count;++i){auto len=read<uint32_t>(input);if(len>100000)throw std::runtime_error("net label");
    std::string name(len,' ');input.read(name.data(),len);auto ground=read<uint8_t>(input);
    if(geometry.addNet(name)!=int(i))throw std::runtime_error("net index");if(ground)geometry.setGrounded(i);}
  std::vector<int> groups;groups.reserve(boxes);
  for(uint64_t i=0;i<boxes;++i){auto net=read<int32_t>(input),owner=read<int32_t>(input);fsv::Box box;
    for(auto&v:box.lo)v=read<double>(input);for(auto&v:box.hi)v=read<double>(input);
    if(owner<0||owner>1)throw std::runtime_error("origin group");geometry.addBox(net,box);groups.push_back(owner);}
  if(input.peek()!=EOF)throw std::runtime_error("trailing scene data");
  fsv::Scene scene(geometry,eps);fsv::Solver solver({.threads=std::stoi(argv[3]),.seed=std::stoull(argv[6])});
  fsv::SolveOptions o;o.min_walks=std::stoll(argv[4]);o.max_walks=16*o.min_walks;o.tol_total=.002;o.tol_coupling=.002;
  o.gauss_offset=std::stod(argv[5]);o.origin_box_groups=groups;
  std::ifstream masters(argv[2]);int master;std::cout<<std::setprecision(17);
  while(masters>>master){std::cerr<<"MASTER "<<master<<std::endl;auto r=solver.solve(scene,master,o);
    if(r.partial_cap.size()!=2)throw std::runtime_error("origin bins");
    std::cout<<"{\"master\":"<<master<<",\"net\":\""<<geometry.netName(master)<<"\",\"walks\":"<<r.walks
      <<",\"hops\":"<<r.hops<<",\"total_ff\":"<<r.cap.at(master)<<",\"sigma_ff\":"<<r.sigma.at(master)
      <<",\"ground\":["<<r.ground<<','<<r.ground_sigma<<"],\"electrodes\":"<<count<<",\"values\":[";
    bool first=true;double sum=0;
    for(uint32_t j=0;j<=count;++j){double v=j==count?r.ground:r.cap[j],s=j==count?r.ground_sigma:r.sigma[j];sum+=v;
      if(std::abs(r.partial_cap[0][j]+r.partial_cap[1][j]-v)>1e-9*std::max(1.,std::abs(v)))throw std::runtime_error("origin sum");
      if(v==0&&s==0&&r.partial_cap[0][j]==0&&r.partial_cap[1][j]==0&&r.partial_sigma[0][j]==0&&r.partial_sigma[1][j]==0)continue;
      if(!first)std::cout<<',';first=false;
      std::cout<<'['<<j<<','<<v<<','<<s<<','<<r.partial_cap[0][j]<<','<<r.partial_sigma[0][j]<<','<<r.partial_cap[1][j]<<','<<r.partial_sigma[1][j]<<']';}
    if(std::abs(sum)>1e-8*r.cap[master])throw std::runtime_error("charge conservation");
    std::cout<<"]}"<<std::endl;
  }
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
