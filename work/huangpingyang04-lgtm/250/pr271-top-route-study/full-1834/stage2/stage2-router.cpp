// PR #276. Only CUGR stage-2 fine maze search, with PR #276 geometry and pin access.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
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

using Access = vector<vector<Node>>;
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

class RadixQueue {
public:
    using Item = pair<uint32_t, int>;

    void clear() {
        for (auto& b : buckets) b.clear();
        last = infinity;
        items = 0;
    }
    void push(uint32_t cost, int vertex) {
        if (!items && last == infinity) last = 0;
        buckets[bucket(cost)].emplace_back(cost, vertex);
        ++items;
    }
    uint32_t first() {
        if (!items) return infinity;
        if (buckets[0].empty()) {
            size_t i = 1;
            while (buckets[i].empty()) ++i;
            last = min_element(buckets[i].begin(), buckets[i].end())->first;
            for (auto entry : buckets[i]) buckets[bucket(entry.first)].push_back(entry);
            buckets[i].clear();
        }
        return last;
    }
    Item pop() {
        const auto item = buckets[0].back();
        buckets[0].pop_back();
        --items;
        return item;
    }
private:
    array<vector<Item>, 33> buckets;
    uint32_t last = infinity;
    size_t items = 0;

    size_t bucket(uint32_t cost) const {
        const uint32_t bits = cost ^ last;
        return bits ? 32 - __builtin_clz(bits) : 0;
    }
};

struct Port {
    const vector<Node>* path;
    vector<int> no_via;
};
uint32_t access_cost(const vector<Node>& path) {
    uint32_t total = 0;
    for (size_t i = 1; i < path.size(); ++i)
        total += path[i-1].layer == path[i].layer ? md(path[i-1], path[i]) : 28;
    return total * cost_scale;
}
bool vias_fit(const vector<Node>& left, const vector<Node>& right) {
    for (auto u : left)
        for (auto v : right)
            if (via_conflict(u, v)) return false;
    return true;
}

class DetailedMaze {
    struct Front {
        vector<uint32_t> distance;
        vector<int> parent, root;
        vector<Port> ports;
        RadixQueue queue;

        explicit Front(int size) : distance(size, infinity), parent(size), root(size) {}
        void initialize(const TrackGraph& graph, const Access& access) {
            fill(distance.begin(), distance.end(), infinity);
            ports.clear();
            queue.clear();
            for (const auto& path : access) {
                const int u = graph.vertex(path.back());
                const auto cost = access_cost(path);
                if (distance[u] <= cost) continue;
                Port port{&path, {}};
                for (auto p : cuts(path)) graph.via_exclusions(p, port.no_via);
                distance[u] = cost;
                parent[u] = -1;
                root[u] = ports.size();
                ports.push_back(move(port));
                queue.push(cost, u);
            }
        }
    };

public:
    explicit DetailedMaze(const TrackGraph& g)
        : graph(g), forward(2 * g.points), reverse_front(2 * g.points), no_via(g.points) {}
    uint64_t expanded = 0;

    vector<Node> search(const Access& source, const Access& target, const vector<Node>& existing) {
        forward.initialize(graph, source);
        reverse_front.initialize(graph, target);
        vector<int> banned;
        for (auto p : existing) graph.via_exclusions(p, banned);
        for (int p : banned) no_via[p] = true;

        uint64_t best_cost = numeric_limits<uint64_t>::max();
        vector<Node> best_path;
        while (true) {
            const auto f = forward.queue.first(), r = reverse_front.queue.first();
            if (f == infinity || r == infinity || uint64_t(f) + r >= best_cost) break;
            auto& here = f <= r ? forward : reverse_front;
            auto& there = f <= r ? reverse_front : forward;
            const auto [cost, u] = here.queue.pop();
            if (cost != here.distance[u]) continue;
            ++expanded;

            auto meet = [&](int v) {
                if (there.distance[v] == infinity) return;
                const uint64_t candidate_cost = uint64_t(here.distance[v]) + there.distance[v];
                if (candidate_cost >= best_cost) return;
                auto path = join(v);
                if (path.empty()) return;
                best_path = move(path);
                best_cost = candidate_cost;
            };
            meet(u);

            const int p = u / 2, x = p / graph.ny, y = p % graph.ny, root = here.root[u];
            auto relax = [&](int v, int kind, int edge) {
                if (!graph.available(kind, edge)) return;
                const auto candidate = cost + graph.cost(kind, edge, x, y);
                if (candidate >= here.distance[v]) return;
                if (kind == TrackGraph::via) {
                    if (no_via[p]) return;
                    const auto& exclusions = here.ports[root].no_via;
                    if (find(exclusions.begin(), exclusions.end(), p) != exclusions.end()) return;
                }
                here.distance[v] = candidate;
                here.parent[v] = u;
                here.root[v] = root;
                here.queue.push(candidate, v);
                meet(v);
            };
            if (u % 2 == 0) {
                if (x > 0) relax(u - 2 * graph.ny, TrackGraph::horizontal, p - graph.ny);
                if (x + 1 < graph.nx) relax(u + 2 * graph.ny, TrackGraph::horizontal, p);
            } else {
                if (y > 0) relax(u - 2, TrackGraph::vertical, p - 1);
                if (y + 1 < graph.ny) relax(u + 2, TrackGraph::vertical, p);
            }
            relax(u ^ 1, TrackGraph::via, p);
        }
        for (int p : banned) no_via[p] = false;
        return best_path;
    }

private:
    const TrackGraph& graph;
    Front forward, reverse_front;
    vector<uint8_t> no_via;

    vector<Node> join(int vertex) const {
        const auto& start = *forward.ports[forward.root[vertex]].path;
        const auto& end = *reverse_front.ports[reverse_front.root[vertex]].path;
        vector<Node> middle;
        for (int v = vertex; v != -1; v = forward.parent[v]) middle.push_back(graph.node(v));
        reverse(middle.begin(), middle.end());
        for (int v = reverse_front.parent[vertex]; v != -1; v = reverse_front.parent[v])
            middle.push_back(graph.node(v));

        const auto a = cuts(start), b = cuts(end), c = cuts(middle);
        if (!vias_fit(a, b) || !vias_fit(a, c) || !vias_fit(b, c)) return {};
        vector<Node> result = start;
        result.insert(result.end(), next(middle.begin()), middle.end());
        result.insert(result.end(), next(end.rbegin()), end.rend());
        return result;
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

enum class Outcome : size_t { routed, driver_access, sink_access, maze_exhausted };

Outcome route_net(const Net& net, const Occupancy& occupied, DetailedMaze& maze, Route& route) {
    const auto launch = portals(net.pins.front(), net, occupied, {}, numeric_limits<int>::max());
    if (launch.empty()) return Outcome::driver_access;
    vector<Node> tree;
    for (size_t pin = 1; pin < net.pins.size(); ++pin) {
        const auto targets = portals(net.pins[pin], net, occupied, route.vias, numeric_limits<int>::max());
        if (targets.empty()) return Outcome::sink_access;
        Access sources;
        if (tree.empty()) {
            sources = launch;
        } else {
            sort(tree.begin(), tree.end(), [](Node a, Node b) { return key(a) < key(b); });
            tree.erase(unique(tree.begin(), tree.end(), [](Node a, Node b) {
                return key(a) == key(b);
            }), tree.end());
            for (auto node : tree) sources.push_back({node});
        }
        const auto path = maze.search(sources, targets, route.vias);
        if (path.empty()) return Outcome::maze_exhausted;
        append_path(route, net, path);
        for (auto node : path) if (on_track(node)) tree.push_back(node);
    }
    return Outcome::routed;
}

// Exhaustively compare the dense obstacle map to the geometric checker on the small smoke graph.
void audit_edges(const Net& net, const Occupancy& occupied, const TrackGraph& graph) {
    auto check = [&](Node from, int kind, int edge, Node to) {
        if (graph.available(kind, edge) != (occupied.blocked(net.id, from, to) == -1))
            throw runtime_error("Detailed graph disagrees with geometric obstacle check");
    };
    for (int x = 0; x < graph.nx; ++x) {
        for (int y = 0; y < graph.ny; ++y) {
            const int p = x * graph.ny + y;
            const auto a = graph.node(2 * p);
            const auto b = graph.node(2 * p + 1);
            if (x + 1 < graph.nx) check(a, TrackGraph::horizontal, p, {a.x + pitch, a.y, 0});
            if (y + 1 < graph.ny) check(b, TrackGraph::vertical, p, {b.x, b.y + pitch, 1});
            check(a, TrackGraph::via, p, b);
        }
    }
}

int main(int argc, char** argv) {
    if (argc != 4) {
        cerr << "usage: stage2-router graph.txt paths.txt short|long|pin-access\n";
        return 1;
    }
    const string ordering = argv[3];
    if (ordering != "short" && ordering != "long" && ordering != "pin-access") return 1;
    ifstream input(argv[1]);
    int count = 0;
    input >> llx >> lly >> urx >> ury >> count;
    if (!input || count <= 0 || llx < 0 || lly < 0 || urx - llx < pitch ||
        ury - lly < pitch || urx >= max_pos || ury >= max_pos) return 2;
    vector<Net> nets(count);
    Occupancy occupied;
    TrackGraph graph;
    for (int id = 0; id < count; ++id) {
        auto& net = nets[id];
        int pins = 0, windows = 0;
        input >> net.id >> pins >> windows;
        if (!input || net.id != id || pins < 2 || windows < 0) return 2;
        net.pins.resize(pins);
        net.windows.resize(windows);
        for (auto& pin : net.pins) {
            input >> pin.x >> pin.y;
            pin.layer = 0;
            if (!input || !occupied.fits(pin)) return 2;
            occupied.add(net.id, pin, pin, 0);
            graph.occupy(pin, pin, 0);
        }
        for (auto& w : net.windows) input >> w.left >> w.bottom >> w.right >> w.top;
    }
    if (!input) return 2;
    vector<int> order(count), span(count);
    vector<size_t> pin_access(count, numeric_limits<size_t>::max());
    iota(order.begin(), order.end(), 0);
    for (const auto& net : nets) {
        for (auto pin : net.pins) {
            span[net.id] = max(span[net.id], md(net.pins.front(), pin));
            if (ordering == "pin-access") {
                auto candidates = portals(pin, net, occupied, {}, numeric_limits<int>::max());
                pin_access[net.id] = min(pin_access[net.id], candidates.size());
            }
        }
    }
    stable_sort(order.begin(), order.end(), [&](int a, int b) {
        if (ordering == "pin-access" && pin_access[a] != pin_access[b])
            return pin_access[a] < pin_access[b];
        if (ordering == "long") return span[a] > span[b];
        return span[a] < span[b];
    });

    DetailedMaze maze(graph);
    vector<Route> routes(count);
    array<int, 4> totals{};
    for (int processed = 0; processed < count; ++processed) {
        const int id = order[processed];
        graph.use_pads(nets[id]);
        if (graph.points < 1000) audit_edges(nets[id], occupied, graph);
        auto& route = routes[id];
        const auto result = route_net(nets[id], occupied, maze, route);
        ++totals[size_t(result)];
        if (result == Outcome::routed) {
            occupied.add_route(id, route);
            graph.occupy(route);
        } else {
            route = {};
        }
        if ((processed + 1) % 100 == 0)
            cerr << "processed " << processed + 1 << " routed " << totals[0]
                 << " expanded " << maze.expanded << '\n';
    }
    write_routes(argv[2], routes);
    cerr << "done " << totals[0] << " / " << count << " driver_access=" << totals[1]
         << " sink_access=" << totals[2] << " maze_exhausted=" << totals[3]
         << " expanded=" << maze.expanded << '\n';
    return 0;
}
