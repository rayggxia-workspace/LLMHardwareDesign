"""Calibrate each routed U ADD2 leaf over the same 32 retired words."""
import json
from pathlib import Path
import sys

from extract_c639_m_ports import extract
from gate_power_300 import analyze


def events(path):
    scope = "test_native_add_scope/scope"
    probes = {"clk", "word_valid", "word_ready", "word_done_valid", "word_done_ready"}
    stack = []
    names = {}
    with path.open() as stream:
        for line in stream:
            fields = line.split()
            if fields[:1] == ["$scope"]:
                stack.append(fields[2])
            elif fields[:1] == ["$upscope"]:
                stack.pop()
            elif fields[:1] == ["$var"] and "/".join(stack) == scope and fields[4] in probes:
                names[fields[3]] = fields[4]
            elif fields[:1] == ["$enddefinitions"]:
                break
        if set(names.values()) != probes:
            raise ValueError("ADD2 monitor ports missing")
        old = {}
        changes = {}
        issued, retired = [], []
        time = None
        for line in stream:
            if line.startswith("#"):
                if time is not None and old.get("clk") == "0" and changes.get("clk") == "1":
                    if old["word_valid"] == old["word_ready"] == "1":
                        issued.append(time)
                    if old["word_done_valid"] == old["word_done_ready"] == "1":
                        retired.append(time)
                old.update(changes)
                changes.clear()
                time = int(line[1:])
            elif line[:1] in {"0", "1"}:
                name = names.get(line[1:].strip())
                if name:
                    changes[name] = line[0]
    return issued, retired, time


path, physical, out = map(Path, sys.argv[1:4])
scope, cores = sys.argv[4], int(sys.argv[5])
issued, retired, extent = events(path)
if len(issued)!=257 or len(retired)!=257:
    raise ValueError(f"ADD2 full and canceled windows did not reconcile: {len(issued)}/{len(retired)}")
start = issued[0]//10000*10000
end = (retired[31]+9999)//10000*10000
quiet_end = start-20000
quiet_start = quiet_end-(end-start)
if quiet_start<50000 or sum(start<=edge<end for edge in retired)!=32:
    raise ValueError("no equal initialized idle window or retirement mismatch")
wave = out/"ports.vcd"
extract(physical/"6_final.v",path,wave,"test_native_add_scope/"+scope,0,extent,100,None)
active = analyze(wave,physical,"dut",out/"active",10000,start,end,cores,clip=True)
quiet = analyze(wave,physical,"dut",out/"quiet",10000,quiet_start,quiet_end,cores,clip=True)
(out/"u-power.json").write_text(json.dumps({
    "active_ps":[start,end], "quiet_ps":[quiet_start,quiet_end], "retired_s128_words":32,
    "incremental_nj":active["energy_nj"]-quiet["energy_nj"],
    "scope":scope, "note":"Deterministic ADD2 fixture, matched prior idle in the same waveform",
},indent=2)+"\n")
