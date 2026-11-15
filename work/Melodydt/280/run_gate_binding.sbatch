#!/usr/bin/env bash
#SBATCH --job-name=mdt-280bind
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:10:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
cd "${SLURM_SUBMIT_DIR:?}"
bundle=$PWD
if [[ ${1:-} != container ]]; then
    sha256sum -c bundle.sha256
    exec srun --exact -N1 -n1 -c 1 /public/software/singularity-ce-4.3.4/bin/singularity exec \
      --cleanenv --bind "$base" --env "SLURM_SUBMIT_DIR=$bundle" "$base/opt/eda/containers/orfs-current-repacked.sif" \
      bash "$bundle/run_gate_binding.sbatch" container "$SLURM_JOB_ID"
fi
out=$bundle/bind-$2
mkdir "$out"
fst=$base/opt/eda/verilator-5.042/share/verilator/include/gtkwave
gcc -std=gnu11 -O2 -D_GNU_SOURCE -I"$fst" -include "$fst/fst_config.h" \
    "$bundle/fst_scope_table.c" "$fst"/{fstapi,fastlz,lz4}.c -lz -o "$out/fst_scope_table"
sha256sum "$fst"/{fstapi.c,fstapi.h,fst_config.h,fastlz.c,lz4.c} > "$out/fst-reader.sha256"
runs=$base/Melodydt/runs
c380=$runs/issue-280/gate-c380-01/c380-116817/replay-116817
c639=$runs/issue-280/gate-c639-01/c639-116856/replay-116856
for mode in 0 1; do
    "$out/fst_scope_table" "$c380/mode-$mode/attention.fst" > "$out/c380-$mode.tsv"
    for wave in gate-up down; do
        "$out/fst_scope_table" "$c639/DDR-$mode/ffn-$wave.fst" > "$out/c639-$mode-$wave.tsv"
    done
done
python3 -B - "$out" "$runs" "$base" <<'PY'
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

out, runs, base = map(Path, sys.argv[1:])


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def table(path):
    data = defaultdict(dict)
    with path.open() as stream:
        tag, begin, end, unit = next(stream).rstrip("\n").split("\t")
        if tag != "time" or int(unit) != -12:
            raise ValueError(f"unexpected FST timescale: {path}")
        for line in stream:
            _, scope, label, width, handle = line.rstrip("\n").split("\t")
            name = label.split()[0]
            data[scope][name] = (int(width), int(handle))
    return (int(begin), int(end)), data


physical_receipt = (base / "project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark"
                    / "s-activity-002/base-read/power-idle/receipt.json")
archived = json.loads(physical_receipt.read_text())
verified_files = {}
for name, expected in archived["source_sha256"].items():
    path = Path(name)
    if digest(path) != expected:
        raise ValueError(f"archived physical input changed: {path}")
    verified_files[name] = expected
gate, = (Path(name) for name in verified_files if name.endswith("/6_final.v"))
rtl = runs / "issue-274/pr272-native-01/source/project/rtl/s_sram"
reference = physical_receipt.parents[2]
rtl_hashes = {}
for name in ("local_s_base.sv", "block_feed_s16k_sram.sv"):
    left, right = digest(rtl / name), digest(reference / name)
    if left != right:
        raise ValueError(f"C380 SRAM RTL differs from characterization: {name}")
    rtl_hashes[name] = left

widths = {"clk": 1, "reset": 1, "req_valid": 1, "req_write": 1, "req_addr": 10,
          "req_data": 128, "req_ready": 1, "rsp_valid": 1, "rsp_ready": 1, "rsp_data": 128}
text = gate.read_text()
if not re.search(r"(?m)^module\s+local_s_base\b", text):
    raise ValueError("expected routed local_s_base top")
ports = {
    name: {"direction": direction, "width": abs(int(msb) - int(lsb)) + 1 if msb else 1}
    for direction, msb, lsb, name in re.findall(
        r"(?m)^\s*(input|output)\s+(?:\[(\d+)\s*:\s*(\d+)\]\s*)?(\w+)\s*;", text)
    if name in widths
}
if {name: p["width"] for name, p in ports.items()} != widths:
    raise ValueError("routed SRAM ports failed name or width verification")
samples = {}
for path in sorted(out.glob("*.tsv")):
    (start, end), scopes = table(path)
    record = {"first_ps": start, "last_ps": end, "scopes": len(scopes),
              "signals": sum(map(len, scopes.values()))}
    if path.name.startswith("c380"):
        if end - start != 20480000:
            raise ValueError("C380 waveform duration differs from capture")
        matches = [(name, signals) for name, signals in scopes.items()
                   if name.endswith("/storage")
                   and {k: signals[k][0] for k in widths if k in signals} == widths]
        if len(matches) != 1:
            raise ValueError(f"unique C380 ordinary SRAM scope not found: {[x[0] for x in matches]}")
        scope, signals = matches[0]
        record["local_s_base_port_binding"] = {"scope": scope,
            "ports": {name: {**ports[name], "fst_handle": signals[name][1]} for name in sorted(ports)}}
    else:
        if end - start != 81920000:
            raise ValueError("C639 waveform duration differs from capture")
        # This inventory is a scope check; a gate-level name/activity map still needs physical input.
        record["p_scope_counts"] = {
            lane: sum(bool(pattern.search(scope)) for scope in scopes)
            for lane, pattern in (("P0", re.compile(r"(^|/)p0(/|$)")),
                                  ("P1", re.compile(r"(^|/)ps\[1\](/|$)")),
                                  ("P2", re.compile(r"(^|/)ps\[2\](/|$)")))
        }
    samples[path.stem] = record
if len(samples) != 6:
    raise ValueError("expected six waveform inventories")
(out / "binding.json").write_text(json.dumps({
    "scope": "C380 routed local_s_base boundary ports and C639 RTL waveform inventory",
    "c380_rtl_sha256": rtl_hashes, "archive_input_sha256": verified_files,
    "samples": samples,
}, indent=2) + "\n")
PY
sha256sum "$out"/{binding.json,fst-reader.sha256} "$out"/*.tsv > "$out/output.sha256"
sha256sum -c "$out/output.sha256"
