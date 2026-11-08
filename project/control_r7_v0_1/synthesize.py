"""Map the R4 control components with a pinned standard-cell library."""
import argparse
from collections import Counter
import hashlib
import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = HERE.parent
CORE = PROJECT / "control_rtl_min_v0_1"
R4 = PROJECT / "control_r4_v0_1"
DMA = PROJECT / "rtl/hbm_feed"
PERIOD_NS = 10 / 3
EXPECTED_LIB_SHA = "8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1"
LEF_SHA = {
    "NangateOpenCellLibrary.tech.lef": "834a79295054cd4209178d1bade67c353863c47bb4b3c22ee38b862b7cec37f2",
    "NangateOpenCellLibrary.macro.mod.lef": "a43aea339f12a57a63497783e508ba16f3da2dc056d3247dec7d99707c2dedef",
}
CASES = [
    ("mother", CORE / "mc_min_controller.sv", {"STALL_LIMIT": 4096}, "clk_i", 1),
    ("local0", CORE / "lc_min_controller.sv",
     {"BLOCK_ID": 0, "STALL_LIMIT": 4096, "DRAIN_LIMIT": 128, "LOCAL_S_BYTES": 16384}, "clk_i", 1),
    ("local1", CORE / "lc_min_controller.sv",
     {"BLOCK_ID": 1, "STALL_LIMIT": 4096, "DRAIN_LIMIT": 128, "LOCAL_S_BYTES": 16384}, "clk_i", 1),
    ("raw16_adapter", R4 / "lc_raw16_s_adapter.sv", {}, "clk", 2),
    ("dma_bridge", R4 / "raw16_dma_bridge.sv", {"TAG_LIMIT": 65535}, "clk", 2),
    ("reset_coordinator", R4 / "cohort_reset_controller.sv",
     {"MEMBERS": 8, "MIN_RESET": 4, "QUIET_CYCLES": 3}, "clk", 1),
    ("group_dma", DMA / "hbm_group_dma.sv",
     {"GROUPS": 1, "S_PER_GROUP": 2, "SLOTS": 8, "NS": 2, "CHANNELS": 1}, "clk", 1),
    ("request_fifo", DMA / "hbm_async_fifo.sv", {"WIDTH": 185, "LGDEPTH": 2}, None, 1),
    ("response_fifo", DMA / "hbm_async_fifo.sv", {"WIDTH": 146, "LGDEPTH": 2}, None, 1),
]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda: f.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def invoke(args, cwd, log):
    command = [str(a) for a in args]
    result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log.write_bytes(result.stdout)
    text = result.stdout.decode("utf-8", errors="replace")
    if result.returncode != 0 or re.search(r"(?im)^(?:Error:|\[ERROR)", text):
        raise RuntimeError(f"{command} exited {result.returncode}\n{text[-3500:]}")
    return text


def measure(case, out, liberty, lef_files, liberty_cells, yosys, openroad):
    name, source, params, clock, count = case
    top = source.stem
    work = out / name
    work.mkdir()
    quote = lambda path: json.dumps(str(path))
    commands = [f"read_verilog -sv -I{source.parent} -I{CORE} {quote(source)}"]
    if params:
        settings = " ".join(f"-set {key} {value}" for key, value in params.items())
        commands.append(f"chparam {settings} {top}")
    commands.extend([
        f"hierarchy -check -top {top}",
        f"synth -top {top} -noabc",
        "check -assert",
        f"dfflibmap -liberty {quote(liberty)}",
        f"abc -liberty {quote(liberty)}",
        "clean",
        f"read_liberty -lib -ignore_miss_func {quote(liberty)}",
        f"hierarchy -check -top {top}",
        "check -assert",
        f"stat -liberty {quote(liberty)}",
        "write_json mapped.json",
        "write_verilog -noattr -noexpr mapped.v",
    ])
    script = work / "synth.ys"
    script.write_text("\n".join(commands) + "\n", encoding="utf-8")
    log = invoke([yosys, "-s", script], work, work / "yosys.log")
    match = re.search(r"Chip area for module .*?:\s*([\d.]+)", log)
    if not match:
        raise ValueError(f"missing mapped area for {name}")
    mapped = json.loads((work / "mapped.json").read_bytes())["modules"][top]
    cells = Counter(cell["type"] for cell in mapped["cells"].values())
    if not cells or cells.keys() - liberty_cells:
        raise ValueError(f"unmapped cells in {name}: {sorted(cells.keys() - liberty_cells)}")
    result = dict(name=name, module=top, source=source.relative_to(PROJECT.parent).as_posix(),
                  source_sha256=sha(source), parameters=params, inventory_instances=count,
                  cell_count=sum(cells.values()), cell_area_um2=float(match.group(1)),
                  flop_cells=sum(n for cell, n in cells.items() if cell.startswith(("DFF", "SDFF"))),
                  mapped_cell_types=dict(sorted(cells.items())))
    if clock:
        sta = work / "timing.tcl"
        lef_commands = "".join(f"read_lef {{{path}}}\n" for path in lef_files)
        sta.write_text(
            lef_commands + f"read_liberty {{{liberty}}}\nread_verilog mapped.v\nlink_design {top}\n"
            f"create_clock -name core -period {PERIOD_NS:.9f} [get_ports {clock}]\n"
            "report_checks -path_delay max -from [all_registers -output_pins] "
            "-to [all_registers -data_pins] -group_path_count 1 -format full_clock_expanded -digits 6\n"
            "exit\n", encoding="utf-8")
        timing = invoke([openroad, "-no_init", "-exit", sta], work, work / "timing.log")
        slack = re.search(r"(-?[\d.]+)\s+slack \((?:MET|VIOLATED)\)", timing)
        start = re.search(r"(?m)^Startpoint:\s*(.+)$", timing)
        end = re.search(r"(?m)^Endpoint:\s*(.+)$", timing)
        if not (slack and start and end):
            raise ValueError(f"no timed register path in {name}")
        result["timing"] = dict(clock_port=clock, period_ns=PERIOD_NS, setup_slack_ns=float(slack.group(1)),
                                startpoint=start.group(1), endpoint=end.group(1),
                                scope="register-to-register setup at typical, ideal clock, zero wire parasitics")
    else:
        result["timing"] = dict(scope="area-only dual-clock FIFO")
    result["artifacts_sha256"] = {path.name: sha(path) for path in sorted(work.iterdir()) if path.is_file()}
    print(f"{name}: {result['cell_count']} cells, {result['cell_area_um2']:.3f} um^2, "
          f"setup slack {result['timing'].get('setup_slack_ns', 'area only')}", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yosys", required=True, type=pathlib.Path)
    parser.add_argument("--openroad", required=True, type=pathlib.Path)
    parser.add_argument("--liberty", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args()
    liberty = args.liberty.resolve()
    if sha(liberty) != EXPECTED_LIB_SHA:
        raise ValueError("Nangate45 Liberty SHA-256 mismatch")
    lef_files = [liberty.parent.parent / "lef" / name for name in LEF_SHA]
    if any(sha(path) != LEF_SHA[path.name] for path in lef_files):
        raise ValueError("Nangate45 LEF SHA-256 mismatch")
    lib = liberty.read_text(encoding="utf-8")
    if not re.search(r'time_unit\s*:\s*"1ns"', lib):
        raise ValueError("timing library does not use ns")
    liberty_cells = set(re.findall(r'\bcell\s*\(\s*"?([\w]+)"?\s*\)', lib))
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    versions = {}
    for name, program, flag in [("yosys", args.yosys, "-V"), ("openroad", args.openroad, "-version")]:
        versions[name] = dict(version=invoke([program, flag], out, out / (name + "-version.log")).strip(),
                              path=str(program), executable_sha256=sha(program.resolve()))
    results = [measure(c, out, liberty, lef_files, liberty_cells, args.yosys, args.openroad) for c in CASES]
    estimate = sum(row["inventory_instances"] * row["cell_area_um2"] for row in results)
    report = dict(schema="control-r7-leaf-synthesis/0.1", tools=versions,
                  liberty=dict(path=str(liberty), sha256=EXPECTED_LIB_SHA, corner="Nangate45 typical"),
                  lef=[dict(path=str(path), sha256=LEF_SHA[path.name]) for path in lef_files],
                  report_scope="independent modules with R4 parameters and open top ports. "
                               "PM, private S, test peer, integration wiring and physical overhead are separate.",
                  modules=results, area_inventory_sum_um2=round(estimate, 6))
    (out / "synthesis-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"PASS {len(results)} mapped module variants, "
          f"{sum('setup_slack_ns' in r['timing'] for r in results)} timed setup paths", flush=True)


if __name__ == "__main__":
    main()
