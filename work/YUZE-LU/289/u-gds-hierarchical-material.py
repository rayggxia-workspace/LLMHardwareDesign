"""Fast sufficient equality proof: identical child hierarchy and equal direct material."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import pya

paths = [Path(os.environ[key]).resolve() for key in ("GDS_COMPARE_A", "GDS_COMPARE_B")]
layouts = [pya.Layout(), pya.Layout()]
for layout, path in zip(layouts, paths):
    layout.read(str(path))
assert layouts[0].dbu == layouts[1].dbu
assert layouts[0].top_cell().name == layouts[1].top_cell().name
cells = [{cell.name: cell for cell in layout.each_cell()} for layout in layouts]
assert cells[0].keys() == cells[1].keys()
def references(cell):
    return Counter((inst.cell.name, str(inst.cplx_trans), str(inst.a), str(inst.b),
                    inst.na, inst.nb) for inst in cell.each_inst())

layer_ids = [{(info.layer, info.datatype): layer for layer in layout.layer_indexes()
              for info in [layout.get_info(layer)]} for layout in layouts]
keys = sorted(layer_ids[0].keys() | layer_ids[1].keys())
rows = []
for name in sorted(cells[0]):
    ca, cb = [catalog[name] for catalog in cells]
    assert references(ca) == references(cb), ("Instance references differ", name)
    for key in keys:
        regions = []
        for cell, ids in zip((ca, cb), layer_ids):
            regions.append(pya.Region(cell.shapes(ids[key])) if key in ids else pya.Region())
        if regions[0].is_empty() and regions[1].is_empty():
            continue
        delta = regions[0] ^ regions[1]
        rows.append(dict(cell=name, layer=key[0], datatype=key[1],
                         equal=delta.is_empty(), xor_area_um2=delta.area()*layouts[0].dbu**2))
    if name == layouts[0].top_cell().name:
        print(json.dumps([row for row in rows if row["cell"] == name]), flush=True)
passed = all(row["equal"] for row in rows)
source_hashes = {}
for path in paths:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    source_hashes[str(path)] = digest.hexdigest()
Path(os.environ["GDS_COMPARE_OUT"]).write_text(json.dumps(
    dict(passed=passed, source_sha256=source_hashes, rows=rows,
         scope="Exact child reference transforms and direct per-cell per-layer material XOR"), indent=2))
assert passed
