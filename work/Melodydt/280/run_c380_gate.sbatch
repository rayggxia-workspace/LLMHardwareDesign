#!/usr/bin/env bash
#SBATCH --job-name=mdt-280g380
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:25:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
bundle=$PWD
root=/public/home/yuzelu
runs=$root/Melodydt/runs
rtl=$runs/issue-280/gate-c380-01/c380-116817
native=$runs/issue-274/pr272-native-01/replay-115330
work=$bundle/c380-gate-$SLURM_JOB_ID
fixture=project/experiments/block_local_native
project=$root/project-circuit/LLMHardwareDesign
phys=$project/issue-200-compact-local-s/run08-base0/results/0/flow/results/nangate45/local_s_base/base
calibration=$project/issue-234-systemc-benchmark/s-activity-002
e_cells=$root/project-circuit/issue234-rope-to-qk-rtl-20261112-01/source/cells.sv

sha256sum -c bundle.sha256
(cd "$rtl" && sha256sum -c activity-source.sha256 && sha256sum --quiet -c activity-results.sha256)
(cd "$native" && sha256sum --quiet -c proof.sha256)
cmp "$calibration/cells.v" "$e_cells"
mkdir "$work"
cp -a "$rtl"/{source,algo1,source.tar,algo1.tar,upstream.sha256,source.sha256,softmax-source.sha256} "$work/"
cd "$work"
sha256sum -c upstream.sha256
for manifest in source.sha256 softmax-source.sha256; do
    grep -v 'run_native_attention_core_scope.sh\|test_native_attention_core_scope.sv' "$manifest" | sha256sum -c -
done
printf '%s  %s\n' \
    add5e99b97b471d35ef6c1eb3161821968172a96af4feb130fd4ca45217254fc "$phys/6_final.v" \
    1871109017b197e12c03beb0a1f2a1bd9f0387898858a831535cf300744fe10e "$calibration/bank-functional.v" \
    62f202ce18b251e751f4c9bfda125e7eef1ce45d96d74d5e3d5c81a06bf4bdfe "$e_cells" > gate-inputs.sha256
sha256sum -c gate-inputs.sha256
cp "$phys/6_final.v" "source/$fixture/local_s_base.v"
cp "$calibration/bank-functional.v" "source/$fixture/bank-functional.v"
cat > "source/$fixture/c380_gate_lint.vlt" <<'VLT'
`verilator_config
lint_off -rule TIMESCALEMOD -file "*/local_s_base.v"
lint_off -rule UNUSEDSIGNAL -file "*/local_s_base.v"
lint_off -rule UNDRIVEN -file "*/local_s_base.v"
lint_off -rule PINMISSING -file "*/local_s_base.v"
lint_off -rule DECLFILENAME -file "*/bank-functional.v"
lint_off -rule BLKSEQ -file "*/bank-functional.v"
lint_off -rule UNUSEDPARAM -file "*/bank-functional.v"
VLT
python3 -B - "source/$fixture/run_native_attention_core_scope.sh" <<'PY'
from pathlib import Path
import sys

runner = Path(sys.argv[1])
text = runner.read_text()
original = '"$S"/{local_s_base,block_feed_s16k_sram}.sv "$bank"'
routed = '"$S/block_feed_s16k_sram.sv" "$EXP"/{c380_gate_lint.vlt,local_s_base.v,bank-functional.v}'
if text.count(original) != 1:
    raise ValueError("ambiguous C380 RTL compile inputs")
runner.write_text(text.replace(original, routed))
PY
bash -n "source/$fixture/run_native_attention_core_scope.sh"
sha256sum source/"$fixture"/{run_native_attention_core_scope.sh,test_native_attention_core_scope.sv,c380_activity_driver.cpp,local_s_base.v,bank-functional.v,c380_gate_lint.vlt} > gate-source.sha256
export SELECT_V_BEAT=1 DDR_RESPONSE_QUEUE=1 OVERLAP_REFILL=1 HALF_TILE=1 OVERLAP_DOT=1
export SLURM_SUBMIT_DIR="$work"
bash "$work/source/$fixture/run_native_attention_core_scope.sh"

out=$work/replay-$SLURM_JOB_ID
for name in descriptors.bin expected.hex key.bin local.hex mother.hex resident.hex value.bin witness.json; do
    cmp "$native/generated/$name" "$out/generated/$name"
done
for mode in 0 1; do
    baseline=$native/mode-$mode
    traced=$rtl/replay-116817/mode-$mode
    current=$out/mode-$mode
    cmp "$baseline/readback.hex" "$current/readback.hex"
    cmp "$baseline/transactions.tsv" "$current/transactions.tsv"
    diff <(grep -E '^(PASS typed AttentionCore|S overlap cycles=|DDR bridge peak outstanding=)' "$baseline/run.log") \
         <(grep -E '^(PASS typed AttentionCore|S overlap cycles=|DDR bridge peak outstanding=)' "$current/run.log")
    cmp <(grep '^ACTIVITY_WINDOW ' "$traced/run.log") <(grep '^ACTIVITY_WINDOW ' "$current/run.log")
    grep -E '^(ACTIVITY_WINDOW|PASS typed AttentionCore|S overlap cycles=|DDR bridge peak outstanding=)' "$current/run.log"
    test -s "$current/attention.fst"
done
sha256sum gate-inputs.sha256 gate-source.sha256 "$out/proof.sha256" \
    "$out"/mode-*/{attention.fst,run.log,readback.hex,transactions.tsv} > gate-results.sha256
sha256sum -c gate-results.sha256
printf '%s\n' 'C380_ROUTED_LEAF_REPLAY_PASS'
