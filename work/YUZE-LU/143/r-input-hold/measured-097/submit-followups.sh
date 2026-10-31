#!/bin/bash
set -euo pipefail
base=/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030
root=$base/snapshots/097
test -f "$root/source-manifest.json"
test ! -e "$base/outputs/098"
test ! -e "$base/outputs/099"
gate=$(sbatch --parsable --exclusive --exclude=node[19-24] --job-name=yzl-bv2-rgates --dependency=afterok:94257 --cpus-per-task=96 --output="$base/run098-%j.out" --error="$base/run098-%j.err" "$base/r-gates-memory098.sh" "$root" "$base/outputs/097" "$base/outputs/098")
printf '098 gate %s depends94257\n' "$gate"
pack=$(sbatch --parsable --exclude=node[19-24] --job-name=yzl-bv2-pack --dependency="afterok:$gate" --cpus-per-task=16 --output="$base/run099-%j.out" --error="$base/run099-%j.err" "$root/project/experiments/block_v2/remote_bundle.sh" "$root" "$base" "$base/outputs/099" r 098)
printf '099 pack %s depends%s\n' "$pack" "$gate"
for jid in 94257 "$gate" "$pack"; do scontrol show job "$jid" -o; done
