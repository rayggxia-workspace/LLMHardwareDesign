"""Rebase real PM boot image lengths and byte counts from all three energy windows."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys


replay,out=map(Path,sys.argv[1:])
expected={("local",352),("mother",240),("mother",272),("mother",1616)}
limits=json.loads((replay/"dma-windows.json").read_bytes())
representatives={}
counts={}
for stage,names in (("prefill",("prefill",)),("decode-live",("first_token","decode"))):
    directory=replay/f"{stage}-w4-tile128-pr272-combined"
    assets=directory/"assets"
    listing=(assets/"ddr-initial.tsv").read_text().splitlines()
    images={}
    for line in listing[1:]:
        address,size,filename=line.split(maxsplit=2)
        images[int(address)]=(int(size),Path(filename))
    events=json.loads((directory/"real-activity.json").read_bytes())["pm_events"]
    counters={name:Counter() for name in names}
    for event in events:
        role,length=event["role"],event["image_bytes"]
        extent,file=images[event["address"]]
        if (role,length) not in expected or event["pm128"]!=length//16 or extent<((length+63)//64)*64:
            raise ValueError(f"unexpected PM image event: {event}")
        name=next(n for n in names if limits[n]["start_ps"]<=event["start_ps"]<limits[n]["end_ps"])
        counters[name][f"{role}-{length}"]+=1
        if (role,length) in representatives:
            continue
        if file.parent.resolve()!=assets.resolve() or file.stat().st_size!=extent:
            raise ValueError(f"PM image not bound to the frozen staged replay: {file}")
        data=file.read_bytes()
        key=f"{role}-{length}"
        for width,last in ((16,length),(64,((length+63)//64)*64)):
            (out/f"{key}.{8*width}.hex").write_text("".join(
                data[i:i+width][::-1].hex()+"\n" for i in range(0,last,width)))
        representatives[role,length]={"path":str(file),"address":event["address"],
                                      "effective_bytes":length,"padded_file_bytes":extent,
                                      "sha256":sha256(data).hexdigest()}
    counts.update(counters)
if set(representatives)!=expected:
    raise ValueError("not all real PM program lengths were captured")
(out/"pm-pages.json").write_text(json.dumps({
    "samples":{f"{role}-{length}":v for (role,length),v in representatives.items()}, "counts_by_window":counts,
},indent=2)+"\n")
