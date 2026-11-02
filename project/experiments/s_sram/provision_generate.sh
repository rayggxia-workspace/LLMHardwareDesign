#!/bin/bash
# Execute only inside an allocated Linux EDA container. Never installs globally.
set -euo pipefail
test -n "${SLURM_JOB_ID:-}"
test "$#" -ge 2
test "$#" -le 3
src=$(realpath "$1")
out=$(realpath "$2")
prefix=/public/home/yuzelu/opt/eda/issue155-sram
mkdir -p "$prefix" "$out"
export OPENRAM_TMP="$out/openram-temp"
export TMPDIR="$out/tmp"
mkdir -p "$OPENRAM_TMP" "$TMPDIR"
exec > >(tee "$out/provision.log") 2>&1
date -u
python3 --version
command -v klayout
mkdir -p "$out/flow-reference"
for f in platforms/nangate45/config.mk platforms/nangate45/pdn/BLOCKS.tcl scripts/macro_placement.tcl scripts/floorplan.tcl scripts/pdn.tcl scripts/global_connect.tcl; do
  if test -f "/OpenROAD-flow-scripts/flow/$f"; then
    cp "/OpenROAD-flow-scripts/flow/$f" "$out/flow-reference/$(basename "$f")"
  fi
done
test -n "${S_SRAM_OFFLINE:-}"
(cd "$S_SRAM_OFFLINE" && sha256sum -c SHA256SUMS)
export PYTHONPATH="$prefix/python${PYTHONPATH:+:$PYTHONPATH}"
if ! python3 -c 'import openram,numpy,scipy,sklearn,coverage; from importlib.metadata import version; assert [version(p) for p in ("openram","numpy","scipy","scikit-learn","coverage")] == ["1.2.48","1.26.4","1.13.1","1.5.2","7.6.1"]'; then
  python3 -m pip install --upgrade --no-cache-dir --no-index --find-links "$S_SRAM_OFFLINE/wheels" --target "$prefix/python" --no-warn-script-location 'openram==1.2.48' 'numpy==1.26.4' 'scipy==1.13.1' 'scikit-learn==1.5.2' 'coverage==7.6.1'
fi
export PATH="$prefix/bin:$PATH"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
if ! command -v ngspice; then
  # Official stable source release, installed only in the authorized tools root.
  cd "$prefix"
  cp "$S_SRAM_OFFLINE/ngspice-45.tar.gz" ngspice-45.tar.gz
  sha256sum ngspice-45.tar.gz | tee "$out/ngspice-source.sha256"
  tar -xzf ngspice-45.tar.gz
  mkdir -p ngspice-build
  cd ngspice-build
  ../ngspice-45/configure --prefix="$prefix" --without-x --with-readline=no --disable-debug
  make -j 8
  make install
fi
ngspice --version
python3 -m pip freeze --path "$prefix/python" > "$out/python-packages.txt"
extra=()
if test "$#" -eq 3; then
  test "$3" = --internal-pins
  extra=(--internal-pins)
fi
compiler="$prefix/python/openram/sram_compiler.py"
if test "${S_SRAM_LINEAR_GRAPH:-0}" = 1; then
  overlay="$prefix/overlays/$(basename "$out")"
  python3 "$src/project/experiments/s_sram/linear_graph_overlay.py" --source "$prefix/python/openram" --destination "$overlay" --out "$out/graph-overlay.json"
  export PYTHONPATH="$overlay:$PYTHONPATH"
  export OPENRAM_HOME="$overlay/openram/compiler"
  export S_SRAM_GRAPH_OVERLAY_RECEIPT="$out/graph-overlay.json"
  compiler="$overlay/openram/sram_compiler.py"
fi
python3 "$src/project/experiments/s_sram/generate_bank.py" --compiler "$compiler" --out "$out/generation" "${extra[@]}"
