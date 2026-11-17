"""Integrate a provisional old-M scenario over Qwen3's modeled residence times."""
from hashlib import sha256
import json
from pathlib import Path
import sys

rollup, active_file, idle_file, out = map(Path, sys.argv[1:])
active = json.loads(active_file.read_bytes())
idle = json.loads(idle_file.read_bytes())
if active["physical_legacy_job"]!=116976 or active["target_clock_mhz"]!=300:
    raise ValueError("expected the old violating 300 MHz M baseline")
idle_w = idle["power_w"]["total"]
if idle["annotated"]!=1330 or idle_w<=0:
    raise ValueError("incomplete clocked idle report")

samples = [[] for _ in range(3)]
for name,row in active["samples"].items():
    lane = int(name.rsplit("-p",1)[1])
    if row["annotated"]!=1330 or row["handshakes"]["a"]<=0:
        raise ValueError(f"incomplete loaded M report: {name}")
    samples[lane].append(row["power_w"]["total"])
if any(len(lane)!=6 for lane in samples):
    raise ValueError("expected six comparable samples per lane")
rates = [(min(values), max(values)) for values in samples]
active_rates = (min(low for low, _ in rates), max(high for _, high in rates))
windows={}
for name,row in json.loads(rollup.read_bytes())["windows"].items():
    elapsed, tokens = row["elapsed_ps"], row["tokens"]
    busy=[site.get("busy_interval_union_ps",0) for site in row["component_activity"]["modeled_m_by_site"]]
    if len(busy)!=4 or busy[3]!=0 or any(t<0 or t>elapsed for t in busy):
        raise ValueError(f"unexpected modeled M residence: {name}")
    busy_ps = sum(busy[:3])
    idle_energy = idle_w * (3 * elapsed - busy_ps)
    energy_w_ps = [idle_energy + rate * busy_ps for rate in active_rates]
    ddr_g32_w = row["ddr_g32_covered_power_w"]
    subtotal_w = [power + energy / elapsed for power, energy in zip(ddr_g32_w, energy_w_ps)]
    windows[name]={
        "elapsed_ps":elapsed,"tokens":tokens,"busy_ps_by_m_site":busy[:3],
        "m_reference_power_w":[energy/elapsed for energy in energy_w_ps],
        "m_reference_energy_mj_per_token":[energy/(1e9*tokens) for energy in energy_w_ps],
        "ddr_g32_increment_old_m_reference_subtotal_w": subtotal_w,
        "ddr_g32_increment_old_m_reference_subtotal_mj_per_token": [
            power * elapsed / (1e9 * tokens) for power in subtotal_w
        ],
    }
with out.open("x") as stream:
    json.dump({
        "source_physical_job":116976,"setup_wns_ns":active["setup_wns_ns"],"hold_wns_ns":active["hold_wns_ns"],
        "clocked_reset_empty_idle_w_per_m":idle_w,"c639_window_power_w_by_lane":rates,
        "c639_window_power_w_pooled":active_rates,
        "method":"Assume three clocked M sites. Use measured reset-empty power outside TLM busy intervals, "
                 "and sampled C639 FFN window average power during the modeled busy intervals. "
                 "Sample spread is a sensitivity range, not a bound or signoff.",
        "subtotal_scope": "DDR devices, G32 activity increment, and the old M reference only.",
        "input_sha256":{str(p):sha256(p.read_bytes()).hexdigest() for p in (rollup,active_file,idle_file)},
        "windows":windows,
    },stream,indent=2)
    stream.write("\n")
