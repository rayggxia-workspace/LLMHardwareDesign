#!/bin/bash
set -euo pipefail
source_root=/public/home/yuzelu/opt/eda/llhd-fsv-i121-block-v1-20261027-099
objects=()
for unit in AliasTable CubeGreens CubePanels Dielectric GaussianSurface Geometry Itf LayeredCubeGreens LayeredSquareGreens LayerModes Scene Solver SpatialIndex SquareGreens Stack WorkerPool; do
 objects+=("$source_root/$unit.o")
done
sha256sum "${objects[@]}" node_row.cpp > compiler-inputs.sha256
g++ -std=c++20 -O3 -pthread -I"$source_root/src/fsv/include" node_row.cpp "${objects[@]}" -o node_row
sha256sum node_row > solver.sha256
python3 pilot.py
