#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
variant=${1:?job ID}
case "$variant" in
  113742) args=() ;;
  113850) args=(--ffn-only) ;;
  *) exit 2 ;;
esac
wait_root=../ffn-wait-06
baseline="$wait_root/run-113287/replay-113287"
candidate="run-$variant/replay-$variant"
timing="results/$variant"
(cd "$candidate"; sha256sum -c ffn-wait.sha256; sha256sum -c proof.sha256 > /dev/null)
mkdir -p "$timing"
for mode in 0 1; do
  python3 -B audit_ffn_wait.py "$candidate/ffn-wait-$mode.log" "$candidate/generated/assets.txt" \
    > "$timing/mode-$mode.json"
done
python3 -B audit_exec_pair.py "$baseline" "$candidate" "$wait_root/results" "$timing" "${args[@]}" \
  > "$timing/ab.json"
for mode in 0 1; do
  python3 -B compare_exec_replays.py "$wait_root/results/mode-$mode.json" "$timing/mode-$mode.json" \
    > "$timing/mode-$mode-comparison.json"
  python3 -B estimate_exec_sensitivity.py "$timing/mode-$mode-comparison.json" \
    ../ffn-weight-05/tlm/run-113165 ../ffn-weight-05/tlm/run-113167 \
    > "$timing/sensitivity-$mode.json"
done
sha256sum "$timing/"*.json > "$timing/results.sha256"
sha256sum -c "$timing/results.sha256"
