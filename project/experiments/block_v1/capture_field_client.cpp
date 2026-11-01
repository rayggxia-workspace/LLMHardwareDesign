// Research-only joint origin/terminal-node flux; unchanged conductor potentials.
// Offset/FV convergence is mandatory before interpreting bins as local charge.
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include "fsv/Solver.h"

void need(bool v,const std::string& why){if(!v)throw std::runtime_error(why);}
int main(int argc,char**argv){try{
  need(argc==7,"threads offset walks scene origin_nodes capture_nodes");
  int threads=std::stoi(argv[1]); double offset=std::stod(argv[2]);
  int64_t walks=std::stoll(argv[3]);
  need(threads>0&&threads<=96&&walks>0&&std::isfinite(offset)&&offset>0,"invalid budget/offset");
  fsv::Geometry g;std::map<std::string,int> nets;std::string master,line;double eps=0;
  std::ifstream input(argv[4]);need(input.good(),"scene missing");
  while(std::getline(input,line)){
    std::istringstream row(line.substr(0,line.find('#')));std::string kind,extra;
    if(!(row>>kind))continue;
    if(kind=="background"){need(bool(row>>eps)&&eps>0&&std::isfinite(eps)&&!(row>>extra),"epsilon");continue;}
    if(kind=="master"){need(master.empty()&&bool(row>>master)&&!(row>>extra),"master");continue;}
    need(kind=="box","unsupported scene grammar");std::string net;fsv::Box box;
    need(bool(row>>net>>box.lo[0]>>box.lo[1]>>box.lo[2]>>box.hi[0]>>box.hi[1]>>box.hi[2])&&!(row>>extra),"box");
    if(!nets.contains(net))nets[net]=g.addNet(net);
    g.addBox(nets.at(net),box);
  }
  need(eps>0&&nets.contains(master),"scene/master missing");
  fsv::Solver solver({.threads=threads});fsv::SolveOptions options;
  options.gauss_offset=offset;options.min_walks=options.max_walks=walks;
  std::ifstream nodes(argv[5]);need(nodes.good(),"nodes missing");std::vector<std::string> ids;
  while(std::getline(nodes,line)){
    std::istringstream row(line.substr(0,line.find('#')));std::string id,extra;fsv::Vec3 p;
    if(!(row>>id))continue;
    need(id.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")==std::string::npos,"node id");
    need(bool(row>>p[0]>>p[1]>>p[2])&&!(row>>extra),"node coordinates");
    need(std::find(ids.begin(),ids.end(),id)==ids.end(),"duplicate node id");
    need(std::all_of(p.begin(),p.end(),[](double v){return std::isfinite(v);}),"nonfinite node");
    bool covered=false;
    for(size_t i=0;i<g.boxes().size();++i){
      const auto& b=g.boxes()[i];bool inside=g.boxNet(i)==nets.at(master);
      for(int k=0;k<3;++k)inside=inside&&p[k]>=b.lo[k]&&p[k]<=b.hi[k];
      covered=covered||inside;
    }
    need(covered,"node outside master conductor");ids.push_back(id);options.partial_nodes.push_back(p);
  }
  need(ids.size()>=2,"too few graph nodes");
  options.capture_nodes.resize(g.netCount());
  std::vector<std::vector<std::string>> capture_ids(g.netCount());
  std::ifstream captures(argv[6]);need(captures.good(),"capture nodes missing");
  while(std::getline(captures,line)){
    std::istringstream row(line.substr(0,line.find('#')));std::string net,id,extra;fsv::Vec3 p;
    if(!(row>>net))continue;
    need(nets.contains(net)&&net!=master,"capture net must be a nonmaster conductor");
    need(bool(row>>id>>p[0]>>p[1]>>p[2])&&!(row>>extra),"capture node syntax");
    need(id.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")==std::string::npos,"capture node id");
    need(std::all_of(p.begin(),p.end(),[](double v){return std::isfinite(v);}),"nonfinite capture node");
    int c=nets.at(net);auto& names=capture_ids[c];
    need(std::find(names.begin(),names.end(),id)==names.end(),"duplicate capture node id");
    bool covered=false;
    for(size_t i=0;i<g.boxes().size();++i){
      const auto& b=g.boxes()[i];bool inside=g.boxNet(i)==c;
      for(int k=0;k<3;++k)inside=inside&&p[k]>=b.lo[k]&&p[k]<=b.hi[k];
      covered=covered||inside;
    }
    need(covered,"capture node outside its conductor");
    names.push_back(id);options.capture_nodes[c].push_back(p);
  }
  for(int c=0;c<g.netCount();++c)need(c==nets.at(master)||!capture_ids[c].empty(),"nonmaster capture nodes missing");
  // Different electrical identities may never touch or overlap. Same-net
  // touching boxes form one conductor and do not expose their shared face.
  for(size_t i=0;i<g.boxes().size();++i)for(size_t j=0;j<i;++j){
    if(g.boxNet(i)==g.boxNet(j))continue;
    bool touches=true;
    for(int k=0;k<3;++k)touches=touches&&std::max(g.boxes()[i].lo[k],g.boxes()[j].lo[k])<=std::min(g.boxes()[i].hi[k],g.boxes()[j].hi[k]);
    need(!touches,"distinct conductor nets touch or overlap");
  }
  auto result=solver.solve(fsv::Scene(g,eps),nets.at(master),options);
  need(result.partial_cap.size()==ids.size(),"graph row missing");
  std::cout<<std::setprecision(17)<<"{\"schema\":\"block-v1-joint-flux/1\",\"master\":\""<<master
    <<"\",\"offset\":"<<offset<<",\"walks\":"<<result.walks<<",\"nodes\":[";
  for(size_t i=0;i<ids.size();++i){if(i)std::cout<<',';std::cout<<'"'<<ids[i]<<'"';}
  std::cout<<"],\"entries\":[";
  for(int c=0;c<=g.netCount();++c){
    double value=c==g.netCount()?result.ground:result.cap[c];
    double sigma=c==g.netCount()?result.ground_sigma:result.sigma[c],sum=0;
    for(const auto& b:result.partial_cap)sum+=b[c];
    need(std::isfinite(value)&&std::abs(sum-value)<1e-10*std::max(1.0,std::abs(value)),"graph conservation");
    if(c)std::cout<<',';
    std::cout<<"{\"net\":\""<<(c==g.netCount()?"ground":g.netName(c))<<"\",\"cap\":"<<value
      <<",\"sigma\":"<<sigma<<",\"partial\":[";
    for(size_t i=0;i<ids.size();++i){if(i)std::cout<<',';std::cout<<result.partial_cap[i][c];}
    std::cout<<"],\"partial_sigma\":[";
    for(size_t i=0;i<ids.size();++i){if(i)std::cout<<',';std::cout<<result.partial_sigma[i][c];}
    std::cout<<"]}";
  }
  std::cout<<"],\"captures\":[";
  size_t d=0;
  for(int c=0;c<=g.netCount();++c){
    size_t count=c==g.netCount()?1:std::max(size_t(1),capture_ids[c].size());
    for(size_t j=0;j<count;++j,++d){
      if(d)std::cout<<',';
      std::string id=c==g.netCount()?"_ground":(capture_ids[c].empty()?"_whole":capture_ids[c][j]);
      std::cout<<"{\"net\":\""<<(c==g.netCount()?"ground":g.netName(c))<<"\",\"node\":\""<<id<<"\",\"partial\":[";
      for(size_t b=0;b<ids.size();++b){if(b)std::cout<<',';std::cout<<result.joint_cap.at(b).at(d);}
      std::cout<<"],\"partial_sigma\":[";
      for(size_t b=0;b<ids.size();++b){if(b)std::cout<<',';std::cout<<result.joint_sigma.at(b).at(d);}
      std::cout<<"]}";
    }
    for(size_t b=0;b<ids.size();++b){
      double sum=0;for(size_t j=d-count;j<d;++j)sum+=result.joint_cap.at(b).at(j);
      need(std::abs(sum-result.partial_cap[b][c])<1e-10*std::max(1.0,std::abs(sum)),"capture marginal conservation");
    }
  }
  need(result.joint_cap.at(0).size()==d,"joint column count");
  std::cout<<"]}"<<std::endl;return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 1;}}
