// Classify all unresolved nets against one immutable, independently verified solution.
#define main transactional_main
#include "transactional-maze.cpp"
#undef main

int main(int argc, char** argv) {
    if (argc != 3 && argc != 5) return 2;
    const unsigned shard = argc == 5 ? stoul(argv[3]) : 0;
    const unsigned shard_count = argc == 5 ? stoul(argv[4]) : 1;
    if (shard >= shard_count) return 2;
    const auto nets = read_nets(argv[1]);
    auto paths = read_paths(argv[2], nets.size());
    Board board(nets);
    for (const auto& net : nets) {
        auto& route = paths[net.id];
        if (!has_route(route)) continue;
        if (!legal_route(net, route, board.occupied))
            throw runtime_error("Independently verified path failed to replay");
        board.install(net.id, move(route));
    }
    Router maze(board.tracks, 24, false);
    const array<const char*, 5> reasons = {
        "available_on_frozen_board", "driver_access", "sink_access",
        "graph_disconnected", "geometry_rejected"
    };
    const int solved = route_count(board);
    cout << "net_index\treason\n";
    for (const auto& net : nets) {
        if (unsigned(net.id) % shard_count != shard || has_route(board.routes[net.id])) continue;
        board.tracks.use_pads(net);
        cout << net.id << '\t' << reasons[maze.run(net, board.occupied).status] << '\n';
    }
    cerr << "verified_routes=" << solved << " unresolved=" << nets.size() - solved
         << " upstream_matched=" << maze.matched << '\n';
}
