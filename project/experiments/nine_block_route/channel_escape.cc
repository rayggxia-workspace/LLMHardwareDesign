// Escape pins to distinct side-channel rows on a two-layer track grid.
#include <algorithm>
#include <iostream>
#include <queue>
#include <stdexcept>
#include <vector>

struct Arc {
    int to;
    int reverse;
    int capacity;
    bool forward;
};

class UnitFlow {
public:
    explicit UnitFlow(int count) : graph(count), levels(count), cursor(count) {}

    void add(int from, int to) {
        graph[from].push_back({to, static_cast<int>(graph[to].size()), 1, true});
        graph[to].push_back({from, static_cast<int>(graph[from].size())-1, 0, false});
    }

    int solve(int source, int sink) {
        int total = 0;
        while (level(source, sink)) {
            std::fill(cursor.begin(), cursor.end(), 0);
            while (augment(source, sink)) ++total;
        }
        return total;
    }

    int next(int from) const {
        for (const Arc &arc : graph[from]) {
            if (arc.forward && arc.capacity == 0) return arc.to;
        }
        return -1;
    }

private:
    bool level(int source, int sink) {
        std::fill(levels.begin(), levels.end(), -1);
        std::queue<int> pending;
        levels[source] = 0;
        pending.push(source);
        while (!pending.empty()) {
            int at = pending.front();
            pending.pop();
            for (const Arc &arc : graph[at]) {
                if (arc.capacity && levels[arc.to] < 0) {
                    levels[arc.to] = levels[at]+1;
                    if (arc.to != sink) pending.push(arc.to);
                }
            }
        }
        return levels[sink] >= 0;
    }

    bool augment(int at, int sink) {
        if (at == sink) return true;
        for (int &i = cursor[at]; i < static_cast<int>(graph[at].size()); ++i) {
            Arc &arc = graph[at][i];
            if (arc.capacity && levels[arc.to] == levels[at]+1 && augment(arc.to, sink)) {
                --arc.capacity;
                ++graph[arc.to][arc.reverse].capacity;
                return true;
            }
        }
        return false;
    }

    std::vector<std::vector<Arc>> graph;
    std::vector<int> levels;
    std::vector<int> cursor;
};

int main() {
    int nx, ny, count, edge;
    if (!(std::cin >> nx >> ny >> count >> edge) || nx < 2 || ny < 2 ||
        count < 1 || (edge != 0 && edge != nx-1)) {
        throw std::runtime_error("Invalid escape grid");
    }
    std::vector<int> xs(nx), ys(ny), starts(count);
    for (int &x : xs) std::cin >> x;
    for (int &y : ys) std::cin >> y;
    const auto vertex = [ny](int x, int y, int layer) { return 4*(x*ny+y)+2*layer; };
    const int source = 4*nx*ny, sink = source+1;
    UnitFlow flow(sink+1);
    for (int x = 0; x < nx; ++x) {
        for (int y = 0; y < ny; ++y) {
            const int h = vertex(x, y, 0), v = vertex(x, y, 1);
            flow.add(h, h+1);
            flow.add(v, v+1);
            if (x > 0) {
                int left = vertex(x-1, y, 0);
                flow.add(left+1, h);
                flow.add(h+1, left);
            }
            if (y > 0) {
                int below = vertex(x, y-1, 1);
                flow.add(below+1, v);
                flow.add(v+1, below);
            }
            // The 4 um grid meets metal spacing. Vias on a checkerboard
            // avoid the 4 um axial pitch, which is too small for two cuts.
            if ((xs[x]+ys[y]) % 2 == 0) {
                flow.add(h+1, v);
                flow.add(v+1, h);
            }
            if (x == edge) flow.add(h+1, sink);
        }
    }
    for (int i = 0; i < count; ++i) {
        int x, y;
        if (!(std::cin >> x >> y) || x < 0 || x >= nx || y < 0 || y >= ny) {
            throw std::runtime_error("Invalid terminal index");
        }
        starts[i] = vertex(x, y, 0);
        flow.add(source, starts[i]);
    }
    const int routed = flow.solve(source, sink);
    std::cerr << "Escaped " << routed << " of " << count << '\n';
    if (routed != count) return 1;
    for (const int start : starts) {
        for (int at = start; at != sink; at = flow.next(at)) {
            if (at < 0) throw std::runtime_error("Incomplete flow path");
            if (at % 2 == 0) {
                std::cout << xs[at/4/ny] << ' ' << ys[at/4%ny] << ' ' << 11+at/2%2 << ' ';
            }
        }
        std::cout << '\n';
    }
}
