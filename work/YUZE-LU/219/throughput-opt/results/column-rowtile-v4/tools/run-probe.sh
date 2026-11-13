#!/bin/bash
set -euo pipefail
directory=$1
tool=/tmp/yzl-issue219-iverilog12-20261109/install/bin
cd "$directory"
"$tool/iverilog" -g2012 -Irtl/block_v2 -I. -s tb_row_tile_probe -o probe.vvp -f compile.f > compile.log 2>&1
"$tool/vvp" probe.vvp > simulate.log 2>&1
echo 'PASS probe simulation process'
