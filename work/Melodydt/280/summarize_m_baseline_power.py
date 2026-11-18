"""Bind each provisional 300 MHz M power report to observable C639 handshakes."""
from hashlib import sha256
import json
from pathlib import Path
import re
import sys


CHANNELS = ("a", "lc", "lr", "mc_req", "mc_rsp", "mc_close", "mc_fence_req", "mc_fence_done")


def handshakes(path):
    required = {"clk"} | {f"{name}_{suffix}" for name in CHANNELS for suffix in ("valid", "ready")}
    aliases = {}
    pairs = {name: 0 for name in CHANNELS}
    previous, updates = {}, {}
    cycles = 0

    def finish_tick():
        if previous.get("clk") == "0" and updates.get("clk") == "1":
            for name in CHANNELS:
                pairs[name] += previous[f"{name}_valid"] == previous[f"{name}_ready"] == "1"
            return 1
        return 0

    with path.open() as stream:
        for line in stream:
            fields = line.split()
            if fields[:1] == ["$var"] and fields[4] in required:
                if fields[2] != "1":
                    raise ValueError(f"non-scalar handshake: {fields[4]}")
                aliases.setdefault(fields[3], []).append(fields[4])
            elif fields[:1] == ["$enddefinitions"]:
                break
        if {name for names in aliases.values() for name in names} != required:
            raise ValueError(f"missing M handshake fields: {path}")
        for line in stream:
            if line.startswith("#"):
                cycles += finish_tick()
                previous.update(updates)
                updates.clear()
            elif line[:1] in {"0", "1"}:
                for name in aliases.get(line[1:].strip(), ()):
                    updates[name] = line[0]
        cycles += finish_tick()
    if cycles != 8192:
        raise ValueError(f"unexpected source clock cycle count: {path}/{cycles}")
    return pairs


wave, output, sta = map(Path, sys.argv[1:])
slack = {
    path: float(value) for path, value in re.findall(
        r"(?m)^worst slack (max|min) (-?\d+\.\d+)$", sta.read_text())
}
if set(slack) != {"max", "min"} or min(slack.values()) >= 0:
    raise ValueError("old failed STA receipt missing")
samples = {}
for sample in sorted(wave.glob("*/ports.vcd")):
    name = sample.parent.name
    power = json.loads((output / name / "receipt.json").read_bytes())
    entry = {key: power[key] for key in ("power_w", "energy_nj", "annotated", "unannotated")}
    entry["handshakes"] = handshakes(sample)
    entry["source_wave_sha256"] = sha256(sample.read_bytes()).hexdigest()
    samples[name] = entry
if len(samples) != 18:
    raise ValueError("expected three M sites in each of six C639 windows")
(output/"baseline-power.json").write_text(json.dumps({
    "physical_legacy_job":116976,
    "source_replay_job":38772137,
    "target_clock_mhz":300,
    "setup_wns_ns":slack["max"],
    "hold_wns_ns":slack["min"],
    "sta_sha256":sha256(sta.read_bytes()).hexdigest(),
    "status":"provisional, timing violations; port activity propagated through the routed design",
    "samples":samples,
},indent=2)+"\n")
