// SPDX-License-Identifier: BSD-3-Clause
// Reuse unchanged physical spatial indices; source identity is a read-only
// view for each electrode, never a mutation of an existing Scene.
#define LOWER_PAIR_LIBRARY_ONLY
#include "lower_pair_field.cpp"
#include <list>
#include <unordered_map>

struct PhysicalEntry {
  Geometry before,after;
  std::vector<int> before_ids,after_ids;
  std::unordered_map<uint32_t,std::pair<uint64_t,double>> targets;
  std::unique_ptr<Scene> bscene,ascene;
  uint64_t native=0,upper=0;
};
struct SourceView {
  const Geometry& physical;
  const std::vector<int>& original_ids;
  uint32_t master;
  const std::vector<Box>& boxes()const{return physical.boxes();}
  int boxNet(int i)const{return physical.boxNet(i)==2?2:(original_ids[i]==int(master)?0:1);}
  int netCount()const{return 3;}
  bool grounded(int n)const{return n==1;}
  const auto& window()const{return physical.window();}
};
struct SourceSpace:Space {
  using GeometryType=SourceView;
  static const std::vector<Box>& shapes(const SourceView&v){return v.boxes();}
  static int shapeNet(const SourceView&v,int i){return v.boxNet(i);}
  static const AlignedBox<2>* window(const SourceView&v){return v.window()?&*v.window():nullptr;}
};
struct SourceScene {
  const SourceView& source;
  const Scene& physical;
  const SourceView& geometry()const{return source;}
  const SpatialIndex<3>& index()const{return physical.index();}
  const Dielectric<3>& dielectric()const{return physical.dielectric();}
};

int main(int argc,char**argv){try{
  if(argc!=12)throw std::runtime_error("tiles masters threads min_walks max_walks offset margin max_margin seed precision alpha");
  std::filesystem::path root(argv[1]);std::ifstream mf(argv[2],std::ios::binary);
  if(!mf)throw std::runtime_error("masters missing");
  std::vector<Master> masters;
  while(mf.peek()!=EOF){Master m;m.id=rd<uint32_t>(mf);for(auto&v:m.bounds.lo)v=rd<double>(mf);
    for(auto&v:m.bounds.hi)v=rd<double>(mf);m.boxes=rd<uint64_t>(mf);m.volume=rd<double>(mf);masters.push_back(m);}
  WorkerPool pool(std::stoi(argv[3]));
  int64_t minimum=std::stoll(argv[4]),maximum=std::stoll(argv[5]);
  double offset=std::stod(argv[6]),margin0=std::stod(argv[7]),margin_max=std::stod(argv[8]);
  uint64_t seed=std::stoull(argv[9]);double tolerance=std::stod(argv[10]),alpha=std::stod(argv[11]);
  if(minimum<256||maximum<minimum||minimum%256||maximum%256
     ||!(margin0>0&&margin_max>=margin0&&tolerance>0&&alpha>0&&alpha<=.05))throw std::runtime_error("invalid paired options");
  std::ifstream cfg(root/"runtime.txt");double tile,eps,capture;cfg>>tile>>eps>>capture;
  if(!cfg)throw std::runtime_error("runtime missing");
  std::map<std::pair<int,int>,uint64_t> tiles;std::ifstream ti(root/"tiles.tsv");int tx,ty;uint64_t count;
  while(ti>>tx>>ty>>count)tiles[{tx,ty}]=count;
  using Key=std::array<double,4>;
  struct Item{std::shared_ptr<PhysicalEntry> entry;std::list<Key>::iterator active;};
  std::map<Key,Item> cache;std::list<Key> lru;
  uint64_t cached_boxes=0,hits=0,misses=0;
  constexpr uint64_t box_budget=2000000;
  auto fetch=[&](const Box&window){
    Key key{window.lo[0],window.lo[1],window.hi[0],window.hi[1]};
    auto found=cache.find(key);
    if(found!=cache.end()){lru.splice(lru.end(),lru,found->second.active);++hits;return found->second.entry;}
    ++misses;uint64_t estimate=0;
    int x0=std::floor(window.lo[0]/tile),x1=std::floor((window.hi[0]-1e-9)/tile);
    int y0=std::floor(window.lo[1]/tile),y1=std::floor((window.hi[1]-1e-9)/tile);
    for(int x=x0;x<=x1;++x)for(int y=y0;y<=y1;++y){auto t=tiles.find({x,y});if(t!=tiles.end())estimate+=t->second;}
    while(!lru.empty()&&(cached_boxes+estimate>box_budget||cache.size()>=8)){
      auto oldest=lru.front();lru.pop_front();auto i=cache.find(oldest);
      cached_boxes-=i->second.entry->native+i->second.entry->upper;cache.erase(i);
    }
    auto entry=std::make_shared<PhysicalEntry>();
    for(auto*g:{&entry->before,&entry->after}){g->addNet("TARGET");g->addNet("QUIET_NATIVE");g->addNet("QUIET_UPPER");
      g->setGrounded(1);g->setWindow({{window.lo[0],window.lo[1]},{window.hi[0],window.hi[1]}});}
    for(int x=x0;x<=x1;++x)for(int y=y0;y<=y1;++y){
      auto t=tiles.find({x,y});if(t==tiles.end())continue;
      auto file=root/"tiles"/(std::to_string(x)+"_"+std::to_string(y)+".bin");
      if(std::filesystem::file_size(file)!=t->second*56)throw std::runtime_error("tile truncated");
      std::ifstream f(file,std::ios::binary);
      while(f.peek()!=EOF){
        int net=rd<int32_t>(f),owner=rd<int32_t>(f);Box box;
        for(auto&v:box.lo)v=rd<double>(f);for(auto&v:box.hi)v=rd<double>(f);
        if(owner==0){entry->after.addBox(2,box);entry->after_ids.push_back(net);++entry->upper;}
        else{
          if(owner!=1)throw std::runtime_error("invalid tile owner");
          entry->before.addBox(1,box);entry->before_ids.push_back(net);
          entry->after.addBox(1,box);entry->after_ids.push_back(net);++entry->native;
          if(net>=2502){auto&target=entry->targets[net];++target.first;double v=1;
            for(int k=0;k<3;++k)v*=box.hi[k]-box.lo[k];target.second+=v;}
        }
      }
    }
    entry->bscene=std::make_unique<Scene>(entry->before,eps);
    entry->ascene=std::make_unique<Scene>(entry->after,eps);
    if(!entry->bscene->interfaces().empty()||!entry->ascene->interfaces().empty())
      throw std::runtime_error("cached source views require uniform dielectric");
    lru.push_back(key);cache.emplace(key,Item{entry,std::prev(lru.end())});
    cached_boxes+=entry->native+entry->upper;
    return entry;
  };
  std::cout<<std::setprecision(17);
  for(const Master&m:masters){
    std::cerr<<"PAIRED "<<m.id<<std::endl;
    double margin=margin0;int attempt=0;
    while(true){
      Box window{{std::floor(m.bounds.lo[0]/tile)*tile-margin,std::floor(m.bounds.lo[1]/tile)*tile-margin,0},
       {(std::floor((m.bounds.hi[0]-1e-9)/tile)+1)*tile+margin,(std::floor((m.bounds.hi[1]-1e-9)/tile)+1)*tile+margin,1e9}};
      auto e=fetch(window);auto target=e->targets.find(m.id);
      if(target==e->targets.end()||std::abs(target->second.second-m.volume)>1e-8*m.volume+1e-16)
        throw std::runtime_error("target volume changed");
      SourceView bv{e->before,e->before_ids,m.id},av{e->after,e->after_ids,m.id};
      SourceScene bs{bv,*e->bscene},as{av,*e->ascene};
      auto r=paired<SourceSpace>(bs,as,pool,eps,capture,offset,
             seed^(0x9E3779B97F4A7C15ull*(uint64_t(m.id)+1)),minimum,maximum,tolerance,e->upper==0,attempt,alpha);
      if(!r.precise&&margin<margin_max&&r.bleak_upper+r.aleak_upper>r.delta_radius){margin*=2;++attempt;continue;}
      double n=r.walks,db=r.tally.delta.mean(n);
      std::cout<<"{\"master\":"<<m.id<<",\"before_ff\":"<<r.tally.before.mean(n)<<",\"after_ff\":"<<r.tally.after.mean(n)
        <<",\"before_sigma_ff\":"<<r.tally.before.se(n)<<",\"after_sigma_ff\":"<<r.tally.after.se(n)
        <<",\"delta_ff\":"<<db<<",\"paired_delta_sigma_ff\":"<<r.tally.delta.se(n)
        <<",\"paired_delta_confidence_radius_ff\":"<<r.delta_radius
        <<",\"before_window_return_upper_ff\":"<<r.bleak_upper<<",\"after_window_return_upper_ff\":"<<r.aleak_upper
        <<",\"full_delta_interval_low_ff\":"<<db-r.delta_radius-r.bleak_upper-r.aleak_upper
        <<",\"full_delta_interval_high_ff\":"<<db+r.delta_radius+r.bleak_upper+r.aleak_upper
        <<",\"upper_mutual_ff\":"<<r.tally.upper.mean(n)<<",\"upper_mutual_sigma_ff\":"<<r.tally.upper.se(n)
        <<",\"before_weight_bound_ff\":"<<r.before_bound<<",\"after_weight_bound_ff\":"<<r.after_bound
        <<",\"walks\":"<<r.walks<<",\"replayed_before_walks\":"<<r.tally.replays<<",\"nonzero_delta_walks\":"<<r.tally.delta.nonzero
        <<",\"native_parts\":"<<e->native<<",\"upper_parts\":"<<e->upper<<",\"target_parts\":"<<target->second.first
        <<",\"target_volume_um3\":"<<target->second.second<<",\"margin_um\":"<<margin<<",\"offset\":"<<offset
        <<",\"analysis_precision_fraction\":"<<tolerance<<",\"qualified_precision\":"<<(r.precise?"true":"false")
        <<",\"per_net_confidence\":"<<1-alpha<<",\"identical_local_scenes\":"<<(e->upper==0?"true":"false")<<"}"<<std::endl;
      break;
    }
  }
  std::cerr<<"PHYSICAL_CACHE hits="<<hits<<" misses="<<misses<<" retained_boxes="<<cached_boxes<<std::endl;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
