// Estimate route scarcity from geometrically valid fine-maze paths with fixed M10 landings.
#define main adapter_main
#include "trunk-engine.cpp"
#undef main

using Corridor = array<int,3>;

Corridor lanes_on_cuts(const Route& route, Node a, Node b) {
    const bool along_x=abs(a.x-b.x)>=abs(a.y-b.y);
    const int start=along_x?a.x:a.y, finish=along_x?b.x:b.y;
    Corridor result{-1,-1,-1};
    for(auto w:route.wires) {
        if(w.a.layer!=(along_x?0:1))continue;
        const int l=along_x?w.a.x:w.a.y, r=along_x?w.b.x:w.b.y;
        const int lane=along_x?w.a.y:w.a.x;
        for(int k=0;k<3;++k) {
            const int cut=(start*(3-k)+finish*(k+1))/4;
            if(min(l,r)<=cut&&cut<=max(l,r)&&result[k]<0)result[k]=lane;
        }
    }
    return result;
}

bool diverse(const Corridor& a,const Corridor& b,int span) {
    int distant=0;
    for(size_t i=0;i<a.size();++i)if(a[i]>=0&&b[i]>=0&&abs(a[i]-b[i])>=2*pitch)++distant;
    return distant>=(span>=500?2:1);
}

int main(int argc,char** argv) {
    if(argc!=4)return 2;
    const auto nets=read_nets(argv[1]);
    if(nets.size()!=1184)throw runtime_error("Unexpected probe input");
    const int part=stoi(argv[2]), total=stoi(argv[3]);
    if(part<0||part>=total)return 2;
    Board open(nets), scored(nets);
    Router nearby(scored.tracks,2,false,28,630), wider(scored.tracks,2,false,28,1600);
    unsigned records=0;
    cout<<"net_index\tpin_index\tsampled_corridors\tspan\n";
    for(const auto& n:nets) {
        if(n.id%total!=part)continue;
        open.tracks.use_pads(n);
        scored.tracks.use_pads(n);
        for(size_t pin=1;pin<n.pins.size();++pin) {
            auto demand=n;
            demand.pins={n.pins.front(),n.pins[pin]};
            demand.windows={n.windows.front(),n.windows[pin]};
            const int span=md(demand.pins[0],demand.pins[1]);
            auto first=nearby.run(demand,open.occupied);
            if(first.status!=connected)first=wider.run(demand,open.occupied);
            vector<Corridor> seen;
            vector<pair<Range,Route>> proposals;
            if(first.status==connected) {
                seen.push_back(lanes_on_cuts(first.route,demand.pins[0],demand.pins[1]));
                proposals.emplace_back(scored.place(int(nets.size())+n.id,first.route),move(first.route));
                for(unsigned cost: {unsigned(250*cost_scale),unsigned(620*cost_scale)}) {
                    scored.tracks.use_relaxed_cost(&open.tracks,cost);
                    auto trial=wider.run(demand,open.occupied,&scored.occupied,cost);
                    scored.tracks.use_relaxed_cost(nullptr,0);
                    if(trial.status!=connected)continue;
                    auto profile=lanes_on_cuts(trial.route,demand.pins[0],demand.pins[1]);
                    if(all_of(seen.begin(),seen.end(),[&](const auto& saved){return diverse(saved,profile,span);}))
                        seen.push_back(profile);
                    proposals.emplace_back(scored.place(int(nets.size())+n.id,trial.route),move(trial.route));
                }
                for(const auto& p:proposals)scored.release(p.first,p.second);
            }
            cout<<n.id<<'\t'<<pin<<'\t'<<seen.size()<<'\t'<<span<<'\n';
            ++records;
        }
    }
    cerr<<"part="<<part<<" checked="<<records<<" upstream_matched="<<nearby.matched+wider.matched<<'\n';
}
