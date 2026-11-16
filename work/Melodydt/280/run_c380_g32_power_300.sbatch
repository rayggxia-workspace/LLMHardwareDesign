#!/usr/bin/env bash
#SBATCH --job-name=mdt-280chip300
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=00:35:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
bundle=$SLURM_SUBMIT_DIR
cd "$bundle"
if [[ ${1:-} != inside ]]; then
    sha256sum -c bundle.sha256
    exec srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
      /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind "$base" \
      "$base/opt/eda/containers/orfs-current-repacked.sif" bash "$bundle/run_c380_g32_power_300.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
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
bank=$project/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib
c380=$runs/gate-c380-idle-04/power-116935
g32=$runs/c639-g32-power-03/power-116943
sha256sum -c "$c380/power-results.sha256" "$g32/power-results.sha256" > "$out/archive-check.log"
python3 -B - "$bundle" "$out" "$c380" "$g32" "$bank" "$cores" <<'PY'
import concurrent.futures
import json
from pathlib import Path
import sys

bundle, out, c380, g32, bank = map(Path, sys.argv[1:6])
sys.path.insert(0, str(bundle))
from gate_power_300 import analyze, sha

def run(case):
    label, source, inputs = case
    path = source / "openroad"
    wave = path / "normalized.vcd"
    receipt = json.loads((path / "receipt.json").read_text())
    physical = (source.parent / "physical-100mhz" / "6_final.odb").resolve().parent
    if sha(wave) != receipt["normalized_vcd_sha256"]:
        raise ValueError(f"wave checksum: {wave}")
    for ext in ("odb", "spef", "v"):
        original = source.parent / "physical-100mhz" / ("6_final." + ext)
        if sha(physical / original.name) != receipt["source_sha256"][str(original)]:
            raise ValueError(f"physical checksum: {original}")
    window = receipt["window"]["window_ps"]
    result = analyze(wave, physical, receipt["scope"], out / label / source.name,
                     10000, 0, window, 3, inputs, reference_annotations=receipt["annotation_count"])
    return label, source.name, result

cases = [("c380", c380 / name, (bank,)) for name in ("mode-0", "mode-1", "idle-0", "idle-1")]
cases += [("g32", g32 / f"mode-{mode}-{phase}", ()) for mode in (0, 1) for phase in ("gate-up", "down")]
with concurrent.futures.ThreadPoolExecutor(max_workers=int(sys.argv[6]) // 3) as pool:
    results = {(label, case): data for label, case, data in pool.map(run, cases)}
summary = {f"{label}/{case}": {key: value for key, value in data.items()
                               if key in {"timing", "annotated", "unannotated", "power_w", "energy_nj"}}
           for (label, case), data in results.items()}
for mode in (0, 1):
    summary[f"c380/mode-{mode}"]["matched_idle_energy_nj"] = results["c380", f"idle-{mode}"]["energy_nj"]
    summary[f"c380/mode-{mode}"]["incremental_energy_nj"] = (
        results["c380", f"mode-{mode}"]["energy_nj"] - results["c380", f"idle-{mode}"]["energy_nj"])
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
PY
cd "$out"
sha256sum summary.json archive-check.log openroad.sha256 */*/{receipt.json,power.log} > results.sha256
sha256sum -c results.sha256
echo C380_G32_POWER_300_PASS
