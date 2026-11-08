// SPDX-License-Identifier: BSD-3-Clause
// Paired reporting over the accepted uniform-dielectric field-walk kernel.
// Both expectations use the same valid closed surface. A walk is replayed
// without the upper metal only when that metal affected a nearest query.
// No physics, first-hop kernel, geometry or original file is modified.
#include <filesystem>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include "lower_paired_solver.cpp"
using namespace fsv;

namespace fsv {
struct Moments {
  double sum=0, square=0;
  uint64_t nonzero=0;
  void add(double x){sum+=x;square+=x*x;nonzero+=x!=0;}
  void merge(const Moments& m){sum+=m.sum;square+=m.square;nonzero+=m.nonzero;}
  double mean(int64_t n)const{return sum/n;}
  double variance(int64_t n)const{return std::max(0.,(square-sum*sum/n)/(n-1));}
  double se(int64_t n)const{return std::sqrt(variance(n)/n);}
  // Two-sided Maurer--Pontil Thm 4, after rescaling a range of length R.
  // An exactly zero observed variable uses the tighter exact zero-event
  // binomial bound. It NEVER produces zero uncertainty merely from no hits.
  double radius(int64_t n,double range,double absolute,double alpha)const{
    if(nonzero==0)return absolute*(-std::expm1(std::log(alpha)/n));
    double log=std::log(4/alpha);
    return std::sqrt(2*variance(n)*log/n)+7*range*log/(3*(n-1));
  }
};
struct PairTally {
  Moments before,after,delta,bleak,aleak,upper;
  uint64_t replays=0;int64_t hops=0;
  void merge(const PairTally& t){
    before.merge(t.before);after.merge(t.after);delta.merge(t.delta);
    bleak.merge(t.bleak);aleak.merge(t.aleak);upper.merge(t.upper);
    replays+=t.replays;hops+=t.hops;
  }
};

double rectangleGap(const Box&a,const Box&b){
  double d=0;
  for(int k=0;k<3;++k)d=std::max(d,std::max(b.lo[k]-a.hi[k],a.lo[k]-b.hi[k]));
  return d;
}
// Uniform eps only. Nearest(center)+rectangle radius guarantees that every
// possible closest box lies in the query. The minimum distance between
// whole closed rectangles gives a lower bound on every first cube size.
double balancedSurface(const Scene& scene,GaussianSurface<3>& gauss,
                       const CubeGreens& greens,double eps){
  std::vector<Box> source;
  const auto& g=scene.geometry();
  for(size_t i=0;i<g.boxes().size();++i)if(g.boxNet(i)==0)source.push_back(g.boxes()[i]);
  source=mergeBoxes<3>(std::move(source));
  SpatialIndex<3> source_index(source);
  std::vector<GaussianSurface<3>::Piece> balanced;
  std::vector<double> gaps;
  std::function<void(const GaussianSurface<3>::Piece&,int)> refine;
  refine=[&](const GaussianSurface<3>::Piece& piece,int depth){
    Vec3 center{};double radius=0;
    for(int k=0;k<3;++k){
      center[k]=(piece.rect.lo[k]+piece.rect.hi[k])/2;
      radius=std::max(radius,(piece.rect.hi[k]-piece.rect.lo[k])/2);
    }
    double search=scene.index().nearest(center).dist+radius+1e-9;
    Box query=piece.rect;
    for(int k=0;k<3;++k){query.lo[k]-=search;query.hi[k]+=search;}
    double gap=piece.rect.lo[2]; // infinite grounded z=0 plane
    scene.index().forEachOverlapping(query,[&](int i){
      gap=std::min(gap,rectangleGap(piece.rect,scene.geometry().boxes()[i]));
    });
    if(!(gap>0))throw std::runtime_error("Gaussian surface has no positive uniform weight bound");
    double upper=piece.rect.hi[2];
    auto close=source_index.nearest(center);
    if(close.box>=0){
      double far=0;
      const auto& b=source[close.box];
      for(int k=0;k<3;++k)far=std::max(far,std::max(b.lo[k]-piece.rect.lo[k],piece.rect.hi[k]-b.hi[k]));
      upper=std::min(upper,far);
    }
    // Subdivide only the integration rectangles, not any metal. Positive
    // importance probabilities proportional to area/min_gap bound every
    // walk; refinement avoids a tiny corner determining a huge weight for
    // an otherwise distant face. The expected flux is exactly unchanged.
    if(upper>4*gap&&depth<20){
      int axis=-1;double length=0;
      for(int k=0;k<3;++k)if(k!=piece.axis&&piece.rect.hi[k]-piece.rect.lo[k]>length){
        axis=k;length=piece.rect.hi[k]-piece.rect.lo[k];
      }
      auto first=piece,second=piece;
      double mid=(piece.rect.lo[axis]+piece.rect.hi[axis])/2;
      first.rect.hi[axis]=mid;second.rect.lo[axis]=mid;
      refine(first,depth+1);refine(second,depth+1);
    }else{balanced.push_back(piece);gaps.push_back(gap);}
  };
  for(const auto&piece:gauss.pieces)refine(piece,0);
  gauss.pieces=std::move(balanced);gauss.cumulative.clear();
  double total=0;
  for(size_t i=0;i<gaps.size();++i){total+=gauss.pieces[i].area()/gaps[i];gauss.cumulative.push_back(total);}
  for(size_t i=0;i<gaps.size();++i)gauss.pieces[i].scale=total*gaps[i];
  double bound=kEps0*eps*greens.gradientNorm()*total;
  if(!(bound>0&&std::isfinite(bound)))throw std::runtime_error("invalid walk weight bound");
  return bound*(1+1e-10);
}

struct PairResult{
  PairTally tally;int64_t walks=0;double before_bound=0,after_bound=0;
  double delta_radius=0,bleak_upper=0,aleak_upper=0,alpha=0;
  bool precise=false;
};
PairResult paired(const Scene& before,const Scene& after,WorkerPool& pool,
                  double eps,double capture,double offset,uint64_t key,
                  int64_t minimum,int64_t maximum,double tolerance,
                  bool identical,int window_attempt,double confidence_budget){
  auto greens=CubeGreens::shared(32);
  const auto& g=after.geometry();
  auto gauss=makeGaussianSurface<3>(g.boxes(),[&](int i){return g.boxNet(i);},
      after.index(),after.dielectric(),0,offset,SurfacePlacement::kClearOfShells);
  PairResult r;
  // Before has a subset of after's zero-potential conductors, hence its
  // first-cube sizes are no smaller on this same Gaussian surface.
  r.after_bound=balancedSurface(after,gauss,*greens,eps);
  r.before_bound=r.after_bound;
  // Uniform geometry has no layered tables. Retain the accepted cache API.
  auto no_tables=[](double)->const Tables<LayeredCubeGreens>&{
    throw std::runtime_error("layered dielectric outside paired uniform contract");
  };
  std::mutex mutex;
  LayeredTableCache<LayeredCubeGreens,3> bt(before.dielectric(),no_tables,mutex),
                                        at(after.dielectric(),no_tables,mutex);
  const std::vector<double> cuts;const std::vector<Vec3> nodes;
  const std::vector<std::vector<Vec3>> captures;const std::vector<int> origins;
  auto walker=[&](const Scene&s,auto&tables){
    return Walker<Space>(s.geometry(),s.index(),s.dielectric(),gauss,*greens,tables,
      capture,100000,key,-1,cuts,nodes,captures,origins,0);
  };
  auto bw=walker(before,bt),aw=walker(after,at);
  constexpr int64_t batch=256;
  int stage=0;
  int64_t goal=minimum;
  while(true){
    int64_t batches=(goal-r.walks+batch-1)/batch;
    std::vector<PairTally> results(batches);std::atomic<int64_t> next=0;
    std::exception_ptr error;std::mutex error_mutex;
    pool.run([&]{
      try{
        while(true){
          auto b=next.fetch_add(1);if(b>=batches)break;
          auto& t=results[b];
          for(int64_t j=0;j<batch;++j){
            auto id=r.walks+b*batch+j;double wa=0,wb=0;
            int64_t ah=0,bh=0;bool al=false,bl=false,changed=false;
            int bin=-1,destination=-1;
            int ac=aw.walk(id,wa,ah,al,bin,destination,&changed),bc=ac;
            if(ac==kHopGuardHit)throw std::runtime_error("paired after hop guard");
            if(changed||std::getenv("LOWER_PAIR_FORCE_REPLAY")){
              bc=bw.walk(id,wb,bh,bl,bin,destination);
              if(bc==kHopGuardHit)throw std::runtime_error("paired before hop guard");
              ++t.replays;
            }else{wb=wa;bl=al;}
            if(std::abs(wa)>r.after_bound||std::abs(wb)>r.before_bound)
              throw std::runtime_error("observed walk exceeds proved bound");
            // A fixed beta=.5 has zero expected control contribution, so
            // both means and their paired difference remain unbiased.
            double cb=wb*((bc==0?1.:0.)-.5),ca=wa*((ac==0?1.:0.)-.5);
            t.before.add(cb);t.after.add(ca);t.delta.add(ca-cb);
            t.bleak.add(bl&&bc==0?std::abs(wb):0.);
            t.aleak.add(al&&ac==0?std::abs(wa):0.);
            t.upper.add(ac==2?-wa:0.);t.hops+=ah+bh;
          }
        }
      }catch(...){std::lock_guard lock(error_mutex);if(!error)error=std::current_exception();}
    });
    if(error)std::rethrow_exception(error);
    for(const auto&t:results)r.tally.merge(t);
    r.walks+=batches*batch;
    // Sum over all doubling stages/windows is below the per-run budget.
    // Four quantities share each stage: delta, two leak means, baseline.
    r.alpha=confidence_budget/((stage+1.)*(stage+2.)*(window_attempt+1.)*(window_attempt+2.));
    double sub=r.alpha/4,db=(r.before_bound+r.after_bound)/2;
    r.delta_radius=identical?0:r.tally.delta.radius(r.walks,2*db,db,sub);
    r.bleak_upper=r.tally.bleak.mean(r.walks)+r.tally.bleak.radius(r.walks,r.before_bound,r.before_bound,sub);
    r.aleak_upper=r.tally.aleak.mean(r.walks)+r.tally.aleak.radius(r.walks,r.after_bound,r.after_bound,sub);
    double base_low=r.tally.before.mean(r.walks)-r.tally.before.radius(r.walks,r.before_bound,r.before_bound/2,sub);
    r.precise=base_low>0&&r.delta_radius+r.bleak_upper+r.aleak_upper<=tolerance*base_low;
    if(r.precise||r.walks>=maximum)break;
    goal=std::min(maximum,r.walks*2);++stage;
  }
  return r;
}
} // namespace fsv

template<class T>T rd(std::ifstream&f){
  T v{};f.read(reinterpret_cast<char*>(&v),sizeof(v));
  if(!f)throw std::runtime_error("truncated record");return v;
}
struct Master{uint32_t id;Box bounds;uint64_t boxes;double volume;};
int main(int argc,char**argv){try{
  if(argc!=12)throw std::runtime_error("tiles masters threads min_walks max_walks offset margin max_margin seed precision alpha");
  std::filesystem::path root(argv[1]);std::ifstream mf(argv[2],std::ios::binary);
  if(!mf)throw std::runtime_error("masters missing");
  std::vector<Master> masters;
  while(mf.peek()!=EOF){Master m;m.id=rd<uint32_t>(mf);
    for(auto&v:m.bounds.lo)v=rd<double>(mf);for(auto&v:m.bounds.hi)v=rd<double>(mf);
    m.boxes=rd<uint64_t>(mf);m.volume=rd<double>(mf);masters.push_back(m);
  }
  WorkerPool pool(std::stoi(argv[3]));
  int64_t minimum=std::stoll(argv[4]),maximum=std::stoll(argv[5]);
  double offset=std::stod(argv[6]),margin0=std::stod(argv[7]),margin_max=std::stod(argv[8]),tolerance=std::stod(argv[10]);
  uint64_t seed=std::stoull(argv[9]);
  double confidence_budget=std::stod(argv[11]);
  if(minimum<256||maximum<minimum||minimum%256||maximum%256||!(margin0>0&&margin_max>=margin0&&tolerance>0)
     ||!(confidence_budget>0&&confidence_budget<=.05))
    throw std::runtime_error("invalid paired options");
  std::ifstream cfg(root/"runtime.txt");double tile,eps,capture;cfg>>tile>>eps>>capture;
  if(!cfg)throw std::runtime_error("runtime missing");
  std::map<std::pair<int,int>,uint64_t> tiles;std::ifstream ti(root/"tiles.tsv");int tx,ty;uint64_t count;
  while(ti>>tx>>ty>>count)tiles[{tx,ty}]=count;
  std::cout<<std::setprecision(17);
  for(const Master&m:masters){
    std::cerr<<"PAIRED "<<m.id<<std::endl;
    double margin=margin0;int attempt=0;
    while(true){
      Box window{{std::floor(m.bounds.lo[0]/tile)*tile-margin,std::floor(m.bounds.lo[1]/tile)*tile-margin,0},
       {(std::floor((m.bounds.hi[0]-1e-9)/tile)+1)*tile+margin,(std::floor((m.bounds.hi[1]-1e-9)/tile)+1)*tile+margin,1e9}};
      Geometry b,a;
      for(auto*g:{&b,&a}){g->addNet("TARGET");g->addNet("QUIET_NATIVE");g->addNet("QUIET_UPPER");
        g->setGrounded(1);g->setWindow({{window.lo[0],window.lo[1]},{window.hi[0],window.hi[1]}});}
      uint64_t upper=0,native=0,parts=0;double volume=0;
      for(int x=std::floor(window.lo[0]/tile);x<=std::floor((window.hi[0]-1e-9)/tile);++x)
       for(int y=std::floor(window.lo[1]/tile);y<=std::floor((window.hi[1]-1e-9)/tile);++y){
        auto entry=tiles.find({x,y});if(entry==tiles.end())continue;
        auto file=root/"tiles"/(std::to_string(x)+"_"+std::to_string(y)+".bin");
        if(std::filesystem::file_size(file)!=entry->second*56)throw std::runtime_error("tile truncated");
        std::ifstream f(file,std::ios::binary);
        while(f.peek()!=EOF){
          int net=rd<int32_t>(f),owner=rd<int32_t>(f);Box box;
          for(auto&v:box.lo)v=rd<double>(f);for(auto&v:box.hi)v=rd<double>(f);
          if(owner==0){a.addBox(2,box);++upper;}
          else{int label=net==int(m.id)?0:1;b.addBox(label,box);a.addBox(label,box);++native;
            if(label==0){++parts;double v=1;for(int k=0;k<3;++k)v*=box.hi[k]-box.lo[k];volume+=v;}
          }
        }
      }
      if(!parts||std::abs(volume-m.volume)>1e-8*m.volume+1e-16)throw std::runtime_error("target volume changed");
      Scene bs(b,eps),as(a,eps);
      auto r=paired(bs,as,pool,eps,capture,offset,seed^(0x9E3779B97F4A7C15ull*(uint64_t(m.id)+1)),
                    minimum,maximum,tolerance,upper==0,attempt,confidence_budget);
      if(!r.precise&&margin<margin_max&&r.bleak_upper+r.aleak_upper>r.delta_radius){
        margin*=2;++attempt;continue;
      }
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
        <<",\"native_parts\":"<<native<<",\"upper_parts\":"<<upper<<",\"target_parts\":"<<parts
        <<",\"target_volume_um3\":"<<volume<<",\"margin_um\":"<<margin<<",\"offset\":"<<offset
        <<",\"analysis_precision_fraction\":"<<tolerance<<",\"qualified_precision\":"<<(r.precise?"true":"false")
        <<",\"per_net_confidence\":"<<1-confidence_budget<<",\"identical_local_scenes\":"<<(upper==0?"true":"false")<<"}"<<std::endl;
      break;
    }
  }
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
