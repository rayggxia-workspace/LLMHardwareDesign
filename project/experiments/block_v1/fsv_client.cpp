// Issue 121 reference client. The unmodified solver/support/goldens are
// separately pinned to OpenROAD 6ea4ca224f3589dd91809933f50f39af66053634.
// Coordinates: um; capacitance: fF (3D), fF/um (2D).
#include <cmath>
#include <fstream>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>
#include "Structures.h"
#include "fsv/Scene.h"
#include "fsv/Solver.h"

using Golden=std::map<std::tuple<std::string,std::string,std::string>,double>;
void require(bool ok,const std::string& message){if(!ok)throw std::runtime_error(message);}
Golden golden(const std::string& file){
  std::ifstream in(std::string(fsv::kGoldenDir)+file);require(in.good(),"missing golden "+file);
  Golden refs;std::string line;
  while(std::getline(in,line)){
    std::istringstream row(line.substr(0,line.find('#')));std::string name,master,net;double value;
    if(row>>name>>master>>net>>value)require(refs.emplace(std::make_tuple(name,master,net),value).second,"duplicate golden");
  }return refs;
}
int netIndex(const fsv::Geometry& geometry,const std::string& name){
  for(int i=0;i<geometry.netCount();++i)if(geometry.netName(i)==name)return i;
  throw std::runtime_error("unknown master "+name);
}
void emit(const std::string& name,const std::string& dimension,const fsv::Geometry& g,const fsv::CapRow& row){
  std::cout<<"{\"schema\":\"block-v1-fsv-row/1\",\"case\":\""<<name<<"\",\"dimension\":\""<<dimension
           <<"\",\"master\":\""<<g.netName(row.master)<<"\",\"walks\":"<<row.walks<<",\"hops\":"<<row.hops<<",\"entries\":[";
  for(int i=0;i<=g.netCount();++i){
    if(i)std::cout<<',';
    std::cout<<"{\"net\":\""<<(i==g.netCount()?"ground":g.netName(i))<<"\",\"cap\":"
             <<(i==g.netCount()?row.ground:row.cap[i])<<",\"sigma\":"
             <<(i==g.netCount()?row.ground_sigma:row.sigma[i])<<'}';
  }std::cout<<"]}"<<std::endl;
}
void compare(const std::string& name,const fsv::Geometry& g,const fsv::CapRow& row,const Golden& refs,bool three){
  const std::string master=g.netName(row.master);double total=refs.at({name,master,master});
  for(int i=0;i<=g.netCount();++i){
    const std::string net=i==g.netCount()?"ground":g.netName(i);
    double expected=refs.at({name,master,net});
    if(i!=row.master && std::abs(expected)<.05*total)continue;
    double value=i==g.netCount()?row.ground:row.cap[i];
    double sigma=i==g.netCount()?row.ground_sigma:row.sigma[i];
    double relative=i==row.master?(three?.005:.003):(three?.01:.005);
    require(std::abs(value-expected)<=relative*std::abs(expected)+3*sigma,"golden mismatch "+name+" "+master+" "+net);
  }
}
void runGolden(int threads,bool three){
  fsv::Solver solver({.threads=threads});fsv::SolveOptions options;
  options.tol_total=three?.002:.001;options.tol_coupling=options.tol_total;
  auto refs=golden(three?"box_3d.txt":"cross_section.txt");
  std::vector<std::pair<std::string,std::vector<std::string>>> cases=three?
    std::vector<std::pair<std::string,std::vector<std::string>>>{{"crossing",{}},{"conformal_line_ends",{}},{"conformal_crossing",{}}}:
    std::vector<std::pair<std::string,std::vector<std::string>>>{{"etch_stop_pair",{"lower","upper"}},
      {"three_wires",{"left","middle"}},{"conformal_pair",{"a"}},{"nested_conformal",{"a"}},
      {"merged_conformal",{"a","b"}},{"sky130_met1_pair",{"a"}}};
  for(auto [name,masters]:cases){
    auto s=fsv::readStructure(name);
    if(three)for(int i=0;i<s.geometry.netCount();++i)masters.push_back(s.geometry.netName(i));
    for(const auto& master:masters){
      fsv::CapRow row=three?solver.solve(fsv::Scene(s.geometry,s.stack),netIndex(s.geometry,master),options):
        solver.solve(fsv::Scene2D(fsv::crossSection(s.geometry),s.stack),netIndex(s.geometry,master),options);
      emit(name,three?"3D":"2D",s.geometry,row);compare(name,s.geometry,row,refs,three);
    }
  }
}
void determinism(int threads){
  fsv::Geometry g;int a=g.addNet("a"),b=g.addNet("b");
  g.addBox(a,{{0,0,1},{.8,10,3}});g.addBox(b,{{1.6,0,1},{2.4,10,3}});
  auto section=fsv::crossSection(g);fsv::SolveOptions options;
  options.min_walks=options.max_walks=32768;options.tol_total=1e-12;
  fsv::Solver one({.threads=1}),many({.threads=threads});
  auto x=one.solve(fsv::Scene2D(section,3.9),a,options);
  auto y=many.solve(fsv::Scene2D(section,3.9),a,options);
  auto z=many.solve(fsv::Scene2D(section,7.8),a,options);
  require(x.cap==y.cap && x.sigma==y.sigma && x.walks==y.walks && x.hops==y.hops && x.ground==y.ground,"thread-dependent result");
  for(size_t i=0;i<x.cap.size();++i)require(std::abs(z.cap[i]-2*x.cap[i])<1e-12,"epsilon scaling");
  emit("determinism-eps39","2D",g,x);emit("determinism-eps78","2D",g,z);
}
// Explicit homogeneous study inputs. Reference goldens additionally exercise
// the author's planar/conformal dielectric implementation unchanged.
void scene(fsv::Solver& solver,bool three,const std::string& path){
  std::ifstream in(path);require(in.good(),"missing scene");fsv::Geometry g;
  std::map<std::string,int> nets;std::vector<std::string> masters;std::string line;double eps=0;
  while(std::getline(in,line)){
    std::istringstream row(line.substr(0,line.find('#')));std::string kind;if(!(row>>kind))continue;
    if(kind=="background"){require(bool(row>>eps)&&eps>0,"bad epsilon");continue;}
    if(kind=="master"){std::string name;require(bool(row>>name),"bad master");masters.push_back(name);continue;}
    require(kind=="box","unsupported scene directive "+kind);std::string name;fsv::Box box;
    require(bool(row>>name>>box.lo[0]>>box.lo[1]>>box.lo[2]>>box.hi[0]>>box.hi[1]>>box.hi[2]),"bad box");
    require(name.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")==std::string::npos,"bad net name");
    if(!nets.contains(name))nets[name]=g.addNet(name);g.addBox(nets.at(name),box);
  }
  require(eps>0 && g.netCount()>0,"empty scene");
  fsv::SolveOptions options;options.tol_total=.002;options.tol_coupling=.002;
  if(masters.empty())for(int i=0;i<g.netCount();++i)masters.push_back(g.netName(i));
  if(three){
    fsv::Scene prepared(g,eps);
    for(const auto& master:masters)emit(std::filesystem::path(path).stem().string(),"3D",g,
      solver.solve(prepared,netIndex(g,master),options));
  }else{
    auto section=fsv::crossSection(g);fsv::Scene2D prepared(section,eps);
    for(const auto& master:masters)emit(std::filesystem::path(path).stem().string(),"2D",g,
      solver.solve(prepared,netIndex(g,master),options));
  }
}
int main(int argc,char**argv){
  try{
    std::cout<<std::setprecision(17);require(argc>=3,"mode threads [scene]");int threads=std::stoi(argv[2]);
    require(threads>0 && threads<=96,"bad thread budget");std::string mode=argv[1];
    if(mode=="golden2d"||mode=="golden3d")runGolden(threads,mode=="golden3d");
    else if(mode=="determinism")determinism(threads);
    else if((mode=="scene2d"||mode=="scene3d")&&argc==4){
      fsv::Solver solver({.threads=threads});scene(solver,mode=="scene3d",argv[3]);
    }else if(mode=="scenelist3d"&&argc==4){
      std::ifstream list(argv[3]);require(list.good(),"missing scene list");std::string path;
      fsv::Solver solver({.threads=threads});
      while(std::getline(list,path)){
        require(!path.empty(),"empty scene list entry");std::cerr<<"SOLVING "<<path<<std::endl;
        scene(solver,true,path);
      }
    }
    else throw std::runtime_error("bad mode");
    std::cout<<"{\"status\":\"PASS\",\"mode\":\""<<mode<<"\"}"<<std::endl;return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}
}
