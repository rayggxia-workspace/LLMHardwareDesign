#!/usr/bin/env bash
set -euo pipefail
cd "$1"
shift
tools_dir=$1
: "${PYTHONPATH:?include block_synthesis, upper_router, native_ingress, and the native codec paths}"
shift
python3.11 -B "$tools_dir/tlm_plan_preflight.py" "$@"
