#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-nearprobe
#SBATCH --partition=c64,c96,debug
#SBATCH --cpus-per-task=6
#SBATCH --time=00:16:00
set -euo pipefail
root=$(pwd -P)
base=$(sed -n 's/^run=//p' "$1")
run=$(mktemp -d "$root/near-probes.XXXXXXXX")
printf 'run=%s\n' "$run"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
cd "$run"
sed -e 's/if(n.id%total!=part)continue;/if(n.id%total!=part||n.pins.size()==2)continue;/' \
    -e '/auto demand=n;/i\            size_t peer=0;\n            for(size_t k=1;k<n.pins.size();++k)\n                if(k!=pin\&\&md(n.pins[k],n.pins[pin])<md(n.pins[peer],n.pins[pin]))peer=k;' \
    -e 's/n.pins.front(),n.pins\[pin\]/n.pins[peer],n.pins[pin]/' \
    -e 's/n.windows.front(),n.windows\[pin\]/n.windows[peer],n.windows[pin]/' \
    "$root/probe-layout.cpp" > probe-near.cpp
g++ -O3 -std=c++17 -Wall -Wextra -Wno-unused-variable -I "$root" probe-near.cpp -o probe
workers=${SLURM_CPUS_PER_TASK:-1}
pids=()
for ((i=0;i<workers;i++)); do
    ./probe "$root/precheck-final/graph.txt" "$i" "$workers" > "part-$i.tsv" &
    pids+=("$!")
done
for pid in "${pids[@]}"; do wait "$pid"; done
head -1 part-0.tsv > near-options.tsv
for f in part-*.tsv; do tail -n +2 "$f"; done | sort -k1,1n -k2,2n >> near-options.tsv
python3 -B "$root/combine-probes.py" "$base/path-options.tsv" near-options.tsv
mv ranked-options.tsv path-options.tsv
sha256sum path-options.tsv near-options.tsv options.json probe-near.cpp
