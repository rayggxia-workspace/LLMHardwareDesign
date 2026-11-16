#!/bin/bash
set -euo pipefail
cache=/mnt/c/Users/wine10/AppData/Local/Codex/issue219-rowtile-rtl
root=/tmp/yzl-issue219-iverilog12-20261109
cd "$root"
apt-get download gperf > "$cache/gperf-download.log" 2>&1
dpkg-deb -x gperf_3.1-1_amd64.deb gperf
export PATH="$root/gperf/usr/bin:$PATH"
sha256sum gperf_3.1-1_amd64.deb > "$cache/gperf.sha256"
apt-cache show gperf > "$cache/gperf-apt.txt"
cd iverilog-12_0
sh autoconf.sh > "$cache/iverilog-autoconf-2.log" 2>&1
./configure --prefix="$root/install" > "$cache/iverilog-configure.log" 2>&1
make -j4 > "$cache/iverilog-make.log" 2>&1
make install > "$cache/iverilog-install.log" 2>&1
"$root/install/bin/iverilog" -V > "$cache/iverilog-version.log" 2>&1
echo 'PASS private Icarus build'
