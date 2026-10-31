#!/bin/bash
set -euo pipefail
base=/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030
root=$base/snapshots/100
test -f "$root/source-manifest.json"
test ! -e "$base/outputs/101"
test ! -e "$base/outputs/102"
gate=$(sbatch --parsable --exclusive --exclude=node[19-24] --job-name=yzl-bv2-rgates --dependency=afterok:94260 --cpus-per-task=96 --output="$base/run101-%j.out" --error="$base/run101-%j.err" "$base/r-gates-memory101.sh" "$root" "$base/outputs/100" "$base/outputs/101")
printf '101 gate %s depends94260\n' "$gate"
pack=$(sbatch --parsable --exclude=node[19-24] --job-name=yzl-bv2-pack --dependency="afterok:$gate" --cpus-per-task=16 --output="$base/run102-%j.out" --error="$base/run102-%j.err" "$root/project/experiments/block_v2/remote_bundle.sh" "$root" "$base" "$base/outputs/102" r 101)
printf '102 pack %s depends%s\n' "$pack" "$gate"
for jid in 94260 "$gate" "$pack"; do scontrol show job "$jid" -o; done
