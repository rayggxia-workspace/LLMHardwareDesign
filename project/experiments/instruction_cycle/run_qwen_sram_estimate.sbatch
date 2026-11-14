#!/usr/bin/env bash
#SBATCH --job-name=zny-qwenest
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:10:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
sha256sum -c source.sha256
root=/public/home/yuzelu/project-circuit
program=$root/issue234-native-fixed-skip-request-H2gY5uiN/request-runtime-archived
trace=$root/issue260-native-kv-window-jL6neTvA/run-107947/page-timing.jsonl
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
printf '%s  %s\n' \
    74078b0b40fdeb73aeae71e3091db3e6a25fc5f27bc03c9981214bfef92b39ef "$program/proof.sha256" \
    422e89d190c43ac567b6e47898ffc38b4f96e4943339b6d177c46a2741e7ece8 "$trace" \
    49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a "$image" > inputs.sha256
sha256sum -c inputs.sha256
srun --exact -n1 -c1 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec \
    --cleanenv --bind /public/home/yuzelu "$image" bash -s -- "$program" "$trace" <<'RUN'
set -euo pipefail
export LC_ALL=C PYTHONDONTWRITEBYTECODE=1
python3 --version > python-version.txt
start=$SECONDS
python3 -B estimate_qwen_sram.py predict "$1" "$2" --through-step 127 > prediction.json
echo "$((SECONDS-start))" > prediction.wall-seconds
RUN
sha256sum source.sha256 inputs.sha256 python-version.txt prediction.json prediction.wall-seconds > output.sha256
sha256sum -c output.sha256
