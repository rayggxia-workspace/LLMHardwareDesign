"""Bind P2545's real native leaf accesses in an interface-only assembly study."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import csv
import json
import re
import sys

root, audit, incidence, output = map(Path, sys.argv[1:])
read = lambda path: json.loads(path.read_bytes())
base = deepcopy(read(root / "native-dma-prerequisites-109781" / "base.json"))
facts = read(audit / "main-p-dma-access-report.json")
path = audit / "main-p-native-access.tsv"
assert base["views"]["P.odb"]["sha256"] == facts["main_p_odb_sha256"]
assert sha256(path.read_bytes()).hexdigest() == facts["main_p_endpoint_table_sha256"]
with incidence.open() as f:
    nets = {row["logical_pin"]: row for row in csv.DictReader(f, delimiter="\t")}
with path.open() as f:
    rows = [row for row in csv.DictReader(f, delimiter="\t") if row["family"] != "p_dma_desc"]
assert len(rows) == len(nets) == 770
added = Counter()
for assembly in base["assemblies"]:
    if assembly["views"].get("odb") != "P.odb":
        continue
    group = assembly["id"]
    dx, dy = assembly["translation_dbu"]
    for row in rows:
        pin = row["logical_pin"]
        net = nets[pin]
        assert row["native_net"] == net["net"] and row["direction"] == net["io"]
        assert int(net["bt_count"]) == 1 and int(net["has_wire"]) == 0
        fields = re.fullmatch(r"\{(\S+) (?:\{([^{}]+)\}|([^{} ]+)) (\d+) (\d+) (\d+) (\d+)\}", row["leaf_shapes"])
        if not fields:
            raise ValueError(f"expected a single leaf M10 shape at {pin}")
        instance, brace_pin, plain_pin, *rectangle = fields.groups()
        leaf_pin = brace_pin or plain_pin
        tcl_pin = f"{{{leaf_pin}}}" if brace_pin else leaf_pin
        assert net["all_nets_terminals"] == f"{{{instance} BLOCK {tcl_pin} {row['direction']}}}"
        endpoint = f"{group}/{pin}"
        term = f"{group}/{instance}/{leaf_pin}"
        assert endpoint not in base["endpoints"]
        base["endpoints"][endpoint] = {
            "assembly": group, "role": "driver" if row["direction"] == "OUTPUT" else "sink",
            "native_net": f"{group}/{net['net']}", "odb_term": term,
            "m10_shapes": [{"layer": "M10", "object": f"{term}/M10/0",
                            "rect_dbu": [int(value) + delta for value, delta in
                                         zip(rectangle, (dx, dy, dx, dy))]}],
        }
        added[group] += 1
assert len(added) == 3 and set(added.values()) == {770}
base["base_id"] += "-direct-p-m10-study"
out = {"base": base, "p_leaf_endpoints": dict(added), "physical_qualified": False,
       "scope": "actual M10 leaf endpoints in the placed P assemblies; upper access still to be routed"}
output.mkdir()
(output / "base.json").write_text(json.dumps(base, indent=2) + "\n")
summary_path = output / "summary.json"
summary_path.write_text(json.dumps(
    {key: value for key, value in out.items() if key != "base"}, indent=2) + "\n")
print(summary_path.read_text(), end="")
