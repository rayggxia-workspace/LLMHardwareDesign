"""Align the completed component calibrations without inventing a system total."""
from hashlib import sha256
import json
from pathlib import Path
import sys


base, write_root, pm, lc, u_root, sram, destination = map(Path, sys.argv[1:])
spans = [write_root/f"span-{job}/real-span-power.json" for job in (38795264,38795265,38795266)]
u_paths = [u_root/f"power-{job}/u-power.json" for job in (38795282,38795283,38795284)]
inputs = [base, pm, lc, sram, *spans, *u_paths]


def read(path):
    return json.loads(path.read_bytes())


actual = {d["window"]:d for d in map(read,spans)}
bridge = read(pm)
local_pm = read(lc)
u_terms = list(map(read,u_paths))
if {item["scope"] for item in u_terms}!={"e","add","scope"} or any(
        item["retired_s128_words"]!=32 or item["active_ps"]!=u_terms[0]["active_ps"] or
        item["quiet_ps"]!=u_terms[0]["quiet_ps"] for item in u_terms):
    raise ValueError("U components are not aligned to the same capture")
u_per_word = sum(item["incremental_nj"] for item in u_terms)/32
memory = read(sram)["windows"]
windows={}
for name,row in read(base)["windows"].items():
    observed = row["dma_transport_events"]["write"]
    q = actual[name]
    if sum(d["row_count"] for d in q["distribution"].values())*8!=observed["completed"]:
        raise ValueError(f"unreconciled DDR write calibrations: {name}")
    write_nj=[0,0]
    for role,d in q["distribution"].items():
        values=[x for key,r in q["cases"].items() if key.startswith(role+"-")
                for x in r["incremental_pj_per_64b"]]
        for edge,v in enumerate((min(values),max(values))):
            write_nj[edge]+=v*d["row_count"]*8/1000
    pages=bridge["counts_by_window"][name]
    bridge_nj=[0,0]
    for role,count in pages.items():
        physical=bridge["samples"][role]["bridge_incremental_nj"]
        bridge_nj[0]+=count*min(physical)
        bridge_nj[1]+=count*max(physical)
    s=memory[name]
    if s["elapsed_ps"]!=row["elapsed_ps"] or s["tokens"]!=row["tokens"]:
        raise ValueError(f"unaligned SRAM coverage: {name}")
    windows[name] = {
        "elapsed_ps":row["elapsed_ps"],"tokens":row["tokens"],
        "ddr_g32_covered_power_w":row["ddr_g32_covered_power_w"],
        "write_dma_sample_scaled_increment_nj":write_nj,
        "pm_bridge_page_class_reference_nj":bridge_nj,
        "lc_pm_program_and_crc_reference_nj":pages.get("local-352",0)*local_pm["boot_and_crc_nj"],
        "u_add2_sample_scaled_increment_nj":u_per_word*s["u_residual_sram_subset"]["write_128bit"],
        "sram_width_matched_increment_nj":s["width_matched_reference_energy_nj"],
    }
destination.write_text(json.dumps({
    "inputs_sha256":{str(p):sha256(p.read_bytes()).hexdigest() for p in inputs},
    "windows":windows,
    "limitations":[
        "Calibrated dynamic contributions only; the sampled span bounds are descriptive and not statistical bounds.",
        "Finalize read-side DMA and M using their routed timing, parasitics and accepted boundary activity.",
        "PM bridge role binding, PM runtime fetches, mother PM array, uncovered SRAM read/write widths, "
        "physical residency, clock, idle and shared control/interconnect still require binding.",
    ],
},indent=2)+"\n")
