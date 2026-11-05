#!/usr/bin/env bash
#SBATCH --job-name=yzl-ucf-wellprobe
#SBATCH --partition=c64
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --time=UNLIMITED
#SBATCH --output=wellprobe-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
base=$PWD
test "$#" -eq 2
read -r -a writers <<< "${UCF_WELL_WRITERS:-raw xy8190 xy1024 xy_multi}"
need=$(($# * ${#writers[@]} * 8))
mapfile -t masks < <(python3 -c 'import os,sys; a=sorted(os.sched_getaffinity(0)); n=int(sys.argv[1]); assert len(a)>=n; print("\n".join(",".join(map(str,a[i:i+8])) for i in range(0,n,8)))' "$need")
test "${#masks[@]}" -eq "$((need / 8))"
pinned=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
idx=0
pids=()
for candidate in "$@"; do
    for writer in "${writers[@]}"; do
        work="$base/wellprobe-$SLURM_JOB_ID-${candidate##*/}-$writer"
        mkdir -p "$work/tmp/klayout" "$work/tmp/cache"
        taskset -c "${masks[idx]}" "$pinned" exec --cleanenv --bind /public/home/yuzelu \
            --pwd "$work" --env "SLURM_JOB_ID=$SLURM_JOB_ID,OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1,KLAYOUT_HOME=$work/tmp/klayout,XDG_CACHE_HOME=$work/tmp/cache" \
            "$image" bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
unset TMPDIR
candidate=$1
writer=$2
if test "$writer" = raw || test "$writer" = rawflat; then
    gds=$(python3 -c "import json,sys; p,=(p for p in json.load(open(sys.argv[1]))[\"outputs\"] if p.endswith(\".gds\")); print(p)" "$candidate/completion.json")
else
    python3 -B "$3/canonical_stream.py" "$candidate" "$writer"
    gds="$PWD/6_final.gds"
fi
deck=/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc
{
    grep -E "^(source\(|report\(|tiles\(|tile_borders\(|deep$|threads\(|verbose\(|pwell + =? *polygons|nwell + =? *polygons)" "$deck"
    grep -Fx "well = nwell.or(pwell)" "$deck"
    grep -F "well.separation(well, 200.nm, euclidian)" "$deck"
} > well-only.drc
test "$(wc -l < well-only.drc)" -eq 11
if test "$writer" = rawflat; then sed -i "s/^deep$/flat/" well-only.drc; fi
klayout -b -r well-only.drc -rd in_gds="$gds" -rd report_file="$PWD/well-only.lyrdb" > well-only.log 2>&1
sha256sum "$deck" "$gds" well-only.drc well-only.lyrdb > diagnostic.sha256
python3 -c "import xml.etree.ElementTree as E; print(len(E.parse(\"well-only.lyrdb\").findall(\".//items/item\")))" > markers
' bash "$candidate" "$writer" "$base" > "$work/job.log" 2>&1 &
        pids+=("$!")
        idx=$((idx+1))
    done
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
exit "$failed"
