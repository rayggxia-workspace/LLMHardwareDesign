#!/usr/bin/env bash
set -euo pipefail
root=$(pwd -P)
top=$1
spec="$2"
run=$(mktemp -d "$root/audit.XXXXXXXX")
b=/public/home/yuzelu/PingyangHuang
a="$b/hpy-pr271-top-hsVf4b"
old="$b/hpy-pr276-more-escape.wTRlKfO9/upper/upper-edge2-d9-116336.log"
prior="$(sed -n 's/^run=//p' "$old")/routes.json"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$a/project/experiments/upper_router:$a/project/experiments/block_synthesis"
python3 -B "$root/verify-top.py" verify "$spec/derived-spec.json" "$top/paths.txt.initial" "$run/initial.json" --original "$a/inputs/top-1834/algorithm2-input.json" --escape "$spec/lower-evidence.json"
python3 -B "$root/audit-cuts.py" "$spec" "$a/inputs/placement.json" --routes "$top/routes.json" > "$run/cuts.json"
python3 -B "$root/post-check.py" "$spec" "$run/initial.json" "$top/routes.json" "$prior" > "$run/comparison.json"
printf 'audit_run=%s\n' "$run"
sha256sum "$run/initial.json" "$run/cuts.json" "$run/comparison.json"
