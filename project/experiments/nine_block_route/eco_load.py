import json
import sys
from pathlib import Path
d=json.loads(Path(sys.argv[1] if len(sys.argv)>1 else "../gds-97924-30/route-load.json").read_text())["results"]
sets={}
for net,v in d.items():
    k=v["driver_block"]
    if k=="P":
        s=net.rsplit("_",1)[1]
        pin={"valid":"m_to_g_valid","take":"g_from_m_take"}.get(s,f"m_to_g_data[{s}]")
    else:
        _,_,op,*t=net.split("_")
        pin=f"tx_data[{t[0]}]" if op=="data" else {"valid":"tx_valid","ready":"rx_ready","stored":"rx_stored"}[op]
    sets.setdefault(k,[]).append((pin,1.5*v["uniform_wire_ff"]+40))
for k,pins in sets.items():
    assert len(pins)==len(set(p[0] for p in pins))
    Path(k+"-load.tsv").write_text("".join(f"{{{p}}} {c:.6f}\n" for p,c in pins))
