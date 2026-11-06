#!/usr/bin/env bash
#SBATCH --job-name=yzl-ucf-pnr
#SBATCH --partition=c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=96
#SBATCH --time=UNLIMITED
#SBATCH --output=physical-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
export LC_ALL=C
export OPENBLAS_NUM_THREADS=1
pinned=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
base=$PWD
budget=${SLURM_CPUS_PER_TASK:?}
test "$((budget % 8))" -eq 0
threads=$((budget / 8))
mapfile -t masks < <(python3 -c 'import os,sys; a=sorted(os.sched_getaffinity(0)); n=int(sys.argv[1]); assert len(a)>=8*n; print("\n".join(",".join(map(str,a[i:i+n])) for i in range(0,8*n,n)))' "$threads")
test "${#masks[@]}" = 8
if (($#)); then
    test "$#" -eq 8
    cases=("$@")
else
    cases=(0:1300 0:1450 0:1600 1:1300 1:1450 1:1600 2:1500 2:1800)
fi
pids=()
for i in "${!cases[@]}"; do
    IFS=: read -r kind side policy <<< "${cases[i]}"
    policy=${policy:-baseline}
    work="$base/run-$SLURM_JOB_ID-$kind-$side-$policy"
    mkdir "$work"
    (
        cd "$work"
        mkdir -p tmp/klayout tmp/cache
        # This Yosys/ABC pair can stall after mapping with a long TMPDIR.
        # See the wave2 short-path positive control; keep tool scratch short.
        taskset -c "${masks[i]}" "$pinned" exec --cleanenv --bind /public/home/yuzelu \
            --pwd "$work" --env "KLAYOUT_HOME=$work/tmp/klayout,XDG_CACHE_HOME=$work/tmp/cache,OMP_NUM_THREADS=$threads,OPENBLAS_NUM_THREADS=1" "$image" \
            bash -c 'set -e; source /OpenROAD-flow-scripts/env.sh; unset TMPDIR; exec python3 -B "$@"' \
            bash "$base/physical_candidate.py" "$kind" "$side" "$threads" "$policy"
    ) >"$work/job.log" 2>&1 &
    pids+=("$!")
done
failed=0
for i in "${!pids[@]}"; do
    if wait "${pids[i]}"; then
        printf '%s PASS_PIPELINE\n' "${cases[i]}"
    else
        printf '%s FAILED\n' "${cases[i]}"
        failed=1
    fi
done
exit "$failed"
