#!/usr/bin/env bash
#SBATCH --job-name=mdt-280pw380
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:15:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
bundle=${SLURM_SUBMIT_DIR:?}
cd "$bundle"
if [[ ${1:-} != container ]]; then
    sha256sum -c bundle.sha256
    exec srun --exact -N1 -n1 -c "$SLURM_CPUS_PER_TASK" \
      /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind "$base" \
      --env "SLURM_SUBMIT_DIR=$bundle" "$base/opt/eda/containers/orfs-current-repacked.sif" \
      bash "$bundle/run_c380_gate_power.sbatch" container "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
fi
source /OpenROAD-flow-scripts/env.sh
job=$2
cores=$3
out=$bundle/power-$job
runs=$base/Melodydt/runs/issue-280
gate=$runs/gate-c380-routed-02/c380-gate-116908
replay=$gate/replay-116908
fst=$base/opt/eda/verilator-5.042/share/verilator/include/gtkwave
calibration=$base/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/s-activity-002
scope=TOP/test_native_attention_core_scope/storage
mkdir "$out"
(cd "$gate" && sha256sum -c gate-results.sha256)
(cd "$replay" && sha256sum --quiet -c proof.sha256)

cat > "$out/fst_to_vcd.c" <<'C'
#include "fstapi.h"

int main(int argc, char **argv) {
    if (argc != 3) return 1;
    fstReaderContext *fst = fstReaderOpen(argv[1]);
    if (!fst) return 2;
    if (fstReaderGetTimescale(fst) != -12 ||
        fstReaderGetEndTime(fst) - fstReaderGetStartTime(fst) != 20480000) return 3;
    FILE *vcd = fopen(argv[2], "w");
    if (!vcd) return 4;
    if (!fstReaderProcessHier(fst, vcd)) return 5;
    fstReaderSetFacProcessMaskAll(fst);
    const int ok = fstReaderIterBlocks(fst, NULL, NULL, vcd);
    const int write_failed = ferror(vcd);
    fstReaderClose(fst);
    const int close_failed = fclose(vcd);
    return !ok || write_failed || close_failed;
}
C
gcc -std=gnu11 -O2 -D_GNU_SOURCE -I"$fst" -include "$fst/fst_config.h" \
    "$out/fst_to_vcd.c" "$fst"/{fstapi,fastlz,lz4}.c -lz -o "$out/fst_to_vcd"
sha256sum "$fst"/{fstapi.c,fstapi.h,fst_config.h,fastlz.c,lz4.c} > "$out/fst-reader.sha256"

python3 -B - "$calibration/base-read/power-idle/receipt.json" "$out" <<'PY'
import hashlib
import json
from pathlib import Path
import re
import sys

reference, out = map(Path, sys.argv[1:])
sources = json.loads(reference.read_text())["source_sha256"]
physical = out / "physical-100mhz"
physical.mkdir()
for suffix in ("v", "odb", "spef", "sdc"):
    original, = (Path(name) for name in sources if name.endswith("/6_final." + suffix))
    with original.open("rb") as stream:
        digest = hashlib.sha256()
        for part in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(part)
    if digest.hexdigest() != sources[str(original)]:
        raise ValueError(f"physical artifact does not match archived receipt: {original}")
    target = physical / original.name
    if suffix == "sdc":
        text = original.read_text()
        text, count = re.subn(r"(?m)^(create_clock -name core -period )3\.3333( \[get_ports \{clk\}\])$",
                              r"\g<1>10.0000\2", text)
        if count != 1 or len(re.findall(r"(?m)^create_clock\b", text)) != 1:
            raise ValueError("physical constraints did not contain expected single routed clock")
        target.write_text(text)
    else:
        target.symlink_to(original)
PY

lib=/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
bank=$base/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib
printf '%s  %s\n' \
    8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1 "$lib" \
    47f8de1c22d27beb51982c73ab745e1f3f2b5a7819e53bcb6da73980ce077189 "$bank" > "$out/liberty.sha256"
sha256sum -c "$out/liberty.sha256"
openroad -version > "$out/openroad-version.txt"
sha256sum "$(command -v openroad)" "$calibration/analyze_activity.py" > "$out/tools.sha256"

for mode in 0 1; do
    sample=$out/mode-$mode
    mkdir "$sample"
    "$out/fst_to_vcd" "$replay/mode-$mode/attention.fst" "$sample/raw.vcd"
    python3 -B - "$sample" "$replay/mode-$mode/run.log" "$scope" <<'PY'
import json
from pathlib import Path
import re
import sys

sample, log = map(Path, sys.argv[1:3])
scope = sys.argv[3].split("/")
text = log.read_text()
start, end = map(int, re.search(r"(?m)^ACTIVITY_WINDOW start_ps=(\d+) end_ps=(\d+) ", text).groups())
if "\nPASS typed AttentionCore " not in text or end - start != 20480000:
    raise ValueError("functional replay and window were not verified")
raw = sample / "raw.vcd"
with raw.open() as source, (sample / "gate.vcd").open("w") as dest:
    stack = []
    clk_id = None
    time = None
    clock_edges = []
    clock_value = None
    for line in source:
        fields = line.split()
        if fields[:1] == ["$timescale"]:
            while fields[-1] != "$end":
                fields.extend(next(source).split())
            if fields != ["$timescale", "1ps", "$end"]:
                raise ValueError(fields)
            line = " ".join(fields) + "\n"
        elif fields[:1] == ["$scope"]:
            stack.append(fields[2])
        elif fields[:1] == ["$upscope"]:
            stack.pop()
        elif fields[:1] == ["$var"]:
            if stack == scope and fields[4] == "clk":
                clk_id = fields[3]
            # GTKWave emits SystemVerilog logic declarations. OpenSTA accepts
            # the equivalent VCD wire declaration with the same ID and range.
            if fields[1] == "logic":
                fields[1] = "wire"
                line = " ".join(fields) + "\n"
        elif line.startswith("#"):
            time = int(line[1:])
        elif line[:1] in ("0", "1") and line[1:].strip() == clk_id and line[0] != clock_value:
            clock_edges.append(time)
            clock_value = line[0]
        dest.write(line)
if clk_id is None or clock_edges != list(range(start, end + 1, 5000)) or time != end:
    raise ValueError("C380 VCD did not have the expected 2048 clock periods and window bounds")
(sample / "functional.json").write_text(json.dumps({"timing": {"passed": True, "window_ps": end - start,
    "first_ps": start, "last_ps": end, "clock_period_ps": 10000, "clock_transitions": len(clock_edges) - 1}}, indent=2) + "\n")
PY
    python3 -B "$calibration/analyze_activity.py" "$out/physical-100mhz" "$lib" \
      "$sample/gate.vcd" "$sample/functional.json" "$sample/openroad" --scope "$scope" --cores "$cores" \
      --escape-sta-backslashes --extra-lib "$bank" --sample-label 'C380 routed local_s_base ordinary 128-bit port'
done
sha256sum "$out"/{fst_to_vcd.c,fst-reader.sha256,liberty.sha256,openroad-version.txt,tools.sha256} \
    "$out/physical-100mhz/6_final.sdc" "$out"/mode-*/{functional.json,openroad/receipt.json,openroad/power.log} > "$out/power-results.sha256"
sha256sum -c "$out/power-results.sha256"
printf '%s\n' 'C380_ROUTED_ACTIVE_POWER_PASS'
