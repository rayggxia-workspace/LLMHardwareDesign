#!/bin/bash
set -euo pipefail
base=/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030
root=$base/snapshots/090
test -f "$root/source-manifest.json"
test ! -e "$base/outputs/091"
test ! -e "$base/outputs/092"
gate=$(sbatch --parsable --exclusive --exclude=node[19-24] --job-name=yzl-bv2-rgates --dependency=afterok:94209 --cpus-per-task=96 --output="$base/run091-%j.out" --error="$base/run091-%j.err" "$base/r-gates-memory091.sh" "$root" "$base/outputs/090" "$base/outputs/091")
printf '091 gate %s depends94209\n' "$gate"
pack=$(sbatch --parsable --exclude=node[19-24] --job-name=yzl-bv2-pack --dependency="afterok:$gate" --cpus-per-task=16 --output="$base/run092-%j.out" --error="$base/run092-%j.err" "$root/project/experiments/block_v2/remote_bundle.sh" "$root" "$base" "$base/outputs/092" r 091)
printf '092 pack %s depends%s\n' "$pack" "$gate"
for jid in 94209 "$gate" "$pack"; do scontrol show job "$jid" -o; done
