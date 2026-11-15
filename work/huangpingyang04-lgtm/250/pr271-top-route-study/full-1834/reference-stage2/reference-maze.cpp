// Physical-track adapter for the original CUGR fine maze loop.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <memory>
#include <numeric>
#include <stdexcept>
#include <queue>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <vector>
using namespace std;

constexpr int pitch = 21;
constexpr int width = 10;
constexpr int spacing = 20;
constexpr int via_spacing = 21;
struct Node { int x, y, layer; };
struct Rect { int left, bottom, right, top; };
struct Wire { Node a, b; };
struct Net { int id; vector<Node> pins; vector<Rect> windows; };
struct Route { vector<Wire> wires; vector<Node> vias; };
constexpr int tile = 105;
constexpr int max_pos = 50000;

int llx, lly, urx, ury;
uint64_t key(Node n) { return (uint64_t(n.x) << 17) | (uint64_t(n.y) << 1) | n.layer; }
Node unpack(uint64_t x) { return {int(x >> 17), int((x >> 1) & 65535), int(x & 1)}; }
int md(Node a, Node b) { return abs(a.x-b.x)+abs(a.y-b.y); }
bool via_conflict(Node a, Node b) {
    return (a.x!=b.x || a.y!=b.y) && abs(a.x-b.x)<via_spacing && abs(a.y-b.y)<via_spacing;
}
vector<Node> cuts(const vector<Node>& path) {
    vector<Node> result;
    for(size_t i=1;i<path.size();i++) if(path[i-1].layer!=path[i].layer) result.push_back(path[i]);
    return result;
}
bool on_track(Node n) { return n.x % pitch == 0 && n.y % pitch == 0; }
bool contains(const Rect& r, Node a, Node b) {
    return r.left<=min(a.x,b.x) && max(a.x,b.x)<=r.right
        && r.bottom<=min(a.y,b.y) && max(a.y,b.y)<=r.top;
}
bool allowed(Node a, Node b, const Net& n) {
    if (on_track(a) && on_track(b)) return true;
    for (auto w : n.windows) if (contains(w,a,b)) return true;
    return false;
}
struct Occupancy {
    struct Shape { int owner, layer, x0, y0, x1, y1; };
    vector<Shape> shapes;
    unordered_map<int, vector<int>> bins;
    static int bin(int x,int y,int layer) { return ((layer*1000+x)*1000+y); }
    void add(int owner, Node a, Node b, int layer) {
        int x0 = min(a.x,b.x), y0 = min(a.y,b.y), x1 = max(a.x,b.x), y1 = max(a.y,b.y);
        int index = shapes.size();
        shapes.push_back({owner,layer,x0,y0,x1,y1});
        for (int x=x0/tile; x<=x1/tile; x++)
            for (int y=y0/tile; y<=y1/tile; y++)
                bins[bin(x,y,layer)].push_back(index);
    }
    void add_route(int owner,const Route& r) {
        for (auto w:r.wires) add(owner,w.a,w.b,w.a.layer);
        for (auto v:r.vias) for(int layer=0;layer<3;layer++) add(owner,v,v,layer);
    }
    int blocker(int owner, Node a, Node b, int layer, unordered_set<int>* blockers=nullptr) const {
        int x0=min(a.x,b.x), y0=min(a.y,b.y), x1=max(a.x,b.x), y1=max(a.y,b.y);
        int d=(layer==2 ? via_spacing:spacing);
        for(int x=max(0,x0-d+1)/tile;x<=(x1+d-1)/tile;x++)
            for(int y=max(0,y0-d+1)/tile;y<=(y1+d-1)/tile;y++) {
                auto found=bins.find(bin(x,y,layer));
                if (found==bins.end()) continue;
                for(int i:found->second) {
                    const auto& s=shapes[i];
                    if (s.owner==owner && (layer!=2 || (x0==s.x0 && y0==s.y0))) continue;
                    if (max(x0-s.x1,s.x0-x1)<d && max(y0-s.y1,s.y0-y1)<d) {
                        if(!blockers) return s.owner;
                        blockers->insert(s.owner);
                    }
                }
            }
        return -1;
    }
    bool fits(Node p) const { return llx<=p.x && p.x<=urx && lly<=p.y && p.y<=ury; }
    int blocked(int owner, Node a, Node b) const {
        if (!fits(b)) return -2;
        if (a.layer==b.layer) return blocker(owner,a,b,a.layer);
        for (int layer=0;layer<3;layer++) {
            int result=blocker(owner,a,b,layer);
            if (result!=-1) return result;
        }
        return -1;
    }
};

constexpr uint32_t cost_scale = 32;
constexpr int capacity = 5;
constexpr uint32_t infinity = numeric_limits<uint32_t>::max();

class TrackGraph {
public:
    const int x0 = ((llx + pitch - 1) / pitch) * pitch;
    const int y0 = ((lly + pitch - 1) / pitch) * pitch;
    const int nx = (urx - x0) / pitch + 1;
    const int ny = (ury - y0) / pitch + 1;
    const int points = nx * ny;
    enum Kind { horizontal, vertical, via };

    TrackGraph() {
        for (auto& v : blocked) v.resize(points);
        for (auto& v : own) v.resize(points);
        for (auto& v : demand) v.resize(points);
        // CUGR Eqs. (4) and (5) with unit overflow cost 4 and logistic slope 1.
        const auto overflow = [](int used) { return 1.0 / (1 + exp(capacity - used)); };
        for (int used = 0; used <= capacity; ++used) {
            wire_cost[used] = lround(cost_scale * pitch *
                                    (1 + 4.0 * used / capacity * overflow(used)));
            for (int other = 0; other <= capacity; ++other) {
                via_cost[used][other] = lround(cost_scale * 28 *
                                              (1 + overflow(used) + overflow(other)));
            }
        }
    }

    int vertex(Node n) const {
        return 2 * (((n.x - x0) / pitch) * ny + (n.y - y0) / pitch) + n.layer;
    }
    Node node(int v) const {
        const int p = v / 2;
        return {x0 + p / ny * pitch, y0 + p % ny * pitch, v % 2};
    }

    void occupy(Node a, Node b, int layer) {
        for_shape(a, b, layer, [&](int kind, int x, int y) {
            const int p = x * ny + y;
            if (blocked[kind][p]++ != 0 || kind == via) return;
            // Every available edge samples five parallel track positions around it.
            for (int d = -2; d <= 2; ++d) {
                const int row = y + (kind == horizontal ? d : 0);
                const int col = x + (kind == vertical ? d : 0);
                if (row >= 0 && row < ny && col >= 0 && col < nx)
                    ++demand[kind][col * ny + row];
            }
        });
    }
    void occupy(const Route& route) {
        for (auto w : route.wires) occupy(w.a, w.b, w.a.layer);
        for (auto p : route.vias)
            for (int layer = 0; layer <= 2; ++layer) occupy(p, p, layer);
    }
    void use_pads(const Net& net) {
        for (auto [kind, p] : touched) own[kind][p] = 0;
        touched.clear();
        for (auto pad : net.pins) {
            for_shape(pad, pad, 0, [&](int kind, int x, int y) {
                const int p = x * ny + y;
                if (own[kind][p]++ == 0) touched.emplace_back(kind, p);
            });
        }
    }
    void via_exclusions(Node p, vector<int>& excluded) const {
        for_box(p.x - via_spacing + 1, p.x + via_spacing - 1,
                p.y - via_spacing + 1, p.y + via_spacing - 1, nx, ny,
                [&](int x, int y) {
            if (x0 + x * pitch != p.x || y0 + y * pitch != p.y)
                excluded.push_back(x * ny + y);
        });
    }
    bool available(int kind, int p) const { return blocked[kind][p] == own[kind][p]; }
    uint32_t cost(int kind, int p, int x, int y) const {
        if (kind != via) return wire_cost[demand[kind][p]];
        const int h = x == nx - 1 && x ? p - ny : p;
        const int v = y == ny - 1 && y ? p - 1 : p;
        return via_cost[demand[horizontal][h]][demand[vertical][v]];
    }

private:
    array<vector<uint16_t>, 3> blocked, own;
    array<vector<uint8_t>, 2> demand;
    array<uint32_t, capacity + 1> wire_cost{};
    array<array<uint32_t, capacity + 1>, capacity + 1> via_cost{};
    vector<pair<int, int>> touched;

    template<class F>
    void for_box(int min_x, int max_x, int min_y, int max_y, int cols, int rows, F visit) const {
        if (max_x < x0 || max_y < y0) return;
        const int left = (max(min_x - x0, 0) + pitch - 1) / pitch;
        const int bottom = (max(min_y - y0, 0) + pitch - 1) / pitch;
        const int right = min(cols - 1, (max_x - x0) / pitch);
        const int top = min(rows - 1, (max_y - y0) / pitch);
        for (int x = left; x <= right; ++x)
            for (int y = bottom; y <= top; ++y) visit(x, y);
    }
    template<class F>
    void for_shape(Node a, Node b, int layer, F visit) const {
        const int margin = (layer == 2 ? via_spacing : spacing) - 1;
        const int min_x = min(a.x, b.x) - margin, max_x = max(a.x, b.x) + margin;
        const int min_y = min(a.y, b.y) - margin, max_y = max(a.y, b.y) + margin;
        if (layer == horizontal)
            for_box(min_x - pitch, max_x, min_y, max_y, nx - 1, ny,
                    [&](int x, int y) { visit(horizontal, x, y); });
        if (layer == vertical)
            for_box(min_x, max_x, min_y - pitch, max_y, nx, ny - 1,
                    [&](int x, int y) { visit(vertical, x, y); });
        for_box(min_x, max_x, min_y, max_y, nx, ny,
                [&](int x, int y) { visit(via, x, y); });
    }
};

void append_path(Route& route, const Net& net, const vector<Node>& path) {
    vector<Wire> wires;
    for (size_t i = 1; i < path.size(); ++i) {
        auto a = path[i-1], b = path[i];
        if (a.layer != b.layer) {
            if (none_of(route.vias.begin(), route.vias.end(),
                        [&](Node v) { return v.x == a.x && v.y == a.y; })) route.vias.push_back(a);
            continue;
        }
        if (!wires.empty() && key(wires.back().b) == key(a) &&
            (a.layer ? ((a.y > wires.back().a.y) == (b.y > a.y))
                     : ((a.x > wires.back().a.x) == (b.x > a.x))) &&
            allowed(wires.back().a, b, net)) {
            wires.back().b = b;
        } else {
            wires.push_back({a, b});
        }
    }
    route.wires.insert(route.wires.end(), wires.begin(), wires.end());
}

void write_routes(const string& path,const vector<Route>& routes) {
    ofstream output(path,ios::trunc);
    for(size_t id=0;id<routes.size();id++) {
        auto& r=routes[id];
        if(r.wires.empty() && r.vias.empty()) continue;
        output<<id<<" "<<r.wires.size()<<" "<<r.vias.size()<<"\n";
        for(auto w:r.wires) output<<w.a.x<<" "<<w.a.y<<" "<<w.b.x<<" "<<w.b.y<<" "<<w.a.layer<<"\n";
        for(auto v:r.vias) output<<v.x<<" "<<v.y<<"\n";
    }
}


enum Direction { main_minus, main_plus, vertical_move, fine_minus, fine_plus };
constexpr array<Direction,5> directions{main_minus,main_plus,vertical_move,fine_minus,fine_plus};

class DetailedGraph {
    struct Edges { array<int,5> target; Edges() {target.fill(-1);} };
    const TrackGraph& tracks;
    const int base;
    vector<int> extra_index;
    vector<int> attached;
    vector<Edges> extra_edges;
    vector<Node> off_track;
    unordered_map<uint64_t,int> off_index;
    vector<int> pin_vertices;
    vector<int> pin_index;

    int vertex(Node n) {
        if(on_track(n)) return tracks.vertex(n);
        auto found=off_index.find(key(n));
        if(found!=off_index.end()) return found->second;
        int id=base+int(off_track.size());
        off_index.emplace(key(n),id);
        off_track.push_back(n);
        extra_index.push_back(-1);
        pin_index.push_back(-1);
        return id;
    }
    Edges& extra(int v) {
        int& i=extra_index[v];
        if(i<0) {
            i=extra_edges.size();
            extra_edges.emplace_back();
            attached.push_back(v);
        }
        return extra_edges[i];
    }
    void connect(Node a,Node b,Direction ab,Direction ba) {
        const int u=vertex(a),v=vertex(b);
        extra(u).target[ab]=v;
        extra(v).target[ba]=u;
    }
    int extra_edge(int u,Direction d) const {
        const int at=extra_index[u];
        return at<0?-1:extra_edges[at].target[d];
    }
public:
    int owner=-1;
    explicit DetailedGraph(const TrackGraph& g)
        : tracks(g),base(2*g.points),extra_index(base,-1),pin_index(base,-1) {}

    void load(const Net& net,const Occupancy& fixed) {
        for(int u:attached) if(u<base) extra_index[u]=-1;
        for(int u:pin_vertices) if(u<base) pin_index[u]=-1;
        extra_index.resize(base);
        pin_index.resize(base);
        attached.clear();
        extra_edges.clear();
        off_track.clear();
        off_index.clear();
        pin_vertices.clear();
        owner=net.id;
        for(const auto p:net.pins) {
            int id=vertex(p);
            if(pin_index[id]>=0)
                throw runtime_error("Two fixed terminals share a physical landing");
            pin_index[id]=pin_vertices.size();
            pin_vertices.push_back(id);
        }
        for(const auto w:net.windows) {
            const int left=max(llx,w.left),right=min(urx,w.right);
            const int bottom=max(lly,w.bottom),top=min(ury,w.top);
            for(int x=left;x<=right;++x) {
                for(int y=bottom;y<=top;++y) {
                    const Node h{x,y,0},v{x,y,1};
                    if(x<right) {
                        const Node next{x+1,y,0};
                        if(fixed.blocked(owner,h,next)==-1) connect(h,next,fine_plus,fine_minus);
                    }
                    if(y<top) {
                        const Node next{x,y+1,1};
                        if(fixed.blocked(owner,v,next)==-1) connect(v,next,fine_plus,fine_minus);
                    }
                    if(!on_track(h)&&fixed.blocked(owner,h,v)==-1) connect(h,v,vertical_move,vertical_move);
                }
            }
        }
    }
    int getNodeNum() const {return base+int(off_track.size());}
    array<int,1> getVertices(int i) const {return {pin_vertices.at(i)};}
    int getPinIdx(int u) const {return pin_index[u];}
    Node point(int u) const {return u<base?tracks.node(u):off_track[u-base];}
    struct LayerPoint {int layerIdx;};
    LayerPoint getPoint(int u) const {return {point(u).layer};}
    void writeDebugFile(const string&) const {}

    bool hasEdge(int u,Direction d) const {
        if(d==fine_minus||d==fine_plus||u>=base) return extra_edge(u,d)>=0;
        const int p=u/2;
        if(d==vertical_move) return tracks.available(TrackGraph::via,p);
        if(u%2==0) {
            const int x=p/tracks.ny;
            return d==main_minus ? x>0&&tracks.available(TrackGraph::horizontal,p-tracks.ny)
                                 : x+1<tracks.nx&&tracks.available(TrackGraph::horizontal,p);
        }
        const int y=p%tracks.ny;
        return d==main_minus ? y>0&&tracks.available(TrackGraph::vertical,p-1)
                             : y+1<tracks.ny&&tracks.available(TrackGraph::vertical,p);
    }
    int getEdgeEndPoint(int u,Direction d) const {
        if(d==fine_minus||d==fine_plus||u>=base) return extra_edge(u,d);
        if(d==vertical_move) return u^1;
        const int scale=(u%2==0?2*tracks.ny:2);
        return d==main_minus?u-scale:u+scale;
    }
    uint32_t getEdgeCost(int u,Direction d) const {
        if(d==fine_minus||d==fine_plus) return cost_scale;
        if(u>=base) return cost_scale*28;
        const int p=u/2;
        if(d==vertical_move) return tracks.cost(TrackGraph::via,p,p/tracks.ny,p%tracks.ny);
        const int length=(u%2==0?tracks.ny:1);
        const int edge=d==main_minus?p-length:p;
        return tracks.cost(u%2,edge,0,0);
    }

    bool can_reach_track(int pin) const {
        const int u=pin_vertices[pin];
        if(u<base) return true;
        vector<int> queue={u};
        unordered_set<int> seen={u};
        for(size_t head=0;head<queue.size();++head) {
            for(auto dir:{fine_minus,fine_plus,vertical_move}) {
                const int v=extra_edge(queue[head],dir);
                if(v<0) continue;
                if(v<base) return true;
                if(seen.insert(v).second) queue.push_back(v);
            }
        }
        return false;
    }
};

namespace db {
using CostT=uint32_t;
enum class RouteStatus { SUCC_NORMAL, FAIL_DISCONNECTED_GRID_GRAPH };
struct MetalLayer {};
}
struct DatabaseShim {
    db::MetalLayer layer;
    const db::MetalLayer& getLayer(int) const {return layer;}
} database;
struct Solution {
    db::CostT cost;
    int vertex;
    shared_ptr<Solution> prev;
    Solution(db::CostT c,int v,const shared_ptr<Solution>& p) : cost(c),vertex(v),prev(p) {}
};
class MazeRoute {
public:
    explicit MazeRoute(const TrackGraph& t) : graph(t) {}
    DetailedGraph graph;
    vector<db::CostT> vertexCosts;
    vector<shared_ptr<Solution>> pinSols;
    vector<int> mergedPinAccessBoxes;
    struct {string getName() const {return {};}} grNet;
    db::RouteStatus route(int startPin);

    db::RouteStatus run(const Net& net,const Occupancy& occupied) {
        graph.load(net,occupied);
        vertexCosts.assign(graph.getNodeNum(),infinity);
        pinSols.assign(net.pins.size(),nullptr);
        mergedPinAccessBoxes.resize(net.pins.size());
        return route(0);
    }
};

// The upstream loop itself is compiled unchanged. The standalone harness
// suppresses its diagnostics and interactive pause on disconnected inputs.
#define printWarnMsg(...) ((void)0)
#define printlog(...) ((void)0)
#define getchar() ((void)0)
#include "cugr-maze-route.inc"
#undef getchar
#undef printlog
#undef printWarnMsg

bool extract_route(const Net& net,const MazeRoute& maze,Route& out) {
    unordered_set<int> connected;
    for(const auto& pin:maze.pinSols) {
        vector<Node> branch;
        for(auto it=pin;it;it=it->prev) {
            branch.push_back(maze.graph.point(it->vertex));
            if(!connected.insert(it->vertex).second) break;
        }
        reverse(branch.begin(),branch.end());
        append_path(out,net,branch);
    }
    for(size_t i=0;i<out.vias.size();++i)
        for(size_t j=0;j<i;++j)
            if(via_conflict(out.vias[i],out.vias[j])) return false;
    return !out.wires.empty()||!out.vias.empty();
}

int main(int argc,char** argv) {
    if(argc!=3) {
        cerr<<"usage: reference-maze graph.txt paths.txt\n";
        return 1;
    }
    ifstream input(argv[1]);
    int count=0;
    input>>llx>>lly>>urx>>ury>>count;
    if(!input||count<=0||llx<0||lly<0||urx-llx<pitch||ury-lly<pitch||
       urx>=max_pos||ury>=max_pos) return 2;
    vector<Net> nets(count);
    Occupancy occupied;
    TrackGraph graph;
    for(int id=0;id<count;++id) {
        auto& n=nets[id];
        int pins=0,windows=0;
        input>>n.id>>pins>>windows;
        if(!input||n.id!=id||pins<2||windows<0)return 2;
        n.pins.resize(pins);
        n.windows.resize(windows);
        for(auto& p:n.pins) {
            input>>p.x>>p.y;
            p.layer=0;
            if(!input||!occupied.fits(p))return 2;
            occupied.add(id,p,p,0);
            graph.occupy(p,p,0);
        }
        for(auto& r:n.windows)input>>r.left>>r.bottom>>r.right>>r.top;
    }
    if(!input)return 2;
    MazeRoute maze(graph);
    vector<Route> routes(count);
    array<int,5> totals{};
    for(const auto& net:nets) {
        graph.use_pads(net);
        auto& candidate=routes[net.id];
        if(maze.run(net,occupied)==db::RouteStatus::SUCC_NORMAL) {
            if(extract_route(net,maze,candidate)) {
                occupied.add_route(net.id,candidate);
                graph.occupy(candidate);
                ++totals[0];
            } else {
                candidate={};
                ++totals[4];
            }
        } else {
            size_t pin=0;
            for(;pin<net.pins.size();++pin) if(!maze.graph.can_reach_track(pin))break;
            ++totals[pin==0?1:pin<net.pins.size()?2:3];
        }
        if((net.id+1)%100==0) cerr<<"processed "<<net.id+1<<" routed "<<totals[0]<<'\n';
    }
    write_routes(argv[2],routes);
    cerr<<"done "<<totals[0]<<" / "<<count<<" driver_window="<<totals[1]<<" sink_window="<<totals[2]
        <<" graph_disconnected="<<totals[3]<<" self_geometry_rejected="<<totals[4]<<'\n';
    return 0;
}
