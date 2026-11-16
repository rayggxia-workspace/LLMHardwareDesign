#!/usr/bin/env bash
#SBATCH --job-name=mdt-280pmfix300
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
      "$base/opt/eda/containers/orfs-current-repacked.sif" bash "$bundle/run_c639_pm_saved_power_300.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
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
old=$runs/c639-pm-power-300-03/result-117751
physical=$old/flow/results/nangate45/mdt_pm_store/base
original=$base/project-circuit/issue234-native-pm-stream-20261112-01/run-103489
sha256sum --quiet -c "$old/physical.sha256"
sha256sum --quiet -c "$original/proof.sha256"
cmp "$original/trace/transactions.tsv" "$old/ddr-active/transactions.tsv"
grep -Fx 'PASS native DDR-to-LC PM, six real DDR callbacks and 22 checked PM write ACKs' "$old/active.log"
first=$(awk '/^POWER_START_PS /{print $2}' "$old/active.log")
last=$(awk '/^POWER_END_PS /{print $2}' "$old/active.log")
sha256sum "$old"/{physical.sha256,active.log,idle.log,active.vcd,idle.vcd,ddr-active/transactions.tsv} \
  "$original/proof.sha256" > "$out/inputs.sha256"
python3 -B - "$bundle" "$old" "$out" "$first" "$last" "$physical" <<'PY'
import json
from pathlib import Path
import sys

bundle, source, output = map(Path, sys.argv[1:4])
first, last = map(int, sys.argv[4:6])
physical = Path(sys.argv[6])
sys.path.insert(0, str(bundle))
from gate_power_300 import analyze

top = ("test_native_pm_image_stream",)
scope = top + ("store",)
# These port/bench counters establish quiescence for the saved idle prefix.
idle_fields = {top: {"reset", "launch_valid", "rd_valid", "pm_ack_valid", "requests", "callbacks", "writes"},
               scope: {"cfg_valid", "pm_valid", "boot_busy"}}

def inspect(path, audit_idle):
    stack, registers, monitored = [], {}, {}
    initial, idle = {}, {}
    time = 0
    last_time = 0
    with path.open() as stream:
        for line in stream:
            fields = line.split()
            if not fields:
                continue
            if fields[0] == "$scope":
                stack.append(fields[2])
            elif fields[0] == "$upscope":
                stack.pop()
            elif fields[0] == "$var":
                site = tuple(stack)
                if site[:len(scope)] == scope:
                    registers[fields[3]] = (site, fields[4])
                if fields[4] in idle_fields.get(site, ()):
                    monitored[fields[3]] = fields[4]
            elif fields[0] == "$enddefinitions":
                break
        if not registers or set(monitored.values()) != set.union(*idle_fields.values()):
            raise ValueError(f"PM VCD missing scope or quiescence signals: {path}")
        for line in stream:
            if line.startswith("#"):
                time = int(line[1:])
                last_time = time
                if audit_idle and time == first and (
                    set(idle) != set(monitored) or any(set(value) != {"0"} for value in idle.values())
                ):
                    raise ValueError(f"idle PM initial counter or port state is nonzero: {idle}")
                if time > last:
                    break
                continue
            if not line.strip() or line.startswith("$"):
                continue
            if line[0] in "bB":
                value, ident = line.split()
                value = value[1:].lower()
            else:
                value, ident = line[0], line[1:].strip()
            if time < first and ident in registers:
                initial[ident] = value
            if audit_idle and ident in monitored:
                idle[ident] = value
                if first <= time <= last and set(value) != {"0"}:
                    raise ValueError(f"idle PM {monitored[ident]} active at {time}: {value}")
        if last_time < last or set(initial) != set(registers):
            raise ValueError(f"PM VCD prefix incomplete: {path}, through {last_time}")
        if audit_idle and (set(idle) != set(monitored) or any(set(value) != {"0"} for value in idle.values())):
            raise ValueError(f"idle PM final counter or port state is nonzero: {idle}")
        return registers, initial, last_time

a, qa, _ = inspect(source / "active.vcd", False)
i, qi, stop = inspect(source / "idle.vcd", True)
if a != i or qa != qi or stop <= last:
    raise ValueError("PM active and idle state/scope differ before the shared start")
summary = {"clock_hz": 300000000, "source_capture_period_ps": 10000,
           "source_window": [first, last], "matching_pm_signal_ids_before_window": len(a),
           "idle_slice_quiescent": True, "active_ddr_callbacks": 6, "active_pm_writes": 22}
results = {label: analyze(source / f"{label}.vcd", physical, "/".join(scope), output / label,
                          10000, first, last, 2, escape=True, clip=True) for label in ("active", "idle")}
a, i = results["active"], results["idle"]
if a["timing"]["window_ps"] != i["timing"]["window_ps"] or a["annotated"] != i["annotated"]:
    raise ValueError("PM power windows differ in time or annotation")
summary.update({"window_ps": a["timing"]["window_ps"], "active_power_w": a["power_w"],
                "idle_power_w": i["power_w"], "annotated": a["annotated"], "unannotated": a["unannotated"],
                "active_energy_nj": a["energy_nj"], "idle_energy_nj": i["energy_nj"],
                "incremental_nj": a["energy_nj"] - i["energy_nj"],
                "incremental_nj_per_write": (a["energy_nj"] - i["energy_nj"]) / 22})
(output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
PY
cd "$out"
sha256sum summary.json inputs.sha256 openroad.sha256 {active,idle}/{receipt.json,power.log} > results.sha256
sha256sum -c results.sha256
echo PM_PAIRED_GATE_POWER_300_PASS
