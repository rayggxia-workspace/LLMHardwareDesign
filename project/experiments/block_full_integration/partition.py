#!/usr/bin/env python3
"""Full original RTL hierarchy inventory; no physical or functional PASS claim.

plan: copy hash-locked complete inputs and emit Yosys script, without EDA.
elaborate: same preparation, then run existing Yosys/read_slang under Slurm.
The first version preserves actual child bodies and only assigns partition
ownership. Auxiliary netlist export/submod awaits the actual hierarchy JSON.
No original flow.py is imported or invoked; it would write original build/.
"""
import argparse
from collections import Counter
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import sys
import time

SCRIPT = Path(__file__).resolve()
DEFAULT_CONFIG = SCRIPT.parent / "configs" / "partition_cases.json"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda: f.read(1048576), b""):
            h.update(part)
    return h.hexdigest()


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def new_output(path, task_root):
    p = Path(path).absolute()
    if not p.parent.is_dir():
        raise ValueError("Output parent must already exist")
    for q in [p] + list(p.parents):
        if q.is_symlink():
            raise ValueError("Output ancestry contains a symlink: " + str(q))
    ancestors = [p.parent.resolve(strict=True)] + list(p.parent.resolve().parents)
    task_root = Path(task_root).absolute()
    for q in [task_root] + list(task_root.parents):
        if q.is_symlink():
            raise ValueError("Task root ancestry contains a symlink: " + str(q))
    root = task_root.resolve(strict=True)
    allowed = Path("/public/home/yuzelu/PingyangHuang").resolve(strict=True)
    if not root.is_dir() or allowed not in root.parents:
        raise ValueError("Task root must be an existing descendant of PingyangHuang")
    if root not in ancestors or root / "worktree" in ancestors:
        raise ValueError("Output must be in current task, outside worktree")
    if p.exists():
        raise FileExistsError("Refusing existing output: " + str(p))
    p.mkdir(mode=0o700)
    return p.resolve(strict=True)


def verify_inputs(case):
    records = case["sources"] + case["auxiliary_inputs"]
    seen = set()
    for r in records:
        rel = Path(r["relative_path"])
        if rel.is_absolute() or ".." in rel.parts or str(rel) in seen:
            raise ValueError("Unsafe/duplicate input relative path")
        seen.add(str(rel))
        p = Path(r["path"])
        if not p.is_file():
            raise FileNotFoundError("Required complete source missing: " + str(p))
        if p.stat().st_size != r["bytes"] or sha(p) != r["sha256"]:
            raise ValueError("Pinned source differs: " + str(p))
    recipe = case.get("recipe_evidence")
    if recipe and sha(recipe["path"]) != recipe["sha256"]:
        raise ValueError("Original elaboration recipe differs")
    return records


def yosys_path_token(path):
    # Actual jobs89954/89955 showed read_slang preserves literal quote characters
    # from a .ys script. Original successful flow.py uses unquoted path tokens.
    # Fail closed for paths needing unsupported quoting; this is NOT shell escape.
    text = str(path)
    if not re.fullmatch(r"[A-Za-z0-9_./+-]+", text):
        raise ValueError("Path cannot be represented as a safe Yosys token: " + text)
    return text


def prepare(config, cid, out):
    case = config["cases"][cid]
    records = verify_inputs(case)
    source_dir = out / "inputs"
    source_dir.mkdir()
    copied = []
    for r in records:
        dst = source_dir / r["relative_path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        with Path(r["path"]).open("rb") as src, dst.open("xb") as target:
            shutil.copyfileobj(src, target)
        if sha(dst) != r["sha256"]:
            raise ValueError("Copied source checksum differs")
        copied.append(dict(r, copied_path=str(dst)))
    known = {Path(r["relative_path"]) for r in records}
    incdirs = [Path(x) for x in case["include_dirs"]]
    for r in records:
        if r["role"] not in ("source", "included_source"):
            continue
        rel = Path(r["relative_path"])
        text = (source_dir / rel).read_text(encoding="utf-8")
        for included in re.findall(r'^\s*' + chr(96) + r'include\s+"([^"]+)"', text, re.M):
            if not any(p in known for p in [rel.parent / included] +
                       [d / included for d in incdirs]):
                raise ValueError("Unpinned include: " + included)
    command = ["read_slang"] + case["frontend_flags"] + ["--keep-hierarchy"]
    if case["filelist_mode"] == "copied_original":
        original = source_dir / case["original_filelist"]
        for line in original.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("//"):
                continue
            if line.startswith("+incdir+"):
                if line[8:] not in case["include_dirs"]:
                    raise ValueError("Unexpected filelist include directory")
            elif line not in {r["relative_path"] for r in case["sources"]}:
                raise ValueError("Unpinned/unsupported filelist entry: " + line)
        # Original filelist retained byte-for-byte, original relative paths work
        # because child CWD is the copied repository root.
        command += ["-f", yosys_path_token(original)]
    else:
        command += [yosys_path_token(source_dir / r["relative_path"]) for r in case["sources"]]
    command += ["--top", case["top"]]
    for name, value in case["parameters"].items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", name):
            raise ValueError("Invalid parameter identifier")
        command += ["-G", name + "=" + str(value)]
    script = "\n".join([
        " ".join(command), "hierarchy -check -top " + case["top"],
        "proc", "memory_collect",
        "write_rtlil " + yosys_path_token(out / "raw_hierarchy.il"),
        "write_json " + yosys_path_token(out / "raw_hierarchy.json"),
        "opt_expr", "opt_clean",
        "write_rtlil " + yosys_path_token(out / "post_cleanup.il"),
        "write_json " + yosys_path_token(out / "post_cleanup.json"),
        "check -assert", "stat",
        "write_rtlil " + yosys_path_token(out / "hierarchy.il"),
        "write_json " + yosys_path_token(out / "hierarchy.json"), ""])
    # Original checkpoints retained before expression cleanup; no flatten,
    # ABC, memory_map, retime, new blackboxing or interface renaming.
    with (out / "elaborate.ys").open("x", encoding="utf-8") as f:
        f.write(script)
    write_json(out / "input_manifest.json", {
        "case": cid, "top": case["top"], "source_base_commit": case["source_base_commit"],
        "parameters": case["parameters"], "frontend_flags": case["frontend_flags"],
        "inputs": copied, "recipe_evidence": case.get("recipe_evidence"),
        "source_lock_basis": config["source_lock_basis"],
        "expected_boundaries": case["expected_boundaries"],
        "allowed_original_storage_blackboxes": case["allowed_storage_blackboxes"],
        "new_functional_blackboxes": [], "elaboration": "NOT_RUN",
        "cleanup_passes": ["opt_expr", "opt_clean"], "raw_checkpoint_retained": True,
        "functional_equivalence": "NOT_RUN",
        "auxiliary_netlist_export": "NOT_RUN_NEEDS_ACTUAL_HIERARCHY_STEP2"})
    return copied, source_dir


def bool_attribute(v):
    if isinstance(v, str) and v and set(v) <= set("01"):
        return int(v, 2) != 0
    return bool(v)


def integer_parameter(v):
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v and set(v) <= set("01"):
        return int(v, 2)
    return None


def module_matches(name, module, expected):
    hdl = module.get("attributes", {}).get("hdlname", "")
    return any(n == expected or n.startswith(expected + "$") or
               n.endswith("\\" + expected)
               for n in [name.lstrip("\\")] + str(hdl).split())


def inventory(json_path, case, out):
    modules = json.loads(Path(json_path).read_text(encoding="utf-8"))["modules"]
    top = case["top"]
    if top not in modules:
        raise ValueError("Elaborated top absent")
    expected = {tuple(b["instance_path"]): b for b in case["expected_boundaries"]}
    if len(expected) != len(case["expected_boundaries"]):
        raise ValueError("Duplicate boundary instance")
    found, paths = {}, set()
    owners, kinds, states_by_owner, storage, boundary_counts = (Counter() for _ in range(5))
    seq_re = re.compile(r"^\$(?:adff|adffe|aldff|aldffe|dff|dffe|sdff|sdffe|sdffce|dffsr|dffsre|dlatch|adlatch|dlatchsr|sr|ff)(?:$|_)")
    allowed = set(case["allowed_storage_blackboxes"])
    unknown_blackboxes = []
    totals = {"state_records": 0, "init_records": 0}

    def emit(f, v):
        f.write(json.dumps(v, ensure_ascii=False, sort_keys=True) + "\n")

    with gzip.open(out / "hierarchy_instances.jsonl.gz", "wt", encoding="utf-8") as hi, \
         gzip.open(out / "partition_leaf_members.jsonl.gz", "wt", encoding="utf-8") as leaves, \
         gzip.open(out / "state_memory_sources.jsonl.gz", "wt", encoding="utf-8") as states:
        def walk(mn, path, owner, ancestry):
            if mn in ancestry:
                raise ValueError("Recursive module hierarchy")
            module = modules[mn]
            if module.get("processes") or module.get("memories"):
                raise ValueError("Unconverted processes/memories remain")
            for name, net in module.get("netnames", {}).items():
                if "init" in net.get("attributes", {}):
                    totals["init_records"] += 1
                    emit(states, {"record_kind": "initialized_net", "owner": owner,
                                  "module": mn, "instance_path": list(path),
                                  "name": name, "bits": net["bits"],
                                  "attributes": net["attributes"]})
            for cn, cell in module.get("cells", {}).items():
                cp, ct = path + (cn,), cell["type"]
                dotted = ".".join(cp)
                paths.add(dotted)
                sub, next_owner = modules.get(ct), owner
                for b in case["expected_boundaries"]:
                    if sub is not None and module_matches(ct, sub, b["rtl_module"]):
                        boundary_counts[b["id"]] += 1
                b = expected.get(cp)
                if b is not None:
                    if sub is None or not module_matches(ct, sub, b["rtl_module"]):
                        raise ValueError("Expected core type differs: " + dotted)
                    if bool_attribute(sub.get("attributes", {}).get("blackbox", 0)):
                        raise ValueError("Core unexpectedly blackboxed: " + dotted)
                    next_owner = b["id"]
                    actual = dict(sub.get("parameter_default_values", {}))
                    actual.update(cell.get("parameters", {}))
                    checks = {}
                    for key, want in b["expected_parameters"].items():
                        got = integer_parameter(actual.get(key))
                        if got is not None and got != want:
                            raise ValueError("Core parameter differs: " + dotted + "/" + key)
                        checks[key] = {"expected": want, "observed": got,
                                       "status": "MATCH" if got == want else "NOT_EXPORTED"}
                    if set(cell["connections"]) != set(sub.get("ports", {})):
                        raise ValueError("Boundary port set differs: " + dotted)
                    ports = {}
                    for pn, pd in sub["ports"].items():
                        conn = cell["connections"][pn]
                        if len(conn) != len(pd["bits"]):
                            raise ValueError("Boundary width differs: " + dotted + "/" + pn)
                        ports[pn] = {"direction": pd["direction"], "width": len(conn),
                                     "offset": pd.get("offset", 0), "upto": pd.get("upto", 0),
                                     "signed": pd.get("signed", 0),
                                     "child_module_local_bits": pd["bits"],
                                     "parent_module_local_bits": conn}
                    found[b["id"]] = {
                        "instance_path": list(cp), "actual_module": ct,
                        "rtl_module_expected": b["rtl_module"], "parent_module": mn,
                        "physical_master_candidate": b["physical_master_candidate"],
                        "parameters": actual, "parameter_checks": checks, "ports": ports,
                        "attributes": cell.get("attributes", {}),
                        "module_attributes": sub.get("attributes", {}),
                        "physical_macro_interface_equivalence": "NOT_RUN"}
                rec = {"instance_path": list(cp), "parent_module": mn,
                       "cell_name": cn, "type": ct, "owner": next_owner,
                       "parameters": cell.get("parameters", {}),
                       "attributes": cell.get("attributes", {})}
                if sub is not None and not bool_attribute(sub.get("attributes", {}).get("blackbox", 0)):
                    emit(hi, dict(rec, record_kind="module_instance"))
                    walk(ct, cp, next_owner, ancestry + (mn,))
                else:
                    if sub is not None:
                        cat = "original_storage_blackbox" if ct in allowed else "unknown_blackbox"
                        if cat == "unknown_blackbox":
                            unknown_blackboxes.append(dotted + ":" + ct)
                        else:
                            storage[next_owner] += 1
                    elif ct.startswith("$mem"):
                        cat = "memory_cell"
                    elif seq_re.match(ct):
                        cat = "sequential_cell"
                    elif ct.startswith("$"):
                        cat = "other_internal_cell"
                    else:
                        raise ValueError("Unknown non-internal leaf: " + ct)
                    full = dict(rec, category=cat, port_directions=cell.get("port_directions", {}),
                                connections=cell.get("connections", {}))
                    emit(leaves, full)
                    owners[next_owner] += 1
                    kinds[cat] += 1
                    if cat in ("memory_cell", "sequential_cell", "original_storage_blackbox"):
                        emit(states, full)
                        totals["state_records"] += 1
                        states_by_owner[next_owner] += 1
        walk(top, (), case["auxiliary_id"], ())

    missing = [b["id"] for b in case["expected_boundaries"] if b["id"] not in found]
    if missing:
        raise ValueError("Missing actual core boundaries: " + repr(missing))
    if any(boundary_counts[b["id"]] != 1 for b in case["expected_boundaries"]):
        raise ValueError("Additional/missing core instances: " + repr(dict(boundary_counts)))
    missing_scope = [p for p in case["coverage_requirements"] if p not in paths]
    if missing_scope:
        raise ValueError("Missing required auxiliary modules: " + repr(missing_scope))
    if unknown_blackboxes:
        raise ValueError("Unqualified functional blackboxes: " + repr(unknown_blackboxes[:20]))
    unresolved = [b + "/" + k for b, r in found.items()
                  for k, v in r["parameter_checks"].items() if v["status"] != "MATCH"]
    write_json(out / "boundary_interfaces.json", {
        "top": top, "boundaries": found, "top_ports": modules[top]["ports"],
        "bit_id_scope": "module local; join with instance path and module, not numeric ID alone",
        "parameter_not_exported": unresolved})
    write_json(out / "partition_inventory.json", {
        "status": "HIERARCHY_INVENTORY_COMPLETE_PARAMETERS_UNRESOLVED" if unresolved else "PASS_HIERARCHY_INVENTORY_ONLY",
        "top": top, "module_definitions": len(modules), "core_instance_counts": dict(boundary_counts),
        "leaf_owner_counts": dict(owners), "leaf_categories": dict(kinds),
        "state_or_memory_records": totals["state_records"],
        "state_or_memory_owner_counts": dict(states_by_owner),
        "original_storage_blackbox_counts": dict(storage), "initialized_net_records": totals["init_records"],
        "required_auxiliary_modules_seen": case["coverage_requirements"],
        "partition_assignment": "Every elaborated leaf belongs to the nearest selected core or auxiliary owner; no source graph transformation.",
        "auxiliary_partition": {"id": case["auxiliary_id"], "members": "partition_leaf_members.jsonl.gz",
                                "filter": {"owner": case["auxiliary_id"]},
                                "netlist_export": "NOT_RUN_NEEDS_ACTUAL_HIERARCHY_STEP2"},
        "parameter_not_exported": unresolved, "functional_equivalence": "NOT_RUN",
        "mapped_child_equivalence": "NOT_RUN", "physical_implementation": "NOT_RUN",
        "added_pipeline": "NOT_APPLICABLE_NO_PARTITION_TRANSFORM_YET",
        "limitations": [
            "Recognized RTLIL sequential and memory types are labeled; all other internal cells remain inventoried, never discarded.",
            "Original blackbox SRAM interfaces are not simulation models or transistor layouts.",
            "No submod, physical child replacement, or functional equivalence has run.",
            "Step2 must reflatten its result and compare full cells/parameters/bit connections/top aliases before claiming structural preservation."]})


def cleanup_audit(raw_path, cleaned_path, case, out):
    """Compare state/storage and selected core boundaries, not RTL equivalence.

    Only transparent $buf chains are normalized. Other changed driver identities
    stay explicit review items, even when a synthesis pass may prove constants.
    """
    raw = json.loads(Path(raw_path).read_text())["modules"]
    clean = json.loads(Path(cleaned_path).read_text())["modules"]
    state_re = re.compile(r"^\$(?:adff|adffe|aldff|aldffe|dff|dffe|sdff|sdffe|sdffce|dffsr|dffsre|dlatch|adlatch|dlatchsr|sr|ff)(?:$|_)")
    storage_types = set(case["allowed_storage_blackboxes"])
    detailed = []
    boundary_changes = []
    counts = {"before": 0, "after": 0}
    state_removed = []
    state_added = []
    state_changed = []

    def directions(cell, modules):
        return cell.get("port_directions") or {
            p: v["direction"] for p, v in modules.get(cell["type"], {}).get("ports", {}).items()}

    def state(cell):
        return bool(state_re.match(cell["type"])) or cell["type"].startswith("$mem") or cell["type"] in storage_types

    def resolver(module, modules):
        drivers, inputs, names, loads = {}, {}, {}, Counter()
        for pn, pd in module.get("ports", {}).items():
            for i, b in enumerate(pd["bits"]):
                if pd["direction"] in ("input", "inout"):
                    inputs.setdefault(b, []).append(("port", pn, i))
                if pd["direction"] in ("output", "inout"):
                    loads[b] += 1
        for nn, nd in module.get("netnames", {}).items():
            for i, b in enumerate(nd["bits"]):
                names.setdefault(b, []).append((nn, i))
        for cn, c in module.get("cells", {}).items():
            pd = directions(c, modules)
            for pn, bits in c["connections"].items():
                for i, b in enumerate(bits):
                    if pd.get(pn) in ("output", "inout"):
                        drivers.setdefault(b, []).append((cn, c["type"], pn, i))
                    if pd.get(pn) in ("input", "inout"):
                        loads[b] += 1
        cache = {}
        def get(b, active=()):
            if isinstance(b, str):
                return ("constant", b)
            if b in cache:
                return cache[b]
            if b in active:
                return ("buffer_alias_loop",)
            ds = drivers.get(b, [])
            if len(ds) == 1 and ds[0][1] == "$buf" and not inputs.get(b):
                cn, _, pn, index = ds[0]
                c = module["cells"][cn]
                if pn == "Y" and len(c["connections"].get("A", [])) == len(c["connections"].get("Y", [])):
                    value = get(c["connections"]["A"][index], active + (b,))
                    cache[b] = value
                    return value
            value = ("drivers", tuple(sorted(ds)), tuple(sorted(inputs.get(b, []))))
            if not ds and not inputs.get(b):
                value = ("undriven", tuple(sorted(names.get(b, []))))
            cache[b] = value
            return value
        return get, loads

    def signature(cell, resolve, modules):
        return {"type": cell["type"], "parameters": cell.get("parameters", {}),
                "port_directions": directions(cell, modules),
                "connections": {pn: [resolve(b) for b in bits]
                                for pn, bits in cell["connections"].items()}}

    for mn in sorted(set(raw) | set(clean)):
        a, b = raw.get(mn, {}), clean.get(mn, {})
        ar, aloads = resolver(a, raw)
        br, _ = resolver(b, clean)
        ac = {n: c for n, c in a.get("cells", {}).items() if state(c)}
        bc = {n: c for n, c in b.get("cells", {}).items() if state(c)}
        counts["before"] += len(ac)
        counts["after"] += len(bc)
        for cn in sorted(set(ac) | set(bc)):
            label = mn + "/" + cn
            if cn not in bc:
                state_removed.append(label)
                old = ac[cn]
                pd = directions(old, raw)
                uses = sum(aloads[x] for p, bits in old["connections"].items()
                           if pd.get(p) in ("output", "inout") for x in bits)
                detailed.append({"kind": "removed_state_or_memory", "module": mn, "cell": cn,
                                 "before": old, "output_local_load_count": uses,
                                 "reason_candidate": "NO_LOCAL_OUTPUT_LOAD" if not uses else "HAS_LOCAL_LOAD_REQUIRES_REVIEW",
                                 "removal_semantically_approved": False})
            elif cn not in ac:
                state_added.append(label)
                detailed.append({"kind": "added_state_or_memory", "module": mn, "cell": cn, "after": bc[cn]})
            elif signature(ac[cn], ar, raw) != signature(bc[cn], br, clean):
                state_changed.append(label)
                detailed.append({"kind": "changed_state_or_memory", "module": mn, "cell": cn,
                                 "before": ac[cn], "after": bc[cn],
                                 "before_normalized": signature(ac[cn], ar, raw),
                                 "after_normalized": signature(bc[cn], br, clean),
                                 "attributes": ac[cn].get("attributes", {}),
                                 "semantic_equivalence": "NOT_PROVEN"})
        for cn, old in a.get("cells", {}).items():
            sub = raw.get(old["type"])
            if not sub or not any(module_matches(old["type"], sub, x["rtl_module"])
                                  for x in case["expected_boundaries"]):
                continue
            new = b.get("cells", {}).get(cn)
            if new is None or signature(old, ar, raw) != signature(new, br, clean):
                boundary_changes.append(mn + "/" + cn)
                detailed.append({"kind": "changed_core_boundary_connections", "module": mn, "cell": cn,
                                 "before": old, "after": new})
        # Definitions may keep ports but change alias relationships. Preserve a
        # direct shape/parameter comparison and normalized endpoint comparison.
        if mn == case["top"] or any(module_matches(mn, a, x["rtl_module"])
                                    for x in case["expected_boundaries"]):
            def ports(m, resolve):
                return {pn: dict([(k, v) for k, v in pd.items() if k != "bits"] +
                                 [("normalized_bits", [resolve(x) for x in pd["bits"]])])
                        for pn, pd in m.get("ports", {}).items()}
            if ports(a, ar) != ports(b, br) or a.get("parameter_default_values", {}) != b.get("parameter_default_values", {}):
                boundary_changes.append(mn + "/<definition>")
                detailed.append({"kind": "changed_top_or_core_definition", "module": mn,
                                 "before_parameters": a.get("parameter_default_values", {}),
                                 "after_parameters": b.get("parameter_default_values", {}),
                                 "before_ports": ports(a, ar), "after_ports": ports(b, br)})

    with gzip.open(out / "cleanup_state_boundary_changes.jsonl.gz", "wt", encoding="utf-8") as f:
        for r in detailed:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    review = bool(state_removed or state_added or state_changed or boundary_changes)
    result = {
        "status": "REQUIRES_STATE_BOUNDARY_REVIEW" if review else "PASS_STATE_AND_CORE_BOUNDARY_IDENTITY_UNDER_BUFFER_ALIASES",
        "passes": ["opt_expr", "opt_clean"], "raw_sha256": sha(raw_path), "cleaned_sha256": sha(cleaned_path),
        "state_memory_definition_counts": counts,
        "removed_state_memory": state_removed, "added_state_memory": state_added,
        "changed_state_memory": state_changed, "changed_core_boundaries": boundary_changes,
        "changes": "cleanup_state_boundary_changes.jsonl.gz",
        "review_required": review,
        "count_scope": "module-definition cells; complete expanded instance ownership is separately inventoried",
        "raw_check_history": "Open job89957 reported4 loops in VPU branch-local lo/hi/ge/z after proc; source RTL bug is NOT established.",
        "functional_equivalence": "NOT_PROVEN",
        "limits": ["Only transparent $buf chains normalized; changed logic driver is never assumed equivalent.",
                   "All removed/changed state is listed with original source attributes; even zero-load removals require review.",
                   "Native check -assert must still pass after cleanup; this audit cannot override it."]}
    write_json(out / "cleanup_audit.json", result)
    return result


def local_expr_resolver(module, modules):
    """Conservative bit rewrites; never assume an arbitrary cell is combinational."""
    cells = module.get("cells", {})
    drivers, inputs = {}, {}
    for pn, pd in module.get("ports", {}).items():
        if pd["direction"] in ("input", "inout"):
            for i, b in enumerate(pd["bits"]):
                inputs.setdefault(b, []).append(("port", pn, i))
    for cn, c in cells.items():
        dirs = c.get("port_directions") or {p: v["direction"] for p, v in modules.get(c["type"], {}).get("ports", {}).items()}
        for pn, bs in c["connections"].items():
            if dirs.get(pn) in ("output", "inout"):
                for i, b in enumerate(bs):
                    if isinstance(b, int):
                        drivers.setdefault(b, []).append((cn, c["type"], pn, i))
    cache, rewrite = {}, {}
    def known(xs):
        if all(x[0] == "constant" and x[1] in ("0", "1") for x in xs):
            return sum(int(x[1]) << i for i, x in enumerate(xs))
        return None
    def extended(xs, n, signed):
        return (xs + [xs[-1] if signed and xs else ("constant", "0")] * max(0, n-len(xs)))[:n]
    def get(bit, active=frozenset()):
        if isinstance(bit, str):
            return ("constant", bit)
        if bit in cache:
            return cache[bit]
        ds, ins = drivers.get(bit, []), inputs.get(bit, [])
        anchor = ("drivers", tuple(sorted(ds)), tuple(sorted(ins)))
        if bit in active:
            return anchor
        if len(ds) != 1 or ins:
            cache[bit] = anchor
            return anchor
        cn, typ, pn, i = ds[0]
        c = cells[cn]
        con, par = c["connections"], c.get("parameters", {})
        if pn != "Y" or typ not in ("$buf", "$add", "$div", "$mod", "$mul", "$and", "$or", "$logic_and", "$logic_or", "$mux"):
            cache[bit] = anchor
            return anchor
        act = active | frozenset([bit])
        aa = [get(b, act) for b in con.get("A", [])]
        bb = [get(b, act) for b in con.get("B", [])]
        av, bv = known(aa), known(bb)
        original_aa = aa[:]
        n = len(con["Y"])
        signed = bool(integer_parameter(par.get("A_SIGNED", 0)) and integer_parameter(par.get("B_SIGNED", 0)))
        aa = extended(aa, n, signed)
        bb = extended(bb, n, signed)
        val, rule = anchor, None
        if typ == "$buf" and len(con.get("A", [])) == n:
            val, rule = aa[i], "transparent_buf"
        elif typ == "$add":
            if bv == 0:
                val, rule = aa[i], "add_zero_rhs"
            elif av == 0:
                val, rule = bb[i], "add_zero_lhs"
        elif typ == "$div" and bv and bv & (bv-1) == 0 and not integer_parameter(par.get("A_SIGNED", 0)) and not integer_parameter(par.get("B_SIGNED", 0)):
            shift = bv.bit_length()-1
            val, rule = (original_aa[i+shift] if i+shift < len(original_aa) else ("constant", "0")), "unsigned_divide_power_of_two"
        elif typ == "$mod" and bv and bv & (bv-1) == 0 and not integer_parameter(par.get("A_SIGNED", 0)) and not integer_parameter(par.get("B_SIGNED", 0)):
            val, rule = (aa[i] if i < bv.bit_length()-1 else ("constant", "0")), "unsigned_modulo_power_of_two"
        elif typ == "$mul" and (av == 0 or bv == 0):
            val, rule = ("constant", "0"), "two_state_product_zero"
        elif typ == "$mul" and av is not None and bv is not None and not signed:
            val, rule = ("constant", str(((av*bv) >> i) & 1)), "constant_unsigned_product_mod_width"
        elif typ in ("$and", "$or"):
            a, b = aa[i], bb[i]
            if typ == "$and":
                if a == ("constant", "0") or b == ("constant", "0"):
                    val, rule = ("constant", "0"), "bit_and_zero"
                elif a == ("constant", "1"):
                    val, rule = b, "bit_and_one"
                elif b == ("constant", "1"):
                    val, rule = a, "bit_and_one"
            else:
                if a == ("constant", "1") or b == ("constant", "1"):
                    val, rule = ("constant", "1"), "bit_or_one"
                elif a == ("constant", "0"):
                    val, rule = b, "bit_or_zero"
                elif b == ("constant", "0"):
                    val, rule = a, "bit_or_zero"
        elif typ in ("$logic_and", "$logic_or"):
            if typ == "$logic_and" and (av == 0 or bv == 0):
                val, rule = ("constant", "0"), "logical_and_zero"
            elif typ == "$logic_or" and ((av is not None and av != 0) or (bv is not None and bv != 0)):
                val, rule = ("constant", str(int(i == 0))), "logical_or_known_nonzero"
        elif typ == "$mux":
            ss = [get(b, act) for b in con.get("S", [])]
            sv = known(ss)
            if len(ss) == 1 and sv in (0, 1):
                val, rule = (bb if sv else aa)[i], "mux_known_select"
        if rule:
            rewrite.setdefault(cn, set()).add(rule)
        cache[bit] = val
        return val
    def output_cone(use_rewrites):
        todo = [b for p in module.get("ports", {}).values() if p["direction"] in ("output", "inout") for b in p["bits"]]
        visited_bits, visited_cells = set(), set()
        while todo:
            b = todo.pop()
            if not isinstance(b, int) or b in visited_bits:
                continue
            visited_bits.add(b)
            identity = get(b) if use_rewrites else ("drivers", tuple(drivers.get(b, [])), ())
            if identity[0] != "drivers":
                continue
            for cn, typ, pn, index in identity[1]:
                if cn in visited_cells:
                    continue
                visited_cells.add(cn)
                c = cells[cn]
                dirs = c.get("port_directions") or {p: v["direction"] for p, v in modules.get(c["type"], {}).get("ports", {}).items()}
                for ip, bs in c["connections"].items():
                    if dirs.get(ip) in ("input", "inout"):
                        todo.extend(bs)
        return visited_cells
    return get, output_cone, rewrite


def cleanup_attribution(raw, clean, changes):
    """Local output reachability and restricted arithmetic identities, not LEC."""
    grouped, records, cache = {}, [], {}
    def resolvers(mn):
        if mn not in cache:
            r = local_expr_resolver(raw[mn], raw)
            c = local_expr_resolver(clean[mn], clean)
            cache[mn] = (r, c, r[1](False), None)
        return cache[mn]
    for item in changes:
        kind, mn, cn = item["kind"], item["module"], item.get("cell")
        r, c, raw_cone, folded_cone = resolvers(mn)
        record = {"module": mn, "cell": cn, "kind": kind,
                  "source": item.get("before", {}).get("attributes", {}),
                  "semantic_scope": "module output/inout observability only; no hidden testbench hierarchical observation"}
        if kind == "removed_state_or_memory":
            if cn not in raw_cone:
                reason = "NO_RAW_GRAPH_PATH_TO_MODULE_OUTPUT"
            else:
                if folded_cone is None:
                    folded_cone = r[1](True)
                    cache[mn] = (r, c, raw_cone, folded_cone)
                reason = "NO_OUTPUT_PATH_AFTER_RESTRICTED_CONSTANT_REWRITES" if cn not in folded_cone else "UNRESOLVED_OUTPUT_PATH"
            record["attribution"] = reason
            record["type"] = item["before"]["type"]
            record["parameters"] = item["before"].get("parameters", {})
        elif kind == "changed_state_or_memory":
            before, after = item["before"], item["after"]
            base_same = all(before.get(k, {}) == after.get(k, {}) for k in ("type", "parameters", "port_directions"))
            pin_proofs = {}
            for pn in sorted(set(before["connections"]) | set(after["connections"])):
                av = [r[0](x) for x in before["connections"].get(pn, [])]
                bv = [c[0](x) for x in after["connections"].get(pn, [])]
                pin_proofs[pn] = {"width_before": len(av), "width_after": len(bv), "equal": av == bv,
                                 "before_expression_sha256": hashlib.sha256(json.dumps(av, sort_keys=True).encode()).hexdigest(),
                                 "after_expression_sha256": hashlib.sha256(json.dumps(bv, sort_keys=True).encode()).hexdigest()}
            reason = "ALL_STATE_PORTS_IDENTICAL_UNDER_RESTRICTED_REWRITES" if base_same and all(x["equal"] for x in pin_proofs.values()) else "UNRESOLVED_STATE_EXPRESSION"
            record.update(attribution=reason, type_parameters_directions_identical=base_same, pins=pin_proofs)
        else:
            record["attribution"] = "UNRESOLVED_NONSTATE_OR_BOUNDARY_CHANGE"
        grouped[record["attribution"]] = grouped.get(record["attribution"], 0) + 1
        records.append(record)
    rewrites = {mn: {cn: sorted(rules) for cn, rules in v[0][2].items()} for mn, v in cache.items()}
    return records, grouped, rewrites


def qualify_closed_hierarchy(path, case_id, task_root):
    p = Path(path).resolve(strict=True)
    root = Path(task_root).resolve(strict=True)
    if root not in p.parents or not p.is_dir():
        raise ValueError("Closed hierarchy must be inside the current task")
    e = p / "execution.json"
    data = json.loads(e.read_text())
    permitted = ("HIERARCHY_INVENTORY_COMPLETE_PARAMETERS_UNRESOLVED", "HIERARCHY_INVENTORY_COMPLETE", "HIERARCHY_COMPLETE_CLEANUP_REVIEW_REQUIRED")
    if data.get("case") != case_id or data.get("status") not in permitted or not data.get("inputs_unchanged"):
        raise ValueError("Hierarchy is not a closed usable input")
    if not data.get("commands") or any(x.get("returncode") != 0 for x in data["commands"]):
        raise ValueError("Hierarchy EDA did not complete successfully")
    wanted = ["hierarchy.json", "hierarchy.il", "partition_inventory.json", "boundary_interfaces.json", "input_manifest.json"]
    if (p / "raw_hierarchy.json").is_file():
        wanted += ["raw_hierarchy.json", "post_cleanup.json", "cleanup_audit.json", "cleanup_state_boundary_changes.jsonl.gz"]
    locked = {str(e): sha(e)}
    for name in wanted:
        fp = p / name
        actual = sha(fp)
        if data.get("output_sha256", {}).get(name) != actual:
            raise ValueError("Closed hierarchy output mismatch: " + name)
        locked[str(fp)] = actual
    return p, data, locked


def run_cleanup_review(args, case, config_path):
    if not args.hierarchy_run:
        raise ValueError("--hierarchy-run is required")
    src, prior, locked = qualify_closed_hierarchy(args.hierarchy_run, args.case, args.task_root)
    for name in ("raw_hierarchy.json", "post_cleanup.json", "cleanup_state_boundary_changes.jsonl.gz"):
        if str(src / name) not in locked:
            raise ValueError("Raw/cleaned cleanup evidence absent: " + name)
    out = new_output(args.out, args.task_root)
    receipt = {"case": args.case, "action": "review-cleanup", "status": "RUNNING",
               "source_execution_status": prior["status"], "source_files": locked,
               "script_sha256": sha(SCRIPT), "config_sha256": sha(config_path),
               "functional_equivalence": "NOT_PROVEN", "physical_equivalence": "NOT_RUN",
               "parameter_not_exported": json.loads((src / "partition_inventory.json").read_text())["parameter_not_exported"]}
    code = 1
    try:
        raw = json.loads((src / "raw_hierarchy.json").read_text())["modules"]
        clean = json.loads((src / "post_cleanup.json").read_text())["modules"]
        with gzip.open(str(src / "cleanup_state_boundary_changes.jsonl.gz"), "rt") as f:
            changes = [json.loads(l) for l in f]
        records, counts, rules = cleanup_attribution(raw, clean, changes)
        with gzip.open(str(out / "attributions.jsonl.gz"), "wt") as f:
            for record in records:
                f.write(json.dumps(record, sort_keys=True) + "\n")
        write_json(out / "restricted_rewrites.json", rules)
        receipt["counts"] = counts
        receipt["all_changes_attributed"] = not any(k.startswith("UNRESOLVED") for k in counts)
        receipt["scope"] = "Local unobservable state pruning and restricted two-state bit/arithmetic identities; not full RTL equivalence, not four-state/initial-state equivalence"
        receipt["limits"] = ["Module-local numeric bit IDs never compared across JSON files.",
                             "Symbolic data are binary (two-state hardware semantics); product-by-zero is not a four-state X-propagation proof.",
                             "Unknown changes fail closed; old cleanup receipt is never rewritten.",
                             "Deleted objects remain in the raw checkpoint and this explicit source-to-clean inventory.",
                             "Unexported parameter values remain unresolved."]
        receipt["status"] = "PASS_LIMITED_CLEANUP_ATTRIBUTION" if receipt["all_changes_attributed"] else "CLEANUP_ATTRIBUTION_INCOMPLETE"
        if any(sha(p) != h for p, h in locked.items()) or sha(SCRIPT) != receipt["script_sha256"] or sha(config_path) != receipt["config_sha256"]:
            raise ValueError("Input or running review code changed")
        receipt["inputs_unchanged"] = True
        code = 0 if receipt["all_changes_attributed"] else 2
    except Exception as exc:
        receipt.update(status="FAILED_CLEANUP_REVIEW", error=type(exc).__name__ + ": " + str(exc))
    receipt["output_sha256"] = {p.name: sha(p) for p in out.iterdir() if p.is_file()}
    write_json(out / "execution.json", receipt)
    print(json.dumps({"status": receipt["status"], "output": str(out)}))
    return code


def review_parameter_bindings(src, case, case_id, locked):
    """Check explicit locked SV binding syntax plus executed -G and elaborated evidence.
    This is deliberately a small recognizer, not a second SystemVerilog elaborator.
    """
    manifest = json.loads((src / "input_manifest.json").read_text())
    if manifest["parameters"] != case["parameters"]:
        raise ValueError("Actual hierarchy manifest parameters differ")
    script = src / "elaborate.ys"
    execution = json.loads((src / "execution.json").read_text())
    if sha(script) != execution["output_sha256"]["elaborate.ys"]:
        raise ValueError("Executed script identity mismatch")
    locked[str(script)] = sha(script)
    args = re.findall(r"(?:^|\s)-G\s*([A-Za-z_][A-Za-z0-9_]*)=([0-9]+)(?=\s|$)", script.read_text())
    if len(args) != len(dict(args)) or {k: int(v) for k, v in args} != case["parameters"]:
        raise ValueError("Actual read_slang -G parameter list differs")
    boundary = json.loads((src / "boundary_interfaces.json").read_text())
    modules = json.loads((src / "hierarchy.json").read_text())["modules"]
    source_records = {r["relative_path"]: r for r in manifest["inputs"]}
    excerpts = []
    def read(rel):
        r = source_records[rel]
        p = Path(r["copied_path"])
        if p.stat().st_size != r["bytes"] or sha(p) != r["sha256"]:
            raise ValueError("Copied SV source differs: " + rel)
        locked[str(p)] = r["sha256"]
        return p.read_text()
    def uncomment(text):
        return re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", lambda m: "\n" * m.group(0).count("\n"), text)
    def binding(text, typ, inst, rel):
        m = re.search(r"\b" + re.escape(typ) + r"\s*#\s*\((.*?)\)\s*" + re.escape(inst) + r"\s*\(", uncomment(text), re.S)
        if not m:
            raise ValueError("Explicit instance binding absent: " + inst)
        pattern = r"\.([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*([^()]*)\s*\)"
        found = re.findall(pattern, m.group(1))
        residue = re.sub(pattern, "", m.group(1)).replace(",", "").strip()
        if residue or len(found) != len(dict(found)):
            raise ValueError("Unsupported or duplicate binding expression: " + inst)
        excerpts.append({"source": rel, "instance": inst,
                         "line": uncomment(text)[:m.start()].count("\n") + 1, "text": m.group(0)})
        return {k: v.strip() for k, v in found}
    def literal(expr, env):
        expr = expr.strip()
        if expr in env:
            return env[expr]
        if re.fullmatch(r"[0-9]+", expr):
            return int(expr)
        m = re.fullmatch(r"(?:[0-9]+)?'([bBdDhH])([0-9a-fA-F_]+)", expr)
        if m:
            return int(m.group(2).replace("_", ""), {"b": 2, "d": 10, "h": 16}[m.group(1).lower()])
        raise ValueError("Unsupported parameter expression: " + expr)
    def default(text, name, rel):
        m = re.search(r"\bparameter\s+(?:int|bit)\s+" + re.escape(name) + r"\s*=\s*([^,\n)]+)", uncomment(text))
        if not m:
            raise ValueError("Required default absent: " + name)
        value = literal(m.group(1), {})
        excerpts.append({"source": rel, "parameter_default": name, "value": value,
                         "line": uncomment(text)[:m.start()].count("\n")+1, "text": m.group(0)})
        return value
    expected = {b["id"]: b["expected_parameters"] for b in case["expected_boundaries"]}
    actual, structural, widths = {}, {}, {}
    if case_id == "opentpu":
        top_rel, slice_rel = "rtl/asic/otpu_asic_top.sv", "rtl/top/otpu_slice.sv"
        top, slc = read(top_rel), read(slice_rel)
        env = dict(case["parameters"])
        for name in ("MXU_E", "SEQ_WC", "COLL_GATHER"):
            env[name] = default(top, name, top_rel)
        if (env["MXU_E"], env["SEQ_WC"], env["COLL_GATHER"]) != (0, 0, 1):
            raise ValueError("Selected default branch configuration changed")
        sb = binding(top, "otpu_slice", "u_slice", top_rel)
        # Every child-relevant parameter must be explicitly forwarded; no guessed defaults.
        needed = set(("SID", "S", "D", "MCOLS", "ACT_BLOCKS", "ACT_ROWS", "FIFO_DEPTH",
                      "ULANES", "MXU_IMPL", "MXU_CL", "MXU_E", "SEQ_WC"))
        child_env = {k: literal(sb[k], env) for k in needed}
        if child_env["SID"] != 0 or child_env["S"] != 1:
            raise ValueError("Complete small-case slice binding differs")
        for cid, typ, inst in [("act", "otpu_actram", "u_act"), ("mxu", "otpu_mxu", "u_mxu")]:
            cb = binding(slc, typ, inst, slice_rel)
            actual[cid] = {k: literal(cb[k], child_env) for k in expected[cid]}
        # Existing full elaboration must expose these independent width consequences.
        widths = {"act": {"r_data": 512, "r_scale": 128, "ren": 2, "we": 4},
                  "mxu": {"act_data": 512, "act_scale": 128, "b_rdata": 256,
                          "t_ren": 4, "t_rdata": 128, "pf_level": 7}}
        topcells = modules[case["top"]]["cells"]
        if "u_slice" not in topcells or "g_coll.u_coll" not in topcells:
            raise ValueError("Required one-slice and GATHER branch absent")
        if any("g_bar" in n for n in topcells):
            raise ValueError("Unexpected BAR-only collective branch")
        structural = {"actual_slice_instances": ["u_slice"], "actual_collective_branch": "g_coll.u_coll",
                      "source_default_MXU_E": 0, "source_default_SEQ_WC": 0,
                      "source_default_COLL_GATHER": 1,
                      "CL_parameter": child_env["MXU_CL"]}
    else:
        top_rel, gemm_rel = "rtl/llaccel_core.sv", "rtl/gemm_engine.sv"
        top, gemm = read(top_rel), read(gemm_rel)
        gb = binding(top, "gemm_engine", "u_gemm", top_rel)
        actual["gemm"] = {k: literal(gb[k], case["parameters"]) for k in expected["gemm"]}
        actual["vector"] = {}
        if not re.search(r"if\s*\(\s*EPILOGUE_FUSION\s*\)\s*begin\s*:\s*g_fusion", uncomment(gemm)):
            raise ValueError("Fusion generate condition changed")
        if not re.search(r"else\s+begin\s*:\s*g_nofusion", uncomment(gemm)):
            raise ValueError("Nonfusion source branch absent")
        gm = modules[boundary["boundaries"]["gemm"]["actual_module"]]
        names = list(gm.get("cells", {})) + list(gm.get("netnames", {}))
        active = [n for n in names if "g_nofusion." in n]
        inactive = [n for n in names if "g_fusion." in n]
        if not active or inactive:
            raise ValueError("Actual elaboration fusion branch differs")
        widths = {"gemm": {"instr": 512, "gemm_w_rdata": 2048, "gemm_a_rdata": 512, "gemm_wr_wstrb": 64},
                  "vector": {"instr": 512, "vec_rd0_rdata": 512, "vec_wr_wstrb": 64}}
        structural = {"actual_nonfusion_named_objects": len(active), "fusion_named_objects": len(inactive),
                      "external_SRAM_bodies_in_core": False}
    if actual != expected:
        raise ValueError("Actual source binding does not resolve expected parameters")
    checks = []
    for cid, ps in widths.items():
        ports = boundary["boundaries"][cid]["ports"]
        for name, width in ps.items():
            observed = ports[name]["width"]
            if observed != width:
                raise ValueError("Elaborated boundary width differs: " + cid + "/" + name)
            checks.append({"core": cid, "port": name, "actual_width": observed, "expected_width": width})
    return {"status": "PASS_SOURCE_BINDING_AND_ELABORATED_BOUNDARY_EVIDENCE",
            "method": "Executed exact -G arguments + pinned explicit SV parameter expressions/defaults + actual branch/port consequences",
            "resolved_core_parameters": actual, "executed_top_overrides": case["parameters"],
            "source_excerpts": excerpts, "elaborated_width_checks": checks,
            "elaborated_branch_checks": structural, "remaining": [],
            "json_parameter_metadata_still_absent": boundary["parameter_not_exported"],
            "limits": ["Does not fabricate missing read_slang JSON parameter fields.",
                       "Not a full behavioral equivalence or physical-hardmacro interface equivalence result.",
                       "Only these two pinned cases and literal/identifier parameter bindings are recognized."]}


def run_parameter_review(args, case, config_path):
    if not args.hierarchy_run:
        raise ValueError("--hierarchy-run is required")
    src, prior, locked = qualify_closed_hierarchy(args.hierarchy_run, args.case, args.task_root)
    out = new_output(args.out, args.task_root)
    receipt = {"case": args.case, "action": "review-parameters", "status": "RUNNING",
               "source_execution_status": prior["status"], "source_files": locked,
               "script_sha256": sha(SCRIPT), "config_sha256": sha(config_path),
               "functional_equivalence": "NOT_PROVEN", "physical_equivalence": "NOT_RUN"}
    code = 1
    try:
        evidence = review_parameter_bindings(src, case, args.case, locked)
        write_json(out / "resolved_parameter_evidence.json", evidence)
        if any(sha(p) != h for p, h in locked.items()) or sha(SCRIPT) != receipt["script_sha256"] or sha(config_path) != receipt["config_sha256"]:
            raise ValueError("Input or running review code changed")
        receipt["inputs_unchanged"] = True
        receipt["status"] = evidence["status"]
        code = 0
    except Exception as exc:
        receipt.update(status="FAILED_PARAMETER_REVIEW", error=type(exc).__name__ + ": " + str(exc))
    receipt["output_sha256"] = {p.name: sha(p) for p in out.iterdir() if p.is_file()}
    write_json(out / "execution.json", receipt)
    print(json.dumps({"status": receipt["status"], "output": str(out)}))
    return code


def stop_group(proc):
    if proc is None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    # The leader may have exited while descendants still hold files open.
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    if proc.poll() is None:
        proc.wait(timeout=5)


def termination_signal(signum, frame):
    raise RuntimeError("Termination signal " + str(signum))


def run_command(argv, cwd, env, out, label, timeout, memory_gib):
    start = time.monotonic()
    def bounded_child():
        previous = resource.getrlimit(resource.RLIMIT_AS)
        limit = int(memory_gib * 1024 ** 3)
        soft = min(limit, previous[0]) if previous[0] != resource.RLIM_INFINITY else limit
        resource.setrlimit(resource.RLIMIT_AS, (soft, previous[1]))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    proc = None
    with (out / (label + ".log")).open("x") as log:
        log.write("COMMAND " + json.dumps(argv) + "\n")
        log.flush()
        try:
            proc = subprocess.Popen(argv, cwd=str(cwd), env=env, stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True,
                                    preexec_fn=bounded_child)
            try:
                rc = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                rc = 124
        finally:
            # Also runs for SIGTERM/SIGINT-handler exceptions and failed waits.
            stop_group(proc)
    return {"argv": argv, "returncode": rc, "seconds": round(time.monotonic() - start, 3),
            "log": label + ".log", "log_sha256": sha(out / (label + ".log"))}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["plan", "elaborate", "review-cleanup", "review-parameters"])
    ap.add_argument("--case", required=True, choices=["opentpu", "llaccel"])
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--task-root", type=Path, required=True, help="Explicit current task root, independent of the driver snapshot path")
    ap.add_argument("--yosys", default="yosys")
    ap.add_argument("--plugin", default=None)
    ap.add_argument("--hierarchy-run", type=Path, help="Closed prior hierarchy run, never overwritten")
    ap.add_argument("--seconds", type=int, default=600)
    ap.add_argument("--max-as-gib", type=int, default=16)
    a = ap.parse_args()
    if not 1 <= a.seconds <= 1800 or not 1 <= a.max_as_gib <= 64:
        ap.error("Bounds: seconds1..1800, AS GiB1..64")
    if a.action == "elaborate" and not os.environ.get("SLURM_JOB_ID"):
        ap.error("Actual elaboration requires Slurm")
    config_path = a.config.resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported configuration schema")
    case = config["cases"][a.case]
    verify_inputs(case)
    if a.action == "review-cleanup":
        return run_cleanup_review(a, case, config_path)
    if a.action == "review-parameters":
        return run_parameter_review(a, case, config_path)
    out = new_output(a.out, a.task_root)
    status = {"schema_version": 1, "case": a.case, "action": a.action,
              "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "job_id": os.environ.get("SLURM_JOB_ID"), "task_root": str(a.task_root.resolve()), "status": "PREPARING",
              "script_sha256": sha(SCRIPT), "config_sha256": sha(config_path),
              "commands": [], "functional_verified": False, "physical_verified": False,
              "partition_netlist_exported": False}
    code = 1
    signal.signal(signal.SIGTERM, termination_signal)
    signal.signal(signal.SIGINT, termination_signal)
    try:
        copied, source_dir = prepare(config, a.case, out)
        env = os.environ.copy()
        for k, name in [("HOME", "home"), ("TMPDIR", "tmp"), ("TMP", "tmp"),
                        ("TEMP", "tmp"), ("XDG_CACHE_HOME", "cache")]:
            target = out / name
            target.mkdir(exist_ok=True)
            env[k] = str(target)
        env.update(PYTHONDONTWRITEBYTECODE="1", HISTFILE="/dev/null", OMP_NUM_THREADS="1")
        if a.action == "plan":
            status["status"] = "PLAN_READY_ELABORATION_NOT_RUN"
        else:
            exe = shutil.which(a.yosys)
            if not exe:
                raise FileNotFoundError("Existing Yosys not found: " + a.yosys)
            prefix = [exe] + (["-m", a.plugin] if a.plugin else [])
            status["tool"] = {"path": exe, "sha256": sha(exe), "plugin": a.plugin,
                              "plugin_sha256": sha(a.plugin) if a.plugin else None}
            for label, argv in [
                ("yosys-version", [exe, "-V"]),
                ("read-slang-help", prefix + ["-Q", "-T", "-p", "help read_slang"])]:
                rec = run_command(argv, source_dir, env, out, label, 30, a.max_as_gib)
                status["commands"].append(rec)
                if rec["returncode"]:
                    raise RuntimeError(label + " failed")
            help_text = (out / "read-slang-help.log").read_text(errors="replace")
            if "--keep-hierarchy" not in help_text:
                raise RuntimeError("Installed read_slang has no keep-hierarchy option")
            rec = run_command(prefix + ["-Q", "-T", "-s", str(out / "elaborate.ys")],
                              source_dir, env, out, "elaboration", a.seconds, a.max_as_gib)
            status["commands"].append(rec)
            audit = None
            if (out / "raw_hierarchy.json").is_file() and (out / "post_cleanup.json").is_file():
                audit = cleanup_audit(out / "raw_hierarchy.json", out / "post_cleanup.json", case, out)
                status["cleanup_review_required"] = audit["review_required"]
                status["cleanup_audit_status"] = audit["status"]
            if rec["returncode"]:
                raise RuntimeError("Yosys elaboration failed or timed out; diagnostic checkpoints retained if complete")
            if audit is None:
                raise RuntimeError("Required raw/cleaned checkpoint comparison missing")
            inventory(out / "hierarchy.json", case, out)
            status["status"] = json.loads((out / "partition_inventory.json").read_text())["status"]
            if audit["review_required"]:
                status["status"] = "HIERARCHY_COMPLETE_CLEANUP_REVIEW_REQUIRED"
        verify_inputs(case)
        if sha(SCRIPT) != status["script_sha256"] or sha(config_path) != status["config_sha256"]:
            raise RuntimeError("Running script/config changed")
        for r in copied:
            if sha(r["copied_path"]) != r["sha256"]:
                raise RuntimeError("Copied input changed")
        status["inputs_unchanged"] = True
        code = 0
    except Exception as exc:
        status["status"] = "FAILED_PREPARATION_OR_ELABORATION"
        status["error"] = type(exc).__name__ + ": " + str(exc)
        try:
            verify_inputs(case)
            status["inputs_unchanged"] = True
        except Exception:
            status["inputs_unchanged"] = False
    finally:
        status["output_sha256"] = {str(p.relative_to(out)): sha(p)
                                   for p in sorted(out.iterdir()) if p.is_file()}
        write_json(out / "execution.json", status)
    print(json.dumps({"status": status["status"], "output": str(out)}))
    return code


if __name__ == "__main__":
    sys.exit(main())
