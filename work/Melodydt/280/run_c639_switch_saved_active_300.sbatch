#!/usr/bin/env bash
#SBATCH --job-name=mdt-280swact2
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:10:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
if [[ ${1:-} == inside ]]; then
    bundle=$2
else
    bundle=${SLURM_SUBMIT_DIR:?}
fi
cd "$bundle"
if [[ ${1:-} != inside ]]; then
    sha256sum -c bundle.sha256
    exec srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
      /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind "$base" \
      "$base/opt/eda/containers/orfs-current-repacked.sif" bash "$bundle/run_c639_switch_saved_active_300.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
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
ref=$runs/c639-g32-gate-01/c639-g32-116937
routed=$runs/c639-switch-power-300-02/result-117841
physical=$routed/flow/results/nangate45/mdt_c639_switch/base
capture=$runs/c639-switch-active-300-01/result-117854
replay=$capture/replay-117854
scope=TOP/test_native_decode638_product_replay/controller/cohort/transport
(cd "$routed" && sha256sum --quiet -c results.sha256)
sha256sum --quiet -c "$capture/reused-model.sha256"
sha256sum "$routed"/{physical.sha256,results.sha256} "$replay"/DDR-*/switch-active.fst \
    "$replay"/replay-{0,1}.log "$capture/reused-model.sha256" > "$out/inputs.sha256"
extractor=$runs/c639-g32-power-03/power-116943/fst_scope_vcd
python3 - "$ref/replay-116937" "$replay" <<'PY'
from pathlib import Path
import sys
original, replay = map(Path, sys.argv[1:])
for mode in range(2):
    case = f"DDR-{mode}"
    for name in ("transactions.tsv", "write-transactions.tsv", "activation-transactions.tsv"):
        expected = original / case / name
        path = replay / case / name
        if not path.exists() or path.stat().st_size == 0:
            with expected.open() as stream:
                first_row = next(stream).split()
            last_ps = next(int(line.split()[2]) for line in (replay / f"replay-{mode}.log").open()
                           if line.startswith("SWITCH_ACTIVE "))
            if int(first_row[1]) <= last_ps // 10000:
                raise ValueError(f"capture omitted an expected DDR event: {case}/{name}")
            continue
        with expected.open("rb") as reference, path.open("rb") as sampled:
            for block in iter(lambda: sampled.read(1024 * 1024), b""):
                if block != reference.read(len(block)):
                    raise ValueError(f"switch capture changed DDR prefix: {case}/{name}")
PY
for mode in 0 1; do
    item=$out/mode-$mode
    mkdir "$item"
    wave=$replay/DDR-$mode/switch-active.fst
    read -r first last accepts < <(awk '/^SWITCH_ACTIVE /{print $2,$3,$4}' "$replay/replay-$mode.log")
    [[ $((last-first)) == 81920000 && $accepts -ge 2 ]]
    printf '%s\n' "$accepts" > "$item/handshake-cycles.txt"
    "$extractor" "$wave" "$item/raw.vcd" "$scope" > "$item/extract.log"
    python3 -B - "$bundle" "$physical/6_final.v" "$item" "$scope" "$first" "$last" <<'PY'
from pathlib import Path
import sys
bundle, netlist, item = map(Path, sys.argv[1:4])
scope, first, last = sys.argv[4:]
sys.path.insert(0, str(bundle))
from extract_c639_m_ports import extract
extract(netlist, item / "raw.vcd", item / "ports.vcd", scope, int(first), int(last), 100, 762)
PY
    python3 -B "$bundle/gate_power_300.py" "$item/ports.vcd" "$physical" dut "$item/power" \
        10000 0 81920000 --cores "$cores" --reference-annotations 762
done
python3 - "$out" "$routed/summary.json" <<'PY'
import json
from pathlib import Path
import sys
out, idle = map(Path, sys.argv[1:])
idle_data = json.loads(idle.read_text())["windows"]
rows = []
for mode in range(2):
    case = out / f"mode-{mode}"
    facts = json.loads((case / "power/receipt.json").read_text())
    baseline = idle_data[f"mode-{mode}-gate-up"]
    rows.append({"mode": mode, "handshake_cycles": int((case / "handshake-cycles.txt").read_text()),
                 "power_w": facts["power_w"], "energy_nj": facts["energy_nj"],
                 "idle_reference_energy_nj": baseline["energy_nj"],
                 "active_minus_idle_reference_nj": facts["energy_nj"] - baseline["energy_nj"]})
(out / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
PY
cd "$out"
sha256sum summary.json inputs.sha256 "$capture/reused-model.sha256" "$replay"/replay-{0,1}.log \
    mode-*/{handshake-cycles.txt,power/receipt.json,power/power.log} > results.sha256
sha256sum -c results.sha256
echo C639_SWITCH_ACTIVE_300_PASS
