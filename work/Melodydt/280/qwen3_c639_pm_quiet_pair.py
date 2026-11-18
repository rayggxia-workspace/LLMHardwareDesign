"""Estimate paired, loaded-quiet power from the captured C639 PM boundary."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys

from gate_power_300 import analyze
from qwen3_c639_pm_runtime_audit import count, digest


def quiet_reference(source, target):
    ports = {}
    values = {}
    start_requirements = {"certified": 1, "reset": 0, "boot_busy": 0, "cfg_valid": 0,
                          "cfg_rsp_valid": 0, "pm_valid": 0, "pm_rsp_valid": 0}
    always_requirements = {name: value for name, value in start_requirements.items()
                           if not name.startswith("pm_")}
    timestamp = None
    with source.open() as original, target.open("x") as output:
        for row in original:
            items = row.split()
            if items[:1] == ["$var"]:
                ports[items[3]] = items[4]
            output.write(row)
            if items[:1] == ["$enddefinitions"]:
                break
        if not (set(start_requirements) | {"generation", "image_bytes"}) <= set(ports.values()):
            raise ValueError("PM certification or transaction ports missing")
        for row in original:
            if row.startswith("#"):
                timestamp = int(row[1:])
            elif row[:1] in {"0", "1", "b"}:
                value, code = row[1:].split() if row[0] == "b" else (row[0], row[1:].strip())
                name = ports[code]
                if timestamp == 0:
                    values[name] = int(value, 2)
                if name in always_requirements and int(value, 2) != always_requirements[name]:
                    raise ValueError("unloaded state or configuration activity: {}".format(name))
                if timestamp and name in {"generation", "image_bytes"} and int(value, 2) != values[name]:
                    raise ValueError("PM contents changed in the measured window")
                if timestamp and name.startswith("pm_"):
                    continue
            output.write(row)
    if any(values.get(name) != expected for name, expected in start_requirements.items()):
        raise ValueError("expected a certified and drained PM at the first sample")
    if timestamp != 81_920_000 or not values["image_bytes"] or not values["generation"]:
        raise ValueError("invalid loaded-quiet sample duration or program state")
    return {"generation": values["generation"], "image_bytes": values["image_bytes"]}


def main(live, netlist, out, cores):
    active_path = live / "pm-live-window-power.json"
    active = json.loads(active_path.read_bytes())
    if active["target_clock_mhz"] != 300 or len(active["windows"]) != 6:
        raise ValueError("expected six measured 300 MHz active windows")

    def per_case(item):
        name, current = item
        folder = out / name
        folder.mkdir()
        inputs = live / name / "ports.vcd"
        quiet_vcd = folder / "quiet.vcd"
        state = quiet_reference(inputs, quiet_vcd)
        transfers = count(quiet_vcd, "dut")
        if any(transfers[key] for key in ("requests", "responses", "pending_at_start", "pending_at_end", "errors")):
            raise ValueError("transactions leaked into the loaded-quiet sample")
        quiet = analyze(quiet_vcd, netlist, "dut", folder / "power", 10_000, 0, 81_920_000,
                        cores // 3, reference_annotations=current["annotated"])
        requests = current["handshakes"]["requests"]
        return name, {"certified_program": state, "clock_edges": transfers["rising_edges"],
                      "requests": requests, "active_total_w": current["power_w"]["total"],
                      "quiet_total_w": quiet["power_w"]["total"], "quiet_power_w": quiet["power_w"],
                      "increment_pj_per_read": (current["energy_nj"] - quiet["energy_nj"]) * 1000 / requests,
                      "active_port_vcd_sha256": digest(inputs), "quiet_port_vcd_sha256": digest(quiet_vcd)}

    with ThreadPoolExecutor(max_workers=3) as workers:
        windows = dict(workers.map(per_case, sorted(active["windows"].items())))
    (out / "pm-quiet-pair.json").write_text(json.dumps({
        "target_clock_mhz": 300,
        "scope": "Routed lc_program_store_1k, same-window port activity from six C639 writer-active samples",
        "quiet_method": "Freeze runtime PM ports to their drained, certified initial values. Retain the full clock and non-PM boundary trace. Internal activity is propagated; no new internal state trace is implied.",
        "active_sha256": digest(active_path), "windows": windows,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main(*map(Path, sys.argv[1:4]), int(sys.argv[4]))
