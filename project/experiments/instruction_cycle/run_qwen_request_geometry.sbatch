#!/usr/bin/env bash
#SBATCH --job-name=zny-qwengeom
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:15:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
sha256sum -c source.sha256
root=/public/home/yuzelu/project-circuit
program=$root/issue234-native-fixed-skip-request-H2gY5uiN/request-runtime-archived
archive=$root/issue260-native-two-dma-sRx1azw1
dependencies=$root/issue260-tlm-joint-9BiJdfEg
config=$root/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini
python=/public/home/yuzelu/Melodydt/runs/issue-265/reference-env-20261113-01/venv/bin/python
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
printf '%s  %s\n' \
    49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a "$image" \
    748ba1a2e06c26f4a71f27a9a98060ecf00432376ad417deae1ab92afdcb0766 "$config" > tools.sha256
sha256sum -c tools.sha256
srun --exact -n1 -c1 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec \
    --cleanenv --bind /public/home/yuzelu "$image" "$python" --version > python-version.txt
srun --exact -n1 -c1 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec \
    --cleanenv --bind /public/home/yuzelu "$image" "$python" -B qwen_request_geometry.py \
    "$program" "$archive" "$dependencies" > geometry.json
sha256sum geometry.json source.sha256 tools.sha256 python-version.txt > output.sha256
sha256sum -c output.sha256
