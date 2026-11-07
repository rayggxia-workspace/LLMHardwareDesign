"""Join actual lower RC trees with a declared upper-layer pi model."""
from decimal import Decimal
import json
from pathlib import Path
import re
import sys


def stitch(original, target, links, variant):
    raw = original.read_text()
    if not re.search(r"(?m)^\*C_UNIT\s+1\s+PF$", raw) or not re.search(r"(?m)^\*R_UNIT\s+1\s+OHM$", raw):
        raise ValueError("unexpected OpenRCX units")
    entries = re.split(r"(?m)(^\*D_NET\s+\S+\s+\S+[^\S\n]*\n)", raw)
    header = entries[0]
    names = {}
    networks = {}
    aliases = {}
    for title,body in zip(entries[1::2], entries[2::2]):
        _,key,cap = title.split()
        connection, caps, resistors = re.fullmatch(
            r"\*CONN\s*\n(.*?)\*CAP\s*\n(.*?)\*RES\s*\n(.*?)\*END\s*",
            body, re.S).groups()
        ports = re.findall(r"(?m)^\*P\s+(\S+)\s+([IOB])(?:\s|$)", connection)
        for literal,direction in ports:
            name = re.sub(r"\\(.)", r"\1", literal)
            if name in names:
                raise ValueError(f"repeated SPEF port {name}")
            names[name] = key,literal,direction
        networks[key] = cap,connection,caps,resistors
    join = {}
    for link in links:
        source,literal_a,direction_a = names[link["source"]]
        sink,literal_b,direction_b = names[link["sink"]]
        if direction_a!="O" or direction_b!="I" or source in join or sink in join or source==sink:
            raise ValueError("invalid or shared stitched net")
        a,b = source+":999999901",source+":999999902"
        aliases.update({literal_a:a,literal_b:b})
        rc = link["rc"][variant]
        join[source] = sink,a,b,Decimal(str(rc["c_ff"]))/1000,Decimal(str(rc["r_ohm"]))
        join[sink] = None
    sink_ids = {row[0]:key for key,row in join.items() if row}

    def node(token):
        if token in aliases:
            return aliases[token]
        name, sep, suffix = token.partition(":")
        return sink_ids.get(name,name)+sep+suffix

    def records(lines):
        return [[node(v) for v in fields[1:-1]]+[fields[-1]]
                for line in lines.splitlines() if (fields:=line.split())]

    def numbered(rows):
        return "".join(f"{i} {' '.join(row)}\n" for i,row in enumerate(rows,1))

    def connections(text):
        return "".join(line+"\n" for line in text.splitlines()
                       if not (line.startswith("*P ") and line.split()[1] in aliases))

    def filtered_header():
        before,marker,ports = header.partition("*PORTS\n")
        if not marker:
            return header
        return before+marker+"".join(line for line in ports.splitlines(keepends=True)
                                    if not (line.split() and line.split()[0] in aliases))

    with target.open("w") as output:
        output.write(filtered_header())
        for key,(cap,pins,caps,res) in networks.items():
            if key in sink_ids:
                continue
            c, r = records(caps), records(res)
            pins = connections(pins)
            total = Decimal(cap)
            if key in join:
                other,a,b,extra,series = join[key]
                input_cap,input_pins,input_c,input_r = networks[other]
                if any(n in raw for n in (a,b)):
                    raise ValueError("stitched SPEF internal node collision")
                total += Decimal(input_cap)+extra
                pins += connections(input_pins)
                c += records(input_c) + [[a,str(extra/2)],[b,str(extra/2)]]
                r += records(input_r) + [[a,b,str(series)]]
            output.write(f"*D_NET {key} {total}\n*CONN\n{pins}*CAP\n{numbered(c)}"
                         f"*RES\n{numbered(r)}*END\n\n")
    return len(links)


if __name__ == "__main__":
    run, final = map(Path,sys.argv[1:3])
    links = json.loads((run/"binding.json").read_text())["connections"]
    pairs = "".join(f"{row['source']}\t{row['sink']}\n" for row in links)
    (run/"stitched-ports.tsv").write_text(pairs)
    for variant in ("base","high"):
        count = stitch(final/"6_final.spef",run/f"stitched-{variant}.spef",links,variant)
        print(f"{variant}: stitched {count} real two-sided parasitic trees")
