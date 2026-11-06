#!/usr/bin/env bash
#SBATCH --job-name=yzl-ucf-c-load
#SBATCH --partition=c64
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --output=loads-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
pinned=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
[[ $# -eq 2 ]]
mapfile -t masks < <(python3 -c 'import os; a=sorted(os.sched_getaffinity(0)); assert len(a)>=8; print(",".join(map(str,a[:4]))); print(",".join(map(str,a[4:8])))')
pids=()
i=0
for audit in "$@"; do
    work="$PWD/loads-$SLURM_JOB_ID-${audit##*/}"
    mkdir "$work"
    sha256sum "$audit/sta.tcl" > "$work/input.sha256"
    test "$(grep -c 'report_check_types .* -max_count 3 ' "$audit/sta.tcl")" -eq 1
    sed 's/ -max_count 3 / -max_count 96 /' "$audit/sta.tcl" > "$work/sta-loads.tcl"
    taskset -c "${masks[i]}" "$pinned" exec --cleanenv --bind /public/home/yuzelu \
        --pwd "$work" --env OMP_NUM_THREADS=4 "$image" \
        bash -c 'source /OpenROAD-flow-scripts/env.sh; unset TMPDIR; exec openroad -no_init -exit sta-loads.tcl' \
        > "$work/sta-loads.log" 2>&1 &
    pids+=("$!")
    i=$((i+1))
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
for work in "$PWD"/loads-"$SLURM_JOB_ID"-audit-*; do
    (cd "$work"; sha256sum -c input.sha256; sha256sum electrical-worst.rpt > result.sha256)
done
exit "$failed"
