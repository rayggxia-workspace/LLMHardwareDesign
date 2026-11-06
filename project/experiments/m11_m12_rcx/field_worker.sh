#!/usr/bin/env bash
set -euo pipefail
export PATH="/OpenROAD-flow-scripts/tools/install/OpenROAD/bin:/usr/local/bin/wrapped-cc:$PATH"
out=$1
shift
repo="$PWD/project/experiments/m11_m12_rcx"
if [[ ${1:-} == --coupon ]]; then
    shift
    exec python3 -B "$repo/field_coupon.py" --out "$out" "$@"
fi
source=/public/home/yuzelu/opt/eda/llhd-fsv-i121-block-v1-20261027-099
mkdir "$out"
printf '3b93cdc256e6671364f35e4f1d55a1b4671cdb6a74164136c6935c89d3b7f71c  %s\n' \
    "$source/llhd-capture-field" | sha256sum -c -
printf '09050c70f91ca154b207d959991dc3762968c62a06870573346fb10d421333d3  %s\n' \
    "$source/src/fsv/include/fsv/Solver.h" | sha256sum -c -
objects=()
for unit in AliasTable CubeGreens CubePanels Dielectric GaussianSurface Geometry Itf \
    LayeredCubeGreens LayeredSquareGreens LayerModes Scene Solver SpatialIndex SquareGreens Stack WorkerPool; do
    objects+=("$source/$unit.o")
done
sha256sum "${objects[@]}" "$repo/field_row.cpp" > "$out/solver-inputs.sha256"
g++ -std=c++20 -O3 -pthread -I"$source/src/fsv/include" \
    "$repo/field_row.cpp" "${objects[@]}" -o "$out/field_row"
sha256sum "$out/field_row" > "$out/solver.sha256"
python3 -B "$repo/field_extract.py" --out "$out/result" --solver "$out/field_row" "$@"
