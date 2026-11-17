"""Verify the recorded route, native reader pin tables and OASIS fingerprint."""
import argparse
from collections import Counter, defaultdict
import csv
import gzip
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/"engine"))
from check import verify


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return sha256(path.read_bytes()).hexdigest()


def nonoverlap(a,b):
    return min(a[2],b[2])<=max(a[0],b[0]) or min(a[3],b[3])<=max(a[1],b[1])


parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--reader-odb-dir", type=Path,
                    help="Optional directory containing C0/extended.odb and P2/extended.odb")
options=parser.parse_args()
case=root
manifest=read(case/"provenance.json")
for file,expected_hash in manifest["sha256"].items():
    assert sha(case/file)==expected_hash, file
placed=read(case/"placement.json")
receipt=read(case/"stream-receipt.json")
spec=read(case/"check/spec.json")
route=read(case/"check/route.json")
summary=read(case/"check/checks.json")
lower_bytes=gzip.decompress((case/"lower-overlay.json.gz").read_bytes())
lower=json.loads(lower_bytes)["by_terminal"]
assert spec["context"]["placement_sha256"]==sha(case/"placement.json")
assert spec["context"]["lower_overlay_sha256"]==sha256(lower_bytes).hexdigest()
assert spec["technology"]["bounds"]==placed["bounds_dbu"]
assert all(summary[k]==v for k,v in verify(spec,route).items())
assert (summary["nets_checked"],summary["via10_count"],summary["via11_count"])==(1049,2102,4221)
assert not route["failed"]
assert receipt["shape_round_trip"] and receipt["all_v10_cuts_enclosed_by_m10"]
assert receipt["checked_top_nets"]==1049 and receipt["verified_contact_count"]==2102
assert receipt["sha256"]==sha(case/"271-repacked-four-links-compact.oas")

branches=case/"check/connections.csv"
assert sha(branches)==summary["identical_branch_table_sha256"]
with branches.open(newline="") as f:
    rows=list(csv.DictReader(f))
assert len(rows)==1053 and {r["net"] for r in rows}==set(route["routes"])
assert {r["status"] for r in rows}=={"upper_geometry_checked"}
assert Counter(r["group"] for r in rows)=={k:v["checked"] for k,v in summary["by_group"].items()}
expected={(n["id"],n["driver"],s) for n in spec["nets"] for s in n["sinks"]}
assert {(r["net"],r["driver"],r["sink"]) for r in rows}==expected

boxes=placed["boxes_dbu"]
assert len(boxes)==14 and all(nonoverlap(a,b) for a,b in combinations(boxes.values(),2))
shapes=defaultdict(list)
for pin,items in lower.items():
    shapes[pin.split(".",1)[0]].extend(rect for _,rect in items)
for pin,rects in spec["pins"].items():
    shapes[pin.split(".",1)[0]].extend(rects)
for block,rects in shapes.items():
    assert all(nonoverlap(r,b) for r in rects for other,b in boxes.items() if other!=block)
    shapes[block]=[min(r[0] for r in rects),min(r[1] for r in rects),
                   max(r[2] for r in rects),max(r[3] for r in rects)]
assert all(nonoverlap(a,b) for a,b in combinations(shapes.values(),2))
for block in ("C0","P2"):
    reader=root/"readers"/block
    pos=read(reader/"reader-placement.json")
    name=pos["instance"]
    assert boxes[name]==pos["die_dbu"]==receipt["streamed_readers"][name]["die_dbu"]
    if options.reader_odb_dir is not None:
        odb=options.reader_odb_dir/block/"extended.odb"
        assert receipt["streamed_readers"][name]["odb_sha256"]==sha(odb)
    assert (reader/"reader.drc").stat().st_size==0
    x,y=pos["origin_dbu"]
    with (reader/"readback-reader.tsv").open(newline="") as f:
        pins=list(csv.reader(f,delimiter="\t"))
    assert len(pins)==206
    for pin,layer,a,b,c,d in pins:
        assert layer=="metal10"
        assert spec["pins"][f"{name}.{pin}"]==[[int(a)+x,int(b)+y,int(c)+x,int(d)+y]]
print("1,053 original branches and 1,049 compacted nets verified with 14 nonoverlapping instances.")
