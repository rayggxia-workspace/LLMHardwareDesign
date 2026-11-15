// Pick up nets that fit the verified board once the temporary reservations are gone.
#define main transactional_main
#include "transactional-maze.cpp"
#undef main

int main(int argc, char** argv) {
    if (argc != 5) return 2;
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
    const int initial = route_count(board);
    write_routes(string(argv[4]) + ".initial", board.routes);
    ifstream input(argv[3]);
    if (!input) throw runtime_error("Cannot read candidate net indices");
    Router maze(board.tracks, 24, false);
    int id, attempts = 0, added = 0;
    while (input >> id) {
        if (has_route(board.routes.at(id))) continue;
        const auto& net = nets.at(id);
        board.tracks.use_pads(net);
        ++attempts;
        auto trial = maze.run(net, board.occupied);
        if (trial.status != connected) continue;
        board.install(id, move(trial.route));
        cout << "adopted " << id << '\n';
        ++added;
    }
    if (!input.eof() || route_count(board) != initial + added)
        throw runtime_error("Could not verify completion of direct retry pass");
    write_routes(argv[4], board.routes);
    cerr << "close initial=" << initial << " attempted=" << attempts << " added=" << added
         << " upstream_matched=" << maze.matched << " now=" << route_count(board) << '\n';
}
