"""Plot declared service-model effects; no physical performance attribution."""
import hashlib
import json
from pathlib import Path
import platform
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

source, dest = map(Path, sys.argv[1:3])
rows = json.loads((source/"cases.json").read_text())
ports = ["1RW", "1R1W", "2RW"]
fig, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
data = {}
for index, phase in enumerate(["observed-prefill32", "observed-decode48"]):
    numbers = []
    for port in ports:
        candidates = [r for r in rows if r["status"]=="feasible" and r["workload"]==phase and
                      r["config"]["key_tile"]==16 and r["config"]["bank_ports"]==port and
                      r["config"]["bank_bytes"]==[65536,65536] and
                      r["config"]["bank_port_bytes_per_cycle"]==64 and not r["disabled_links"]]
        baseline = next(r for r in candidates if r["placement"]==dict(O=0,m=0,l=0))
        other = next(r for r in candidates if r["placement"]==dict(O=1,m=1,l=1))
        assert baseline["traffic"] == other["traffic"]
        numbers.append(100*(1-other["makespan"]/baseline["makespan"]))
    data[phase] = numbers
    positions = [x+(-0.18 if index==0 else 0.18) for x in range(3)]
    bars=ax.bar(positions,numbers,width=0.34,label="Prefill tile (32 queries)" if index==0 else "Decode tile (1 query)",color=["#2664a0","#dd7c34"][index])
    ax.bar_label(bars,labels=[f"{v:.2f}%" for v in numbers],padding=5,fontsize=11)
ax.set_xticks(range(3),ports)
ax.set_ylim(0,5.6)
ax.set_ylabel("Reduction in modeled query-tile cycles (%)")
ax.set_xlabel("Bank port contract (separate hardware sensitivity cases)")
ax.set_title("Moving O / m / l from B0 to B1: same traffic, different contention",fontsize=12,pad=16)
ax.spines[["top","right"]].set_visible(False)
ax.legend(frameon=False,loc="upper right")
ax.grid(axis="y",alpha=.2)
ax.set_axisbelow(True)
fig.text(.5,-.025,"Best of the same four policies; assumed service costs. No chip / full-model speedup claim.",ha="center",fontsize=9)
dest.mkdir(parents=True,exist_ok=True)
for suffix in ("png","svg"):
    fig.savefig(dest/("state-placement-port-sensitivity."+suffix),dpi=180,bbox_inches="tight")
svg = dest/"state-placement-port-sensitivity.svg"
svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines())+"\n", encoding="utf-8", newline="\n")
meta=dict(python=platform.python_version(),matplotlib=matplotlib.__version__,source_sha256=hashlib.sha256((source/"cases.json").read_bytes()).hexdigest(),
          data=data,files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.glob("state-placement-port-sensitivity.*")})
(dest/"plot-manifest.json").write_text(json.dumps(meta,indent=2)+"\n",encoding="utf-8",newline="\n")
