#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-fixed-reach
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:12:00
set -euo pipefail
source_dir=$(pwd -P)
variant=$1
graph=$2
run=$(mktemp -d "$source_dir/diag-$variant.XXXXXXXX")
cd "$run"
export TMPDIR="$run"
printf 'run=%s\nvariant=%s\n' "$run" "$variant"
g++ -std=c++17 -O3 -Wall -Wextra -Wno-unused-variable "$source_dir/fixed-reach.cpp" -o fixed-reach
./fixed-reach "$graph" fixed-reach.tsv
sha256sum "$graph" fixed-reach.tsv "$source_dir/fixed-reach.cpp" "$source_dir/reference-maze.cpp"
