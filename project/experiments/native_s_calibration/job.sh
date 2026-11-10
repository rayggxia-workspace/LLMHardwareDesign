#!/usr/bin/env bash
#SBATCH --job-name=yzl-native-s
#SBATCH --partition=c96
#SBATCH --nodes=1
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=12
#SBATCH --time=01:00:00
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
sha256sum -c source.sha256 > source-check.log
scontrol show job "$SLURM_JOB_ID" > allocation.txt
SIF=/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif
RUN=/public/software/singularity-ce-4.3.4/bin/singularity
SC=/public/home/yuzelu/opt/systemc-3.0.2-issue219
ENTRY=source/project/experiments/native_s_calibration
sha256sum "$SIF" "$RUN" > tools.sha256
"$RUN" exec --cleanenv --bind /public/home/yuzelu "$SIF" g++ --version > tools.txt
"$RUN" exec --cleanenv --bind /public/home/yuzelu "$SIF" python3 -B "$ENTRY/prepare.py" generated
"$RUN" exec --cleanenv --bind /public/home/yuzelu "$SIF" g++ -std=c++17 -O2 -Wall -Wextra -Werror generated/candidate/model.cpp -Igenerated/candidate -I"$SC/include" -L"$SC/lib" -Wl,-rpath,"$SC/lib" -lsystemc -o candidate.exe > build.log 2>&1
srun --exact -n8 -c12 --cpu-bind=cores --output=rank-%t.log bash -c 'exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env SLURM_PROCID="$SLURM_PROCID" --env SLURM_JOB_ID="$SLURM_JOB_ID" /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif python3 -B source/project/experiments/native_s_calibration/driver.py'
