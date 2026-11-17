#define LASER_NO_MAIN
#include "laser-maze.cpp"

struct Gap {int id;Node a,b;};
int main(int argc,char**argv) {
 if(argc!=5)return 2;
 auto nets=read_nets(argv[1]);auto frozen=read_paths(argv[2],nets.size());
 vector<Gap> gaps;ifstream in(argv[3]);
 for(int id,x,y,a,b;in>>id>>x>>y>>a>>b;)gaps.push_back({id,{x,y,0},{a,b,0}});
 LaserBoard board(nets);
 for(auto& n:nets)board.install(n.id,frozen[n.id]);
 vector<bool> done(gaps.size());
 LaserSearch search(12);search.cell_limit=12000000;search.seek_cut_alternatives=true;
 auto save=[&] {
  write_routes(argv[4],board.routes);
  ofstream f(string(argv[4])+".pending");
  for(size_t i=0;i<gaps.size();++i)if(!done[i])f<<gaps[i].id<<"\n";
 };
 for(int wave=0;wave<4;++wave) {
  int tried=0;
  for(size_t k=0;k<gaps.size();++k) {
   size_t i=wave%2?gaps.size()-1-k:k;
   if(done[i])continue;
   auto h=gaps[i];Net target{h.id,{h.a,h.b},{}};
   size_t start=board.copper.shapes.size();
   for(auto p:frozen[h.id].vias)board.copper.add(-3,p,p,2);
   auto found=search.run(target,board.copper,wave==0?250:1000+wave*500,5);
   for(size_t j=start;j<board.copper.shapes.size();++j)board.copper.shapes[j].owner=-2;
   if(found.status==connected) {
    Route joined=frozen[h.id];
    joined.wires.insert(joined.wires.end(),found.route.wires.begin(),found.route.wires.end());
    joined.vias.insert(joined.vias.end(),found.route.vias.begin(),found.route.vias.end());
    if(legal_route(nets[h.id],joined,board.copper)) {
     board.install(h.id,move(joined));done[i]=true;
    }
   }
   if(++tried%10==0) {save();cerr<<"wave="<<wave<<" tried="<<tried<<" gaps_remaining="<<count(done.begin(),done.end(),false)<<"\n";}
  }
  save();cerr<<"wave_end="<<wave<<" gaps_remaining="<<count(done.begin(),done.end(),false)<<"\n";
  if(all_of(done.begin(),done.end(),[](bool x){return x;}))break;
 }
 save();
 cerr<<"final_gaps="<<count(done.begin(),done.end(),false)<<" graph_skips="<<search.size_skipped<<" no_graph_path="<<search.no_graph_path<<"\n";
}
