"""Check that a detailed abstract changes OBS granularity, not macro pins/size."""
import hashlib
import json
import os
from pathlib import Path
import re

root = Path.cwd()
original = Path(os.environ["LLHD_BLOCK"]) / "flow/results/nangate45/llhd_vec_original/base"
view = Path(os.environ["LLHD_MACRO_VIEW"])


def parse(path):
    pins, current, obs = {}, None, {}
    dimensions = None
    in_obs, layer = False, None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for raw in stream:
            digest.update(raw)
            line = " ".join(raw.decode().split())
            if line.startswith("SIZE "):
                dimensions = line
            if line.startswith("PIN "):
                current = line.split()[1]
                pins[current] = []
            elif current is not None:
                if line == "END " + current:
                    current = None
                else:
                    pins[current].append(line)
            if line == "OBS":
                in_obs = True
            elif in_obs and line.startswith("LAYER "):
                layer = line.split()[1]
                obs.setdefault(layer, 0)
            elif in_obs and line.startswith("RECT "):
                obs[layer] += 1
    return dimensions, pins, obs, digest.hexdigest()


old = parse(original / "vec_engine.lef")
new = parse(view / "vec_engine.lef")
assert old[0] == new[0], "macro dimensions changed"
assert old[1] == new[1], "macro pin geometry/direction/use changed"
assert {"VDD", "VSS"} <= set(new[1])
assert set(old[2]) <= set(new[2]), "occupied obstruction layer disappeared"
assert all(new[2][layer] > 0 for layer in old[2])
assert sum(new[2].values()) > sum(old[2].values()), "detailed OBS were not produced"
lib_hash = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert lib_hash(original / "vec_engine_typ.lib") == lib_hash(view / "vec_engine_typ.lib")
report = {
    "pass": True,
    "kind": "H1 new detailed view and M10 power access, not H2 frozen base",
    "profile": os.environ["LLHD_MACRO_PDN"],
    "bloat_factor": 1 if os.environ["LLHD_MACRO_PDN"] == "guarded-m10" else 0,
    "source_odb": str(original / "6_final.odb"),
    "original_lef": str(original / "vec_engine.lef"),
    "detailed_lef": str(view / "vec_engine.lef"),
    "original_lef_sha256": old[3], "detailed_lef_sha256": new[3],
    "size_statement": new[0], "unchanged_pin_count": len(new[1]),
    "all_pin_geometry_direction_use_identical": True,
    "original_obstruction_rectangles_per_layer": old[2],
    "detailed_obstruction_rectangles_per_layer": new[2],
    "liberty_copied_byte_identical": True,
    "acceptance_note": "Detailed OBS retained on every occupied layer. Legal PG via access and route DRC require the new top flow; this view check alone does not prove connectivity.",
}
(root / "macro-view-validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
