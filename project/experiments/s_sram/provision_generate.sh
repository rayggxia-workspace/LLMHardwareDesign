#!/bin/bash
# Execute only inside an allocated Linux EDA container. Never installs globally.
set -euo pipefail
test -n "${SLURM_JOB_ID:-}"
test "$#" -eq 2
src=$(realpath "$1")
out=$(realpath "$2")
prefix=/public/home/yuzelu/opt/eda/issue155-sram
mkdir -p "$prefix" "$out"
exec > >(tee "$out/provision.log") 2>&1
date -u
python3 --version
command -v klayout
python3 -m pip install --target "$prefix/python" --no-warn-script-location 'openram==1.2.48' 'numpy==1.26.4' 'scipy==1.13.1' 'scikit-learn==1.5.2' 'coverage==7.6.1'
export PYTHONPATH="$prefix/python${PYTHONPATH:+:$PYTHONPATH}"
export PATH="$prefix/bin:$PATH"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
if ! command -v ngspice; then
  # Official stable source release, installed only in the authorized tools root.
  cd "$prefix"
  curl --fail --location --retry 2 --max-time 180 -o ngspice-45.tar.gz https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/old-releases/45/ngspice-45.tar.gz
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
python3 "$src/project/experiments/s_sram/generate_bank.py" --compiler "$prefix/python/openram/sram_compiler.py" --out "$out/generation"
