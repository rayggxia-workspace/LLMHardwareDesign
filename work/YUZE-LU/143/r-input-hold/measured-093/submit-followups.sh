#!/bin/bash
set -euo pipefail
base=/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030
root=$base/snapshots/093
test -f "$root/source-manifest.json"
test ! -e "$base/outputs/094"
test ! -e "$base/outputs/095"
gate=$(sbatch --parsable --exclusive --exclude=node[19-24] --job-name=yzl-bv2-rgates --dependency=afterok:94218 --cpus-per-task=96 --output="$base/run094-%j.out" --error="$base/run094-%j.err" "$base/r-gates-memory094.sh" "$root" "$base/outputs/093" "$base/outputs/094")
printf '094 gate %s depends94218\n' "$gate"
pack=$(sbatch --parsable --exclude=node[19-24] --job-name=yzl-bv2-pack --dependency="afterok:$gate" --cpus-per-task=16 --output="$base/run095-%j.out" --error="$base/run095-%j.err" "$root/project/experiments/block_v2/remote_bundle.sh" "$root" "$base" "$base/outputs/095" r 094)
printf '095 pack %s depends%s\n' "$pack" "$gate"
for jid in 94218 "$gate" "$pack"; do scontrol show job "$jid" -o; done
