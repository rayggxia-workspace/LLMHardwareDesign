#!/usr/bin/env bash
#SBATCH --job-name=yzl-ucf-delivery
#SBATCH --partition=c64
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --output=pack-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
[[ $# -eq 8 ]]
delivery=$1
gate=$2
shift 2
pinned=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
runtime=("$pinned" exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" "$image")
candidates=(--candidate U "$1" "$2" --candidate C "$3" "$4" --candidate F "$5" "$6")
"${runtime[@]}" python3 -B package_accepted.py "$delivery" "$gate" "${candidates[@]}"
"${runtime[@]}" python3 -B package_sources.py "$delivery" --gate-stage "$PWD" "${candidates[@]}"
(
    cd "$delivery"
    sha256sum U16.tar.gz C16.tar.gz F16.tar.gz execution-source.tar.gz delivery.json \
        execution-source.sha256 gate/* > SHA256SUMS
)
printf '%s\n' "PASS sealed U16/C16/F16 delivery and execution sources"
