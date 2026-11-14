#!/usr/bin/env bash
#SBATCH --job-name=zny-qwenmodel
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:10:00
#SBATCH --output=slurm-%j.out
set -euo pipefail

sha256sum -c source.sha256
shared=/public/home/yuzelu/project-circuit
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
archive=$shared/issue260-decode638-live-product-next-rms-u8Z2olTH/replay-105530
embedding=$shared/LLMHardwareDesign/issue-234-systemc-benchmark/native-model-constants-mC0bSR2w/image/0000.s32le
prefix=$(realpath "${1:?verified prompt prediction directory required}")
shift
(
    cd "$prefix"
    sha256sum -c prediction.sha256
)
sha256sum "$image" "$archive/proof.sha256" "$prefix"/prediction-{0,1}.json > inputs.sha256
srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
    --bind /public/home/yuzelu "$image" bash -s -- "$archive" "$prefix" "$embedding" "$@" <<'RUN'
set -euo pipefail
export LC_ALL=C
archive=$1
prefix=$2
embedding=$3
shift 3
python3 --version > python-version.txt

python3 -B qwen_native_control.py "$archive" --compare --read-traces "$@" > control-comparison.json &
control_pid=$!
for mode in 0 1; do
    python3 -B qwen_prompt_rms.py predict "$archive" "$prefix/prediction-$mode.json" "$embedding" \
        > "rms-prediction-$mode.json"
done
sha256sum rms-prediction-{0,1}.json > rms-prediction.sha256
for mode in 0 1; do
    python3 -B qwen_prompt_rms.py compare "$archive" "rms-prediction-$mode.json" \
        > "rms-comparison-$mode.json"
done
wait "$control_pid"
sha256sum -c rms-prediction.sha256
sha256sum control-comparison.json rms-prediction-?.json rms-comparison-?.json \
    rms-prediction.sha256 inputs.sha256 source.sha256 python-version.txt > output.sha256
RUN
