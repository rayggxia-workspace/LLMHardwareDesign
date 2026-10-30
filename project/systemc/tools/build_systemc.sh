#!/usr/bin/env bash
set -euo pipefail
# Local dependency only; no sudo and no global configuration changes.
repo_root=$(cd "$(dirname "$0")/../../.." && pwd)
deps="$repo_root/.systemc-deps"
mkdir -p "$deps"
cd "$deps"
if [ ! -f systemc.tar.gz ]; then
  curl -fL --connect-timeout 15 --max-time 180 \
    https://codeload.github.com/accellera-official/systemc/tar.gz/refs/tags/3.0.1 \
    -o systemc.tar.gz
fi
printf '%s  %s\n' d07765d0d2ffd6c01767880d0c6aaf53cd9487975f898c593ffffd713258fcbb systemc.tar.gz | sha256sum -c -
if [ ! -d systemc-3.0.1 ]; then tar -xzf systemc.tar.gz; fi
cmake -S systemc-3.0.1 -B build -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$deps/install"
cmake --build build -j 6
cmake --install build
