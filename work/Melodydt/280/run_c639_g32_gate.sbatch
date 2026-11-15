#!/usr/bin/env bash
#SBATCH --job-name=mdt-280g639
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=01:15:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
base=/public/home/yuzelu
project=$base/project-circuit
bundle=$PWD
archive=$base/Melodydt/runs/issue-280/gate-c639-01/c639-116856
sealed=$archive/replay-116856
work=$bundle/c639-g32-$SLURM_JOB_ID
fixture=project/experiments/block_local_native
physical=$project/issue250-p-final-native-diode-gate-GlrL0V
source_w8=project/rtl/w8a16_v1
sha256sum -c bundle.sha256
sha256sum -c "$archive/activity-source.sha256"
(cd "$sealed" && sha256sum --quiet -c proof.sha256)
cmp "$physical/source-tracked/$source_w8/g_s32.sv" "$archive/source/$source_w8/g_s32.sv"
cmp "$physical/source-tracked/$source_w8/g_s128_frontend.sv" "$archive/source/$source_w8/g_s128_frontend.sv"
cmp "$physical/cells.v" "$project/issue234-rope-to-qk-rtl-20261112-01/source/cells.sv"
mkdir "$work"
cp -a "$archive/"{source,source.tar,activity-0.txt,activity-1.txt} "$work/"
cd "$work"
printf '%s  %s\n' 93134a119f0950a684e297e93add809985579553a365feb667aae67e6ce46764 "$physical/g-final.v" > physical.sha256
sha256sum -c physical.sha256
cp "$physical/g-final.v" "source/$source_w8/g_s32.v"
for name in m_native_leaf_s32 m_native_s32; do
    status=0
    diff -u "$physical/source-tracked/$source_w8/$name.sv" "$archive/source/$source_w8/$name.sv" > "$name.diff" || status=$?
    if ((status > 1)); then exit "$status"; fi
done
cat > "source/$fixture/c639_g32_lint.vlt" <<'VLT'
`verilator_config
lint_off -rule TIMESCALEMOD -file "*/g_s32.v"
lint_off -rule UNUSEDSIGNAL -file "*/g_s32.v"
lint_off -rule UNDRIVEN -file "*/g_s32.v"
lint_off -rule PINMISSING -file "*/g_s32.v"
VLT
runner=$work/source/$fixture/run_decode638_q_tile_replay.sh
python3 -B - "$runner" <<'PY'
from pathlib import Path
import sys

runner = Path(sys.argv[1])
source = runner.read_text()
original = ',scale_group_s32,g_s32,g_s128_frontend,e_s32_native}.sv'
replacement = ',scale_group_s32,g_s128_frontend,e_s32_native}.sv "$W/g_s32.v" "$EXP/c639_g32_lint.vlt"'
if source.count(original) != 1:
    raise ValueError("ambiguous C639 G32 source location")
runner.write_text(source.replace(original, replacement))
PY
bash -n "$runner"
sha256sum "$runner" "source/$fixture/"{c639_activity_driver.cpp,c639_g32_lint.vlt} \
    "source/$source_w8/"{g_s32.v,g_s32.sv,g_s128_frontend.sv} activity-*.txt > gate-source.sha256
srun --exact -N1 -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind "$base" \
    --env "SLURM_JOB_ID=$SLURM_JOB_ID,SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK,FORCE_SECOND_FFN_REARM=1" \
    "$base/opt/eda/containers/orfs-current-repacked.sif" bash "$runner" "$work" \
    "$project/issue260-token-decode638-live-qkv-xWSJhdWQ/linked-103952" history-final-product-ffn-repeat 636 2
out=$work/replay-$SLURM_JOB_ID
(cd "$out" && sha256sum --quiet -c proof.sha256)
for mode in 0 1; do
    diff <(grep -E '^(PASS |C639_ACTIVITY )' "$sealed/replay-$mode.log") \
         <(grep -E '^(PASS |C639_ACTIVITY )' "$out/replay-$mode.log")
    for item in transactions.tsv write-transactions.tsv activation-transactions.tsv committed-kv.bin; do
        cmp "$sealed/DDR-$mode/$item" "$out/DDR-$mode/$item"
    done
    grep '^C639_ACTIVITY ' "$out/replay-$mode.log"
    for phase in gate-up down; do test -s "$out/DDR-$mode/ffn-$phase.fst"; done
done
sha256sum gate-source.sha256 physical.sha256 m_native*.diff "$out/proof.sha256" "$out"/DDR-*/ffn-*.fst > gate-results.sha256
sha256sum -c gate-results.sha256
printf '%s\n' 'C639_G32_ROUTED_REPLAY_PASS'
