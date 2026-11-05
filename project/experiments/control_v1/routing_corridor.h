#pragma once
// Software search guide only: XY squares around a real unit-edge coarse path.
// Both upper layers remain available; the fine router still enforces fixed
// ownership, unit edges and checkerboard vias. No macro or physical gate changes.
struct RoutingCorridor {
 std::vector<uint32_t> marked;uint32_t epoch=0;int nx=0,ny=0;
 uint64_t vertices=0;
 void build(int width,int height,const std::vector<int>&path,int radius){
  if(width<9||height<9||radius<0||path.empty())throw std::runtime_error("invalid routing corridor");
  nx=width;ny=height;size_t plane=size_t(nx)*ny;
  if(marked.size()!=plane){marked.assign(plane,0);epoch=0;}
  if(!++epoch){std::fill(marked.begin(),marked.end(),0);epoch=1;}
  vertices=0;
  for(int v:path){
   if(v<0||size_t(v)>=2*plane)throw std::runtime_error("routing corridor vertex outside grid");
   int x=v%nx,y=(v%plane)/nx;
   for(int yy=std::max(4,y-radius);yy<=std::min(ny-5,y+radius);++yy)
    for(int xx=std::max(4,x-radius);xx<=std::min(nx-5,x+radius);++xx){
     auto&entry=marked[yy*nx+xx];if(entry!=epoch){entry=epoch;++vertices;}
    }
  }
 }
 bool contains(int v)const{
  int plane=nx*ny;return v>=0&&v<2*plane&&marked[v%plane]==epoch;
 }
};
