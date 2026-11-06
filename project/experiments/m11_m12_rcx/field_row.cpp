// SPDX-License-Identifier: BSD-3-Clause
// One Maxwell row with origin and capture bins at physical resistor nodes.
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "fsv/Solver.h"

int main(int argc, char** argv)
{
  try {
    if (argc != 6) {
      throw std::runtime_error("usage: field_row scene master threads seed min_walks");
    }
    const int master = std::stoi(argv[2]);
    const int threads = std::stoi(argv[3]);
    const auto seed = std::stoull(argv[4]);
    const auto min_walks = std::stoll(argv[5]);
    std::ifstream scene(argv[1]);
    double eps;
    int count;
    if (!(scene >> eps >> count) || master < 0 || master >= count
        || !(eps > 0) || threads < 1 || min_walks < 16384) {
      throw std::runtime_error("invalid scene or solve budget");
    }
    fsv::Geometry geometry;
    std::vector<std::vector<fsv::Vec3>> nodes(count);
    for (int i = 0; i < count; ++i) {
      int boxes, bins;
      if (!(scene >> boxes >> bins) || boxes < 1 || bins < 2) {
        throw std::runtime_error("invalid conductor inventory");
      }
      const int net = geometry.addNet("n" + std::to_string(i));
      std::vector<fsv::Box> bounds;
      for (int j = 0; j < boxes; ++j) {
        fsv::Box box;
        for (auto& v : box.lo) scene >> v;
        for (auto& v : box.hi) scene >> v;
        if (!scene) throw std::runtime_error("invalid box");
        geometry.addBox(net, box);
        bounds.push_back(box);
      }
      for (int j = 0; j < bins; ++j) {
        fsv::Vec3 node;
        for (auto& v : node) scene >> v;
        bool covered = false;
        for (const auto& b : bounds) {
          covered |= node[0] >= b.lo[0] && node[0] <= b.hi[0]
                  && node[1] >= b.lo[1] && node[1] <= b.hi[1]
                  && node[2] >= b.lo[2] && node[2] <= b.hi[2];
        }
        if (!scene || !covered) throw std::runtime_error("node outside conductor");
        nodes[i].push_back(node);
      }
    }
    fsv::SolveOptions opts;
    opts.min_walks = min_walks;
    opts.max_walks = 16 * min_walks;
    opts.tol_total = 0.0015;
    opts.tol_coupling = 0.0015;
    opts.gauss_offset = 0.25;
    opts.partial_nodes = nodes[master];
    opts.capture_nodes = nodes;
    opts.capture_nodes[master].clear();
    fsv::SolverOptions engine;
    engine.threads = threads;
    engine.seed = seed;
    auto row = fsv::Solver(engine).solve(fsv::Scene(geometry, eps), master, opts);
    std::cout << std::setprecision(17) << "{\"master\":" << master
              << ",\"walks\":" << row.walks << ",\"hops\":" << row.hops << ",\"values\":[";
    for (int n = 0; n < count; ++n) {
      if (n) std::cout << ',';
      std::cout << '[' << row.cap[n] << ',' << row.sigma[n] << ']';
    }
    std::cout << "],\"ground\":[" << row.ground << ',' << row.ground_sigma << "],\"bins\":[";
    bool first = true;
    int col = 0;
    for (int n = 0; n <= count; ++n) {
      const int targets = (n == master || n == count) ? 1 : nodes[n].size();
      for (int j = 0; j < targets; ++j, ++col) {
        if (n == master) continue;
        for (size_t i = 0; i < nodes[master].size(); ++i) {
          const auto value = row.joint_cap.at(i).at(col);
          const auto sigma = row.joint_sigma.at(i).at(col);
          if (value == 0 && sigma == 0) continue;
          if (!first) std::cout << ',';
          first = false;
          std::cout << '[' << n << ',' << i << ',' << j << ',' << value << ',' << sigma << ']';
        }
      }
    }
    if (row.joint_cap.at(0).size() != static_cast<size_t>(col)) {
      throw std::runtime_error("joint column count");
    }
    std::cout << "]}\n";
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
