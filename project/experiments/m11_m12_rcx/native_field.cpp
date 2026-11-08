// SPDX-License-Identifier: BSD-3-Clause
// Grouped native context is exact for upper excitation: all non-excited
// electrodes are held at the same zero potential in a Maxwell basis solve.
// Native signal groups are retained separately from grounded PG conductors.
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include "fsv/Solver.h"

template <class T> T read(std::ifstream& file) {
  T v{}; file.read(reinterpret_cast<char*>(&v), sizeof(v));
  if (!file) throw std::runtime_error("truncated scene");
  return v;
}

int main(int argc, char** argv) {
  try {
    if (argc != 7) throw std::runtime_error("scene masters threads walks offset seed");
    std::ifstream input(argv[1], std::ios::binary);
    char magic[8]; input.read(magic, 8);
    if (std::string(magic, 8) != "NATIVE22") throw std::runtime_error("scene format");
    const auto count = read<uint32_t>(input);
    const auto boxes = read<uint64_t>(input);
    const auto eps = read<double>(input);
    fsv::Geometry geometry;
    for (uint32_t i = 0; i < count; ++i) {
      auto len = read<uint32_t>(input);
      if (len > 100000) throw std::runtime_error("invalid net label");
      std::string name(len, ' '); input.read(name.data(), len);
      auto grounded = read<uint8_t>(input);
      if (geometry.addNet(name) != int(i)) throw std::runtime_error("net index");
      if (grounded) geometry.setGrounded(i);
    }
    std::vector<int> groups;
    groups.reserve(boxes);
    for (uint64_t i = 0; i < boxes; ++i) {
      const int net = read<int32_t>(input), group = read<int32_t>(input);
      fsv::Box box;
      for (auto& v : box.lo) v = read<double>(input);
      for (auto& v : box.hi) v = read<double>(input);
      if (group < 0 || group > 1) throw std::runtime_error("invalid origin group");
      geometry.addBox(net, box); groups.push_back(group);
    }
    if (input.peek() != EOF) throw std::runtime_error("scene has trailing bytes");
    std::cerr << "SCENE " << count << " nets " << boxes << " boxes\n";
    fsv::Scene scene(geometry, eps);
    const int threads = std::stoi(argv[3]);
    fsv::Solver solver({.threads=threads, .seed=std::stoull(argv[6])});
    fsv::SolveOptions options;
    options.min_walks = std::stoll(argv[4]);
    options.max_walks = 16 * options.min_walks;
    options.tol_total = 0.002;
    options.tol_coupling = 0.002;
    options.gauss_offset = std::stod(argv[5]);
    options.origin_box_groups = groups;
    std::ifstream masters(argv[2]);
    int master;
    std::cout << std::setprecision(17);
    while (masters >> master) {
      std::cerr << "MASTER " << master << std::endl;
      auto row = solver.solve(scene, master, options);
      if (row.partial_cap.size() != 2) throw std::runtime_error("origin bins missing");
      std::cout << "{\"master\":" << master << ",\"net\":\"" << geometry.netName(master)
                << "\",\"walks\":" << row.walks << ",\"hops\":" << row.hops
                << ",\"total_ff\":" << row.cap.at(master)
                << ",\"sigma_ff\":" << row.sigma.at(master)
                << ",\"ground\":[" << row.ground << ',' << row.ground_sigma
                << "],\"values\":[";
      for (uint32_t j = 0; j <= count; ++j) {
        const double value = j == count ? row.ground : row.cap[j];
        const double sigma = j == count ? row.ground_sigma : row.sigma[j];
        const double sum = row.partial_cap[0][j] + row.partial_cap[1][j];
        if (std::abs(sum-value) > 1e-9*std::max(1.0,std::abs(value)))
          throw std::runtime_error("origin sum violates total row");
        if (j) std::cout << ',';
        std::cout << '[' << value << ',' << sigma << ','
                  << row.partial_cap[0][j] << ',' << row.partial_sigma[0][j] << ','
                  << row.partial_cap[1][j] << ',' << row.partial_sigma[1][j] << ']';
      }
      std::cout << "]}" << std::endl;
    }
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n'; return 1;
  }
}
