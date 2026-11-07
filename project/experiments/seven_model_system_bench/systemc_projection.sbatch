#!/bin/bash
#SBATCH --job-name=hpy-seven-scm
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --cpus-per-task=2
set -euo pipefail
root=$(realpath "$1")
systemc=$(realpath "$2")
source_run=$(realpath "$3")
case "$root" in /public/home/yuzelu/PingyangHuang/issue-197-*) ;; *) exit 2;; esac
cd "$root"
sha256sum -c sc-projection-upload.sha256
mkdir sc-projection-results sc-projection-tmp
out="$root/sc-projection-results"
export TMPDIR="$root/sc-projection-tmp"
g++ -std=c++17 -DSC_ALLOW_DEPRECATED_IEEE_API -O2 -Wall -Wextra -Werror -I"$systemc/include" \
    -I"$source_run/source-systemc/project/systemc/include" "$root/systemc_projection.cpp" \
    -L"$systemc/lib64" "-Wl,-rpath,$systemc/lib64" -lsystemc -o "$out/sc-projection" \
    >"$out/build.log" 2>&1
for run in "$source_run"/projection-results/*/vectors.json; do
    folder=${run%/*}
    model=${folder##*/}
    mkdir "$out/$model"
    for fixture in "$folder"/*.txt; do
        file=${fixture##*/}
        "$out/sc-projection" "$fixture" >"$out/$model/${file%.txt}.json" \
            2>"$out/$model/${file%.txt}.log"
    done
done
(cd "$out"; sha256sum -- */*.json sc-projection >results.sha256)
