"""Measure routed SRAM power at 300 MHz from an equal-window zero-delay replay."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys


EXPECTED = {
    "idle": (0, 0, 0, 0), "read128": (64, 64, 0, 0), "write128": (16, 0, 16, 0),
    "write256": (16, 0, 32, 0), "write512": (16, 0, 64, 0), "read512": (16, 0, 0, 32),
}
POWER_FIELDS = ("internal_w", "switching_w", "leakage_w", "total_w")


def retime(source, destination, start, end):
    stack, scopes, values, changes = [], set(), {}, []
    first_dump = False
    tick, previous_out, clock_edges = None, None, []
    previous_clk, clk = None, None
    banks = set()

    def flush(dst):
        nonlocal first_dump, previous_out, previous_clk
        if tick is None or tick > end:
            return
        for identifier, record in changes:
            if identifier == clk and record[0] != previous_clk:
                previous_clk = record[0]
                if tick >= start:
                    clock_edges.append(tick)
        if tick <= start:
            values.update(changes)
            if tick < start:
                return
        if not first_dump:
            dst.write("#0\n$dumpvars\n")
            dst.writelines(values.values())
            dst.write("$end\n")
            first_dump, previous_out = True, 0
            if tick == start:
                return
        shifted = ((tick - start) + 1) // 3
        if shifted > previous_out:
            dst.write("#{}\n".format(shifted))
            previous_out = shifted
        dst.writelines(record for _, record in changes)

    with source.open() as src, destination.open("w") as dst:
        for line in src:
            fields = line.split()
            if fields[:1] == ["$timescale"]:
                while fields[-1] != "$end":
                    fields.extend(next(src).split())
                if fields != ["$timescale", "1ps", "$end"]:
                    raise ValueError("expected 1ps Verilator VCD")
                line = " ".join(fields) + "\n"
            elif fields[:1] == ["$scope"]:
                stack.append(fields[2])
                if fields[2] == "dut" and "qwen3_sram_macro_fixture" in stack:
                    scopes.add("/".join(stack))
                if re.search(r"storage\.banks\[[0-3]\]\.memory$", fields[2]):
                    banks.add(fields[2])
                fields[2] = fields[2].replace("\\", "\\\\")
                line = " ".join(fields) + "\n"
            elif fields[:1] == ["$upscope"]:
                stack.pop()
            elif fields[:1] == ["$var"]:
                if "/".join(stack) in scopes and fields[4] == "clk":
                    clk = fields[3]
                if fields[1] in ("logic", "bit", "int", "reg"):
                    fields[1] = "wire"
                fields[4] = fields[4].replace("\\", "\\\\")
                line = " ".join(fields) + "\n"
            dst.write(line)
            if fields[:1] == ["$enddefinitions"]:
                break
        if not clk or len(scopes) != 1 or len(banks) != 4:
            raise ValueError("gate VCD lacks DUT clock or four routed bank scopes: {}".format(banks))
        for line in src:
            if line.startswith("#"):
                flush(dst)
                changes = []
                tick = int(line[1:])
                if tick > end:
                    break
            elif line[:1] in ("0", "1", "x", "z"):
                changes.append((line[1:].strip(), line))
            elif line[:1] in ("b", "B", "r", "R"):
                changes.append((line.split()[-1], line))
        flush(dst)
    if clock_edges != list(range(start, end + 1, 5000)):
        raise ValueError("unexpected 100 MHz source edge sequence")
    return scopes.pop(), ((end - start) + 1) // 3


def report(case, out, physical, cells, bank, cores):
    sample = out / case
    runlog = (sample / "run.log").read_text()
    match = re.search(r"(?m)^PASS SRAM " + case + r" (\d+) (\d+) (\d+) (\d+)$", runlog)
    if not match or tuple(map(int, match.groups())) != EXPECTED[case]:
        raise ValueError("unexpected transaction or feeder coverage in " + str(sample))
    start, end = map(int, re.search(r"(?m)^WINDOW (\d+) (\d+)$", runlog).groups())
    if end - start != 5120000:
        raise ValueError("unequal power window")
    scope, elapsed = retime(sample / "raw.vcd", sample / "gate-300mhz.vcd", start, end)
    tcl = sample / "power.tcl"
    tcl.write_text(
        "read_liberty {{{}}}\nread_liberty {{{}}}\n".format(cells, bank)
        + "read_db {{{0}/6_final.odb}}\nread_sdc {{{0}/6_final.sdc}}\nread_spef {{{0}/6_final.spef}}\n".format(physical)
        + "set_propagated_clock [all_clocks]\n"
        + "read_vcd -scope {{{}}} {{{}}}\n".format(scope, sample / "gate-300mhz.vcd")
        + "puts UNANNOTATED_PINS_BEGIN\nreport_activity_annotation -report_unannotated\nputs UNANNOTATED_PINS_END\n"
        + "report_worst_slack -max\nreport_worst_slack -min\nreport_power -digits 9\nputs ACTIVITY_ANALYSIS_COMPLETED\n"
    )
    log = sample / "power.log"
    with log.open("w") as stream:
        subprocess.run(["openroad", "-no_init", "-threads", str(cores), "-exit", str(tcl)],
                       stdout=stream, stderr=subprocess.STDOUT, check=True)
    text = log.read_text()
    if "ACTIVITY_ANALYSIS_COMPLETED" not in text or re.search(r"(?m)^(Error:|\[ERROR)", text):
        raise ValueError("OpenROAD did not complete: " + str(log))
    direct = int(re.search(r"Annotated (\d+) pin activities\.", text).group(1))
    remaining = int(re.search(r"(?m)^unannotated\s+(\d+)", text).group(1))
    unannotated = text.split("UNANNOTATED_PINS_BEGIN", 1)[1].split("UNANNOTATED_PINS_END", 1)[0]
    if direct / (direct + remaining) < .99 or re.search(r"storage\.banks\[[0-3]\]\.memory[/.]", unannotated):
        raise ValueError("incomplete routed pin or macro activity coverage: " + str(log))
    power = {}
    for label, key in (("Total", "total"), ("Macro", "macro")):
        values = re.search(r"(?m)^" + label + r"\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)", text)
        power[key] = dict(zip(POWER_FIELDS, map(float, values.groups())))
    if power["macro"]["leakage_w"] <= 0 or power["macro"]["internal_w"] <= 0:
        raise ValueError("bank Liberty internal and leakage power were not exercised")
    result = {
        "scope": scope, "time_ps": elapsed, "logical_groups": EXPECTED[case][0],
        "ordinary_read128": EXPECTED[case][1], "ordinary_write128": EXPECTED[case][2],
        "simultaneous_four_bank_reads512": EXPECTED[case][3], "annotated": direct, "unannotated": remaining,
        "setup_hold_report_ns": re.findall(r"(?m)^worst slack (?:max|min)\s+([\d.eE+-]+)", text),
        "power": power,
    }
    (sample / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    return case, result


def main(out, physical, cells, bank, cores, cases):
    workers = min(3, cores)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = dict(pool.map(lambda x: report(x, out, physical, cells, bank, cores // workers), cases))
    idle = rows["idle"]
    for case, row in rows.items():
        if case == "idle":
            continue
        if (row["annotated"], row["unannotated"], row["time_ps"]) != (idle["annotated"], idle["unannotated"], idle["time_ps"]):
            raise ValueError("paired windows do not have identical duration and pin coverage")
        count = row["simultaneous_four_bank_reads512"] if case == "read512" else row["logical_groups"]
        for label in ("total", "macro"):
            delta = row["power"][label]["total_w"] - idle["power"][label]["total_w"]
            row[label + "_increment_pj_per_operation"] = delta * row["time_ps"] / count
    result = {"clock_mhz": 300, "simulator": "zero-delay routed activity excluding path-delay glitches",
              "sample": "fixed paired 512-cycle windows, same 64-word preload and quiescent tail",
              "scope_note": "512 feeder result per physical same-address read; 256/512 writes are logical groups of 2/4 serial beats",
              "macro_group": "OpenSTA Macro row, included in the Total row", "windows": rows}
    (out / "calibration.json").write_text(json.dumps(result, indent=2) + "\n")
    print(out, [(case, row.get("total_increment_pj_per_operation")) for case, row in rows.items()])


if __name__ == "__main__":
    main(*map(Path, sys.argv[1:5]), int(sys.argv[5]), sys.argv[6:])
