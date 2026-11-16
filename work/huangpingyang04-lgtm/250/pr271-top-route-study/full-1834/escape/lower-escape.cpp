#include <algorithm>
#include <array>
#include <fstream>
#include <iostream>
#include <limits>
#include <queue>
#include <tuple>
#include <unordered_map>
#include <vector>
using namespace std;

constexpr int pitch = 3200;
constexpr int half_wire = 800;
constexpr int tile = 24000;
struct Box { int l, b, r, t; };
struct Point { int x, y, layer; };
struct Shape { int owner, layer; Box box; };
struct Landing { int x, y, end_x, end_y; bool used = false; };
struct Job { int net, owner; Box terminal; };

Box shape(Point a, Point b, int half=half_wire) {
    return {min(a.x,b.x)-half, min(a.y,b.y)-half, max(a.x,b.x)+half, max(a.y,b.y)+half};
}
bool contains(Box a, Box b) {
    return a.l <= b.l && a.b <= b.b && b.r <= a.r && b.t <= a.t;
}
bool wide(Box a) { return min(a.r-a.l, a.t-a.b) >= 3000; }

struct Occupied {
    vector<Shape> all;
    unordered_map<long long, vector<int>> bins;
    static long long key(int layer, int x, int y) { return (layer*10000LL+x)*10000+y; }
    void add(int owner, int layer, Box a) {
        int i = all.size();
        all.push_back({owner,layer,a});
        for (int x=a.l/tile; x<=a.r/tile; ++x)
            for (int y=a.b/tile; y<=a.t/tile; ++y)
                bins[key(layer,x,y)].push_back(i);
    }
    bool legal(int owner, int layer, Box a) const {
        for (int x=(a.l-3000)/tile; x<=(a.r+3000)/tile; ++x)
            for (int y=(a.b-3000)/tile; y<=(a.t+3000)/tile; ++y) {
                auto found=bins.find(key(layer,x,y));
                if (found==bins.end()) continue;
                for (int i:found->second) {
                    const auto& s=all[i];
                    const auto b=s.box;
                    if (s.owner==owner && (layer!=2 ||
                        (a.l==b.l && a.b==b.b && a.r==b.r && a.t==b.t))) continue;
                    const int gap=layer==2 ? 1760 : (wide(a)||wide(b) ? 3000 : 1600);
                    if (max(a.l-b.r,b.l-a.r)<gap && max(a.b-b.t,b.b-a.t)<gap) return false;
                }
            }
        return true;
    }
};
struct Graph {
    int x0,y0,nx,ny;
    int vertex(int x,int y,int layer) const { return ((x-x0)/pitch*ny+(y-y0)/pitch)*2+layer; }
    Point point(int v) const { return {x0+v/2/ny*pitch,y0+v/2%ny*pitch,v%2}; }
    bool fits(int x,int y) const {
        return x0<=x && x<x0+nx*pitch && y0<=y && y<y0+ny*pitch;
    }
};

vector<Point> join(const Graph& graph, const vector<int>& parent, int v) {
    vector<Point> path;
    for (int u=v;u!=-1;u=parent[u]) path.push_back(graph.point(u));
    reverse(path.begin(),path.end());
    return path;
}
bool separated_vias(const vector<Point>& path) {
    vector<Point> cuts;
    for (size_t i=1;i<path.size();++i) {
        if (path[i-1].layer==path[i].layer) continue;
        auto p=path[i];
        for (auto v:cuts) if (abs(p.x-v.x)<3360 && abs(p.y-v.y)<3360) return false;
        cuts.push_back(p);
    }
    return true;
}
vector<Point> route(const Graph& graph,const Occupied& occupancy,const Job& job,
                    const vector<Landing>& landings,const vector<int>& targets,int& selected) {
    const int size=graph.nx*graph.ny*2;
    vector<int> cost(size,numeric_limits<int>::max()), parent(size,-1), last_via(size,-1);
    using Item=pair<int,int>;
    priority_queue<Item,vector<Item>,greater<Item>> queue;
    const int from_x=max(0,(job.terminal.l+half_wire-graph.x0+pitch-1)/pitch);
    const int from_y=max(0,(job.terminal.b+half_wire-graph.y0+pitch-1)/pitch);
    for (int x=from_x; x<graph.nx && graph.x0+x*pitch<=job.terminal.r-half_wire; ++x)
        for (int y=from_y; y<graph.ny && graph.y0+y*pitch<=job.terminal.t-half_wire; ++y) {
            const int v=(x*graph.ny+y)*2+1;
            const auto p=graph.point(v);
            if (!contains(job.terminal,shape(p,p)) || !occupancy.legal(job.owner,1,shape(p,p))) continue;
            cost[v]=0;
            queue.emplace(0,v);
        }
    while(!queue.empty()) {
        auto [length,u]=queue.top();
        queue.pop();
        if (length!=cost[u]) continue;
        const auto a=graph.point(u);
        const int t=targets[u];
        if (t>=0 && !landings[t].used) {
            const auto& p=landings[t];
            const Box pad{p.x-2000,p.y-2000,p.x+2000,p.y+2000};
            if (occupancy.legal(job.owner,1,pad)) {
                auto path=join(graph,parent,u);
                if (path.size()>1 && separated_vias(path)) {
                    selected=t;
                    return path;
                }
            }
        }
        auto relax=[&](Point b) {
            if (!graph.fits(b.x,b.y)) return;
            const int v=graph.vertex(b.x,b.y,b.layer);
            const bool via=a.layer!=b.layer;
            const int next=length+(via?4:1);
            if (next>=cost[v]) return;
            if (via && last_via[u]>=0) {
                const auto previous=graph.point(last_via[u]);
                if (abs(a.x-previous.x)<3360 && abs(a.y-previous.y)<3360) return;
            }
            const auto box=shape(a,b);
            if (!occupancy.legal(job.owner,a.layer,box)) return;
            if (via && (!occupancy.legal(job.owner,b.layer,box) || !occupancy.legal(job.owner,2,box))) return;
            cost[v]=next;
            parent[v]=u;
            last_via[v]=via?u:last_via[u];
            queue.emplace(next,v);
        };
        for (int d : {-pitch,pitch}) relax(a.layer ? Point{a.x,a.y+d,1} : Point{a.x+d,a.y,0});
        relax({a.x,a.y,1-a.layer});
    }
    return {};
}

int main(int argc,char** argv) {
    if (argc!=4) return 2;
    ifstream input(argv[1]);
    ofstream out(argv[2]);
    const int goal=stoi(argv[3]);
    Graph graph{};
    int count=0;
    input>>graph.x0>>graph.y0>>graph.nx>>graph.ny>>count;
    Occupied occupancy;
    for(int i=0;i<count;++i) {
        Shape s{};
        input>>s.owner>>s.layer>>s.box.l>>s.box.b>>s.box.r>>s.box.t;
        occupancy.add(s.owner,s.layer,s.box);
    }
    input>>count;
    vector<Landing> landings(count);
    vector<int> targets(graph.nx*graph.ny*2,-1);
    for(int i=0;i<count;++i) {
        auto& l=landings[i];
        input>>l.x>>l.y>>l.end_x>>l.end_y;
        const int v=graph.vertex(l.end_x,l.end_y,1);
        if (targets.at(v)!=-1) throw runtime_error("duplicate lower landing node");
        targets[v]=i;
    }
    input>>count;
    vector<Job> jobs(count);
    for(auto& j:jobs) input>>j.net>>j.owner>>j.terminal.l>>j.terminal.b>>j.terminal.r>>j.terminal.t;
    if(!input || !out || goal<=0) return 2;
    int accepted=0, checked=0;
    for(const auto& job:jobs) {
        int selected=-1;
        auto path=route(graph,occupancy,job,landings,targets,selected);
        if(!path.empty()) {
            auto& p=landings[selected];
            p.used=true;
            for(size_t i=1;i<path.size();++i) {
                auto a=path[i-1], b=path[i];
                auto box=shape(a,b);
                occupancy.add(job.owner,a.layer,box);
                if(a.layer!=b.layer) {
                    occupancy.add(job.owner,b.layer,box);
                    occupancy.add(job.owner,2,box);
                }
            }
            occupancy.add(job.owner,1,{p.x-2000,p.y-2000,p.x+2000,p.y+2000});
            out<<job.net<<' '<<selected<<' '<<path.size()<<'\n';
            for(auto point:path) out<<point.x<<' '<<point.y<<' '<<point.layer<<'\n';
            ++accepted;
        }
        if(++checked%50==0) cerr<<"lower tried "<<checked<<" connected "<<accepted<<'\n';
        if(accepted==goal) break;
    }
    cerr<<"lower done "<<accepted<<" tried "<<checked<<" candidates "<<jobs.size()<<'\n';
}
