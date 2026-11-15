#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>
#include <unordered_map>
#include <utility>
#include <vector>
using namespace std;

constexpr int pitch=1600, tile=24000;
constexpr array<int,4> half_wire{400,400,800,800};
constexpr array<int,3> half_cut{400,400,800};
constexpr array<int,3> cut_spacing{880,880,1760};
constexpr uint32_t infinity=numeric_limits<uint32_t>::max();

struct Box{int l,b,r,t;};
struct Point{int x,y,layer;};
struct Shape{int owner,layer;Box box;};
struct Candidate{int x,y,ex,ey;bool used=false;};
struct Job{int index,owner;Box terminal;};

Box rect(Point a,Point b,int h) {
    return {min(a.x,b.x)-h,min(a.y,b.y)-h,max(a.x,b.x)+h,max(a.y,b.y)+h};
}
bool contains(Box a,Box b) {return a.l<=b.l&&a.b<=b.b&&a.r>=b.r&&a.t>=b.t;}
int width(Box b) {return min(b.r-b.l,b.t-b.b);}
int spacing(int layer,int w) {
    if(layer>=4) return cut_spacing[layer-4];
    if(layer>=2) return w>=3000?3000:1600;
    if(w>=3000) return 3000;
    if(w>=1800) return 1800;
    return w>=1000?1000:800;
}

class Occupancy {
public:
    vector<Shape> shapes;
    void add(Shape s) {
        const int id=shapes.size();
        shapes.push_back(s);
        const auto b=s.box;
        for(int x=b.l/tile;x<=b.r/tile;++x)
            for(int y=b.b/tile;y<=b.t/tile;++y) bins[key(s.layer,x,y)].push_back(id);
    }
    bool legal(int owner,int layer,Box a) const {
        for(int x=(a.l-3000)/tile;x<=(a.r+3000)/tile;++x)
            for(int y=(a.b-3000)/tile;y<=(a.t+3000)/tile;++y) {
                auto it=bins.find(key(layer,x,y));
                if(it==bins.end()) continue;
                for(int id:it->second) {
                    const auto s=shapes[id];
                    const auto b=s.box;
                    if(s.owner==owner && (layer<4 || (a.l==b.l&&a.r==b.r&&a.b==b.b&&a.t==b.t))) continue;
                    const int gap=spacing(layer,max(width(a),width(b)));
                    if(max(a.l-b.r,b.l-a.r)<gap && max(a.b-b.t,b.b-a.t)<gap) return false;
                }
            }
        return true;
    }
private:
    unordered_map<int,vector<int>> bins;
    static int key(int layer,int x,int y) {return (layer*1000+x)*1000+y;}
};

class Tracks {
public:
    const int x0,y0,nx,ny,points;
    Tracks(int x,int y,int lx,int ly):x0(x),y0(y),nx(lx),ny(ly),points(nx*ny) {
        for(auto& set:assigned) set.resize(points);
    }
    int index(int x,int y) const {return ((x-x0)/pitch)*ny+(y-y0)/pitch;}
    Point point(int u) const {return {x0+(u/4)/ny*pitch,y0+(u/4)%ny*pitch,u%4};}
    bool available(int edge,int pos,int owner) const {return assigned[edge][pos]==0||assigned[edge][pos]==owner;}
    bool native_track(int x,int y,int layer) const {
        return layer<2||((layer==2?y:x)%2==0);
    }
    void add(Shape s) {
        const auto b=s.box;
        const int l=s.layer;
        if(l<4) {
            const int extent=half_wire[l]+spacing(l,max(width(b),2*half_wire[l]))-1;
            rectangle(b,l,extent,(l%2==0?pitch:0),(l%2==1?pitch:0),s.owner,false);
            if(l>0) rectangle(b,l+3,extent,0,0,s.owner,false);
            if(l<3) rectangle(b,l+4,extent,0,0,s.owner,false);
        } else {
            const int extent=half_cut[l-4]+cut_spacing[l-4]-1;
            rectangle(b,l,extent,0,0,s.owner,true);
        }
    }
private:
    array<vector<int>,7> assigned;
    void rectangle(Box b,int edge,int margin,int along_x,int along_y,int owner,bool cut) {
        const int right=b.r+margin-x0,top=b.t+margin-y0;
        if(right<0||top<0) return;
        const int left=(max(0,b.l-margin-along_x-x0)+pitch-1)/pitch;
        const int bottom=(max(0,b.b-margin-along_y-y0)+pitch-1)/pitch;
        const int matching_half=cut?half_cut[edge-4]:0;
        for(int x=left;x<nx && x<=right/pitch;++x)
            for(int y=bottom;y<ny && y<=top/pitch;++y) {
                int next=owner;
                if(cut && (b.l!=x0+x*pitch-matching_half||b.r!=x0+x*pitch+matching_half||
                           b.b!=y0+y*pitch-matching_half||b.t!=y0+y*pitch+matching_half)) next=-1;
                int& cell=assigned[edge][x*ny+y];
                if(cell==0) cell=next;
                else if(cell!=next) cell=-1;
            }
    }
};

class MinQueue {
    using Item=pair<uint32_t,int>;
    array<vector<Item>,33> bins;
    uint32_t last=0;
    size_t size=0;
    int bucket(uint32_t x) const {
        const auto diff=x^last;
        return diff ? 32-__builtin_clz(diff) : 0;
    }
public:
    void clear() {for(auto& b:bins)b.clear();last=0;size=0;}
    bool empty() const {return size==0;}
    void push(uint32_t count,int node) {bins[bucket(count)].emplace_back(count,node);++size;}
    Item pop() {
        if(bins[0].empty()) {
            int i=1;
            while(bins[i].empty())++i;
            last=min_element(bins[i].begin(),bins[i].end())->first;
            for(auto entry:bins[i])bins[bucket(entry.first)].push_back(entry);
            bins[i].clear();
        }
        const auto item=bins[0].back();
        bins[0].pop_back(); --size;
        return item;
    }
};

vector<Shape> build_shapes(int owner,const vector<Point>& path,Box landing) {
    vector<Shape> shapes;
    vector<pair<int,Point>> vias;
    for(size_t i=1;i<path.size();++i) {
        const auto a=path[i-1],b=path[i];
        if(a.layer==b.layer) {
            shapes.push_back({owner,a.layer,rect(a,b,half_wire[a.layer])});
            continue;
        }
        const int v=min(a.layer,b.layer);
        const int gap=2*half_cut[v]+cut_spacing[v];
        for(const auto& [j,p]:vias)
            if(j==v&&abs(a.x-p.x)<gap&&abs(a.y-p.y)<gap) return {};
        vias.push_back({v,a});
        shapes.push_back({owner,a.layer,rect(a,a,half_wire[a.layer])});
        shapes.push_back({owner,b.layer,rect(a,a,half_wire[b.layer])});
        shapes.push_back({owner,v+4,rect(a,a,half_cut[v])});
    }
    shapes.push_back({owner,3,landing});
    return shapes;
}

class Search {
public:
    const Tracks& tracks;
    vector<uint32_t> costs;
    vector<int> predecessor;
    vector<int> previous_via;
    MinQueue queue;
    uint64_t settled=0;
    explicit Search(const Tracks& g):tracks(g),costs(4*g.points),predecessor(4*g.points),previous_via(4*g.points) {}
    pair<int,vector<Point>> run(const Occupancy& occupied,const Job& job,const vector<Candidate>& landings,
                               const vector<int>& targets,int via_penalty) {
        fill(costs.begin(),costs.end(),infinity);
        queue.clear();
        const int xlo=(max(0,job.terminal.l+800-tracks.x0)+pitch-1)/pitch;
        const int ylo=(max(0,job.terminal.b+800-tracks.y0)+pitch-1)/pitch;
        for(int x=xlo;x<tracks.nx && tracks.x0+x*pitch<=job.terminal.r-800;++x)
            for(int y=ylo;y<tracks.ny && tracks.y0+y*pitch<=job.terminal.t-800;++y) {
                if(!tracks.native_track(x,y,3)) continue;
                const int u=(x*tracks.ny+y)*4+3;
                const auto p=tracks.point(u);
                const auto box=rect(p,p,800);
                if(!contains(job.terminal,box)||!occupied.legal(job.owner,3,box)) continue;
                costs[u]=0; predecessor[u]=-1; previous_via[u]=-1;
                queue.push(0,u);
            }
        while(!queue.empty()) {
            const auto [cost,u]=queue.pop();
            if(cost!=costs[u])continue;
            ++settled;
            const int layer=u%4,pos=u/4,x=pos/tracks.ny,y=pos%tracks.ny;
            const Point p=tracks.point(u);
            const int target=layer==3?targets[pos]:-1;
            if(target>=0 && !landings[target].used) {
                const auto l=landings[target];
                const Box pad{l.x-2000,l.y-2000,l.x+2000,l.y+2000};
                if(occupied.legal(job.owner,3,pad)) {
                    vector<Point> path;
                    for(int v=u;v!=-1;v=predecessor[v])path.push_back(tracks.point(v));
                    reverse(path.begin(),path.end());
                    const auto added=build_shapes(job.owner,path,pad);
                    if(path.size()>1&&!added.empty()&&all_of(added.begin(),added.end(),[&](const auto& s){
                        return occupied.legal(s.owner,s.layer,s.box);
                    })) return {target,move(path)};
                }
            }
            auto relax=[&](int v,int edge,int index,bool via) {
                if(!tracks.available(edge,index,job.owner))return;
                const uint32_t next=cost+(via?via_penalty:1);
                if(next>=costs[v])return;
                if(via&&previous_via[u]>=0 && previous_via[u]%4==edge-4) {
                    const auto a=tracks.point(previous_via[u]);
                    const int gap=2*half_cut[edge-4]+cut_spacing[edge-4];
                    if(abs(a.x-p.x)<gap&&abs(a.y-p.y)<gap)return;
                }
                costs[v]=next;
                predecessor[v]=u;
                previous_via[v]=via?4*pos+(edge-4):previous_via[u];
                queue.push(next,v);
            };
            if(layer%2==0) {
                if(x>0)relax(u-4*tracks.ny,layer,pos-tracks.ny,false);
                if(x+1<tracks.nx)relax(u+4*tracks.ny,layer,pos,false);
            } else {
                if(y>0)relax(u-4,layer,pos-1,false);
                if(y+1<tracks.ny)relax(u+4,layer,pos,false);
            }
            if(layer>0&&tracks.native_track(x,y,layer-1))relax(u-1,layer+3,pos,true);
            if(layer<3&&tracks.native_track(x,y,layer+1))relax(u+1,layer+4,pos,true);
        }
        return {-1,{}};
    }
};

int main(int argc,char** argv) {
    if(argc!=5)return 2;
    ifstream in(argv[1]);
    ofstream out(argv[2]);
    const int target_count=stoi(argv[3]),via_penalty=stoi(argv[4]);
    int x0,y0,nx,ny,n;
    in>>x0>>y0>>nx>>ny>>n;
    if(!in || !out || min(nx,ny)<=0 || min(target_count,via_penalty)<=0)return 2;
    Tracks tracks(x0,y0,nx,ny);
    Occupancy occupied;
    auto commit=[&](Shape s){
        occupied.add(s);
        tracks.add(s);
    };
    for(int i=0;i<n;++i){
        Shape s{};
        in>>s.owner>>s.layer>>s.box.l>>s.box.b>>s.box.r>>s.box.t;
        commit(s);
    }
    in>>n;
    vector<Candidate> landings(n);
    vector<int> targets(tracks.points,-1);
    for(int i=0;i<n;++i) {
        auto& p=landings[i];
        in>>p.x>>p.y>>p.ex>>p.ey;
        const int id=tracks.index(p.ex,p.ey);
        if(targets.at(id)>=0)throw runtime_error("overlapping landing target nodes");
        targets[id]=i;
    }
    in>>n;
    vector<Job> jobs(n);
    for(auto& j:jobs)in>>j.index>>j.owner>>j.terminal.l>>j.terminal.b>>j.terminal.r>>j.terminal.t;
    if(!in)return 2;
    Search router(tracks);
    int tried=0,accepted=0;
    for(const auto& j:jobs) {
        auto [i,path]=router.run(occupied,j,landings,targets,via_penalty);
        if(i>=0) {
            auto& l=landings[i];
            l.used=true;
            const Box pad{l.x-2000,l.y-2000,l.x+2000,l.y+2000};
            for(auto s:build_shapes(j.owner,path,pad))commit(s);
            out<<j.index<<' '<<i<<' '<<path.size()<<'\n';
            for(auto p:path)out<<p.x<<' '<<p.y<<' '<<p.layer<<'\n';
            ++accepted;
        }
        if(++tried%40==0)cerr<<"tried "<<tried<<" added "<<accepted<<" expanded "<<router.settled<<'\n';
        if(accepted>=target_count)break;
    }
    cerr<<"added "<<accepted<<" tried "<<tried<<" candidates "<<jobs.size()<<" expanded "<<router.settled<<'\n';
    return 0;
}
