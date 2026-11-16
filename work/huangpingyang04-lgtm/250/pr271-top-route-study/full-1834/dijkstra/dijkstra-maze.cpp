// PR #276 experiment. Shared geometry and access rules come from its previous router.
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
bool coarse(Node n) { return n.x % pitch == 0 && n.y % pitch == 0; }
bool contains(const Rect& r, Node a, Node b) {
    return r.left<=min(a.x,b.x) && max(a.x,b.x)<=r.right
        && r.bottom<=min(a.y,b.y) && max(a.y,b.y)<=r.top;
}
bool allowed(Node a, Node b, const Net& n) {
    if (coarse(a) && coarse(b)) return true;
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

// Collect several independently reachable coarse locations in each pin window.
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
        if(coarse(a)) {
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

constexpr int via_cost = 28;
constexpr int tracks_per_cell = tile / pitch;
using Access = vector<vector<Node>>;

int access_cost(const vector<Node>& path) {
    int cost = 0;
    for (size_t i = 1; i < path.size(); ++i)
        cost += path[i-1].layer == path[i].layer ? md(path[i-1], path[i]) : via_cost;
    return cost;
}

struct GuideGrid {
    const int nx = urx / tile + 1;
    const int ny = ury / tile + 1;
    vector<double> demand = vector<double>(2 * nx * ny);
    explicit GuideGrid(const vector<Net>& nets) {
        for (const auto& net : nets)
            for (auto p : net.pins)
                demand[index(p)] += 0.1;
    }
    int index(int x, int y, int layer) const { return (x * ny + y) * 2 + layer; }
    int index(Node p) const { return index(p.x / tile, p.y / tile, p.layer); }
    Node cell(int id) const { return {(id / 2) / ny, (id / 2) % ny, id % 2}; }
    double remaining(int id) const { return max(0.1, tracks_per_cell - demand[id]); }

    void add(const Route& route) {
        for (auto w : route.wires) {
            const int layer = w.a.layer;
            int a = layer ? w.a.y : w.a.x;
            int b = layer ? w.b.y : w.b.x;
            const int fixed = (layer ? w.a.x : w.a.y) / tile;
            if (a > b) swap(a, b);
            for (int begin = a; begin < b;) {
                const int along = begin / tile;
                const int end = min(b, (along + 1) * tile);
                const int id = layer ? index(fixed, along, layer) : index(along, fixed, layer);
                demand[id] += double(end - begin) / tile;
                begin = end;
            }
        }
        for (auto v : route.vias) {
            demand[index(v.x / tile, v.y / tile, 0)] += 0.2;
            demand[index(v.x / tile, v.y / tile, 1)] += 0.2;
        }
    }

    vector<int> plan(const Access& sources, const Access& targets) const {
        using Entry = pair<double, int>;
        priority_queue<Entry, vector<Entry>, greater<Entry>> queue;
        vector<double> cost(demand.size(), numeric_limits<double>::infinity());
        vector<int> predecessor(demand.size(), -1);
        vector<bool> target(demand.size());
        for (const auto& path : targets) target[index(path.back())] = true;
        for (const auto& path : sources) {
            const int id = index(path.back());
            if (cost[id] == 0) continue;
            cost[id] = 0;
            queue.emplace(0, id);
        }
        while (!queue.empty()) {
            const auto [distance, id] = queue.top();
            queue.pop();
            if (distance != cost[id]) continue;
            if (target[id]) {
                vector<int> path;
                for (int at = id; at != -1; at = predecessor[at]) path.push_back(at);
                return path;
            }
            const auto c = cell(id);
            auto relax = [&](int x, int y, int layer, int scale) {
                if (x < llx / tile || x >= nx || y < lly / tile || y >= ny) return;
                const int next = index(x, y, layer);
                // CUGR Eq. 8, with remaining tracks estimated from committed geometry.
                const double new_cost = distance + scale * (1 / remaining(id) + 1 / remaining(next));
                if (new_cost >= cost[next]) return;
                cost[next] = new_cost;
                predecessor[next] = id;
                queue.emplace(new_cost, next);
            };
            for (int delta : {-1, 1})
                relax(c.x + (c.layer == 0 ? delta : 0), c.y + (c.layer == 1 ? delta : 0),
                      c.layer, tracks_per_cell);
            relax(c.x, c.y, 1 - c.layer, 1);
        }
        return {};
    }

    vector<bool> corridor(const vector<int>& path, const Access& sources,
                          const Access& targets, int padding) const {
        vector<bool> guide(demand.size());
        auto mark = [&](int id, int radius) {
            const auto c = cell(id);
            for (int x = max(0, c.x-radius); x < nx && x <= c.x+radius; ++x) {
                for (int y = max(0, c.y-radius); y < ny && y <= c.y+radius; ++y) {
                    // Provide an adjacent-layer option within each guide rectangle.
                    guide[index(x, y, 0)] = true;
                    guide[index(x, y, 1)] = true;
                }
            }
        };
        for (int id : path) mark(id, padding);
        for (const auto& s : sources) mark(index(s.back()), 0);
        for (const auto& t : targets) mark(index(t.back()), 0);
        return guide;
    }

    int fine_cost(Node a, Node b) const {
        const int base = a.layer == b.layer ? md(a, b) : via_cost;
        const double resources = min(remaining(index(a)), remaining(index(b)));
        // Soft congestion cost complements hard spacing and occupancy checks.
        return base + int(ceil(base * (tracks_per_cell - resources) / tracks_per_cell));
    }
};

bool vias_fit(const vector<Node>& left, const vector<Node>& right) {
    for (auto u : left)
        for (auto v : right)
            if (via_conflict(u, v)) return false;
    return true;
}

vector<Node> fine_maze(const Net& net, const Occupancy& occupied, const GuideGrid& grid,
                       const vector<bool>& guide, const Access& sources, const Access& targets,
                       const vector<Node>& prior_vias, int budget, int& expanded) {
    struct Visit { int cost; uint64_t predecessor; size_t source; };
    using Entry = pair<int, uint64_t>;
    const uint64_t none = numeric_limits<uint64_t>::max();
    priority_queue<Entry, vector<Entry>, greater<Entry>> queue;
    unordered_map<uint64_t, Visit> visits;
    unordered_map<uint64_t, vector<size_t>> endpoint;
    vector<vector<Node>> source_vias, target_vias;
    vector<int> target_cost;
    for (size_t i = 0; i < targets.size(); ++i) {
        endpoint[key(targets[i].back())].push_back(i);
        target_vias.push_back(cuts(targets[i]));
        target_cost.push_back(access_cost(targets[i]));
    }
    for (size_t i = 0; i < sources.size(); ++i) {
        source_vias.push_back(cuts(sources[i]));
        const auto k = key(sources[i].back());
        const int cost = access_cost(sources[i]);
        const auto old = visits.find(k);
        if (old != visits.end() && old->second.cost <= cost) continue;
        visits.insert_or_assign(k, Visit{cost, none, i});
        queue.emplace(cost, k);
    }
    int best = numeric_limits<int>::max();
    vector<Node> result;
    int settled = 0;
    while (!queue.empty() && settled < budget) {
        const auto [cost, k] = queue.top();
        queue.pop();
        if (cost >= best) break;
        const auto prior = visits.at(k);
        if (cost != prior.cost) continue;
        ++settled;
        const auto a = unpack(k);
        auto target = endpoint.find(k);
        if (target != endpoint.end()) {
            for (size_t t : target->second) {
                if (cost + target_cost[t] >= best) continue;
                vector<Node> path;
                for (auto back = k; back != none; back = visits.at(back).predecessor)
                    path.push_back(unpack(back));
                reverse(path.begin(), path.end());
                auto vias = cuts(path);
                if (!vias_fit(vias, target_vias[t]) ||
                    !vias_fit(source_vias[prior.source], target_vias[t])) continue;
                result = sources[prior.source];
                result.insert(result.end(), next(path.begin()), path.end());
                result.insert(result.end(), next(targets[t].rbegin()), targets[t].rend());
                best = cost + target_cost[t];
            }
        }
        auto relax = [&](Node b) {
            if (!occupied.fits(b) || !guide[grid.index(b)]) return;
            const auto id = key(b);
            const int new_cost = cost + grid.fine_cost(a, b);
            const auto old = visits.find(id);
            if (old != visits.end() && old->second.cost <= new_cost) return;
            if (a.layer != b.layer) {
                for (auto v : prior_vias) if (via_conflict(a, v)) return;
                for (auto v : source_vias[prior.source]) if (via_conflict(a, v)) return;
            }
            if (occupied.blocked(net.id, a, b) != -1) return;
            visits.insert_or_assign(id, Visit{new_cost, k, prior.source});
            queue.emplace(new_cost, id);
        };
        for (int delta : {-pitch, pitch}) {
            auto b = a;
            (b.layer ? b.y : b.x) += delta;
            relax(b);
        }
        relax({a.x, a.y, 1-a.layer});
    }
    expanded += settled;
    return result;
}

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

enum class Outcome : size_t { routed, source_access, sink_access, guide_search };

Outcome route_net(const Net& net, const Occupancy& occupied, const GuideGrid& grid,
                  int padding, int budget, Route& route, int& expanded) {
    const auto launch = portals(net.pins[0], net, occupied, {}, 24);
    if (launch.empty()) return Outcome::source_access;
    vector<Node> tree;
    for (size_t pin = 1; pin < net.pins.size(); ++pin) {
        const Node goal = net.pins[pin];
        const auto targets = portals(goal, net, occupied, route.vias, 24);
        if (targets.empty()) return Outcome::sink_access;
        Access sources;
        if (tree.empty()) {
            sources = launch;
        } else {
            sort(tree.begin(), tree.end(), [&](Node a, Node b) {
                return make_pair(md(a, goal), key(a)) < make_pair(md(b, goal), key(b));
            });
            tree.erase(unique(tree.begin(), tree.end(), [](Node a, Node b) {
                return key(a) == key(b);
            }), tree.end());
            for (size_t i = 0; i < tree.size() && i < 24; ++i) sources.push_back({tree[i]});
        }
        const auto plan = grid.plan(sources, targets);
        if (plan.empty()) return Outcome::guide_search;
        auto guide = grid.corridor(plan, sources, targets, padding);
        auto path = fine_maze(net, occupied, grid, guide, sources, targets, route.vias,
                              budget, expanded);
        if (path.empty()) {
            guide = grid.corridor(plan, sources, targets, padding + 1);
            path = fine_maze(net, occupied, grid, guide, sources, targets, route.vias,
                             budget, expanded);
        }
        if (path.empty()) return Outcome::guide_search;
        append_path(route, net, path);
        for (auto node : path) if (coarse(node)) tree.push_back(node);
    }
    return Outcome::routed;
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

int repair(const vector<Net>& nets, vector<Route>& routes, int padding, int budget,
           int rounds) {
    Occupancy pads;
    for (const auto& net : nets)
        for (auto p : net.pins) pads.add(net.id, p, p, 0);
    const GuideGrid empty_grid(nets);
    Occupancy occupied = pads;
    GuideGrid grid = empty_grid;
    auto has_route = [&](int id) {
        return !routes[id].wires.empty() || !routes[id].vias.empty();
    };
    for (const auto& net : nets) {
        if (!has_route(net.id)) continue;
        occupied.add_route(net.id, routes[net.id]);
        grid.add(routes[net.id]);
    }
    int total = 0;
    for (int pass = 0; pass < rounds; ++pass) {
        int added = 0, replaced = 0, examined = 0, candidates = 0;
        for (size_t step = 0; step < nets.size(); ++step) {
            const auto& net = nets[pass % 2 ? nets.size() - 1 - step : step];
            if (has_route(net.id)) continue;
            Route candidate;
            int expanded = 0;
            if (route_net(net, occupied, grid, padding, budget, candidate, expanded) == Outcome::routed) {
                occupied.add_route(net.id, candidate);
                grid.add(candidate);
                routes[net.id] = move(candidate);
                ++added;
                continue;
            }
            ++examined;
            candidate = {};
            if (route_net(net, pads, empty_grid, padding, budget, candidate, expanded) != Outcome::routed)
                continue;
            unordered_set<int> blockers;
            for (const auto& wire : candidate.wires)
                occupied.blocker(net.id, wire.a, wire.b, wire.a.layer, &blockers);
            for (auto via : candidate.vias)
                for (int layer = 0; layer < 3; ++layer)
                    occupied.blocker(net.id, via, via, layer, &blockers);
            if (blockers.size() > 4) continue;
            ++candidates;
            vector<int> displaced(blockers.begin(), blockers.end());
            sort(displaced.begin(), displaced.end());
            Occupancy trial = pads;
            GuideGrid trial_grid = empty_grid;
            for (const auto& other : nets) {
                if (!has_route(other.id) || blockers.count(other.id)) continue;
                trial.add_route(other.id, routes[other.id]);
                trial_grid.add(routes[other.id]);
            }
            trial.add_route(net.id, candidate);
            trial_grid.add(candidate);
            vector<Route> recovered;
            for (int id : displaced) {
                if (!has_route(id)) break;
                Route route;
                if (route_net(nets[id], trial, trial_grid, padding, budget, route, expanded) != Outcome::routed)
                    break;
                trial.add_route(id, route);
                trial_grid.add(route);
                recovered.push_back(move(route));
            }
            if (recovered.size() != displaced.size()) continue;
            for (size_t i = 0; i < displaced.size(); ++i)
                routes[displaced[i]] = move(recovered[i]);
            routes[net.id] = move(candidate);
            occupied = move(trial);
            grid.demand = move(trial_grid.demand);
            ++added;
            replaced += displaced.size();
        }
        total += added;
        cerr << "repair " << pass + 1 << " added=" << added << " displaced_recovered="
             << replaced << " conflicts_examined=" << examined << " swap_candidates="
             << candidates << '\n';
        if (!added) break;
    }
    return total;
}

int main(int argc, char** argv) {
    if (argc != 7) {
        cerr << "usage: router graph.txt paths.txt guide-padding states-per-search passes repair-passes\n";
        return 1;
    }
    ifstream input(argv[1]);
    const int padding = stoi(argv[3]), budget = stoi(argv[4]), passes = stoi(argv[5]);
    const int repair_passes = stoi(argv[6]);
    int count = 0;
    input >> llx >> lly >> urx >> ury >> count;
    if (!input || count <= 0 || llx < 0 || lly < 0 || urx < llx || ury < lly ||
        urx >= max_pos || ury >= max_pos || padding < 0 || padding > 20 ||
        budget <= 0 || passes <= 0 || repair_passes < 0) return 2;
    vector<Net> nets(count);
    for (int id = 0; id < count; ++id) {
        auto& net = nets[id];
        int pins = 0, windows = 0;
        input >> net.id >> pins >> windows;
        if (!input || net.id != id || pins < 2 || windows < 0) return 2;
        net.pins.resize(pins);
        net.windows.resize(windows);
        for (auto& p : net.pins) {
            input >> p.x >> p.y;
            p.layer = 0;
            if (!Occupancy{}.fits(p)) return 2;
        }
        for (auto& w : net.windows) input >> w.left >> w.bottom >> w.right >> w.top;
    }
    if (!input) return 2;
    vector<int> order(count), span(count);
    iota(order.begin(), order.end(), 0);
    for (const auto& net : nets)
        for (auto pin : net.pins)
            span[net.id] = max(span[net.id], md(net.pins.front(), pin));
    stable_sort(order.begin(), order.end(), [&](int a, int b) {
        if (nets[a].pins.size() != nets[b].pins.size())
            return nets[a].pins.size() > nets[b].pins.size();
        return span[a] < span[b];
    });
    vector<int> misses(count);
    vector<Route> best_routes;
    int best = -1;
    for (int pass = 0; pass < passes; ++pass) {
        Occupancy occupied;
        for (const auto& net : nets)
            for (auto p : net.pins) occupied.add(net.id, p, p, 0);
        GuideGrid grid(nets);
        vector<Route> routes(count);
        vector<bool> routed(count);
        array<int, 4> outcomes{};
        long long fine_states = 0;
        int processed = 0;
        for (int id : order) {
            int expanded = 0;
            const auto outcome = route_net(nets[id], occupied, grid, padding, budget,
                                           routes[id], expanded);
            ++outcomes[size_t(outcome)];
            fine_states += expanded;
            if (outcome == Outcome::routed) {
                routed[id] = true;
                occupied.add_route(id, routes[id]);
                grid.add(routes[id]);
            } else {
                routes[id] = {};
                ++misses[id];
            }
            if (++processed % 200 == 0)
                cerr << "pass " << pass + 1 << " processed " << processed
                     << " routed " << outcomes[0] << '\n';
        }
        cerr << "pass " << pass + 1 << " done " << outcomes[0]
             << " source_access=" << outcomes[1] << " sink_access=" << outcomes[2]
             << " guide_search=" << outcomes[3] << " fine_states=" << fine_states << '\n';
        if (outcomes[0] > best) {
            write_routes(argv[2], routes);
            best = outcomes[0];
            best_routes = move(routes);
        }
        if (best == count) break;
        stable_sort(order.begin(), order.end(), [&](int a, int b) {
            if (routed[a] != routed[b]) return !routed[a];
            if (misses[a] != misses[b]) return misses[a] > misses[b];
            return pass % 2 ? span[a] < span[b] : span[a] > span[b];
        });
    }
    if (repair_passes && best < count) {
        best += repair(nets, best_routes, padding, budget, repair_passes);
        write_routes(argv[2], best_routes);
    }
    cerr << "best " << best << " / " << count << '\n';
    return 0;
}
