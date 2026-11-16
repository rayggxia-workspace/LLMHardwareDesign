#!/bin/bash
set -euo pipefail
root=/tmp/yzl-issue219-python3128-20261109
mkdir "$root"
cd "$root"
tar -xzf /mnt/c/Users/wine10/AppData/Local/Codex/issue219-linux-python3128/Python-3.12.8.tgz
cd Python-3.12.8
./configure --prefix="$root/install" --with-ensurepip=install > "$root/configure.log" 2>&1
make -j4 > "$root/build.log" 2>&1
make install > "$root/install.log" 2>&1
"$root/install/bin/python3.12" -VV
"$root/install/bin/python3.12" -m test test_set test_json test_dataclasses > "$root/runtime-tests.log" 2>&1
printf '%s\n' "$root"
