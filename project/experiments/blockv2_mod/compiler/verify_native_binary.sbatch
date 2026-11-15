#!/bin/bash
set -euo pipefail
export PYTHONPATH="$PWD/compiler:/public/home/yuzelu/project-circuit/issue260-tlm-request-Xuwu5O"
python3.11 -B compiler/verify_native_binary.py "$1"
