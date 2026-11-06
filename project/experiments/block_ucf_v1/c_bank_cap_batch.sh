#!/usr/bin/env bash
#SBATCH --job-name=yzl-ucf-c-bank-cap
#SBATCH --partition=c64
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=36
#SBATCH --time=UNLIMITED
#SBATCH --output=bank-cap-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
base="$PWD"
parent="$(dirname "$base")"
pinned=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
name=run-97680-c-skew3-post2
source="$parent/pnr-22/$name"
audit="$parent/audit-13/audit-97696-$name"
loads="$parent/pnr-20/loads-97697-audit-97696-$name"
modes=(minimal guard reroute)
if [[ $# -eq 1 ]]; then modes=("$1"); fi
mapfile -t masks < <(python3 -c 'import os,sys; a=sorted(os.sched_getaffinity(0)); n=int(sys.argv[1])*12; assert len(a)>=n; print("\n".join(",".join(map(str,a[i:i+12])) for i in range(0,n,12)))' "${#modes[@]}")
pids=()
i=0
for mode in "${modes[@]}"; do
    work="$base/run-$SLURM_JOB_ID-c-cap-$mode"
    mkdir -p "$work/tmp/klayout" "$work/tmp/cache"
    taskset -c "${masks[i]}" "$pinned" exec --cleanenv --bind /public/home/yuzelu \
        --pwd "$work" --env "OMP_NUM_THREADS=12,OPENBLAS_NUM_THREADS=1,KLAYOUT_HOME=$work/tmp/klayout,XDG_CACHE_HOME=$work/tmp/cache" \
        "$image" bash -c 'source /OpenROAD-flow-scripts/env.sh; unset TMPDIR; exec python3 -B "$@"' \
        bash "$base/resume_c_bank_cap.py" "$source" "$audit" "$loads" "$mode" > "$work/job.log" 2>&1 &
    pids+=("$!")
    i=$((i+1))
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
exit "$failed"
