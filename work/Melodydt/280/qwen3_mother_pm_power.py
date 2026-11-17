#!/usr/bin/env python3
"""Replay the three measured PM page payloads against the four routed #223 SRAMs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess


PAGES = (240, 272, 1616)
PIN_WIDTHS = {"clk0": 1, "csb0": 1, "web0": 1, "addr0": 8, "din0": 128, "dout0": 128}
VCD_SCOPE = ("test_qwen3_mother_pm", "dut", "sram", "storage")
MACRO_BASE = "program_store.sram.storage.banks"
PERIOD_PS = 10_000
TARGET_HZ = 300_000_000
CELL = Path("/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib")
NUMBER = r"[+-]?\d+(?:\.\d*)?(?:[Ee][+-]?\d+)?"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_bank_wave(path):
    scopes, ids = [], {}
    traces = [{} for _ in range(4)]
    with path.open() as stream:
        timescale = []
        in_timescale = False
        for line in stream:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "$timescale":
                in_timescale = True
            if in_timescale:
                timescale.extend(parts)
                if "$end" in parts:
                    in_timescale = False
            if parts[0] == "$scope":
                scopes.append(parts[2])
            elif parts[0] == "$upscope":
                scopes.pop()
            elif parts[0] == "$var" and len(scopes) >= 6 and tuple(scopes[-6:-2]) == VCD_SCOPE:
                bank = re.fullmatch(r"banks\[([0-3])\]", scopes[-2])
                width, alias, name = parts[2:5]
                if bank and scopes[-1] == "memory" and name in PIN_WIDTHS:
                    i = int(bank[1])
                    if name in traces[i] or int(width) != PIN_WIDTHS[name]:
                        raise ValueError(f"incorrect bank declaration {i}/{name} in {path}")
                    if len(parts) > 6 and parts[5] != f"[{int(width)-1}:0]":
                        raise ValueError(f"unexpected VCD bit order {parts} in {path}")
                    traces[i][name] = []
                    ids.setdefault(alias, []).append(traces[i][name])
            elif parts[0] == "$enddefinitions":
                break
        if "".join(timescale) != "$timescale1ps$end" or any(t.keys() != PIN_WIDTHS.keys() for t in traces):
            raise ValueError(f"incomplete 1ps bank wave {path}")
        time_ps = 0
        for line in stream:
            line = line.strip()
            if line.startswith("#"):
                time_ps = int(line[1:])
            elif line and not line.startswith("$"):
                if line[0] in "bB":
                    value, alias = line[1:].split()
                else:
                    value, alias = line[0], line[1:]
                if alias in ids:
                    if re.search(r"[^01]", value):
                        raise ValueError(f"unknown logic value for bank pin {alias} in {path} at {time_ps}ps")
                    for trace in ids[alias]:
                        current = int(value, 2)
                        if trace and trace[-1][0] == time_ps:
                            trace[-1] = (time_ps, current)
                        elif not trace or trace[-1][1] != current:
                            trace.append((time_ps, current))
    return traces, time_ps


def value_at(trace, time_ps, *, pre=False):
    for t, level in reversed(trace):
        if t < time_ps or (t == time_ps and not pre):
            return level
    raise ValueError(f"bank pin has no value before sample at {time_ps}ps")


def edges(traces):
    all_edges = []
    for bank in traces:
        events = []
        previous = bank["clk0"][0][1]
        for t, level in bank["clk0"][1:]:
            if previous != level:
                events.append((t, level, value_at(bank["csb0"], t, pre=True),
                               value_at(bank["web0"], t, pre=True)))
            previous = level
        all_edges.append(events)
    clock = [[(t, e) for t, e, _, _ in lane] for lane in all_edges]
    if any(row != clock[0] for row in clock[1:]) or any(
            b[0]-a[0] != PERIOD_PS//2 for a, b in zip(clock[0], clock[0][1:])):
        raise ValueError("expected four phase-aligned 100 MHz source clocks")
    return all_edges


def activity(trace, width, start, end, quiet=False, pin=None):
    initial = value_at(trace, start)
    level = 1 if quiet and pin == "csb0" else initial
    points = [] if quiet and pin != "clk0" else [(t, v) for t, v in trace if start < t < end]
    # The left-boundary edge is included in clock event accounting and in the annotation.
    toggles, high = [0]*width, [0]*width
    if pin == "clk0" and value_at(trace, start, pre=True) != level:
        toggles[0] += 1
    prev = start
    for t, replacement in points+[(end, level)]:
        if t == end:
            replacement = level
        for index in range(width):
            high[index] += ((level >> index) & 1)*(t-prev)
            toggles[index] += ((level ^ replacement) >> index) & 1
        level, prev = replacement, t
    cycles = (end-start)//PERIOD_PS
    return list(zip((n/cycles for n in toggles), (d/(end-start) for d in high)))


def arc_table(lib):
    source = lib.read_text()
    if not re.search(r'time_unit\s*:\s*"1ns"', source) or not re.search(
            r'leakage_power_unit\s*:\s*"1mW"', source):
        raise ValueError("expected #155 1ns/1mW SRAM Liberty")
    table = {}
    for csb in (0, 1):
        for web in (0, 1):
            cond = f'{"" if csb else "!"}csb0 & {"" if web else "!"}web0'
            match = re.search(r'internal_power\s*\(\s*\)\s*\{\s*when\s*:\s*"'+re.escape(cond)+
                              r'"\s*;\s*rise_power\(scalar\)\s*\{\s*values\("('+NUMBER+
                              r')"\);\s*\}\s*fall_power\(scalar\)\s*\{\s*values\("('+NUMBER+r')"\);',source)
            if not match:
                raise ValueError(f"missing conditional clock energy for {cond}")
            table[(csb, web)] = tuple(map(float, match.groups()))
    return table


def analyze_page(page, wave, lib_table):
    traces, end_ps = read_bank_wave(wave)
    ordered = edges(traces)
    seen = [t for bank in ordered for (t, _, _, _) in bank]
    all_cases = {}
    for name, web in (("write", 0), ("read", 1)):
        starts = [t for bank in ordered for t, e, c, w in bank if e and not c and w == web]
        if len(starts) != page//16:
            raise ValueError(f"incorrect {page}B {name} count {len(starts)}")
        start = min(starts)-PERIOD_PS//2
        # Keep a complete cycle after the final command to include the bank's read output.
        end = max(starts)+3*PERIOD_PS//2
        if not min(seen) < start < end <= end_ps or (end-start)%PERIOD_PS:
            raise ValueError(f"invalid {page}B {name} interval {start}–{end}ps")
        for quiet in (False, True):
            banks = []
            for bank, clock in zip(traces, ordered):
                held_web = value_at(bank["web0"], start)
                states = [(e, 1, held_web) if quiet else (e, c, w) for t, e, c, w in clock
                          if start <= t < end]
                rises = [w for e, c, w in states if e and not c]
                if any(w != web for w in rises) or len(states) != 2*(end-start)//PERIOD_PS:
                    raise ValueError(f"mixed commands or incomplete clocks in {page}B {name}")
                signals = {key: activity(bank[key], width, start, end, quiet, key)
                           for key, width in PIN_WIDTHS.items()}
                banks.append({"pins": signals, "requests": len(rises),
                              "clock_arc_pj": sum(lib_table[c, w][1-e] for e, c, w in states)})
            case = f"{name}-{'quiet' if quiet else 'active'}"
            requests = sum(b["requests"] for b in banks)
            if requests != (0 if quiet else page//16):
                raise ValueError(f"{case} does not reconcile bank counts for {page}B")
            all_cases[case] = {"start_ps_at_source": start, "end_ps_at_source": end,
                               "duration_s": ((end-start)//PERIOD_PS)/TARGET_HZ,
                               "banks": banks, "requests": requests}
    return all_cases


def tcl_for(cases, physical, lib):
    lines = [f"read_liberty {{{CELL}}}", f"read_liberty {{{lib}}}",
             f"read_db {{{physical / '6_final.odb'}}}", f"read_sdc {{{physical / '6_final.sdc'}}}",
             f"read_spef {{{physical / '6_final.spef'}}}", "set_propagated_clock [all_clocks]",
             f"foreach cell [get_cells {{{MACRO_BASE}*.memory}}] {{",
             f"  if {{[regexp {{^{re.escape(MACRO_BASE)}\[([0-3])\]\.memory$}} [get_full_name $cell] -> bank]}} {{",
             "    set cells($bank) $cell",
             "    foreach pin [get_pins -of_objects $cell] {",
             "      set name [lindex [split [get_full_name $pin] /] end]",
             "      set pins($bank,$name) $pin",
             '      puts "BOUND $bank $name"', "    }", "  }", "}",
             'if {[array size cells] != 4} {error "could not bind four routed program_store macros"}']
    for case, row in cases.items():
        for bank_idx, bank in enumerate(row["banks"]):
            for pin, values in bank["pins"].items():
                for bit, (density, duty) in enumerate(values):
                    name = pin if len(values) == 1 else f"{pin}[{bit}]"
                    lookup = f"[set {{pins({bank_idx},{name})}}]"
                    lines.append(f"set_power_activity -pins {lookup} -activity {density:.12g} -duty {duty:.12g}")
        for bank_idx in range(4):
            lines.extend((f"puts {{BEGIN_PM {case} {bank_idx}}}",
                          f"report_power -instances $cells({bank_idx}) -digits 9",
                          f"puts {{END_PM {case} {bank_idx}}}"))
    return "\n".join(lines+["puts {MOTHER_MACROS_DONE}", ""])


def one_page(page, waves, physical, lib, lib_table, output, threads):
    wave = waves / f"mother-{page}.vcd"
    old_test = (waves / f"mother-{page}.log").read_text()
    if not re.search(rf"PASS mother PM bytes={page}\s+reads={page//16}\s+writes={page//16}\b", old_test):
        raise ValueError(f"missing archived checked readback for {page}B")
    cases = analyze_page(page, wave, lib_table)
    sub = output / str(page)
    sub.mkdir()
    tcl = sub / "power.tcl"
    log = sub / "power.log"
    tcl.write_text(tcl_for(cases, physical, lib))
    with log.open("w") as stream:
        subprocess.run(["openroad", "-no_init", "-threads", str(threads), "-exit", str(tcl)],
                       stdout=stream, stderr=subprocess.STDOUT, check=True)
    report = log.read_text()
    if re.search(r"(?m)^(?:Error:|\[ERROR)", report) or "MOTHER_MACROS_DONE" not in report:
        raise ValueError(f"failed routed macro probe, see {log}")
    scalars = tuple("internal switching leakage total".split())
    for name, row in cases.items():
        for i, bank in enumerate(row["banks"]):
            text = report.partition(f"BEGIN_PM {name} {i}")[2].partition(f"END_PM {name} {i}")[0]
            matches = re.findall(r"(?m)^\s*("+NUMBER+r")\s+("+NUMBER+r")\s+("+NUMBER+r")\s+("+NUMBER+r")\s+",text)
            if len(matches) != 1 or not re.search(r"Internal\s+Switching\s+Leakage\s+Total", text):
                raise ValueError(f"missing {name} bank {i} power in {log}")
            values = list(map(float, matches[0]))
            if any(not math.isfinite(v) or v < 0 for v in values):
                raise ValueError(f"invalid {name} bank {i} power in {log}")
            bank["opensta_w"] = dict(zip(scalars, values))
            del bank["pins"]
        row["opensta_w"] = {key: sum(bank["opensta_w"][key] for bank in row["banks"]) for key in scalars}
        row["exact_clock_arc_pj"] = sum(bank["clock_arc_pj"] for bank in row["banks"])
    increments = {}
    for operation in ("write", "read"):
        active, quiet = (cases[f"{operation}-{condition}"] for condition in ("active", "quiet"))
        increments[operation] = {"requests": active["requests"], "duration_s": active["duration_s"],
                                 "exact_clock_arc_pj": active["exact_clock_arc_pj"]-quiet["exact_clock_arc_pj"],
                                 "opensta_pj": {key: (active["opensta_w"][key]-quiet["opensta_w"][key])*
                                                       active["duration_s"]*1e12 for key in scalars}}
    return {"bytes":page, "source_vcd_sha256":sha(wave), "cases":cases,
            "increment":increments, "power_log_sha256":sha(log), "tcl_sha256":sha(tcl)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("waves", "physical", "bank_lib", "output"):
        parser.add_argument(name,type=Path)
    parser.add_argument("--cores",type=int,default=3)
    parser.add_argument("--prepare-only",action="store_true")
    args = parser.parse_args()
    lib_table = arc_table(args.bank_lib)
    if args.prepare_only:
        for page in PAGES:
            cases = analyze_page(page,args.waves / f"mother-{page}.vcd",lib_table)
            print(page, {case: result["requests"] for case,result in cases.items()})
        return
    if args.cores < 3:
        raise ValueError("at least three cores are needed for parallel page analysis")
    with ThreadPoolExecutor(max_workers=3) as pool:
        pages = list(pool.map(lambda page: one_page(page,args.waves,args.physical,args.bank_lib,lib_table,
                                                   args.output,args.cores//3),PAGES))
    record = {"scope":"four #223 routed program_store SRAM macro instances",
              "source":"38795749 checked PM readback", "target_clock_hz":TARGET_HZ,
              "quiet":"clock and time matched; hold pin values at start, force CS inactive",
              "internal_clock":"exact per-edge joint CSB/WEB conditional scalar energy in #155 Liberty",
              "opensta":"observed per-pin switching rates and duty applied to matching post-route instances",
              "physical_sha256":{name:sha(args.physical / name) for name in ("6_final.v","6_final.odb","6_final.sdc","6_final.spef")},
              "liberty_sha256":{str(path):sha(path) for path in (CELL,args.bank_lib)},
              "openroad_version":subprocess.check_output(["openroad","-version"],text=True).strip(),
              "pages":pages}
    (args.output / "mother-pm-macro-power.json").write_text(json.dumps(record,indent=2)+"\n")


if __name__ == "__main__":
    main()
