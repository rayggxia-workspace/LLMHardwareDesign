"""Vector-based power on the accepted E32 ODB, with an idle-clock control."""

import json
from pathlib import Path
import re


def instrument(source, destination):
    text = source.read_text(encoding="utf-8")
    clock = "reg clk;initial clk=0;always #5 clk=~clk;"
    assert text.count(clock) == 1
    text = text.replace(clock, clock + """
 string activity_path;
 integer start_activity_cycle;""")
    boot = "$readmemh(path,v);repeat(4)@(negedge clk);reset=0;"
    assert text.count(boot) == 1
    text = text.replace(boot, boot + """
  repeat(4)@(negedge clk);
  if(!$value$plusargs("activity=%s",activity_path))$fatal(1,"VCD path required");
  start_activity_cycle=cycle;
  $dumpfile(activity_path);
  $dumpvars;
  if($test$plusargs("activity_idle"))begin
   repeat(256)@(negedge clk);
   $display("E_ACTIVITY cycles=%0d jobs=0 idle=1",cycle-start_activity_cycle);
   $finish;
  end""")
    terminal = "  $finish;\n end\nendmodule"
    assert text.count(terminal) == 1
    text = text.replace(terminal, """  $display("E_ACTIVITY cycles=%0d jobs=%0d idle=0",cycle-start_activity_cycle,legal+1);
""" + terminal)
    destination.write_text(text, encoding="utf-8")


def find_leaf_scope(vcd):
    stack, matches = [], []
    with vcd.open(encoding="ascii") as stream:
        for line in stream:
            words = line.split()
            if not words:
                continue
            if words[0] == "$scope":
                stack.append(words[2])
                if stack[-2:] == ["narrow_leaf", "arithmetic"]:
                    matches.append("/".join(stack))
            elif words[0] == "$upscope":
                stack.pop()
            elif words[0] == "$enddefinitions":
                break
    scope, = matches
    return scope


def normalize_period(source, destination):
    """Retain the real-bank functional timing, scale trace time to TT300."""
    raw_header = ""
    previous = -1
    with source.open(encoding="ascii") as reader, destination.open("w", encoding="ascii") as writer:
        for line in reader:
            if line.startswith("#"):
                tick = int(line[1:]) * 3333 // 10000
                assert tick >= previous
                previous = tick
                writer.write(f"#{tick}\n")
            else:
                if previous < 0 and len(raw_header) < 500:
                    raw_header += line
                writer.write(line)
    assert re.search(r"\$timescale\s+1\s*ps\s+\$end", raw_header) and previous > 0


def report(out, results, lib, run, sha, mode, log):
    run_log = (out / log).read_text()
    marker, = re.findall(r"^E_ACTIVITY cycles=(\d+) jobs=(\d+) idle=([01])$", run_log, re.M)
    cycles, jobs, idle = map(int, marker)
    assert cycles > 0 and bool(jobs) != bool(idle)
    raw_vcd = out / f"{mode}.vcd"
    vcd = out / f"{mode}-tt300.vcd"
    normalize_period(raw_vcd,vcd)
    scope = find_leaf_scope(vcd)
    script = out / f"{mode}-power.tcl"
    script.write_text(f"""read_liberty {{{lib}}}
read_db {{{results / '6_final.odb'}}}
read_sdc {{{results / '6_final.sdc'}}}
read_spef {{{results / '6_final.spef'}}}
read_vcd -scope {{{scope}}} {{{vcd}}}
report_activity_annotation
report_power -digits 12
""")
    power_log = out / f"{mode}-power.log"
    run(["openroad", "-no_init", "-exit", script], power_log.name)
    text = power_log.read_text()
    annotations = re.search(r"Annotated (\d+) pin activities", text, re.I)
    assert annotations and int(annotations[1]) >= 158, text[-3000:]
    unannotated = re.search(r"^unannotated\s+(\d+)$", text, re.M)
    assert unannotated, text[-3000:]
    totals, = re.findall(r"^Total\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)", text, re.M)
    internal, switching, leakage, total = map(float, totals)
    assert internal > 0 and switching > 0 and leakage > 0
    assert abs(internal+switching+leakage-total) < max(1e-12, total*1e-6)
    seconds = cycles * 3333e-12
    return dict(mode=mode, cycles=cycles, operations=jobs, idle=bool(idle), seconds=seconds,
                vcd_scope=scope, annotated_pins=int(annotations[1]), unannotated_pins=int(unannotated[1]),
                raw_vcd_sha256=sha(raw_vcd), vcd_sha256=sha(vcd),
                report_sha256=sha(power_log), internal_W=internal, switching_W=switching,
                leakage_W=leakage, total_W=total, interval_J=total*seconds)


def save(out, results, runs, sha):
    active, idle = runs
    assert not active["idle"] and idle["idle"]
    dynamic = lambda row: row["internal_W"]+row["switching_W"]
    incremental = (dynamic(active)-dynamic(idle))*active["seconds"]/active["operations"]
    assert incremental > 0
    result = dict(schema="native-leaf-energy-profile/1", provider="E32_POINTWISE_AP64", clock_period_ps=3333,
                  postroute_inputs={name:sha(results/name) for name in ("6_final.odb","6_final.sdc","6_final.spef")},
                  cases=runs, incremental_dynamic_J_per_observed_service=incremental,
                  scope="Zero-delay final gate activity with real-bank functional timing; 10 ns activity trace timestamps normalized to 3333 ps. Original TT Liberty and extracted SPEF. Mixed E test service, active and clocked idle. SRAM, input frontend and external traffic outside the E leaf are excluded.")
    (out/"energy.json").write_text(json.dumps(result,indent=2)+"\n")
