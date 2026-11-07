#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=${1:?output directory}
mkdir -p "$out";out=$(cd "$out" && pwd)
python3 -B "$here/prepare_hold.py" --out "$out"
SMOKE=0 bash "$out/hold-run.sh" "$out"
