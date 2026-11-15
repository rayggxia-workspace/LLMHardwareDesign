#!/usr/bin/env bash
#SBATCH --job-name=mdt-280c380
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:15:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
bundle=$PWD
prior=/public/home/yuzelu/Melodydt/runs/issue-274/pr272-native-01
archived=$prior/replay-115330
work=$bundle/c380-$SLURM_JOB_ID
fixture=project/experiments/block_local_native
sha256sum -c bundle.sha256
(cd "$archived" && sha256sum --quiet -c proof.sha256)
mkdir "$work"
cp -a "$prior"/{source,algo1,source.tar,algo1.tar,upstream.sha256,source.sha256,softmax-source.sha256} "$work/"
cd "$work"
sha256sum -c source.sha256
sha256sum -c softmax-source.sha256
cp "$bundle/c380_activity_driver.cpp" "source/$fixture/"
python3 -B - <<'PY'
from pathlib import Path
directory = Path("source/project/experiments/block_local_native")

def replace(name, old, new):
    path = directory / name
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError("ambiguous C380 activity instrumentation: " + old)
    path.write_text(text.replace(old, new))

replace("test_native_attention_core_scope.sv", "OVERLAP_DOT=1'b0);",
        "OVERLAP_DOT=1'b0)(output logic [31:0] sample_kv_callbacks);")
replace("test_native_attention_core_scope.sv", "    int unsigned kv_requests,kv_callbacks;",
        "    int unsigned kv_requests,kv_callbacks;\n    assign sample_kv_callbacks = kv_callbacks;")
replace("run_native_attention_core_scope.sh", "--binary --timing",
        "--cc --exe --build --trace-fst --trace-depth 4 --timing")
replace("run_native_attention_core_scope.sh", '"$PWD/$EXP/ddr_read_bridge.cpp" --Mdir',
        '"$PWD/$EXP/ddr_read_bridge.cpp" "$PWD/$EXP/c380_activity_driver.cpp" --Mdir')
PY
sha256sum source/"$fixture"/{c380_activity_driver.cpp,test_native_attention_core_scope.sv,run_native_attention_core_scope.sh} > activity-source.sha256
export SELECT_V_BEAT=1 DDR_RESPONSE_QUEUE=1 OVERLAP_REFILL=1 HALF_TILE=1 OVERLAP_DOT=1
export SLURM_SUBMIT_DIR="$work"
bash "$work/source/$fixture/run_native_attention_core_scope.sh"
out=$work/replay-$SLURM_JOB_ID
for mode in 0 1; do
    original=$archived/mode-$mode
    current=$out/mode-$mode
    cmp "$original/readback.hex" "$current/readback.hex"
    cmp "$original/transactions.tsv" "$current/transactions.tsv"
    diff <(grep -E '^(PASS typed AttentionCore|S overlap cycles=)' "$original/run.log") \
         <(grep -E '^(PASS typed AttentionCore|S overlap cycles=)' "$current/run.log")
    grep '^ACTIVITY_WINDOW ' "$current/run.log"
    test -s "$current/attention.fst"
done
for name in descriptors.bin expected.hex key.bin local.hex mother.hex resident.hex value.bin witness.json; do
    cmp "$archived/generated/$name" "$out/generated/$name"
done
sha256sum activity-source.sha256 "$out/proof.sha256" "$out"/mode-*/{attention.fst,run.log,readback.hex,transactions.tsv} > activity-results.sha256
sha256sum -c activity-results.sha256
