#!/bin/bash
#SBATCH -J yzl-289-Cmargin
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n6
#SBATCH -c8
#SBATCH --time=02:30:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-margin-actual-%j.log
set -euo pipefail
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
sing=/public/software/singularity-ce-4.3.4/bin/singularity
plans=$r/diagnostics/C-actual-seven-size-v4/selectedplans
(cd "$plans"; sha256sum -c selection.sha256) > /dev/null
count=$(python3 -c 'import json,sys; n=json.load(open(sys.argv[1]))["selected_count"]; assert 1<=n<=6; print(n)' "$plans/selection.json")
pids=()
for ((case_id=0;case_id<count;case_id++));do
 srun --exclusive -N1 -n1 -c8 "$sing" exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 "$image" bash "$r/run-c-margin-actual-v1.sh" "$case_id" > "$r/c-margin-actual-${SLURM_JOB_ID}-${case_id}.log" 2>&1 &
 pids+=("$!")
done
rc=0;for p in "${pids[@]}";do wait "$p" || rc=1;done;exit "$rc"
