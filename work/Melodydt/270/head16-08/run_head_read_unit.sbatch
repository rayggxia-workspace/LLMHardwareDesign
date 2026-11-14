#!/bin/bash
#SBATCH --job-name=zny-head-rd-u
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:08:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
work="$SLURM_SUBMIT_DIR/unit-$SLURM_JOB_ID"
mkdir "$work"
srun --exact -n1 -c"$SLURM_CPUS_PER_TASK" --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec \
 --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -s -- "$work" "$SLURM_CPUS_PER_TASK" <<'RUN'
set -euo pipefail
work=$1
cores=$2
source="$PWD/run-114150/source/project"
candidate="$work/source"
mkdir "$candidate"
(cd "$source/.." && tar -cf - project/rtl/block_local_native/{s128_vocabulary_retire,s128_vocabulary_tile_consumer,native_vocabulary_product_terminal}.sv project/experiments/block_local_native/test_s128_vocabulary_retire.sv) | tar -xf - -C "$candidate"
python3 -B prepare_head_read.py "$candidate"
bank=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
vlt=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
exp=experiments/block_local_native
rtl=rtl/block_local_native
sram=rtl/s_sram
cd "$work"
python3 -B - <<'PY'
from pathlib import Path
maxima={13, 14, 2049, 151935}
with Path("vocab.hex").open("w") as f:
    for index in range(0, 151936, 4):
        f.write("".join(f"{(14313851 if n in maxima else -n-1) & 0xffffffff:08x}" 
                        for n in range(index+3, index-1, -1)) + "\n")
PY
"$vlt" --version > tool.txt
sha256sum "$vlt" "$bank" vocab.hex "$candidate/project/$rtl/s128_vocabulary_retire.sv" \
 "$candidate/project/$exp/test_s128_vocabulary_retire.sv" "$source/$rtl/s32_token_argmax.sv" \
 "$source/$sram/"{local_s_base,block_feed_s16k_sram}.sv > inputs.sha256
"$vlt" --binary --timing --assert -Wno-fatal -j "$cores" --Mdir obj --top-module test_s128_vocabulary_retire \
 "$candidate/project/$exp/test_s128_vocabulary_retire.sv" "$candidate/project/$rtl/s128_vocabulary_retire.sv" \
 "$source/$rtl/s32_token_argmax.sv" "$source/$sram/"{local_s_base,block_feed_s16k_sram}.sv "$bank" > build.log 2>&1
./obj/Vtest_s128_vocabulary_retire | tee replay.log
grep -F 'mismatched read tag fenced' replay.log
sha256sum inputs.sha256 tool.txt build.log replay.log > output.sha256
sha256sum -c output.sha256
RUN
