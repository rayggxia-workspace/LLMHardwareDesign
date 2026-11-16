"""Account for modeled wide SRAM writes on the validated ordinary S128 path."""
from hashlib import sha256
import json
from pathlib import Path
import sys

rollup, rtl, serial_log, out = map(Path, sys.argv[1:])
source = rtl.read_text()
for anchor in ("input wire [127:0] din", "wire selected=w_fire||(n_fire",
               ".web0(!(n_fire&&wr))", ".din0(din)"):
    if anchor not in source:
        raise ValueError("SRAM port map changed")
if "PASS SRAM SERIAL:" not in serial_log.read_text():
    raise ValueError("no validated serialized waveform")
result = {
    "scope": "Counts for the demonstrated serialized S128 path and four-bank 512-bit feeder read. "
    "Modeled wide beats do not establish product-wide same-cycle write support or product scheduling.",
    "inputs_sha256": {str(p):sha256(p.read_bytes()).hexdigest() for p in (rollup,rtl,serial_log)},
    "windows": {},
}
for name, row in json.loads(rollup.read_bytes())["windows"].items():
    counts = row["component_activity"]["sram_by_site"]
    if len(counts)!=4:
        raise ValueError("expected four Qwen3 modeled sites")
    rows=[]
    for site, c in zip(("P","CONTEXT","MID","U"), counts):
        width = {str(w):c.get(f"write_{w}bit",0) for w in (128,256,384,512)}
        if sum(width.values())!=c.get("write_beats",0):
            raise ValueError(f"physical write widths did not reconcile: {name}/{site}")
        serial = sum(int(w)//128*n for w,n in width.items())
        if any(width[str(w)] for w in (384,)) or 16*serial!=c.get("write_bytes",0):
            raise ValueError(f"unexpected write packing in {name}/{site}")
        rows.append({"site":site,"tlm_write_beats":width,"serialized_s128_writes":serial,
                     "ordinary_128bit_reads":c.get("read_128bit",0),
                     "bank_addressed_512bit_reads":c.get("read_512bit",0)})
    result["windows"][name]=rows
with out.open("x") as stream:
    json.dump(result,stream,indent=2)
    stream.write("\n")
