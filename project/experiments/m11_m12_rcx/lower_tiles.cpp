// SPDX-License-Identifier: BSD-3-Clause
// Exact tile partition of existing conductor boxes, retaining global net IDs.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <list>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
#include "fsv/Geometry.h"
using namespace fsv;
template<class T>T rd(std::ifstream&f){T v{};f.read(reinterpret_cast<char*>(&v),sizeof(v));if(!f)throw std::runtime_error("truncated input");return v;}
template<class T>void wr(std::ofstream&f,const T&v){f.write(reinterpret_cast<const char*>(&v),sizeof(v));if(!f)throw std::runtime_error("write failure");}
using Key=std::pair<int,int>;
struct Tile{std::unique_ptr<std::ofstream>f;std::list<Key>::iterator active;uint64_t count=0;};
int main(int argc,char**argv){try{
 if(argc!=4)throw std::runtime_error("scene out tile_size");
 std::filesystem::path out(argv[2]);std::filesystem::create_directory(out);std::filesystem::create_directory(out/"tiles");
 double size=std::stod(argv[3]);if(!(size>0))throw std::runtime_error("tile size");
 std::ifstream in(argv[1],std::ios::binary);char magic[8];in.read(magic,8);if(std::string(magic,8)!="NATIVE22")throw std::runtime_error("format");
 auto n=rd<uint32_t>(in);auto count=rd<uint64_t>(in);auto eps=rd<double>(in);
 for(uint32_t i=0;i<n;++i){auto len=rd<uint32_t>(in);in.seekg(len+1,std::ios::cur);}
 std::vector<Box>bounds(n);std::vector<uint64_t>net_count(n,0);std::vector<double>net_volume(n,0.);
 double global_min=std::numeric_limits<double>::max();
 std::map<Key,Tile>tiles;std::list<Key>lru;uint64_t emitted=0,skipped=0;
 for(uint64_t k=0;k<count;++k){int net=rd<int32_t>(in),owner=rd<int32_t>(in);Box b;
  for(auto&v:b.lo)v=rd<double>(in);for(auto&v:b.hi)v=rd<double>(in);
  double input_volume=1;for(int d=0;d<3;++d){global_min=std::min(global_min,b.hi[d]-b.lo[d]);input_volume*=b.hi[d]-b.lo[d];}
  if(net>=2502){if(!net_count[net])bounds[net]=b;else for(int d=0;d<3;++d){bounds[net].lo[d]=std::min(bounds[net].lo[d],b.lo[d]);bounds[net].hi[d]=std::max(bounds[net].hi[d],b.hi[d]);}++net_count[net];net_volume[net]+=input_volume;}
  // These shared M10 boxes are already covered by identical native metal;
  // only genuinely added material belongs to the UPPER node in local solves.
  if(owner==0&&b.hi[2]<=12.09+1e-10){++skipped;continue;}
  int x0=std::floor(b.lo[0]/size),x1=std::floor((b.hi[0]-1e-9)/size);
  int y0=std::floor(b.lo[1]/size),y1=std::floor((b.hi[1]-1e-9)/size);double volume=0;
  for(int x=x0;x<=x1;++x)for(int y=y0;y<=y1;++y){Box c=b;
   c.lo[0]=std::max(c.lo[0],x*size);c.hi[0]=std::min(c.hi[0],(x+1)*size);
   c.lo[1]=std::max(c.lo[1],y*size);c.hi[1]=std::min(c.hi[1],(y+1)*size);
   double v=1;for(int d=0;d<3;++d)v*=c.hi[d]-c.lo[d];if(!(v>0))throw std::runtime_error("degenerate tile piece");volume+=v;
   auto key=std::make_pair(x,y);auto&t=tiles[key];if(!t.f){
    if(lru.size()>=128){auto old=lru.front();lru.pop_front();tiles.at(old).f.reset();}
    auto p=out/"tiles"/(std::to_string(x)+"_"+std::to_string(y)+".bin");
    t.f=std::make_unique<std::ofstream>(p,std::ios::binary|std::ios::app);if(!*t.f)throw std::runtime_error("tile open");
    lru.push_back(key);t.active=std::prev(lru.end());
   }else{
    lru.splice(lru.end(),lru,t.active);
   }
   wr(*t.f,net);wr(*t.f,owner);for(double v:c.lo)wr(*t.f,v);for(double v:c.hi)wr(*t.f,v);++t.count;++emitted;
  }
  double original=1;for(int d=0;d<3;++d)original*=b.hi[d]-b.lo[d];
  if(std::abs(volume-original)>1e-8*original+1e-16)throw std::runtime_error("tile partition volume changed");
  if(k%8388608==0)std::cerr<<"TILE_PROGRESS "<<k<<' '<<count<<' '<<tiles.size()<<std::endl;
 }
 if(in.peek()!=EOF)throw std::runtime_error("trailing input");
 for(auto&[key,t]:tiles)t.f.reset();
 std::ofstream index(out/"tiles.tsv");for(auto&[key,t]:tiles)index<<key.first<<'\t'<<key.second<<'\t'<<t.count<<'\n';
 std::ofstream masters(out/"masters.bin",std::ios::binary);uint64_t selected=0;
 for(uint32_t i=2502;i<n;++i)if(net_count[i]){wr(masters,i);for(double v:bounds[i].lo)wr(masters,v);for(double v:bounds[i].hi)wr(masters,v);wr(masters,net_count[i]);wr(masters,net_volume[i]);++selected;}
 std::ofstream runtime(out/"runtime.txt");runtime.precision(17);runtime<<size<<' '<<eps<<' '<<global_min*1e-4<<'\n';
 std::ofstream meta(out/"tiles.json");meta.precision(17);
 meta<<"{\"tile_size_um\":"<<size<<",\"relative_permittivity\":"<<eps<<",\"source_boxes\":"<<count<<",\"tile_parts\":"<<emitted
     <<",\"tiles\":"<<tiles.size()<<",\"selected_electrodes\":"<<selected<<",\"omitted_duplicate_shared_m10_boxes\":"<<skipped<<",\"global_minimum_box_dimension_um\":"<<global_min<<",\"per_box_volume_conserved\":true}\n";
 std::cout<<"TILED "<<selected<<" targets "<<tiles.size()<<" tiles "<<emitted<<" pieces\n";
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
