#!/bin/bash
set -euo pipefail
cache=/mnt/c/Users/wine10/AppData/Local/Codex/issue219-rowtile-rtl
root=/tmp/yzl-issue219-iverilog12-20261109
mkdir "$root"
cd "$root"
tar -xzf "$cache/iverilog-v12_0.tar.gz"
cd iverilog-12_0
sh autoconf.sh > "$cache/iverilog-autoconf.log" 2>&1
./configure --prefix="$root/install" > "$cache/iverilog-configure.log" 2>&1
make -j4 > "$cache/iverilog-make.log" 2>&1
make install > "$cache/iverilog-install.log" 2>&1
"$root/install/bin/iverilog" -V > "$cache/iverilog-version.log" 2>&1
echo 'PASS private Icarus build'
