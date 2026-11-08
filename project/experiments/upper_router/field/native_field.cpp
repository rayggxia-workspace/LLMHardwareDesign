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
    if (std::string(magic, 8) != "UPPERR23") throw std::runtime_error("scene format");
    const auto count = read<uint32_t>(input);
    const auto boxes = read<uint64_t>(input);
    const auto eps = read<double>(input);
    const auto native_bin = read<uint32_t>(input);
    fsv::Geometry geometry;
    std::vector<std::vector<fsv::Vec3>> nodes(count);
    for (uint32_t i = 0; i < count; ++i) {
      auto len = read<uint32_t>(input);
      if (len > 100000) throw std::runtime_error("invalid net label");
      std::string name(len, ' '); input.read(name.data(), len);
      auto grounded = read<uint8_t>(input);
      if (geometry.addNet(name) != int(i)) throw std::runtime_error("net index");
      if (grounded) geometry.setGrounded(i);
      const auto bins=read<uint32_t>(input);
      for(uint32_t j=0;j<bins;++j) {
        fsv::Vec3 node;
        for(auto& v:node)v=read<double>(input);
        nodes[i].push_back(node);
      }
    }
    std::vector<int> groups;
    groups.reserve(boxes);
    for (uint64_t i = 0; i < boxes; ++i) {
      const int net = read<int32_t>(input), group = read<int32_t>(input);
      fsv::Box box;
      for (auto& v : box.lo) v = read<double>(input);
      for (auto& v : box.hi) v = read<double>(input);
      if (group < 0 || group > int(native_bin)) throw std::runtime_error("invalid origin group");
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
      options.capture_nodes=nodes;options.capture_nodes.at(master).clear();
      auto row = solver.solve(scene, master, options);
      if (row.partial_cap.size() != native_bin+1) throw std::runtime_error("origin bins missing");
      std::cout << "{\"master\":" << master << ",\"net\":\"" << geometry.netName(master)
                << "\",\"walks\":" << row.walks << ",\"hops\":" << row.hops
                << ",\"total_ff\":" << row.cap.at(master)
                << ",\"sigma_ff\":" << row.sigma.at(master)
                << ",\"ground\":[" << row.ground << ',' << row.ground_sigma
                << "],\"values\":[";
      for (uint32_t j = 0; j <= count; ++j) {
        const double value = j == count ? row.ground : row.cap[j];
        const double sigma = j == count ? row.ground_sigma : row.sigma[j];
        double sum=0;for(const auto& p:row.partial_cap)sum+=p[j];
        if (std::abs(sum-value) > 1e-9*std::max(1.0,std::abs(value)))
          throw std::runtime_error("origin sum violates total row");
        if (j) std::cout << ',';
        std::cout << '[' << value << ',' << sigma << ']';
      }
      std::cout << "],\"node_self\":[";
      for(size_t i=0;i<nodes[master].size();++i) {
        if(i)std::cout<<',';
        std::cout<<'['<<row.partial_cap[i][master]<<','<<row.partial_sigma[i][master]<<']';
      }
      std::cout << "],\"bins\":[";
      bool first=true;int column=0;
      for(uint32_t target=0;target<=count;++target) {
        const int captures=(target==count || target==uint32_t(master) || nodes[target].empty())?1:nodes[target].size();
        for(int j=0;j<captures;++j,++column) {
          if(target==uint32_t(master))continue;
          for(size_t i=0;i<nodes[master].size();++i) {
            double c=row.joint_cap.at(i).at(column),s=row.joint_sigma.at(i).at(column);
            if(c==0 && s==0)continue;
            if(!first)std::cout<<',';first=false;
            std::cout<<'['<<target<<','<<i<<','<<j<<','<<c<<','<<s<<']';
          }
        }
      }
      if(row.joint_cap.at(0).size()!=size_t(column))throw std::runtime_error("capture count mismatch");
      std::cout << "]}" << std::endl;
    }
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n'; return 1;
  }
}

