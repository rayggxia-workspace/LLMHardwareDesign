"""Screen uniform upper-layer wire load against true C/U cell limits."""
import json
import math
from pathlib import Path
import re
import sys

base=Path(sys.argv[1])
case=Path(sys.argv[2])
route=json.loads(case.read_text())["routes"]
mappings={}
for block in ("C","U","P") if len(sys.argv)>3 else ("C","U"):
    folder=base/f"{block}16"
    output=Path(sys.argv[3]) if block=="P" else folder/"6_final.v"
    liberty=((base/"C16" if block=="P" else folder)/"NangateOpenCellLibrary_typical.lib").read_text()
    assert re.search(r"capacitive_load_unit\s*\(\s*1,ff\s*\)",liberty)
    cells=re.split(r"\bcell\s*\(\s*(\w+)\s*\)",liberty)
    cell_limits={}
    for cell,body in zip(cells[1::2],cells[2::2]):
        pins=re.split(r"(?<!_)\bpin\s*\(\s*(\w+)\s*\)",body)
        for pin,properties in zip(pins[1::2],pins[2::2]):
            limit=re.search(r"max_capacitance\s*:\s*([0-9.]+)",properties)
            if limit and re.search(r"direction\s*:\s*output",properties):
                cell_limits[cell,pin]=float(limit[1])
    active=None
    found={}
    with output.open() as src:
        for line in src:
            header=re.match(r"^\s+(\w+)\s+[^\s]+\s+\(",line)
            if header:
                active=header[1]
            port=re.search(r"\.(\w+)\((tx_data\[\d+\]|tx_valid|rx_ready|rx_stored|m_to_g_data\[\d+\]|m_to_g_valid|g_from_m_take)\)",line)
            if port and (active,port[1]) in cell_limits:
                if port[2] in found:
                    raise ValueError(f"multiple output drivers for {port[2]}")
                found[port[2]]=(active,port[1],cell_limits[active,port[1]])
            if ");" in line:
                active=None
    mappings[block]=found

c_per_um=0.0088541878128*3.9*(2/0.8+2*2/2)
results={}
for net,entry in route.items():
    if net.startswith('p_gate') and 'P' not in mappings:
        continue
    if net.startswith('p_gate'):
        suffix=net.rsplit('_',1)[1]
        driver='P'
        port={'valid':'m_to_g_valid','take':'g_from_m_take'}.get(suffix,f'm_to_g_data[{suffix}]')
    else:
        origin,destination,service,*tail=net.split('_')
        driver=origin[0] if service in ("data","valid") else destination[0]
        port=f"tx_data[{tail[0]}]" if service=="data" else {
            "valid":"tx_valid","ready":"rx_ready","stored":"rx_stored",
        }[service]
    cell,pin,limit=mappings[driver][port]
    length=sum(abs(p[0]-q[0])+abs(p[1]-q[1]) for _,p,q in entry["segments"])/2000
    source=entry['segments'][0][1]
    dest=entry['segments'][-2][1]
    shortest=sum(abs(a-b) for a,b in zip(source,dest))/2000
    c=length*c_per_um
    results[net]=dict(driver_block=driver,length_um=length,manhattan_um=shortest,minimum_wire_ff=shortest*c_per_um,uniform_wire_ff=c,driver_cell=cell,driver_pin=pin,
                      max_capacitance_ff=limit,wire_only_ratio=c/limit)
out=case.with_name(case.stem+"-load.json")
out.write_text(json.dumps(dict(c_ff_per_um=c_per_um,results=results),indent=2))
print(len(results),sum(v["wire_only_ratio"]>1 for v in results.values()),
      max(results.items(),key=lambda entry:entry[1]["wire_only_ratio"]))
