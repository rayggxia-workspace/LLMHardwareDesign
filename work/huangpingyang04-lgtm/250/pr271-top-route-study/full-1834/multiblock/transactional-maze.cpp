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
                    if (s.owner == -2) continue;
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

// Collect several independently reachable main-track locations in each pin window.
vector<vector<Node>> portals(Node pin, const Net& n, const Occupancy& occ,
                             const vector<Node>& existing, int count) {
    using Entry = pair<int,uint64_t>;
    priority_queue<Entry, vector<Entry>, greater<Entry>> q;
    unordered_map<uint64_t,pair<int,uint64_t>> prev;
    uint64_t start=key(pin);
    q.emplace(0,start); prev[start]={0,start};
    vector<vector<Node>> results;
    auto add=[&](Node a,Node b,int d) {
        if (!occ.fits(b) || !allowed(a,b,n) || occ.blocked(n.id,a,b)!=-1) return;
        uint64_t k=key(b), parent=key(a);
        auto it=prev.find(k);
        if (it!=prev.end() && it->second.first<=d) return;
        prev[k]={d,parent};
        q.emplace(d,k);
    };
    while(!q.empty() && int(results.size())<count) {
        auto [dist, id]=q.top(); q.pop();
        if(prev[id].first!=dist) continue;
        Node a=unpack(id);
        if(on_track(a)) {
            vector<Node> path;
            for(auto k=id;;k=prev[k].second) {
                path.push_back(unpack(k));
                if(k==start) break;
            }
            reverse(path.begin(),path.end());
            // Eliminate local paths that violate spacing between their own vias.
            vector<Node> vias;
            bool valid=true;
            for(size_t i=1;i<path.size();i++) if(path[i-1].layer!=path[i].layer) {
                for(auto v:vias) if(abs(v.x-path[i].x)<via_spacing && abs(v.y-path[i].y)<via_spacing)
                    valid=false;
                vias.push_back(path[i]);
            }
            for(auto v:vias) for(auto current:existing) if(via_conflict(v,current)) valid=false;
            if(valid) results.push_back(move(path));
            continue;
        }
        bool turn=true;
        for(auto v:existing) if(via_conflict(v,a)) turn=false;
        if(turn) {
            for(auto node=id;prev[node].second!=node;node=prev[node].second) {
                auto u=unpack(node), v=unpack(prev[node].second);
                if(u.layer!=v.layer && (via_conflict(a,u) || (a.x==u.x && a.y==u.y))) {
                    turn=false;
                    break;
                }
            }
        }
        if(turn) add(a,{a.x,a.y,1-a.layer},dist+14);
        for(int delta:{-1,1}) {
            auto b=a;
            (b.layer?b.y:b.x)+=delta;
            add(a,b,dist+1);
        }
    }
    return results;
}

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

    void occupy(Node a, Node b, int layer, int delta=1) {
        for_shape(a, b, layer, [&](int kind, int x, int y) {
            const int p = x * ny + y;
            auto& count = blocked[kind][p];
            const bool was_blocked = count != 0;
            count += delta;
            if (was_blocked == (count != 0) || kind == via) return;
            // Every available edge samples five parallel track positions around it.
            for (int d = -2; d <= 2; ++d) {
                const int row = y + (kind == horizontal ? d : 0);
                const int col = x + (kind == vertical ? d : 0);
                if (row >= 0 && row < ny && col >= 0 && col < nx)
                    demand[kind][col * ny + row] += delta;
            }
        });
    }
    void occupy(const Route& route, int delta=1) {
        for (auto w : route.wires) occupy(w.a, w.b, w.a.layer, delta);
        for (auto p : route.vias)
            for (int layer = 0; layer <= 2; ++layer) occupy(p, p, layer, delta);
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
    unordered_set<int> forbidden_vias;

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
        forbidden_vias.clear();
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

    void forbid_via(Node p) {
        forbidden_vias.insert(vertex({p.x,p.y,0}));
        forbidden_vias.insert(vertex({p.x,p.y,1}));
    }
    bool hasEdge(int u,Direction d) const {
        if(d==vertical_move&&!forbidden_vias.empty()&&forbidden_vias.count(u))return false;
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


// Arena storage for the same MazeRoute::route state transitions. The heap
// compares cost alone, as upstream, and keeps immutable predecessor indices.
class FastMaze {
    struct Label {uint32_t cost; int vertex,parent;};
    struct Key {uint32_t cost; int label;};
    struct Later {bool operator()(Key a,Key b)const{return a.cost>b.cost;}};
    vector<Label> history;
    vector<uint32_t> costs;
    vector<int> pin_solutions;
    vector<Key> queue;
    vector<bool> visited;
    void push(uint32_t cost,int vertex,int previous) {
        const int i=history.size();
        history.push_back({cost,vertex,previous});
        queue.push_back({cost,i});
        push_heap(queue.begin(),queue.end(),Later{});
        if(cost<costs[vertex]) costs[vertex]=cost;
    }
    int pop() {
        pop_heap(queue.begin(),queue.end(),Later{});
        const auto i=queue.back().label;
        queue.pop_back();
        return i;
    }
public:
    DetailedGraph graph;
    uint64_t expanded=0;
    explicit FastMaze(const TrackGraph& t):graph(t) {}
    bool route(size_t pins) {
        history.clear();
        queue.clear();
        costs.assign(graph.getNodeNum(),infinity);
        pin_solutions.assign(pins,-1);
        visited.assign(pins,false);
        visited[0]=true;
        for(auto v:graph.getVertices(0)) push(0,v,-1);
        for(size_t connected=1;connected<pins;++connected) {
            int hit=-1, pin=-1;
            while(!queue.empty()) {
                const int index=pop();
                const auto cell=history[index];
                const int u=cell.vertex;
                pin=graph.getPinIdx(u);
                if(pin>=0&&!visited[pin]) {hit=index; break;}
                if(cell.cost>costs[u])continue;
                ++expanded;
                const int back=cell.parent<0?-1:history[cell.parent].vertex;
                for(auto d:directions) {
                    if(!graph.hasEdge(u,d))continue;
                    const int v=graph.getEdgeEndPoint(u,d);
                    if(v==back)continue;
                    const auto cost=cell.cost+graph.getEdgeCost(u,d);
                    if(cost<costs[v])push(cost,v,index);
                }
            }
            if(hit<0)return false;
            pin_solutions[pin]=hit;
            for(int i=hit;i>=0&&history[i].cost!=0;) {
                const auto state=history[i];
                push(0,state.vertex,state.parent);
                i=state.parent;
            }
            for(auto v:graph.getVertices(pin))
                if(v!=history[hit].vertex)push(0,v,-1);
            visited[pin]=true;
        }
        return true;
    }

    Route extract(const Net& net) const {
        Route route;
        unordered_set<int> connected;
        for(auto id:pin_solutions) {
            vector<Node> branch;
            for(int it=id;it>=0;it=history[it].parent) {
                const int u=history[it].vertex;
                branch.push_back(graph.point(u));
                if(!connected.insert(u).second)break;
            }
            reverse(branch.begin(),branch.end());
            append_path(route,net,branch);
        }
        return route;
    }
};

bool same_route(const Route& a,const Route& b) {
    if(a.wires.size()!=b.wires.size()||a.vias.size()!=b.vias.size())return false;
    for(size_t i=0;i<a.wires.size();++i)
        if(key(a.wires[i].a)!=key(b.wires[i].a)||key(a.wires[i].b)!=key(b.wires[i].b))return false;
    for(size_t i=0;i<a.vias.size();++i) if(key(a.vias[i])!=key(b.vias[i]))return false;
    return true;
}

Rect rectangle(Node a,Node b) {
    return {min(a.x,b.x)-width/2,min(a.y,b.y)-width/2,
            max(a.x,b.x)+width/2,max(a.y,b.y)+width/2};
}
bool touch(Rect a,Rect b) {
    return max(a.left,b.left)<=min(a.right,b.right)&&max(a.bottom,b.bottom)<=min(a.top,b.top);
}

bool legal_route(const Net& net,const Route& route,const Occupancy& occupied) {
    if(route.wires.empty()&&route.vias.empty())return false;
    struct Metal {int layer;Rect box;};
    vector<Metal> physical;
    vector<pair<int,int>> vertical_edges;
    for(auto pin:net.pins) physical.push_back({0,rectangle(pin,pin)});
    for(auto w:route.wires) {
        const auto a=w.a,b=w.b;
        if(!occupied.fits(a)||!occupied.fits(b)||!allowed(a,b,net)||a.layer!=b.layer||
           (a.layer==0?(a.y!=b.y||a.x==b.x):(a.x!=b.x||a.y==b.y))||
           occupied.blocked(net.id,a,b)!=-1)return false;
        physical.push_back({a.layer,rectangle(a,b)});
    }
    for(size_t i=0;i<route.vias.size();++i) {
        auto p=route.vias[i];
        p.layer=0;
        const Node q{p.x,p.y,1};
        if(!occupied.fits(p)||!allowed(p,q,net)||occupied.blocked(net.id,p,q)!=-1)return false;
        for(size_t j=0;j<i;++j)
            if(via_conflict(p,route.vias[j])||
               (p.x==route.vias[j].x&&p.y==route.vias[j].y))return false;
        int first=physical.size();
        auto r=rectangle(p,p);
        physical.push_back({0,r});
        physical.push_back({1,r});
        vertical_edges.emplace_back(first,first+1);
    }
    vector<int> links(physical.size());
    iota(links.begin(),links.end(),0);
    auto root=[&](int i){
        while(links[i]!=i) {
            links[i]=links[links[i]];
            i=links[i];
        }
        return i;
    };
    for(auto [a,b]:vertical_edges)links[root(a)]=root(b);
    for(size_t i=0;i<physical.size();++i)
        for(size_t j=0;j<i;++j)
            if(physical[i].layer==physical[j].layer&&touch(physical[i].box,physical[j].box))
                links[root(i)]=root(j);
    const int start=root(0);
    for(size_t i=1;i<links.size();++i)if(root(i)!=start)return false;
    return true;
}

enum Attempt {connected,driver_blocked,sink_blocked,graph_blocked,geometry_blocked};
struct Trial {Attempt status;Route route;};

class Router {
    FastMaze solver;
    MazeRoute reference;
    int compare_remaining;
    bool force_stock;
public:
    int matched=0;
    Router(const TrackGraph& tracks,int count,bool use_stock)
        :solver(tracks),reference(tracks),compare_remaining(count),force_stock(use_stock) {}
    Trial run(const Net& net,const Occupancy& occupied) {
        banned.clear();
        solver.graph.load(net,occupied);
        for(int attempt=0;attempt<4;++attempt) {
            bool ok=solver.route(net.pins.size());
            Route candidate=ok?solver.extract(net):Route{};
            if((compare_remaining>0&&attempt==0)||force_stock) {
                reference.graph.load(net,occupied);
                if(attempt>0) for(auto v:banned) reference.graph.forbid_via(v);
                reference.vertexCosts.assign(reference.graph.getNodeNum(),infinity);
                reference.pinSols.assign(net.pins.size(),nullptr);
                reference.mergedPinAccessBoxes.resize(net.pins.size());
                const bool stock=reference.route(0)==db::RouteStatus::SUCC_NORMAL;
                Route stock_path;
                // Preserve the tree even when its combined vias are too close.
                if(stock) extract_route(net,reference,stock_path);
                if(stock!=ok||!same_route(stock_path,candidate))
                    throw runtime_error("Arena graph diverged from upstream CUGR tree");
                if(compare_remaining>0&&attempt==0){--compare_remaining;++matched;}
                if(force_stock)candidate=move(stock_path);
            }
            if(!ok) {
                if(attempt>0)break;
                for(size_t pin=0;pin<net.pins.size();++pin)
                    if(!solver.graph.can_reach_track(int(pin)))
                        return {pin? sink_blocked:driver_blocked,{}};
                return {graph_blocked,{}};
            }
            if(legal_route(net,candidate,occupied))return {connected,move(candidate)};
            bool placed=false;
            for(size_t i=0;i<candidate.vias.size()&&!placed;++i)
                for(size_t j=0;j<i&&!placed;++j)
                    if(via_conflict(candidate.vias[i],candidate.vias[j])) {
                        const auto cut=candidate.vias[i];
                        banned.push_back(cut);
                        solver.graph.forbid_via(cut);
                        placed=true;
                    }
            if(!placed)break;
        }
        return {geometry_blocked,{}};
    }
    void reset() {banned.clear();}
private:
    vector<Node> banned;
};


using Range=pair<size_t,size_t>;
bool has_route(const Route& r){return !r.wires.empty()||!r.vias.empty();}

class Board {
public:
    TrackGraph tracks;
    Occupancy occupied;
    vector<Route> routes;
    vector<Range> active;
    explicit Board(const vector<Net>& nets):routes(nets.size()),active(nets.size()) {
        for(const auto& net:nets) for(auto p:net.pins) {
            occupied.add(net.id,p,p,0);
            tracks.occupy(p,p,0);
        }
    }
    Range place(int owner,const Route& route) {
        const size_t first=occupied.shapes.size();
        occupied.add_route(owner,route);
        tracks.occupy(route);
        return {first,occupied.shapes.size()};
    }
    void release(Range range,const Route& route) {
        const auto [first,last]=range;
        for(size_t i=first;i<last;++i)occupied.shapes[i].owner=-2;
        tracks.occupy(route,-1);
    }
    void install(int id,Route route) {
        active[id]=place(id,route);
        routes[id]=move(route);
    }
    Route remove(int id) {
        auto previous=move(routes[id]);
        release(active[id],previous);
        active[id]={};
        routes[id]={};
        return previous;
    }
};

vector<Net> read_nets(const string& file) {
    ifstream input(file);
    int count=0;
    input>>llx>>lly>>urx>>ury>>count;
    if(!input||count<=0||llx<0||lly<0||urx-llx<pitch||ury-lly<pitch||
       urx>=max_pos||ury>=max_pos)throw runtime_error("Invalid track graph bounds");
    vector<Net> nets(count);
    for(int id=0;id<count;++id) {
        auto& n=nets[id];
        int pins=0,windows=0;
        input>>n.id>>pins>>windows;
        if(!input||n.id!=id||pins<2||windows<0)throw runtime_error("Invalid net graph record");
        n.pins.resize(pins);
        n.windows.resize(windows);
        for(auto& p:n.pins) {
            input>>p.x>>p.y;
            p.layer=0;
            if(!input||p.x<llx||p.x>urx||p.y<lly||p.y>ury)throw runtime_error("Invalid fixed pin coordinates");
        }
        for(auto& w:n.windows)input>>w.left>>w.bottom>>w.right>>w.top;
    }
    if(!input)throw runtime_error("Incomplete graph");
    return nets;
}

vector<Route> read_paths(const string& path,size_t count) {
    vector<Route> routes(count);
    if(path=="-")return routes;
    ifstream input(path);
    if(!input)throw runtime_error("Cannot open verified replay paths");
    int id,nw,nv;
    while(input>>id>>nw>>nv) {
        auto& route=routes.at(id);
        if(nw<0||nv<0||has_route(route))throw runtime_error("Invalid replay path header");
        for(int i=0;i<nw;++i) {
            Wire wire;
            input>>wire.a.x>>wire.a.y>>wire.b.x>>wire.b.y>>wire.a.layer;
            wire.b.layer=wire.a.layer;
            route.wires.push_back(wire);
        }
        for(int i=0;i<nv;++i){Node v{0,0,0};input>>v.x>>v.y;route.vias.push_back(v);}
        if(!input)throw runtime_error("Incomplete replay paths");
    }
    return routes;
}

struct Reservation {Route stub;Range shapes;};
vector<Reservation> reserve_access(const vector<Net>& nets,Board& board,int threshold) {
    constexpr int radius=4*pitch;
    struct Item{int density,net,pin;};
    unordered_map<int,vector<pair<int,Node>>> bins;
    auto cell=[](int x,int y){return x*5000+y;};
    for(const auto& n:nets)
        for(auto p:n.pins)bins[cell(p.x/radius,p.y/radius)].push_back({n.id,p});
    vector<Item> eligible;
    for(const auto& n:nets) {
        if(has_route(board.routes[n.id]))continue;
        for(size_t j=0;j<n.pins.size();++j) {
            const auto p=n.pins[j];
            int neighbors=0;
            for(int x=max(0,p.x/radius-1);x<=p.x/radius+1;++x)
                for(int y=max(0,p.y/radius-1);y<=p.y/radius+1;++y) {
                    auto found=bins.find(cell(x,y));
                    if(found==bins.end())continue;
                    for(auto [other,loc]:found->second)
                        if(other!=n.id&&abs(loc.x-p.x)<=radius&&abs(loc.y-p.y)<=radius)++neighbors;
                }
            if(neighbors>=threshold)eligible.push_back({neighbors,n.id,int(j)});
        }
    }
    stable_sort(eligible.begin(),eligible.end(),[](auto a,auto b){return a.density>b.density;});
    vector<Reservation> reservations(nets.size());
    Occupancy preview=board.occupied;
    int reserved=0;
    for(auto e:eligible) {
        const auto& n=nets[e.net];
        const auto pin=n.pins[e.pin];
        const auto peer=n.pins[e.pin?0:1];
        auto& owned=reservations[n.id].stub;
        const auto choices=portals(pin,n,preview,owned.vias,24);
        vector<Node> selected;
        int best=numeric_limits<int>::max();
        for(const auto& path:choices) {
            const auto start=path.back();
            for(int d:{-pitch,pitch}) {
                auto next=start;
                (next.layer?next.y:next.x)+=d;
                if(!preview.fits(next)||preview.blocked(n.id,start,next)!=-1)continue;
                int score=md(next,peer)-md(pin,peer)+int(path.size());
                if(score>=best)continue;
                selected=path;
                selected.push_back(next);
                best=score;
            }
        }
        if(selected.empty())continue;
        Route stub;
        append_path(stub,n,selected);
        preview.add_route(n.id,stub);
        owned.wires.insert(owned.wires.end(),stub.wires.begin(),stub.wires.end());
        for(auto v:stub.vias) if(none_of(owned.vias.begin(),owned.vias.end(),[&](Node q){
            return v.x==q.x&&v.y==q.y;
        }))owned.vias.push_back(v);
        ++reserved;
    }
    for(const auto& n:nets)
        reservations[n.id].shapes=board.place(n.id,reservations[n.id].stub);
    cerr<<"reservations "<<reserved<<" / "<<eligible.size()<<" threshold "<<threshold<<'\n';
    return reservations;
}

vector<int> blockers(const Board& board,int owner,const Route& path) {
    unordered_set<int> blocked;
    for(auto w:path.wires)
        board.occupied.blocker(owner,w.a,w.b,w.a.layer,&blocked);
    for(auto cut:path.vias)
        for(int layer=0;layer<3;++layer)
            board.occupied.blocker(owner,cut,cut,layer,&blocked);
    vector<int> result(blocked.begin(),blocked.end());
    sort(result.begin(),result.end());
    return result;
}

int route_count(const Board& b){return count_if(b.routes.begin(),b.routes.end(),has_route);}

vector<int> order_by_span(const vector<Net>& nets) {
    vector<int> ids(nets.size()),cost(nets.size());
    iota(ids.begin(),ids.end(),0);
    for(const auto& net:nets)for(auto p:net.pins)cost[net.id]=max(cost[net.id],md(net.pins.front(),p));
    stable_sort(ids.begin(),ids.end(),[&](int a,int b){return cost[a]<cost[b];});
    return ids;
}

void run_repair(Board& board,const vector<Net>& nets,Router& maze,const vector<int>& ids,int max_attempts,
                const string& path) {
    if(max_attempts<=0)return;
    Board isolated(nets);
    Router solo(isolated.tracks,0,false);
    int tried=0,direct=0,committed=0,rolled=0,evicted=0,too_many=0,no_alone=0,transactions=0;
    const int original=route_count(board);
    for(int index:ids) {
        if(has_route(board.routes[index]))continue;
        if(tried>=max_attempts)break;
        ++tried;
        const auto& n=nets[index];
        board.tracks.use_pads(n);
        auto route=maze.run(n,board.occupied);
        if(route.status==connected) {
            board.install(index,move(route.route));
            ++direct;
            continue;
        }
        isolated.tracks.use_pads(n);
        auto alone=solo.run(n,isolated.occupied);
        if(alone.status!=connected) {++no_alone;continue;}
        auto ids_to_move=blockers(board,index,alone.route);
        if(ids_to_move.size()>4){++too_many;continue;}
        if(any_of(ids_to_move.begin(),ids_to_move.end(),[&](int id){
            return id<0||id>=int(nets.size())||!has_route(board.routes[id]);
        }))continue;
        ++transactions;
        vector<Route> previous;
        for(int id:ids_to_move)previous.push_back(board.remove(id));
        vector<int> placed;
        if(legal_route(n,alone.route,board.occupied)){
            board.install(index,move(alone.route));
            placed.push_back(index);
        }
        if(!placed.empty())for(int id:ids_to_move) {
            board.tracks.use_pads(nets[id]);
            auto replacement=maze.run(nets[id],board.occupied);
            if(replacement.status!=connected)break;
            board.install(id,move(replacement.route));
            placed.push_back(id);
        }
        const bool complete=placed.size()==ids_to_move.size()+1;
        bool checked=complete;
        if(complete) for(int id:placed)
            checked=checked&&legal_route(nets[id],board.routes[id],board.occupied);
        if(!checked) {
            for(int id:placed)board.remove(id);
            for(size_t i=0;i<previous.size();++i) {
                int id=ids_to_move[i];
                if(!legal_route(nets[id],previous[i],board.occupied))
                    throw runtime_error("Could not exactly restore a displaced route");
                board.install(id,move(previous[i]));
            }
            ++rolled;
        } else {
            ++committed;
            evicted+=ids_to_move.size();
            write_routes(path,board.routes);
        }
    }
    if(route_count(board)!=original+direct+committed)throw runtime_error("Repair route-count invariant failed");
    cerr<<"repair tried="<<tried<<" direct="<<direct<<" transactions="<<transactions
        <<" committed="<<committed<<" rolled_back="<<rolled<<" old_restored_on_commit="<<evicted
        <<" blocked_by_more_than_four="<<too_many<<" no_isolated_route="<<no_alone
        <<" now="<<route_count(board)<<'\n';
}

int main(int argc,char** argv) {
    if(argc!=6) {
        cerr<<"usage: transactional-maze graph.txt paths.txt verified-seed-or-dash reservation-density repair-attempts\n";
        return 2;
    }
    const auto nets=read_nets(argv[1]);
    const string path=argv[2];
    const auto saved=read_paths(argv[3],nets.size());
    const int density=stoi(argv[4]),repair_attempts=stoi(argv[5]);
    Board board(nets);
    int retained=0;
    for(const auto& n:nets) if(has_route(saved[n.id])&&legal_route(n,saved[n.id],board.occupied)) {
        board.install(n.id,saved[n.id]);
        ++retained;
    }
    cerr<<"seed retained "<<retained<<'\n';
    const auto ids=order_by_span(nets);
    const auto stubs=reserve_access(nets,board,density);
    Router maze(board.tracks,24,false);
    array<int,5> result{};
    int attempted=0;
    for(int index:ids) {
        if(has_route(board.routes[index]))continue;
        board.release(stubs[index].shapes,stubs[index].stub);
        const auto& net=nets[index];
        board.tracks.use_pads(net);
        auto route=maze.run(net,board.occupied);
        ++result[route.status];
        if(route.status==connected)board.install(index,move(route.route));
        if(++attempted%100==0)cerr<<"processed "<<attempted<<" routed "<<retained+result[0]<<'\n';
    }
    if(attempted+retained!=int(nets.size())) throw runtime_error("Full input was not processed");
    cerr<<"initial "<<route_count(board)<<" / "<<nets.size()
        <<" driver_access="<<result[1]<<" sink_access="<<result[2]<<" graph_disconnected="<<result[3]
        <<" geometry_rejected="<<result[4]<<" upstream_matched="<<maze.matched<<'\n';
    write_routes(path+".initial",board.routes);
    write_routes(path,board.routes);
    run_repair(board,nets,maze,ids,repair_attempts,path);
    write_routes(path,board.routes);
    cerr<<"done "<<route_count(board)<<" / "<<nets.size()<<'\n';
    return 0;
}
