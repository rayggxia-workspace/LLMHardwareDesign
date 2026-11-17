#!/bin/bash
set -euo pipefail
source_root=/public/home/yuzelu/opt/eda/llhd-fsv-i121-block-v1-20261027-099
g++ -std=c++20 -O3 -pthread -Iinclude -I"$source_root/src/fsv/include" -I"$source_root/src/fsv/src" -c Solver-edge.cpp -o Solver-edge.o
objects=()
for unit in AliasTable CubeGreens CubePanels Dielectric GaussianSurface Geometry Itf LayeredCubeGreens LayeredSquareGreens LayerModes Scene SpatialIndex SquareGreens Stack WorkerPool; do objects+=("$source_root/$unit.o"); done
g++ -std=c++20 -O3 -pthread -Iinclude -I"$source_root/src/fsv/include" node_edge.cpp Solver-edge.o "${objects[@]}" -o node_edge
sha256sum node_edge Solver-edge.cpp include/fsv/Solver.h > edge-solver.sha256
PROJECTION_PREFIX=edge- python3 pilot.py
