#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-transaction
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:45:00
set -euo pipefail
root=$(pwd -P)
spec_dir=$1
seed_mode=$2
density=$3
repairs=$4
variant=$(basename "$spec_dir")
run=$(mktemp -d "$root/top-$seed_mode.XXXXXXXX")
cd "$run"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
b=/public/home/yuzelu/PingyangHuang
origin="$b/hpy-pr271-top-hsVf4b"
export PYTHONPATH="$origin/project/experiments/upper_router:$origin/project/experiments/block_synthesis"
old="$b/hpy-pr276-more-escape.wTRlKfO9/upper/upper-edge2-d9-116336.log"
seed=-
if [[ "$seed_mode" == warm ]]; then
    seed="$(sed -n 's/^run=//p' "$old")/paths.txt"
    test -f "$seed"
    sha256sum "$seed"
fi
printf 'run=%s\nvariant=%s\nseed_mode=%s density=%s repairs_requested=%s\n' "$run" "$variant" "$seed_mode" "$density" "$repairs"
printf '%s  %s\n' 9c28df8dccacb06ce71a65ffc1141755a1a443e1f732a7a21f3d45abc0e80c61 "$root/cugr-maze-route.inc" | sha256sum -c
g++ -std=c++17 -O3 -Wall -Wextra -Wno-unused-variable "$root/transactional-maze.cpp" -o transactional-maze
printf '%s\n' '1 1 420 420 2' '0 3 3' '43 42' '251 210' '336 42' '21 21 64 64' '230 189 273 231' '315 21 357 63' '1 2 2' '42 336' '252 336' '21 315 63 357' '231 315 273 357' > smoke.graph
./transactional-maze smoke.graph smoke.paths - 4 0
test "$(awk 'NF == 3 { n++ } END { print n+0 }' smoke.paths)" = 2
spec="$spec_dir/derived-spec.json"
overlay="$spec_dir/lower-evidence.json"
original="$origin/inputs/top-1834/algorithm2-input.json"
sha256sum "$spec" "$overlay" "$spec_dir/graph.txt" "$root/transactional-maze.cpp" "$root/cugr-maze-route.inc" "$root/verify-top.py" "$root/run-upper.sh"
/usr/bin/time -f 'routing_seconds=%e rss_kib=%M' ./transactional-maze "$spec_dir/graph.txt" paths.txt "$seed" "$density" "$repairs"
python3 -B "$root/verify-top.py" verify "$spec" paths.txt routes.json --original "$original" --escape "$overlay"
sha256sum paths.txt paths.txt.initial routes.json
