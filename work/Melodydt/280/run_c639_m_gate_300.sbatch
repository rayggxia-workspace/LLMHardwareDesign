#!/usr/bin/env bash
#SBATCH --job-name=mdt-280mgate
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=06:00:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
bundle=$SLURM_SUBMIT_DIR
cd "$bundle"
if [[ ${1:-} != inside ]]; then
    sha256sum -c bundle.sha256
    exec srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
      /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind "$base" \
      "$base/opt/eda/containers/orfs-current-repacked.sif" bash "$bundle/run_c639_m_gate_300.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
fi
source /OpenROAD-flow-scripts/env.sh
bundle=$2
runs=$base/Melodydt/runs/issue-280
project=$base/project-circuit/LLMHardwareDesign
out=$bundle/result-$3
cores=$4
mkdir "$out"
openroad -version > "$out/openroad-version.txt"
sha256sum "$(command -v openroad)" > "$out/openroad.sha256"
job=$3
frozen=$runs/c639-g32-gate-01/c639-g32-116937
prior=$frozen/replay-116937
route=$runs/c639-m-physical-03/route-116976
physical=$route/native/flow/results/nangate45/bv1_m_native_leaf_s32/base
fixture=project/experiments/block_local_native
rtl=project/rtl/w8a16_v1
driver=$fixture/run_decode638_q_tile_replay.sh
cells=$base/project-circuit/issue234-rope-to-qk-rtl-20261112-01/source/cells.sv
(cd "$frozen" && sha256sum --quiet -c gate-results.sha256)
(cd "$prior" && sha256sum --quiet -c proof.sha256)
(cd "$route" && sha256sum --quiet -c route-results.sha256)
cp -a "$frozen/"{source,source.tar,activity-0.txt,activity-1.txt} "$out/"
cp "$physical/6_final.v" "$out/source/$rtl/c639_m_routed.v"
cat > "$out/source/$fixture/c639_m_routed.vlt" <<'VLT'
`verilator_config
lint_off -rule DECLFILENAME -file "*/c639_m_routed.v"
lint_off -rule TIMESCALEMOD -file "*/c639_m_routed.v"
lint_off -rule UNUSEDSIGNAL -file "*/c639_m_routed.v"
lint_off -rule UNDRIVEN -file "*/c639_m_routed.v"
lint_off -rule PINMISSING -file "*/c639_m_routed.v"
VLT
python3 - "$out/source/$driver" "$physical/6_final.v" "$cells" <<'PY'
from pathlib import Path
import re
import sys

runner, netlist, cells = map(Path, sys.argv[1:])
candidate = set(re.findall(r"(?m)^\s+([A-Z][A-Z0-9_]*_X[0-9]+)\s+[^\n]+\(", netlist.read_text()))
models = set(re.findall(r"(?m)^module\s+(\w+)\s*\(", cells.read_text()))
if not candidate or candidate - models:
    raise ValueError(f"missing standard-cell simulation models: {candidate - models}")
source = runner.read_text()
before = '"$W"/{m_native_leaf_s32,m_native_s32,weight_records,m_group_s32,projection_context_s32,scale_group_s32,g_s128_frontend,e_s32_native}.sv'
after = '"$W"/{m_native_s32,weight_records,m_group_s32,projection_context_s32,scale_group_s32,g_s128_frontend,e_s32_native}.sv "$W/c639_m_routed.v" "$EXP/c639_m_routed.vlt"'
if source.count(before) != 1:
    raise ValueError("M source anchor mismatch")
runner.write_text(source.replace(before, after))
PY
sha256sum "$out/source/$driver" "$out/source/$rtl/c639_m_routed.v" "$out/source/$fixture/c639_m_routed.vlt" \
  "$out/source/$fixture/c639_activity_driver.cpp" "$cells" "$out"/activity-*.txt > "$out/inputs.sha256"
bash -n "$out/source/$driver"
export SLURM_JOB_ID=$job SLURM_CPUS_PER_TASK=$cores FORCE_SECOND_FFN_REARM=1
bash "$out/source/$driver" "$out" \
     "$base/project-circuit/issue260-token-decode638-live-qkv-xWSJhdWQ/linked-103952" \
     history-final-product-ffn-repeat 636 2 > "$out/runner.log" 2>&1
replay=$out/replay-$job
(cd "$replay" && sha256sum --quiet -c proof.sha256)
for mode in 0 1; do
    diff <(grep -E '^(PASS |C639_ACTIVITY )' "$prior/replay-$mode.log") \
         <(grep -E '^(PASS |C639_ACTIVITY )' "$replay/replay-$mode.log")
    for item in transactions.tsv write-transactions.tsv activation-transactions.tsv committed-kv.bin; do
        cmp "$prior/DDR-$mode/$item" "$replay/DDR-$mode/$item"
    done
done
echo C639_M_GATE_REPLAY_MATCH
extract=$runs/c639-g32-power-03/power-116943/fst_scope_vcd
scopes=$runs/gate-binding-01/bind-116893/fst_scope_table
sha256sum "$extract" "$scopes" >> "$out/inputs.sha256"

power_case() {
    local wave=$1 phase_dir=$2 lane=$3 scope=$4 first=$5 last=$6
    "$extract" "$wave" "$phase_dir/$lane.vcd" "$scope" > "$phase_dir/$lane.extract.log"
    python3 -B "$bundle/gate_power_300.py" "$phase_dir/$lane.vcd" "$physical" "$scope" \
        "$phase_dir/$lane" 10000 "$first" "$last" --cores 4 --escape
}
for mode in 0 1; do
    for phase in gate-up down; do
        wave=$replay/DDR-$mode/ffn-$phase.fst
        phase_dir=$out/mode-$mode-$phase
        mkdir "$phase_dir"
        read -r first last < <(awk -v phase="$phase" '$1 == phase {print $2, $3}' "$out/activity-$mode.txt")
        "$scopes" "$wave" | awk -F '\t' '$1=="var" && $2 ~ /\/M$/ && $3=="clk" {print $2}' > "$phase_dir/sites.txt"
        mapfile -t sites < "$phase_dir/sites.txt"
        [[ ${#sites[@]} == 3 ]]
        pids=()
        for scope in "${sites[@]}"; do
            case "$scope" in
                */p0/*) lane=P0 ;;
                */ps\[1\]/*) lane=P1 ;;
                */ps\[2\]/*) lane=P2 ;;
                *) echo "unexpected M scope $scope" >&2; exit 1 ;;
            esac
            (set -e; power_case "$wave" "$phase_dir" "$lane" "$scope" "$first" "$last") &
            pids+=("$!")
        done
        failed=0
        for pid in "${pids[@]}"; do if ! wait "$pid"; then failed=1; fi; done
        ((failed == 0))
    done
done
python3 - "$out" <<'PY'
import json
from pathlib import Path
import sys
out = Path(sys.argv[1])
rows = {}
for path in sorted(out.glob("mode-*/P*/receipt.json")):
    receipt = json.loads(path.read_text())
    if receipt["annotated"] <= 1330:
        raise ValueError(f"internal pins absent from {path}")
    rows[str(path.parent.relative_to(out))] = {
        key: value for key, value in receipt.items() if key in {"annotated", "unannotated", "power_w", "energy_nj", "timing"}
    }
if len(rows) != 12:
    raise ValueError("expected 12 gate power samples")
(out / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
PY
cd "$out"
sha256sum inputs.sha256 openroad.sha256 summary.json "replay-$job/proof.sha256" "replay-$job"/DDR-*/ffn-*.fst \
    mode-*/P*/{receipt.json,power.log} > results.sha256
sha256sum -c results.sha256
echo C639_M_ACTIVE_GATE_300_PASS
