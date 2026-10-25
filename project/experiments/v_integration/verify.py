"""Independent symbolic receiver: validates addresses, provenance, global statistics and leases.
Does not import the planner and does not validate actual numerical values or hardware timing.
"""
import argparse
import gzip
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def keys(value, wanted):
    require(type(value) is dict and set(value) == set(wanted.split()), "exact schema: "+wanted)


def num(value):
    require(type(value) is int, "strict integer")
    return value


def layout_result(p):
    regions = p["regions"]
    require(type(regions) is list and regions, "regions")
    errors = []
    names = set()
    by_phase = {}
    for r in regions:
        keys(r, "name start bytes live")
        require(type(r["name"]) is str and type(r["live"]) is list and all(type(v) is str for v in r["live"]), "region strings")
        if r["name"] in names:
            errors.append("duplicate region name")
        names.add(r["name"])
        start, size = num(r["start"]), num(r["bytes"])
        if start < 0 or size < 1 or start+size > 16384:
            errors.append("out of bounds: "+r["name"])
        if start % 16 or size % 16:
            errors.append("alignment: "+r["name"])
        if not r["live"] or len(set(r["live"])) != len(r["live"]):
            errors.append("invalid lifetime: "+r["name"])
        for phase in r["live"]:
            by_phase[phase] = by_phase.get(phase, 0)+size
    for i in range(len(regions)):
        a = regions[i]
        for b in regions[i+1:]:
            if any(phase in b["live"] for phase in a["live"]) and a["start"] < b["start"]+b["bytes"] and b["start"] < a["start"]+a["bytes"]:
                errors.append("live overlap: "+a["name"]+"/"+b["name"])
    return {"valid": not errors, "errors": errors, "active_bytes_by_phase": by_phase}


def verify_trace(trace, p, cfg):
    require(layout_result(p)["valid"], "invalid physical layout")
    h, tile = num(p["h"]), num(p["tile"])
    require(h in (1536, 2560) and tile in (256, 1408, 1536) and h % 4 == tile % 4 == 0, "bounded shape")
    require(p["mode"] in ("resident", "stream"), "mode")
    n, t = h//4, tile//4
    regions = {r["name"]: r for r in p["regions"]}
    require(regions["XY"]["bytes"] >= 4*(h if p["mode"] == "resident" else tile), "X capacity")
    require(regions["G"]["bytes"] >= 4*tile, "gamma capacity")
    if p["frame_active"]:
        require(regions["V"]["bytes"] == 512, "frame capacity")
    store, stats, output, computed = {}, set(), set(), set()
    g_loaded, g_used, held = set(), set(), {}
    pending_ext = None
    den, done, next_gamma = False, False, 0
    counts = Counter()
    for event in trace:
        require(type(event) is list and not done, "event after DONE/type")
        if event[0] == "C":
            require(len(event) >= 3 and all(type(v) is int for v in event[2:]), "control schema")
            if event[1] == "DEN":
                require(event == ["C", "DEN", h] and not den and stats == set(range(n)) and not held and pending_ext is None, "global H statistics barrier")
                den = True
            elif event[1] == "NORM":
                i = event[2]
                require(len(event) == 3 and den and held == {"X": i, "G": i} and i not in computed, "complete consumer line before publish")
                held = {"NORM": i}
                computed.add(i)
                g_used.add(i)
            elif event[1] == "GAMMA_RELEASE":
                first, length = next_gamma, min(t, n-next_gamma)
                expected = set(range(first, first+length))
                require(event == ["C", "GAMMA_RELEASE", first, length] and g_loaded == g_used == expected and expected <= output and not held and pending_ext is None, "gamma tile drained before release")
                g_loaded.clear()
                g_used.clear()
                next_gamma += length
            elif event[1] == "DONE":
                require(event == ["C", "DONE", h] and den and stats == output == computed == set(range(n)) and next_gamma == n and not g_loaded and not held and pending_ext is None, "complete publish/drain")
                done = True
            else:
                raise ValueError("unknown control")
            continue
        require(len(event) == 6, "memory event schema")
        bus, op, addr, obj, i, phase = event
        num(addr); num(i)
        require(bus in ("S", "E") and op in ("R", "W") and obj in ("X", "G", "Y") and 0 <= i < n and addr % 16 == 0, "memory event domain")
        require(type(phase) is str, "phase type")
        counts[bus+"_"+op] += 1
        if bus == "E":
            require(addr == cfg["structural_input_addresses"][obj]+16*i, "external exact source/output address")
            if op == "R":
                require(obj in ("X", "G") and pending_ext is None, "finite external response holder")
                require(phase in ("load_x", "load_stats_x", "load_output_x", "load_gamma"), "load phase")
                pending_ext = (obj, i, phase)
            else:
                require(obj == "Y" and phase == "egress" and held == {"EGRESS": i} and i not in output, "drain exact Y before next overwrite")
                held.clear()
                output.add(i)
            continue
        region = regions["G" if obj == "G" else "XY"]
        offset = i % t if obj == "G" or p["mode"] == "stream" else i
        require(addr == region["start"]+16*offset and region["start"] <= addr < region["start"]+region["bytes"] and addr+16 <= 16384, "exact resident/tile address; no frame/A/guard access")
        if op == "W":
            if obj in ("X", "G"):
                require(pending_ext == (obj, i, phase), "write needs same source response")
                pending_ext = None
                old = store.get(addr)
                if old and old[0] == "X":
                    require(old[1] in stats, "do not overwrite X before global statistics consumed")
                if old and old[0] == "Y":
                    require(old[1] in output, "do not overwrite Y before drain")
                if obj == "G":
                    require(den and next_gamma <= i < min(next_gamma+t, n) and i not in g_loaded, "gamma input credit and sequential tile lease")
                    g_loaded.add(i)
                else:
                    require(phase in ("load_x", "load_stats_x", "load_output_x"), "X load stage")
                store[addr] = (obj, i)
            else:
                require(phase == "output" and den and held == {"NORM": i}, "no early or stale Y")
                held.clear()
                store[addr] = ("Y", i)
        else:
            require(store.get(addr) == (obj, i), "read correct live symbolic line")
            if phase == "stats":
                require(obj == "X" and not den and i not in stats and not held, "one global statistics read per X line")
                stats.add(i)
            elif phase == "output":
                require(den and obj in ("X", "G") and obj not in held and set(held) <= {"X", "G"}, "finite output line registers")
                if obj == "G":
                    require(i in g_loaded and i not in g_used, "live gamma before use")
                held[obj] = i
            elif phase == "egress":
                require(obj == "Y" and not held and i in computed, "finite egress holder")
                held["EGRESS"] = i
            else:
                raise ValueError("unknown read phase")
    require(done, "missing DONE")
    # Independent closed forms include input staging, statistics, output and egress.
    expected = {"E_R": (3 if p["mode"] == "stream" else 2)*n, "E_W": n,
                "S_R": 4*n, "S_W": (4 if p["mode"] == "stream" else 3)*n}
    require(dict(counts) == expected, "all expected reads/writes; no missing reload cost")
    expected["external_transactions"] = expected["E_R"]+expected["E_W"]
    expected["external_payload_bytes"] = expected["external_transactions"]*16
    expected["prototype_wire_bytes"] = expected["external_transactions"]*80
    expected["store_operations"] = expected["S_R"]+expected["S_W"]
    expected["store_line_bytes"] = expected["store_operations"]*16
    return expected


def verify(folder, contract=HERE/"contract.json"):
    raw = (folder/"report.json").read_bytes()
    report = json.loads(raw)
    keys(report, "schema status source_commit contract_sha256 sources layouts traces exclusions")
    require(report["schema"] == "v-integration91-structure-v1" and report["status"] == "STRUCTURAL_ONLY_NOT_RTL", "evidence class")
    cfg = json.loads(contract.read_text(encoding="utf-8"))
    require(hashlib.sha256(contract.read_bytes()).hexdigest() == report["contract_sha256"], "contract SHA")
    require(cfg["schema"] == "v-integration91-contract-v1" and (cfg["store_bytes"], cfg["line_bytes"], cfg["external_transaction_beats"], cfg["external_beat_bytes"]) == (16384, 16, 5, 16), "physical inventory")
    require(report["exclusions"] == cfg["notes"], "no removed scope exclusions")
    require(len(report["source_commit"]) == 40 and len(report["sources"]) >= 18, "source binding")
    seen = set()
    for s in report["sources"]:
        keys(s, "path bytes sha256")
        require(s["path"] not in seen and not Path(s["path"]).is_absolute() and ".." not in Path(s["path"]).parts, "source name")
        seen.add(s["path"])
        data = subprocess.check_output(["git", "show", report["source_commit"]+":"+s["path"]], cwd=ROOT)
        require(len(data) == num(s["bytes"]) and hashlib.sha256(data).hexdigest() == s["sha256"], "original Git source bytes")
    require("project/experiments/v_integration/verify.py" in seen and "project/experiments/v_integration/contract.json" in seen, "receiver and contract bound")
    contract_source = next(s for s in report["sources"] if s["path"] == "project/experiments/v_integration/contract.json")
    require(contract_source["sha256"] == report["contract_sha256"], "source/config identity")
    require(set(report["layouts"]) == {p["id"] for p in cfg["profiles"]}, "exact layout cohort")
    require(set(report["traces"]) == {p["id"] for p in cfg["profiles"] if "mode" in p}, "exact trace cohort")
    for p in cfg["profiles"]:
        expected = layout_result(p)
        require(type(p["expect_valid"]) is bool and expected["valid"] == p["expect_valid"] and report["layouts"][p["id"]] == expected, "layout independent receipt")
        if "mode" not in p:
            continue
        item = report["traces"][p["id"]]
        keys(item, "path bytes sha256 events counters")
        require(item["path"] == p["id"]+".jsonl.gz", "trace path")
        data = (folder/item["path"]).read_bytes()
        require(len(data) == num(item["bytes"]) and hashlib.sha256(data).hexdigest() == item["sha256"], "trace byte SHA")
        trace = [json.loads(line) for line in gzip.decompress(data).splitlines()]
        require(len(trace) == num(item["events"]), "event count")
        expected_counters = verify_trace(trace, p, cfg)
        require(type(item["counters"]) is dict and all(type(v) is int for v in item["counters"].values()) and item["counters"] == expected_counters, "reported counters independently reconstructed")
    return {"schema": "v-integration91-receipt-v1", "status": "PASS_STRUCTURAL_ONLY",
            "report_sha256": hashlib.sha256(raw).hexdigest(), "source_commit": report["source_commit"],
            "original_git_sources": len(seen), "layouts": len(report["layouts"]), "traces": len(report["traces"]),
            "scope": "addresses/lifetimes/line provenance/finite symbolic holders/global H barrier and transaction accounting; no numerics, RTL, cycles or PPA"}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    require(not a.out.exists(), "receipt must be new")
    result = verify(a.folder)
    a.out.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps(result))
