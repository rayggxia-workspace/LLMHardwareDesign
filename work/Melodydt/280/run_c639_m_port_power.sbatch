#!/usr/bin/env bash
#SBATCH --job-name=mdt-280mpwr
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=01:30:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
bundle=$SLURM_SUBMIT_DIR
cd "$bundle"
if [[ ${1:-} != inside ]]; then
    sha256sum -c bundle.sha256
    exec srun --exact -N1 -n1 -c "$SLURM_CPUS_PER_TASK" \
        /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind "$base" \
        --env "SLURM_SUBMIT_DIR=$bundle" "$base/opt/eda/containers/orfs-current-repacked.sif" \
        bash "$bundle/run_c639_m_port_power.sbatch" inside "$SLURM_JOB_ID"
fi
source /OpenROAD-flow-scripts/env.sh
runs=$base/Melodydt/runs/issue-280
route=$runs/c639-m-physical-03/route-116976
physical=$route/native/flow/results/nangate45/bv1_m_native_leaf_s32/base
main=$runs/c639-g32-gate-01/c639-g32-116937
replay=$main/replay-116937
prior=$runs/c639-g32-power-03/power-116943
extractor=$prior/fst_scope_vcd
scopes=$runs/gate-binding-01/bind-116893/fst_scope_table
audit=$runs/c639-m-wave-audit-01/wave-116958
lib=/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
out=$bundle/power-$2
mkdir "$out"
(cd "$route" && sha256sum -c route-results.sha256)
sha256sum -c "$audit/wave-inputs.sha256"
sha256sum "$physical"/6_final.{odb,v,sdc,spef} "$extractor" "$scopes" "$(command -v openroad)" "$lib" \
    "$audit/wave-inputs.sha256" "$main"/activity-{0,1}.txt > "$out/inputs.sha256"
openroad -version > "$out/openroad-version.txt"
python3 - "$physical/6_final.sdc" "$out/at-100mhz.sdc" <<'PY'
from pathlib import Path
import re
import sys

text = Path(sys.argv[1]).read_text()
ref, count = re.subn(r"(?m)^(create_clock -name core -period )3\.333[0-9]* ", r"\g<1>10.0000 ", text)
if count != 1:
    raise ValueError("unexpected original clock")
Path(sys.argv[2]).write_text(ref)
PY
run_power() {
    local phase_dir=$1 lane=$2 wave=$3 scope=$4 first=$5 last=$6
    local sample=$phase_dir/$lane
    mkdir "$sample"
    "$extractor" "$wave" "$sample/raw.vcd" "$scope" > "$sample/extract.log"
    python3 "$bundle/extract_c639_m_ports.py" "$physical/6_final.v" "$sample/raw.vcd" \
        "$sample/port.vcd" "$scope" "$first" "$last"
    rm "$sample/raw.vcd"
    cat > "$sample/power.tcl" <<TCL
read_liberty {$lib}
read_db {$physical/6_final.odb}
read_sdc {$out/at-100mhz.sdc}
read_spef {$physical/6_final.spef}
set_propagated_clock [all_clocks]
read_vcd -scope dut {$sample/port.vcd}
report_activity_annotation
report_power -digits 9
puts "MDT_C639_M_PORT_ACTIVITY_COMPLETE"
TCL
    openroad -no_init -threads 4 -exit "$sample/power.tcl" > "$sample/power.log" 2>&1
    grep -F 'MDT_C639_M_PORT_ACTIVITY_COMPLETE' "$sample/power.log"
    if grep -E '^(Error:|\[ERROR)' "$sample/power.log"; then return 1; fi
}
for mode in 0 1; do
    for phase in gate-up down; do
        phase_dir=$out/mode-$mode-$phase
        wave=$replay/DDR-$mode/ffn-$phase.fst
        mkdir "$phase_dir"
        read -r first last < <(awk -v phase="$phase" '$1 == phase {print $2, $3}' "$main/activity-$mode.txt")
        "$scopes" "$wave" | awk -F '\t' '$1=="var" && $2 ~ /\/M$/ && $3=="clk" {print $2}' > "$phase_dir/sites.txt"
        mapfile -t sites < "$phase_dir/sites.txt"
        [[ ${#sites[@]} == 3 ]]
        pids=()
        for scope in "${sites[@]}"; do
            case "$scope" in
                */p0/*) lane=P0 ;;
                */ps\[1\]/*) lane=P1 ;;
                */ps\[2\]/*) lane=P2 ;;
                *) printf 'unexpected scope %s\n' "$scope" >&2; exit 1 ;;
            esac
            (set -e; run_power "$phase_dir" "$lane" "$wave" "$scope" "$first" "$last") &
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
import re
import sys

out = Path(sys.argv[1])
rows = []
for log in sorted(out.glob("mode-*/*/power.log")):
    text = log.read_text()
    count, = re.findall(r"Annotated (\d+) pin activities\.", text)
    internal, switching, leakage, total = next(iter(re.findall(
        r"(?m)^Total\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)", text)))
    timing = json.loads(log.with_name("port.json").read_text())
    if int(count) != sum(timing["port_bits"].values()):
        raise ValueError(f"expected all M boundary pins to annotate, observed {count}: {log}")
    rows.append({"window": str(log.parent.relative_to(out)), "annotated_pin_count": int(count),
                 "internal_w": float(internal), "switching_w": float(switching), "leakage_w": float(leakage),
                 "total_w": float(total), "window_energy_nj": float(total) * timing["window_ps"] / 1000})
if len(rows) != 12:
    raise ValueError("expected 12 window/lane combinations")
(out / "power.json").write_text(json.dumps({"method": "C639 RTL port VCD and propagated internal activity",
    "clock_hz": 100000000, "scope": "pre-ECO exploratory routed M only", "rows": rows}, indent=2) + "\n")
PY
cd "$out"
sha256sum inputs.sha256 openroad-version.txt at-100mhz.sdc power.json mode-*/*/{port.vcd,port.json,power.tcl,power.log} > power-results.sha256
sha256sum -c power-results.sha256
printf '%s\n' MDT_C639_M_PORT_POWER_PASS
