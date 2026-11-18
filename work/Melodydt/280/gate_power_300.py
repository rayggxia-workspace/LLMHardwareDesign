"""300 MHz OpenROAD power over a gate-level VCD with preserved event order."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

CELL_LIB = Path("/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib")


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()


def retime_wave(source, dest, scope, source_period, start, end, escape, clip):
    denominator = 3 * source_period

    def tick(ps):
        return ((ps - start) * 10000 + denominator // 2) // denominator

    first = time = None
    entered = False
    stack = []
    seen_scope = False
    clk_id = None
    clock = []
    latest = {}

    def remember_clock(ident, value, now):
        if ident == clk_id and value[0] in ("0", "1") and (not clock or clock[-1][1] != value[0]):
            clock.append((now, value[0]))

    with source.open() as src, dest.open("w") as out:
        for line in src:
            fields = line.split()
            if fields[:1] == ["$timescale"]:
                while fields[-1] != "$end":
                    fields.extend(next(src).split())
                if "".join(fields[1:-1]) != "1ps":
                    raise ValueError(f"expected 1 ps VCD: {source}")
                line = "$timescale 1ps $end\n"
            if fields[:1] == ["$scope"]:
                stack.append(fields[2])
                seen_scope |= "/".join(stack) == scope
            elif fields[:1] == ["$upscope"]:
                stack.pop()
            elif fields[:1] == ["$var"] and "/".join(stack) == scope and fields[4] == "clk":
                clk_id = fields[3]
            if fields[:1] == ["$var"] and fields[1] in {"logic", "bit", "int"}:
                fields[1] = "wire"
                line = " ".join(fields) + "\n"
            field = 2 if fields[:1] == ["$scope"] else 4 if fields[:1] == ["$var"] else None
            if escape and field is not None and "\\" in fields[field]:
                fields[field] = fields[field].replace("\\", "\\\\")
                line = " ".join(fields) + "\n"
            out.write(line)
            if fields[:1] == ["$enddefinitions"]:
                break
        if not seen_scope or not clk_id:
            raise ValueError(f"clock scope missing: {scope}")

        for line in src:
            if line.startswith("#"):
                time = int(line[1:])
                if first is None:
                    first = time
                if time > end and clip:
                    break
                if time < start:
                    continue
                if not entered:
                    out.write("#0\n")
                    for ident, value in latest.items():
                        out.write(value)
                        remember_clock(ident, value, start)
                    entered = True
                if time > start:
                    out.write(f"#{tick(time)}\n")
                continue
            if not line.strip() or line.startswith("$"):
                continue
            if line[0] in "01xXzZ":
                ident = line[1:].strip()
            elif line[0] in "bB":
                ident = line.split()[-1]
            else:
                raise ValueError(f"unsupported VCD change in {source}: {line[:80]}")
            if not entered:
                latest[ident] = line
            else:
                out.write(line)
                remember_clock(ident, line, time)

        if time != end and clip:
            out.write(f"#{tick(end)}\n")
        if not entered or first is None or (not clip and (first != start or time != end)):
            raise ValueError(f"window mismatch: {source}, {first}..{time} expected {start}..{end}")
    real_edges = [t for t, _ in clock if t > start]
    expected = (end - start) // (source_period // 2)
    if len(real_edges) < expected - 1 or len(real_edges) > expected or any(
        b - a != source_period // 2 for a, b in zip(real_edges, real_edges[1:])
    ):
        raise ValueError(f"unexpected clock for {source}: {len(real_edges)} edges, expected {expected}")
    return {"source_period_ps": source_period, "source_start_ps": start, "source_end_ps": end,
            "window_ps": tick(end), "clock_hz": 300000000, "clock_edges": len(real_edges)}


def analyze(vcd, physical, scope, output, period, start, end, cores, libs=(), escape=False, clip=False,
            reference_annotations=None):
    output.mkdir(parents=True)
    sdc = physical / "6_final.sdc"
    if len(re.findall(r"(?m)^create_clock .*?-period 3\.333[0-9]* ", sdc.read_text())) != 1:
        raise ValueError(f"expected 300 MHz SDC: {sdc}")
    wave = output / "gate-300mhz.vcd"
    timing = retime_wave(vcd, wave, scope, period, start, end, escape, clip)
    script = output / "power.tcl"
    script.write_text("".join(f"read_liberty {{{lib}}}\n" for lib in (CELL_LIB, *libs))
                      + f"read_db {{{physical / '6_final.odb'}}}\nread_sdc {{{sdc}}}\n"
                      + f"read_spef {{{physical / '6_final.spef'}}}\nset_propagated_clock [all_clocks]\n"
                      + f"read_vcd -scope {{{scope}}} {{{wave}}}\n"
                      + 'report_activity_annotation\nreport_power -digits 9\nputs "GATE_WINDOW_POWER_COMPLETE"\n')
    log = output / "power.log"
    with log.open("w") as stream:
        subprocess.run(["openroad", "-no_init", "-threads", str(cores), "-exit", str(script)],
                       stdout=stream, stderr=subprocess.STDOUT, check=True)
    text = log.read_text()
    count, = re.findall(r"Annotated (\d+) pin activities\.", text)
    missing, = re.findall(r"(?m)^unannotated\s+(\d+)", text)
    total, = re.findall(r"(?m)^Total\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)", text)
    if ("GATE_WINDOW_POWER_COMPLETE" not in text or re.search(r"(?m)^(Error:|\[ERROR)", text)
            or int(count) == 0 or (reference_annotations is not None and int(count) != reference_annotations)):
        raise ValueError(f"bad power result: {log}")
    power = dict(zip(("internal", "switching", "leakage", "total"), map(float, total)))
    inputs = [vcd, wave, *libs, CELL_LIB] + [physical / f"6_final.{x}" for x in ("v", "odb", "sdc", "spef")]
    receipt = {"scope": scope, "timing": timing, "annotated": int(count), "unannotated": int(missing),
               "power_w": power, "energy_nj": power["total"] * timing["window_ps"] / 1000,
               "input_sha256": {str(path): sha(path) for path in inputs}, "power_log_sha256": sha(log),
               "zero_delay_activity": True}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: receipt[k] for k in ("scope", "annotated", "unannotated", "power_w", "energy_nj")}))
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vcd", type=Path)
    parser.add_argument("physical", type=Path)
    parser.add_argument("scope")
    parser.add_argument("output", type=Path)
    parser.add_argument("period", type=int)
    parser.add_argument("start", type=int)
    parser.add_argument("end", type=int)
    parser.add_argument("--cores", type=int, default=2)
    parser.add_argument("--lib", action="append", type=Path, default=[])
    parser.add_argument("--escape", action="store_true")
    parser.add_argument("--clip", action="store_true")
    parser.add_argument("--reference-annotations", type=int)
    args = parser.parse_args()
    analyze(args.vcd, args.physical, args.scope, args.output, args.period, args.start, args.end,
            args.cores, args.lib, args.escape, args.clip, args.reference_annotations)
