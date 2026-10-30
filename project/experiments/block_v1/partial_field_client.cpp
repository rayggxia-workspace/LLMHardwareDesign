// Research-only Gaussian-surface flux bins. Finite-offset bins are not yet
// conductor-local capacitance; independent FV and offset gates are mandatory.
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include "fsv/Solver.h"

void need(bool v,const std::string& why){if(!v)throw std::runtime_error(why);}
int main(int argc,char**argv){try{
  need(argc==7,"threads offset walks scene axis cut");
  int threads=std::stoi(argv[1]),axis=std::stoi(argv[5]);
  double offset=std::stod(argv[2]),cut=std::stod(argv[6]);
  int64_t walks=std::stoll(argv[3]);
  need(threads>0&&threads<=96&&axis>=0&&axis<3&&walks>0,"invalid budget/axis");
  fsv::Geometry g;std::map<std::string,int> nets;std::string master,line;double eps=0;
  std::ifstream input(argv[4]);need(input.good(),"scene missing");
  while(std::getline(input,line)){
    std::istringstream row(line.substr(0,line.find('#')));std::string kind;
    if(!(row>>kind))continue;
    if(kind=="background"){need(bool(row>>eps)&&eps>0,"epsilon");continue;}
    if(kind=="master"){need(master.empty()&&bool(row>>master),"master");continue;}
    need(kind=="box","unsupported scene grammar");std::string net;fsv::Box box;
    need(bool(row>>net>>box.lo[0]>>box.lo[1]>>box.lo[2]>>box.hi[0]>>box.hi[1]>>box.hi[2]),"box");
    need(net.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")==std::string::npos,"net name");
    if(!nets.contains(net))nets[net]=g.addNet(net);
    g.addBox(nets.at(net),box);
  }
  need(eps>0&&nets.contains(master),"scene/master missing");
  fsv::Solver solver({.threads=threads});fsv::SolveOptions options;
  options.gauss_offset=offset;options.partial_axis=axis;options.partial_cuts={cut};
  options.min_walks=options.max_walks=walks;
  auto result=solver.solve(fsv::Scene(g,eps),nets.at(master),options);
  need(result.partial_cap.size()==2,"partial row missing");
  std::cout<<std::setprecision(17)<<"{\"schema\":\"block-v1-partial-flux/1\",\"master\":\""<<master
    <<"\",\"offset\":"<<offset<<",\"walks\":"<<result.walks<<",\"entries\":[";
  for(int c=0;c<=g.netCount();++c){
    double value=c==g.netCount()?result.ground:result.cap[c];
    double sigma=c==g.netCount()?result.ground_sigma:result.sigma[c];
    double sum=result.partial_cap[0][c]+result.partial_cap[1][c];
    need(std::isfinite(value)&&std::abs(sum-value)<1e-10*std::max(1.0,std::abs(value)),"partial conservation");
    if(c)std::cout<<',';
    std::cout<<"{\"net\":\""<<(c==g.netCount()?"ground":g.netName(c))<<"\",\"cap\":"<<value
      <<",\"sigma\":"<<sigma<<",\"partial\":["<<result.partial_cap[0][c]<<','<<result.partial_cap[1][c]
      <<"],\"partial_sigma\":["<<result.partial_sigma[0][c]<<','<<result.partial_sigma[1][c]<<"]}";
  }
  std::cout<<"]}"<<std::endl;return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 1;}}
