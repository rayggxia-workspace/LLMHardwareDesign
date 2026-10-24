"""Independent finite-resource Issue68 service witness receiver.

This module never imports the producer DAG builder or scheduler. Half-open
resource calendars, allocation capacity and dependency lower bounds are checked
from the published witness. They are conditional cycles, not RTL or PPA.
"""
import argparse
from collections import Counter, defaultdict, deque
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import time


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def json_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_semantics(witness):
    task, config, nodes = witness["task"], witness["config"], witness["nodes"]
    require(task["precision"]["state_bits"] == config["state_bits"] and task["precision"]["decay_fraction"] == 31,
            "same exact integer task precision")
    require(task["numeric_quality_accepted"] is False, "service cannot assert numeric quality")
    require(witness["task_fingerprint"] == json_hash(task), "numeric task fingerprint")
    starts = [node for node in nodes if node["kind"] == "start"]
    require(len(starts) == 1 and starts[0]["meta"]["task_fingerprint"] == witness["task_fingerprint"], "task start fingerprint")
    verify_stream_dependencies(nodes)
    norm_counts, r_counts, guards, commits, aborts = Counter(), Counter(), Counter(), Counter(), Counter()
    rescale_counts, tile_guards, full_v, norm_barriers, finest_barriers, layout_count, matrix_count, initial_pack, scale_updates = (Counter() for _ in range(9))
    for node in nodes:
        m, kind = node["meta"], node["kind"]
        if m.get("stream") == "R" and m.get("operation") in ("initial_state_layout", "initial_state_pack_address"):
            require((m["rows"], m["row_bytes"], m["row_stride_bytes"], m["strided_source_base"])
                    == (128, config["tile"] * 4, 512, (m["head"] * 128 * 128 + m["tile"] * config["tile"]) * 4),
                    "actual row-major strided initial layout")
            if kind == "math":
                initial_pack[(m["head"], m["tile"])] += 1
        if m.get("stream") == "norm" and "row" in m:
            row = m["row"]
            require(type(row) is int and 0 <= row < task["norm_rows"], "full hidden row identity")
            if kind == "math":
                op = m["operation"]
                tile = m.get("tile", -1)
                if op in ("unit_min_scan", "align_max", "X16_RNE_square_sum", "norm_gamma", "fresh_A8K128"):
                    require(0 <= tile < 20, "norm H128 tile coverage")
                norm_counts[(row, op, tile)] += 1
            elif kind == "full_hidden_max":
                norm_barriers[row] += 1
            elif kind == "full_hidden_finest_unit":
                finest_barriers[row] += 1
            elif kind == "norm_source_layout_address":
                layout_count[(row, m["tile"])] += 1
            elif kind == "matrix_proxy":
                matrix_count[row] += 1
        if m.get("stream") != "R" or "token" not in m:
            continue
        t = m["token"]
        require(type(t) is int and 0 <= t < len(task["tokens"]), "R token identity")
        if kind == "fullV_head_output_barrier":
            require(m["heads"] == 2 and m["V"] == 128, "complete head output barrier")
            full_v[t] += 1
        if "attempt" not in m:
            continue
        at = m["attempt"]
        require(type(at) is int and 0 <= at < len(task["tokens"][t]["attempts"]), "R retry identity")
        expected = task["tokens"][t]["attempts"][at]
        rescaling = m.get("operation") in ("full_head_trial_RNE_shift1", "rescale_RNE_shift1") or kind == "trial_scale_epoch_update"
        if "scale_epoch" in m:
            require(m["scale_epoch"] == expected["epoch"] + int(rescaling), "causal task unit/epoch transition")
        if kind == "math":
            head, tile = m["head"], m["tile"]
            require(head in (0, 1) and 0 <= tile < 128 // config["tile"], "R complete heads/V tile coverage")
            op, chunk = m["operation"], m.get("chunk", -1)
            if rescaling:
                require(not expected["accepted"] and head in expected.get("rescale_heads", []), "only rejected bad head recode")
                rescale_counts[(t, at, head, tile)] += 1
            else:
                require(m["K"] == 128 and m["Vtile"] == config["tile"] and m["state_bits"] == config["state_bits"]
                        and m["complete_K"] is True and (m.get("decay_bits") == 31 or op == "new_state_completeK_output"), "full K typed recurrence")
                if "output" in op:
                    require(expected["accepted"], "no rejected proposal output work")
                r_counts[(t, at, head, tile, op, chunk)] += 1
        elif kind == "attempt_guard_barrier":
            require(m["accepted"] == expected["accepted"], "actual causal guard outcome")
            guards[(t, at)] += 1
        elif kind == "atomic_group_commit":
            require(expected["accepted"] and m["includes"] == ["state", "output", "units", "epoch", "version"], "complete atomic descriptor publication")
            commits[(t, at)] += 1
        elif kind == "abort_unpublished_generation":
            require(not expected["accepted"] and m["committed_state_unchanged"] is True, "unpublished rejection contract")
            aborts[(t, at)] += 1
        elif kind == "tile_guard_checked":
            tile_guards[(t, at, m["head"], m["tile"])] += 1
        elif kind == "trial_scale_epoch_update":
            require(m["heads"] == expected.get("rescale_heads", []) and m["published"] is False, "unpublished scale epoch update")
            scale_updates[(t, at)] += 1
    expected_norm = Counter()
    for row in range(task["norm_rows"]):
        for op in ("unit_min_scan", "align_max", "X16_RNE_square_sum", "norm_gamma", "fresh_A8K128"):
            for tile in range(20):
                expected_norm[(row, op, tile)] = 1
        for op in ("U64_den_sqrt_div", "FFN_requant_proxy", "attention_reduction_proxy"):
            expected_norm[(row, op, -1)] = 1
    require(norm_counts == expected_norm, "all rows complete hidden norm and same proxy work")
    require(norm_barriers == finest_barriers == matrix_count == Counter({row: 1 for row in range(task["norm_rows"])}), "full hidden reduction/matrix count")
    require(layout_count == Counter({(row, tile): 1 for row in range(task["norm_rows"]) for tile in range(20)}), "source code/unit layout address generation")
    require(initial_pack == Counter({(h, tile): 1 for h in range(2) for tile in range(128 // config["tile"])}), "all initial state packing")
    expected_r, expected_guards, expected_commits, expected_aborts, expected_rescales = Counter(), Counter(), Counter(), Counter(), Counter()
    fragments = 128 * config["tile"] // 256
    local_new = 128 * config["tile"] * (config["state_bits"] // 8) <= 8192
    for t, token in enumerate(task["tokens"]):
        require(token["attempts"], "one or more causal attempts")
        for at, attempt in enumerate(token["attempts"]):
            require(type(attempt["epoch"]) is int and attempt["epoch"] >= 0, "nonnegative integer epoch")
            if attempt["accepted"]:
                require(at == len(token["attempts"]) - 1, "no retry after accepted token")
                expected_commits[(t, at)] = 1
            else:
                expected_aborts[(t, at)] = 1
            expected_guards[(t, at)] = 1
            for head in range(2):
                for tile in range(128 // config["tile"]):
                    for op in ("decay_RNE_completeK_pred", "delta_beta_RNE"):
                        expected_r[(t, at, head, tile, op, -1)] = 1
                    if local_new:
                        expected_r[(t, at, head, tile, "outer_RNE_guard", -1)] = 1
                    else:
                        for chunk in range(fragments):
                            expected_r[(t, at, head, tile, "outer_RNE_guard_fragment", chunk)] = 1
                    if attempt["accepted"]:
                        expected_r[(t, at, head, tile, "new_state_completeK_output", -1)] = 1
            for head in attempt.get("rescale_heads", []):
                require(head in (0, 1) and not attempt["accepted"], "actual bad head identity")
                for tile in range(128 // config["tile"]):
                    expected_rescales[(t, at, head, tile)] = 1
    require(r_counts == expected_r, "complete recurrence operation inventory")
    require(guards == expected_guards and commits == expected_commits and aborts == expected_aborts,
            "guard/reject/commit event inventory")
    require(rescale_counts == expected_rescales, "full bad-head rescale inventory")
    require(tile_guards == Counter({(t, at, h, tile): 1 for t, tok in enumerate(task["tokens"]) for at in range(len(tok["attempts"]))
                                   for h in range(2) for tile in range(128 // config["tile"])}), "all tile guards")
    require(full_v == Counter({t: 1 for t, tok in enumerate(task["tokens"]) if any(at["accepted"] for at in tok["attempts"])}), "full V output before each commit")
    require(scale_updates == Counter({(t, at): 1 for t, tok in enumerate(task["tokens"]) for at, a in enumerate(tok["attempts"]) if a.get("rescale_heads")}), "all trial metadata updates")
    return dict(norm_rows=task["norm_rows"], R_tokens=len(task["tokens"]), R_attempts=sum(len(t["attempts"]) for t in task["tokens"]),
                task_fingerprint=witness["task_fingerprint"], commit_contract=task["commit_contract"])


def verify_witness(witness):
    require(witness["schema"] == "issue68-service/1", "service witness schema")
    capacities, sizes = verify_inventory(witness)
    slots = expected_slots(witness["config"])
    actual_slots = {a["id"]: (a["bank"], a["offset"], a["bytes"]) for a in witness["allocations"]}
    normalized = []
    for a in witness["allocations"]:
        require(a["lifetime"] == "whole schedule; conservative fixed slot", "resident memory lifetime")
        normalized.append(dict(name=a["id"], bank=a["bank"], bytes=a["bytes"], address=a["offset"], resident=[0, witness["makespan"]]))
    memory, names = verify_allocations(normalized, sizes, witness["makespan"])
    require(len(actual_slots) == len(witness["allocations"]) and actual_slots == slots,
            "all full-row/old/new/proxy/backing slots explicit")
    nodes = witness["nodes"]
    require([node["id"] for node in nodes] == list(range(len(nodes))), "complete topological node IDs")
    for node in nodes:
        verify_node_formula(node, witness["config"], slots)
    semantics = verify_semantics(witness)
    verify_transport(witness)
    calendar = verify_intervals(nodes, capacities)
    require(calendar["makespan"] == witness["makespan"], "published completion time")
    counters = Counter(node["kind"] for node in nodes)
    counters["payload_bytes"] = sum(node["meta"]["payload_bytes"] for node in nodes if node["kind"] == "packet")
    counters["wire_bytes"] = sum(node["meta"]["wire_bytes"] for node in nodes if node["kind"] == "packet")
    require(dict(counters) == witness["operation_counters"], "independent operation and transport totals")
    require(witness["producer_audit"]["resident_bytes"] == memory, "independent resident memory summary")
    return dict(status="PASS_INDEPENDENT_SERVICE_WITNESS", **semantics, **calendar, resident_bytes=memory,
                payload_bytes=counters["payload_bytes"], wire_bytes=counters["wire_bytes"],
                limitation="conditional conservative calendar and declared arithmetic lowering; no RTL/PPA or full-model performance")


def packet_key(m):
    return tuple(m.get(k) for k in ("stream", "row", "token", "attempt", "head", "tile", "chunk", "operation",
                                     "src", "dst", "src_object", "dst_object"))


def verify_transport(witness):
    """Check all required payloads, full clone, old/new generations and output offsets."""
    c, task, nodes = witness["config"], witness["task"], witness["nodes"]
    expected = {}
    observed = defaultdict(list)
    def expect(stream, src, dst, size, src_object, dst_object, operation=None, **fields):
        m = dict(stream=stream, src=src, dst=dst, src_object=src_object, dst_object=dst_object,
                 operation=operation, **fields)
        key = packet_key(m)
        require(key not in expected, "unique expected data movement")
        expected[key] = size
    expect("norm", "EXT", "S1", 10240, "backing.consumer_input", "source.gamma", "initial_gamma")
    for row in range(task["norm_rows"]):
        fields = dict(row=row)
        for tile in range(20):
            f = dict(fields, tile=tile)
            expect("norm", "EXT", "S0", 1024, "backing.consumer_input", "source.mixed", "load_mixed_code_plane", **f)
            expect("norm", "EXT", "S0", 256, "backing.consumer_input", "source.mixed", "load_mixed_unit_plane", **f)
            expect("norm", "S0", "V", 256, "source.mixed", "V.norm_tile", "unit_prepass", **f)
            expect("norm", "S0", "V", 1280, "source.mixed", "V.norm_tile", "max_scan", **f)
            if c["norm_route"] == "spill":
                expect("norm", "V", "S1", 1024, "V.norm_tile", "aligned.spill", "aligned_spill", **f)
                expect("norm", "S1", "V", 1024, "aligned.spill", "V.norm_tile", "read_aligned", **f)
            else:
                expect("norm", "S0", "V", 1280, "source.mixed", "V.norm_tile", "reread_mixed", **f)
            expect("norm", "S1", "V", 512, "source.gamma", "V.gamma_tile", "gamma_stream", **f)
        expect("norm", "V", "M", 2612, "V.A8", "M.proxy", "publish_fresh_A8", **fields)
        expect("norm", "S6", "M", 4096, "proxy.source", "M.proxy", "FFN_proxy_weight", **fields)
        expect("norm", "M", "V", 4096, "M.proxy", "V.proxy", "FFN_proxy_output", **fields)
        expect("norm", "V", "S7", 2048, "V.proxy", "proxy.result", "proxy_sink", **fields)
    expect("R", "EXT", "R", 2048, "backing.R_inputs", "R.aux", "initial_QKV_gate_metadata")
    n = 128 * c["tile"] * (c["state_bits"] // 8)
    for head in range(2):
        for tile in range(128 // c["tile"]):
            fields = dict(head=head, tile=tile)
            expect("R", "EXT", "R", n, "backing.raw_initial", "R.old", "initial_state_layout", **fields)
            expect("R", "R", "S3", n, "R.old", "R.stage_new", "initial_state_layout", **fields)
            expect("R", "S3", "EXT", n, "R.stage_new", "backing.model_old", "initial_state_layout", **fields)
    local = n <= 8192
    for t, token in enumerate(task["tokens"]):
        committed = "backing.model_old" if t % 2 == 0 else "backing.proposal"
        proposal = "backing.proposal" if t % 2 == 0 else "backing.model_old"
        expect("R", "EXT", "R", 2048, "backing.R_inputs", "R.aux", "token_QKV_gate_metadata", token=t)
        for at, attempt in enumerate(token["attempts"]):
            for head in range(2):
                for tile in range(128 // c["tile"]):
                    f = dict(token=t, attempt=at, head=head, tile=tile)
                    expect("R", "EXT", "S2", n, committed if at == 0 else "backing.trial", "R.stage_old", "page_committed_or_trial_old", **f)
                    expect("R", "S2", "R", n, "R.stage_old", "R.old", "load_old_tile", **f)
                    if not local:
                        for chunk in range(128 * c["tile"] // 256):
                            expect("R", "R", "S4", 256 * (c["state_bits"] // 8), "R.aux", "R.new_shadow", "shadow_fragment", **dict(f, chunk=chunk))
                    expect("R", "R" if local else "S4", "S3", n, "R.new" if local else "R.new_shadow", "R.stage_new", "stage_proposal", **f)
                    expect("R", "S3", "EXT", n, "R.stage_new", proposal, "write_uncommitted_backing_generation", **f)
                    if attempt["accepted"]:
                        expect("R", "EXT", "S2", n, proposal, "R.stage_old", "page_guarded_new_for_output", **f)
                        expect("R", "S2", "R", n, "R.stage_old", "R.old", **f)
                        expect("R", "R", "S5", c["tile"] * 8, "R.aux", "R.output", "uncommitted_output", **f)
            bad = attempt.get("rescale_heads", [])
            if bad and at == 0:
                for head in range(2):
                    for tile in range(128 // c["tile"]):
                        f = dict(token=t, attempt=at, head=head, tile=tile)
                        expect("R", "EXT", "S2", n, committed, "R.stage_old", "clone_full_committed_trial", **f)
                        expect("R", "S2", "EXT", n, "R.stage_old", "backing.trial", "clone_full_committed_trial", **f)
            for head in bad:
                for tile in range(128 // c["tile"]):
                    f = dict(token=t, attempt=at, head=head, tile=tile)
                    for src, dst, so, do in (("EXT", "S2", "backing.trial", "R.stage_old"),
                                            ("S2", "R", "R.stage_old", "R.old"),
                                            ("R", "S3", "R.old", "R.stage_new"),
                                            ("S3", "EXT", "R.stage_new", "backing.trial")):
                        expect("R", src, dst, n, so, do, "full_head_trial_RNE_shift1", **f)
    for node in nodes:
        if node["kind"] == "packet":
            m = node["meta"]
            observed[packet_key(m)].append((m["object_offset"], m["payload_bytes"]))
            if m.get("operation") == "uncommitted_output":
                require(m["dst_object_offset"] == (m["head"] * 128 + m["tile"] * c["tile"]) * 8,
                        "complete V/head output address placement")
            if m.get("operation") == "publish_fresh_A8":
                require((m["codes_bytes"], m["exponent_bytes"], m["descriptor_bytes"]) == (2560, 20, 32), "fresh A8 actual payload metadata")
        elif node["kind"] == "atomic_group_commit":
            m, t = node["meta"], node["meta"]["token"]
            committed = "backing.model_old" if t % 2 == 0 else "backing.proposal"
            proposal = "backing.proposal" if t % 2 == 0 else "backing.model_old"
            require((m["old_generation"], m["new_generation"]) == (committed, proposal), "atomic old/new backing pointer flip")
    require(set(observed) == set(expected), "complete physical dataflow inventory")
    for key, total in expected.items():
        remaining, wanted = total, []
        for offset in range(0, total, 1984):
            wanted.append((offset, min(1984, total - offset)))
        require(sorted(observed[key]) == wanted, "full payload coverage and packing")


def manifest(folder):
    folder = Path(folder)
    value = read_json(folder / "manifest.json")
    require(value.get("schema") == "issue68-service/1", "service manifest schema")
    checked = {}
    for name, wanted in value["artifacts"].items():
        require(not Path(name).is_absolute() and ".." not in Path(name).parts, "safe artifact name")
        path = folder / name
        checked[name] = dict(bytes=path.stat().st_size, sha256=sha(path))
        require(checked[name] == {k: wanted[k] for k in ("bytes", "sha256")}, "service artifact SHA/bytes " + name)
    require("metrics.json" in checked, "indexed service metrics")
    return value, checked


def original_manifest(folder, names=None):
    folder = Path(folder)
    value = read_json(folder / "manifest.json")
    require(value.get("status") == "PASS", "original execution source status")
    if names is not None:
        require(set(names) <= set(value["artifacts"]), "required selected original artifacts")
    for name, wanted in value["artifacts"].items():
        if names is not None and name not in names:
            continue
        path = folder / name
        require(not Path(name).is_absolute() and ".." not in Path(name).parts
                and dict(bytes=path.stat().st_size, sha256=sha(path)) == {k: wanted[k] for k in ("bytes", "sha256")},
                "original artifact SHA/bytes")
    return value, dict(bytes=(folder / "manifest.json").stat().st_size, sha256=sha(folder / "manifest.json"))


def source_tasks(root, range_root, norm_stage):
    """Rebuild task identity from numeric records, never from producer task fields."""
    root = Path(root)
    state_rows = read_json(root / "state01" / "state-results.json")
    norm_rows = read_json(root / norm_stage / "norm.json")
    state = next(r for r in state_rows if r["id"] == "evaluation.S32.D31")
    norm = next(r for r in norm_rows if r["id"] == "decode.tile16_delta_ACT8")
    _, state_manifest = original_manifest(root / "state01", {"state-results.json", state["artifact"]["name"]})
    _, norm_manifest = original_manifest(root / norm_stage, {"norm.json", "constants.npz", "decode.tile16_delta_ACT8.npz"})
    require(state["integer_steps"] == 32 and norm["rows"] == 32 and norm["hidden"] == 2560, "frozen numeric source tasks")
    static = dict(id="native32.S32D31.static", precision=state["format"],
        R_input_manifest=state_manifest, norm_input_manifest=norm_manifest,
        state_record_sha256=json_hash(state), norm_record_sha256=json_hash(norm),
        norm_rows=32, tokens=[dict(attempts=[dict(accepted=True, epoch=0)]) for _ in range(32)],
        commit_contract="saturating numeric reference, double-buffer group atomic commit",
        streams="independent norm32 captured decode rows and R32 capture; not a complete chained model", numeric_quality_accepted=False)
    tasks = {static["id"]: static}
    if range_root is None:
        return tasks
    rr = Path(range_root)
    range_rows = read_json(rr / "range-results.json")
    selected_range = [r for r in range_rows if r["id"] in ("native.evaluation.S32.D31.guard_rescale", "legacy.layer0-end8192.S32.D31.guard_rescale")]
    names = {"range-results.json"} | {r[k]["name"] for r in selected_range for k in ("artifact", "transaction_trace")}
    rm, rmd = original_manifest(rr, names)
    require(rm["schema"] == "issue68-range/1", "range numeric event schema")
    record_path = rr / "range-results.json"
    records_desc = dict(bytes=record_path.stat().st_size, sha256=sha(record_path))
    for record in range_rows:
        if record["id"] not in ("native.evaluation.S32.D31.guard_rescale", "legacy.layer0-end8192.S32.D31.guard_rescale"):
            continue
        td = record["transaction_trace"]
        trace = read_json(rr / td["name"])
        require(dict(bytes=(rr / td["name"]).stat().st_size, sha256=sha(rr / td["name"]))
                == {k: td[k] for k in ("bytes", "sha256")}, "actual numeric transaction artifact")
        tokens = []
        for token in trace["tokens"]:
            attempts = []
            for at in token["attempts"]:
                require(at["outcome"] != "ABORT_WIDTH", "unqualified width abort excluded")
                waves = [event for event in trace["rescale_events"] if event["token"] == token["token"] and event["after_attempt"] == at["attempt"]]
                require(len(waves) <= 1, "one causal recode wave per retry")
                attempts.append(dict(accepted=at["outcome"] == "COMMIT", epoch=at["epoch"], units=at["units"], guard_count=at["guard_count"],
                                     rescale_heads=waves[0]["heads"] if waves else [], source_attempt_sha256=json_hash(at)))
            tokens.append(dict(attempts=attempts, source_before=token["before"], source_commit=token.get("commit"), outcome=token["outcome"]))
        task = copy.deepcopy(static)
        task.update(id=record["id"], tokens=tokens, precision=record["format"], range_events=records_desc,
                    range_manifest=rmd, range_transaction=td, range_record_sha256=json_hash(record), source_range_cost=record["cost"],
                    R_original_source_artifact=record["source_artifact"], R_original_source_id=record["source_id"], R_role=record["role"],
                    commit_contract="causal guard/rescale, no failed-token publication, atomic state/output/units/epoch/version commit",
                    streams="independent actual norm32 stream and exact range R token events; R length may differ")
        # The producer freezes source descriptors separately for the actual role.
        role = record["role"]
        original_folder = Path(rm["source"][role]["path"])
        original_record = next(r for r in read_json(original_folder / "state-results.json") if r["id"] == record["source_id"])
        _, input_descriptor = original_manifest(original_folder, {"state-results.json", original_record["artifact"]["name"]})
        require(original_record["artifact"] == record["source_artifact"], "range original source artifact")
        task.pop("R_input_manifest")
        task.pop("state_record_sha256")
        tasks[task["id"]] = task
    return tasks


def ceil_div(value, denominator):
    require(value >= 0 and denominator > 0, "nonnegative service amount")
    return (value + denominator - 1) // denominator


def positive_int(value, label, zero=False):
    require(type(value) is int and value >= (0 if zero else 1), "integer domain " + label)
    return value


def verify_intervals(nodes, capacities):
    """Independent sweep and longest path. No scheduling or resource search."""
    by_id = {}
    for node in nodes:
        key = node["id"]
        require(key not in by_id, "unique operation ID")
        by_id[key] = node
        positive_int(node["start"], "start", zero=True)
        positive_int(node["duration"], "duration")
        require(node["end"] == node["start"] + node["duration"], "operation end/duration")
    children, pending = defaultdict(list), {}
    calendars, work = defaultdict(list), defaultdict(int)
    for node in nodes:
        require(len(node["deps"]) == len(set(node["deps"])), "duplicate dependency")
        pending[node["id"]] = len(node["deps"])
        for dep in node["deps"]:
            require(dep in by_id and dep != node["id"], "known non-self dependency")
            require(by_id[dep]["end"] <= node["start"], "dependency publication before use")
            children[dep].append(node["id"])
        for reservation in node["reservations"]:
            resource = reservation["resource"]
            require(resource in capacities, "declared resource")
            offset = positive_int(reservation["offset"], "offset", zero=True)
            duration = positive_int(reservation["duration"], "reservation duration")
            amount = positive_int(reservation["amount"], "reservation amount")
            require(offset + duration <= node["duration"], "reservation contained in operation")
            require(amount <= capacities[resource], "single reservation capacity")
            a = node["start"] + offset
            calendars[resource].extend(((a, amount), (a + duration, -amount)))
            work[resource] += duration * amount
    queue = deque(key for key, degree in pending.items() if degree == 0)
    longest, visited = {}, 0
    while queue:
        key = queue.popleft()
        node = by_id[key]
        longest[key] = node["duration"] + max((longest[dep] for dep in node["deps"]), default=0)
        visited += 1
        for child in children[key]:
            pending[child] -= 1
            if pending[child] == 0:
                queue.append(child)
    require(visited == len(nodes), "acyclic dependency graph")
    peaks = {}
    for resource, points in calendars.items():
        current, peak = 0, 0
        # End events precede starts at the same timestamp: [start,end).
        for when, delta in sorted(points, key=lambda item: (item[0], item[1])):
            current += delta
            require(0 <= current <= capacities[resource], "resource overlap/capacity " + resource)
            peak = max(peak, current)
        require(current == 0, "released resource credit " + resource)
        peaks[resource] = peak
    precedence = max(longest.values(), default=0)
    resource_lb = {key: ceil_div(value, capacities[key]) for key, value in work.items()}
    makespan = max((node["end"] for node in nodes), default=0)
    bound = max([precedence] + list(resource_lb.values()))
    require(makespan >= bound, "independent lower bound")
    return dict(makespan=makespan, precedence_lower_bound=precedence,
                resource_lower_bounds=resource_lb, lower_bound=bound,
                resource_work=dict(work), resource_peaks=peaks, operations=len(nodes))


def verify_allocations(allocations, bank_bytes, makespan):
    used = defaultdict(int)
    names, ranges = set(), defaultdict(list)
    for allocation in allocations:
        name, bank = allocation["name"], allocation["bank"]
        require(name not in names and bank in bank_bytes, "unique allocation/known bank")
        names.add(name)
        amount = positive_int(allocation["bytes"], "allocation bytes")
        require(allocation["resident"] == [0, makespan], "explicit persistent lifetime")
        used[bank] += amount
        if "address" in allocation:
            address = positive_int(allocation["address"], "allocation address", zero=True)
            require(address + amount <= bank_bytes[bank], "allocation address capacity")
            ranges[bank].append((address, address + amount))
    for bank, amount in used.items():
        require(amount <= bank_bytes[bank], "resident bank capacity " + bank)
        ordered = sorted(ranges[bank])
        require(all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])), "resident address overlap " + bank)
    return dict(used), names


def reservations_equal(actual, expected, label):
    require(Counter(json.dumps(v, sort_keys=True) for v in actual)
            == Counter(json.dumps(v, sort_keys=True) for v in expected), "complete reservation formula " + label)


def res(resource, offset, duration, amount=1):
    return dict(resource=resource, offset=offset, duration=duration, amount=amount)


def lane_partition(organization):
    if organization == "shared8":
        return 8, 8
    suffix = organization.removeprefix("shared").removeprefix("split")
    require(suffix in ("2_6", "4_4", "6_2"), "declared lane organization")
    return tuple(map(int, suffix.split("_")))


def verify_inventory(witness):
    inv, c = witness["inventory"], witness["config"]
    require(c["tile"] in (16, 32) and c["state_bits"] in (16, 32)
            and c["norm_route"] in ("reread", "spill") and c["ext_ii"] in (1, 16)
            and c["strategy"] in ("fifo", "critical"), "finite configuration domain")
    vl, rl = lane_partition(c["organization"])
    sizes = dict(V=16384, R=32768, M=32768, EXT=128 * 1024 * 1024,
                 **{"S" + str(i): 32768 for i in range(8)})
    require(inv["bank_sizes"] == sizes, "same complete SRAM/backing inventory")
    capacities = dict(BUS=1, SFU=1, CTRL=1, MATRIX=1)
    for bank in sizes:
        capacities["PORT:" + bank] = 1
        for direction in ("TX", "RX"):
            capacities["EP:" + bank + ":" + direction] = 1
            capacities["FIFO:" + bank + ":" + direction] = 2048
    capacities.update({"LANE:" + str(i): 1 for i in range(8)})
    require(inv["capacities"] == capacities and inv["bus_bits"] == 128
            and inv["total_S8_lanes"] == 8 and inv["V_lanes"] == vl and inv["R_lanes"] == rl,
            "same lane/SFU/bus/1RW/FIFO resources")
    require(inv["external_beat_cycles"] == c["ext_ii"] and inv["physical_claim"] is False,
            "conditional backing profile/PPA boundary")
    return capacities, sizes


def expected_slots(c):
    b, tile = c["state_bits"] // 8, c["tile"]
    n, model = 128 * tile * b, 24 * 32 * 128 * 128 * b
    slots = {
        "V.X16": ("V", 0, 5120), "V.gamma_tile": ("V", 5120, 512),
        "V.norm_tile": ("V", 5632, 2048), "V.meta": ("V", 7680, 1024),
        "V.A8": ("V", 8704, 2752), "V.proxy": ("V", 11456, 4096),
        "R.old": ("R", 0, n), "R.aux": ("R", 16384, 8192),
        "source.mixed": ("S0", 0, 25600), "source.meta": ("S0", 25600, 2048),
        "source.gamma": ("S1", 0, 10240), "aligned.spill": ("S1", 10240, 20480),
        "R.stage_old": ("S2", 0, 16384), "R.stage_new": ("S3", 0, 16384),
        "R.output": ("S5", 0, 2048), "proxy.source": ("S6", 0, 16384),
        "proxy.result": ("S7", 0, 16384), "M.proxy": ("M", 0, 32768),
        "backing.model_old": ("EXT", 0, model),
        "backing.proposal": ("EXT", model, 2 * 128 * 128 * b),
        "backing.trial": ("EXT", model + 2 * 128 * 128 * b, 2 * 128 * 128 * b),
        "backing.consumer_input": ("EXT", model + 4 * 128 * 128 * b, 32 * 25600 + 10240),
        "backing.R_inputs": ("EXT", model + 4 * 128 * 128 * b + 32 * 25600 + 10240, 256 * 2048),
        "backing.descriptor": ("EXT", model + 4 * 128 * 128 * b + 32 * 25600 + 10240 + 256 * 2048, 256),
        "backing.raw_initial": ("EXT", model + 4 * 128 * 128 * b + 32 * 25600 + 10240 + 256 * 2048 + 256, 2 * 128 * 128 * b),
    }
    if n <= 8192:
        slots["R.new"] = ("R", 8192, n)
    else:
        slots["R.new_shadow"] = ("S4", 0, n)
    return slots


def math_work(meta, config):
    """Declared scalar lowering, independently expanded from operation semantics."""
    op, tv, b = meta["operation"], config["tile"], config["state_bits"] // 8
    cells, digits = 128 * tv, 3 if b == 2 else 5
    def multiplication(a, b):
        partials = a * b
        return partials + (partials - 1) * 10
    if op == "align_max":
        return 128 * 20, 1280, 1024 if config["norm_route"] == "spill" else 16, 0
    if op == "unit_min_scan":
        return 128 * 10, 256, 16, 0
    if op == "X16_RNE_square_sum":
        if config["norm_route"] == "reread":
            return 128 * (20 + 10 + multiplication(3, 3) + 10), 1280 + 16, 256, 0
        return 128 * (10 + multiplication(3, 3) + 10), 1024 + 16, 256, 0
    if op == "U64_den_sqrt_div":
        return 100, 32, 16, 96
    if op == "norm_gamma":
        return 128 * (multiplication(3, 5) + multiplication(5, 5) + 20), 256 + 512 + 32, 512, 0
    if op == "fresh_A8K128":
        return 128 * 30, 512, 129, 0
    if op == "FFN_requant_proxy":
        return 1024 * 30, 4096, 1024, 0
    if op == "attention_reduction_proxy":
        return 1024 * 20, 4096, 1024, 64
    if op == "decay_RNE_completeK_pred":
        return cells * (multiplication(digits, 5) + multiplication(digits, 3) + 20) + tv * 10, cells * b + 512 + 16, cells * b + tv * 8, 0
    if op == "delta_beta_RNE":
        return tv * (multiplication(10, 3) + 30), tv * 16, tv * 8, 0
    if op == "outer_RNE_guard":
        return cells * (multiplication(3, 10) + 30), cells * b + tv * 8 + 256, cells * b, 0
    if op == "outer_RNE_guard_fragment":
        cc = min(256, cells - int(meta["chunk"]) * 256)
        require(cc > 0, "outer fragment range")
        return cc * (multiplication(3, 10) + 30), cc * b + tv * 8 + 256, cc * b, 0
    if op == "new_state_completeK_output":
        return cells * (multiplication(digits, 3) + 10) + tv * 10, cells * b + 256, tv * 8, 0
    if op == "rescale_RNE_shift1":
        return cells * 20, cells * b, cells * b, 0
    if op == "initial_state_pack_address":
        return cells * 10 + 128 * 10, cells * b, cells * b, 0
    raise AssertionError("unqualified math operation " + op)


def verify_node_formula(node, config, slots):
    meta, kind = node["meta"], node["kind"]
    if kind == "packet":
        src, dst, size = meta["src"], meta["dst"], meta["payload_bytes"]
        require(src != dst and 0 < size <= 1984, "packet route/payload bounds")
        require(meta["src_object"] in slots and meta["dst_object"] in slots, "allocated packet objects")
        require(slots[meta["src_object"]][0] == src and slots[meta["dst_object"]][0] == dst, "packet object/bank ownership")
        for direction in ("src", "dst"):
            offset = positive_int(meta[direction + "_offset"], direction + " object offset", zero=True)
            require(offset + size <= slots[meta[direction + "_object"]][2], "packet range inside finite slot")
        verify_packet_offsets(meta, config)
        rd = ceil_div(size, 16) * (config["ext_ii"] if src == "EXT" else 1)
        wire = ceil_div(size + 32, 16)
        wr = ceil_div(size, 16) * (config["ext_ii"] if dst == "EXT" else 1)
        duration = rd + wire + wr
        require(meta["wire_bytes"] == wire * 16, "physical packet/header padding")
        expected = [res("PORT:" + src, 0, rd), res("BUS", rd, wire), res("PORT:" + dst, rd + wire, wr)]
        for bank, direction in ((src, "TX"), (dst, "RX")):
            expected.extend((res("EP:" + bank + ":" + direction, 0, duration),
                             res("FIFO:" + bank + ":" + direction, 0, duration, size)))
    elif kind == "math":
        work, read, write, sfu = math_work(meta, config)
        require((meta["lane_work"], meta["read_bytes"], meta["write_bytes"], meta["SFU_iterations"])
                == (work, read, write, sfu), "integer operation work/read/write/SFU formula")
        vl, rl = lane_partition(config["organization"])
        domain = meta["domain"]
        require(domain in ("V", "R") and meta["bank"] == domain, "arithmetic bank/domain")
        lanes = vl if domain == "V" else rl
        require(meta["lanes"] == lanes, "static lane granularity")
        lane_ids = range(8) if config["organization"] == "shared8" else (range(vl) if domain == "V" else range(vl, 8))
        rd, compute, wr = ceil_div(read, 16), max(1, ceil_div(work, lanes)), ceil_div(write, 16)
        duration = rd + compute + sfu + wr
        expected = ([res("PORT:" + domain, 0, rd)] if rd else [])
        expected += [res("LANE:" + str(i), rd, compute) for i in lane_ids]
        if sfu:
            expected.append(res("SFU", rd + compute, sfu))
        if wr:
            expected.append(res("PORT:" + domain, rd + compute + sfu, wr))
    elif kind == "matrix_proxy":
        duration = 4096
        expected = [res("MATRIX", 0, duration), res("PORT:M", 0, duration)]
        require(meta["operations"] == "16x16x4096 S8 MAC; bounded proxy only", "bounded matrix work")
    elif kind in ("atomic_group_commit", "trial_scale_epoch_update"):
        count = 70 if kind == "atomic_group_commit" else len(meta["heads"]) + 4
        beats = ceil_div(count, 16)
        require(meta["descriptor_bytes"] == count and meta["descriptor_object"] == "R.aux" and meta["descriptor_object_offset"] == 4096
                and meta["descriptor_read_beats"] == meta["descriptor_write_beats"] == beats,
                "typed descriptor read/write cost")
        duration = 2 * beats + 20
        expected = [res("PORT:R", 0, beats), res("CTRL", beats, 20), res("PORT:R", beats + 20, beats)]
    else:
        controls = dict(start=1, finish=1, full_hidden_max=1, full_hidden_finest_unit=1, norm_source_layout_address=2, tile_guard_checked=1,
                        attempt_guard_barrier=1, abort_unpublished_generation=1, fullV_head_output_barrier=1)
        require(kind in controls, "declared control operation")
        duration = controls[kind]
        expected = [res("CTRL", 0, duration)]
    require(node["duration"] == duration, "independent operation duration")
    reservations_equal(node["reservations"], expected, kind)


def verify_packet_offsets(meta, config):
    op, src, dst = meta.get("operation"), meta["src"], meta["dst"]
    read, write = 0, 0
    tile = meta.get("tile", 0)
    b = config["state_bits"] // 8
    packed = (meta.get("head", 0) * 128 * 128 + tile * 128 * config["tile"]) * b
    if meta.get("stream") == "norm":
        if op == "initial_gamma": read = 32 * 25600
        elif op == "load_mixed_code_plane": read, write = meta["row"] * 25600 + tile * 1024, tile * 1280
        elif op == "load_mixed_unit_plane": read, write = meta["row"] * 25600 + 20480 + tile * 256, tile * 1280 + 1024
        elif op == "unit_prepass": read = tile * 1280 + 1024
        elif op in ("max_scan", "reread_mixed"): read = tile * 1280
        elif op == "aligned_spill": write = tile * 1024
        elif op == "read_aligned": read = tile * 1024
        elif op == "gamma_stream": read = tile * 512
    elif meta.get("stream") == "R":
        if op == "token_QKV_gate_metadata": read = meta["token"] * 2048
        elif op in ("page_committed_or_trial_old", "page_guarded_new_for_output"): read = packed
        elif op == "write_uncommitted_backing_generation": write = packed
        elif op == "shadow_fragment": read, write = 6144, meta["chunk"] * 256 * b
        elif op == "uncommitted_output": read, write = 3072, (meta["head"] * 128 + tile * config["tile"]) * 8
        elif op in ("clone_full_committed_trial", "full_head_trial_RNE_shift1"):
            if src == "EXT": read = packed
            if dst == "EXT": write = packed
        elif op == "initial_state_layout" and dst == "EXT": write = packed
    offset = meta["object_offset"]
    require(meta["src_offset"] == read + offset and meta["dst_offset"] == write + offset,
            "independent object address/packing")


def verify_stream_dependencies(nodes):
    """Both recorded streams use a single scratch generation: no removed edge."""
    last, reached = {}, {}
    by_id = {node["id"]: node for node in nodes}
    for node in sorted(nodes, key=lambda n: n["id"]):
        ancestors = {}
        for dep in node["deps"]:
            require(dep < node["id"], "generation DAG topological IDs")
            for stream, value in reached[dep].items():
                ancestors[stream] = max(ancestors.get(stream, -1), value)
        stream = node["meta"].get("stream")
        if stream in ("norm", "R"):
            if stream in last:
                require(ancestors.get(stream, -1) >= last[stream], "semantic scratch/data predecessor " + stream)
            ancestors[stream] = node["id"]
            last[stream] = node["id"]
        reached[node["id"]] = ancestors
    finish = [node for node in nodes if node["kind"] == "finish"]
    require(len(finish) == 1, "one finish publication")
    for stream, value in last.items():
        require(reached[finish[0]["id"]].get(stream, -1) >= value, "complete stream finish dependency")


def mutate_witness(witness, mutation):
    changed = copy.deepcopy(witness)
    nodes = changed["nodes"]
    if mutation == "dependency":
        target = next(n for n in nodes if n["kind"] == "math" and n["meta"]["domain"] == "V")
        target["deps"] = []
        return changed, "semantic scratch/data predecessor"
    if mutation == "capacity":
        target = next(a for a in changed["allocations"] if a["id"] == "V.proxy")
        target["bytes"] += 16384
        return changed, "allocation address capacity"
    if mutation == "epoch":
        target = next(n for n in nodes if n["kind"] == "math" and "token" in n["meta"])
        target["meta"]["scale_epoch"] += 1
        return changed, "causal task unit/epoch transition"
    if mutation == "overlap":
        # Every organization has the same EXT 1RW port. Initial norm gamma
        # and R metadata depend only on start, so move the delayed packet to
        # its dependency-ready time. This works in a single split-only shard
        # as well as in a shared8 shard, without changing operation formulas.
        initial = [n for n in nodes if n["kind"] == "packet" and n["meta"]["object_offset"] == 0
                   and n["meta"].get("operation") in ("initial_gamma", "initial_QKV_gate_metadata")]
        by_id = {n["id"]: n for n in nodes}
        for target in initial:
            ready = max((by_id[d]["end"] for d in target["deps"]), default=0)
            port = next(r for r in target["reservations"] if r["resource"] == "PORT:EXT")
            for other in initial:
                if other is target:
                    continue
                other_port = next(r for r in other["reservations"] if r["resource"] == "PORT:EXT")
                lo, hi = ready + port["offset"], ready + port["offset"] + port["duration"]
                ol = other["start"] + other_port["offset"]
                oh = ol + other_port["duration"]
                if ready < target["start"] and max(lo, ol) < min(hi, oh):
                    target["start"], target["end"] = ready, ready + target["duration"]
                    return changed, "resource overlap/capacity"
        # Move an operation earlier while retaining every dependency and its
        # exact duration/reservations; overlap a ready operation of the other stream.
        by_id = {n["id"]: n for n in nodes}
        for target in nodes:
            if target["kind"] != "math":
                continue
            own = next(x for x in target["reservations"] if x["resource"].startswith("LANE:"))
            ready = max((by_id[d]["end"] for d in target["deps"]), default=0)
            for other in nodes:
                if other["kind"] != "math" or other["meta"]["domain"] == target["meta"]["domain"]:
                    continue
                overlap = [r for r in other["reservations"] if r["resource"] == own["resource"]]
                if not overlap:
                    continue
                r = overlap[0]
                start = max(ready, other["start"] + r["offset"] - own["offset"])
                if start < target["start"] and start + own["offset"] < other["start"] + r["offset"] + r["duration"]:
                    target["start"], target["end"] = start, start + target["duration"]
                    return changed, "resource overlap/capacity"
        raise AssertionError("no ready shared-lane overlap negative witness")
    raise ValueError("unknown negative mutation")


def actual_negative(folder, name, out, mutation):
    """Materialize a changed real compressed witness and a valid SHA manifest."""
    out.mkdir()
    original = json.loads(gzip.decompress((folder / name).read_bytes()))
    changed, error = mutate_witness(original, mutation)
    payload = json.dumps(changed, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    destination = out / name
    destination.write_bytes(gzip.compress(payload, mtime=0))
    desc = dict(bytes=destination.stat().st_size, sha256=sha(destination))
    # A deliberately bounded negative capsule has the actual witness and its
    # rewritten SHA/size, rather than an invented claim about full batch reuse.
    save_json(out / "manifest.json", dict(schema="issue68-negative-witness/1", source=str(folder / name),
        source_sha256=sha(folder / name), mutation=mutation, artifacts={name: desc}))
    index = read_json(out / "manifest.json")
    require(desc == dict(bytes=destination.stat().st_size, sha256=sha(destination))
            == index["artifacts"][name], "negative actual artifact SHA/bytes")
    received = json.loads(gzip.decompress(destination.read_bytes()))
    try:
        verify_witness(received)
    except AssertionError as exc:
        require(error in str(exc), "negative intended semantic rejection: " + str(exc))
        return dict(mutation=mutation, artifact=desc, rewritten_SHA_passed=True,
                    status="REJECTED_INDEPENDENT_SEMANTICS", error=str(exc), capsule=str(out))
    raise AssertionError("actual rehashed negative accepted")


def execute(integer, repeat, root, range_root, out, binding=None, norm_stage="norm03"):
    begin = time.monotonic()
    integer, repeat, root, out = map(Path, (integer, repeat, root, out))
    require(not out.exists(), "new audit output directory")
    out.mkdir(parents=True)
    m, checked = manifest(integer)
    m2, checked2 = manifest(repeat)
    require(m["source"] == m2["source"] and m["config"] == m2["config"] and checked == checked2,
            "two-round full scientific SHA/source/config")
    source = dict(receive_service_sha256=sha(__file__))
    if binding:
        b = read_json(binding)
        require(b["receive_service_sha256"] == source["receive_service_sha256"], "receiver source SHA binding")
        source.update(commit=b["commit"], binding_sha256=sha(binding))
    tasks = source_tasks(root, Path(range_root) if range_root else None, norm_stage)
    metrics = read_json(integer / "metrics.json")
    require(metrics["schema"] == "issue68-service/1" and metrics["status"] == "PASS_CONDITIONAL_SCHEDULE"
            and metrics["source"] == m["source"], "service metrics/source status")
    require(any(row["profile"] == "in_place" for row in metrics["refused"]), "different abort/rollback contract excluded")
    cases, seen, fairness = [], set(), {}
    all_witnesses, chosen_negative = set(), None
    for row in metrics["results"]:
        require(row["task"] in tasks, "known actual numeric task")
        expected_task = tasks[row["task"]]
        require(row["task_fingerprint"] == json_hash(expected_task) and row["commit_contract"] == expected_task["commit_contract"]
                and row["state_bits"] == 32, "same precision/source/commit group")
        identity = (row["task"], row["organization"], row["tile"], row["norm_route"], row["ext_ii"])
        require(identity not in seen, "unique finite service case")
        seen.add(identity)
        require({s["strategy"] for s in row["strategies"]} == {"fifo", "critical"}, "both predeclared scheduling strategies")
        for strategy in row["strategies"]:
            name = strategy["witness"]
            require(name in checked and name not in all_witnesses, "indexed unique service witness")
            all_witnesses.add(name)
            witness = json.loads(gzip.decompress((integer / name).read_bytes()))
            require(witness["task"] == expected_task and witness["task_fingerprint"] == row["task_fingerprint"], "independent reconstructed numeric task")
            c = witness["config"]
            require((c["organization"], c["tile"], c["norm_route"], c["ext_ii"], c["strategy"], c["state_bits"])
                    == (row["organization"], row["tile"], row["norm_route"], row["ext_ii"], strategy["strategy"], 32), "case/witness configuration")
            check = verify_witness(witness)
            require(strategy == dict(strategy=c["strategy"], cycles=check["makespan"], witness=name, nodes=check["operations"],
                                     memory=check["resident_bytes"], payload_bytes=check["payload_bytes"], wire_bytes=check["wire_bytes"]),
                    "independent full case metrics")
            cases.append(dict(witness=name, id=list(identity) + [c["strategy"]], cycles=check["makespan"],
                independent_lower_bound=check["lower_bound"], precedence_lower_bound=check["precedence_lower_bound"],
                operations=check["operations"], payload_bytes=check["payload_bytes"], wire_bytes=check["wire_bytes"],
                resident_bytes=check["resident_bytes"], task_fingerprint=check["task_fingerprint"],
                commit_contract=check["commit_contract"], physical_claim=False))
            if c["organization"] != "shared8":
                key = (row["task"], c["tile"], c["norm_route"], c["ext_ii"], c["strategy"], c["organization"].removeprefix("shared").removeprefix("split"))
                value = dict(cycles=check["makespan"], nodes_sha256=json_hash(witness["nodes"]),
                             allocations_sha256=json_hash(witness["allocations"]), inventory_sha256=json_hash(witness["inventory"]))
                if key in fairness:
                    require(fairness[key]["signature"] == value, "shared/split label-only exact zero difference")
                    fairness[key]["organizations"].add(c["organization"])
                else:
                    fairness[key] = dict(signature=value, organizations={c["organization"]})
            if chosen_negative is None:
                chosen_negative = name
        best = min(row["strategies"], key=lambda s: (s["cycles"], s["strategy"]))
        require(row["best"] == best, "minimum within two fixed strategies")
    require(all_witnesses == {name for name in checked if name.endswith(".json.gz")}, "no unreviewed witness omitted")
    observed_tasks = {identity[0] for identity in seen}
    expected_cases = {(task, org, tile, route, ext) for task in observed_tasks for org in m["config"]["lane_profiles"]
                      for tile in m["config"]["tiles"] for route in m["config"]["norm_routes"] for ext in m["config"]["ext_profiles"]}
    require(seen == expected_cases, "complete declared finite candidate grid")
    negatives = [actual_negative(integer, chosen_negative, out / ("rehashed-" + mutation), mutation)
                 for mutation in ("dependency", "overlap", "capacity", "epoch")]
    groups = []
    for task_id in sorted(observed_tasks):
        for ext in m["config"]["ext_profiles"]:
            group = [case for case in cases if case["id"][0] == task_id and case["id"][4] == ext]
            winner = min(group, key=lambda c: (c["cycles"], c["witness"]))
            groups.append(dict(task=task_id, commit_contract=tasks[task_id]["commit_contract"], ext_ii=ext,
                               candidates=len(group), winner=winner["witness"], cycles=winner["cycles"],
                               claim="minimum only within recorded finite grid, includes granularity variants; no global optimum or physical merge benefit"))
    pairs = sum(len(value["organizations"]) == 2 for value in fairness.values())
    result = dict(status="PASS_INDEPENDENT_SERVICE", source=source, seconds=time.monotonic() - begin,
        cases=cases, finite_groups=groups, negative_checks=negatives, complete_witnesses=len(cases),
        two_rounds=dict(all_scientific_SHA_identical=True, artifacts=len(checked), arithmetic_schedules_independent=1),
        shared_split_label_only_pairs=pairs, shared_split_label_only_cycles_difference=0 if pairs else None,
        shared_split_signatures=[dict(key=list(key), signature=value["signature"], organizations=sorted(value["organizations"])) for key, value in fairness.items()],
        declared_source_root=str(root), norm_stage=norm_stage, range_root=str(range_root) if range_root else None,
        validation="Every witness independent operation/payload/address/epoch/dependency/calendar/FIFO/slot/lower-bound replay; original numeric source SHA checked, not redoing arithmetic",
        quality_accepted=False, hardware_implemented=False,
        limitation="Conditional declared scalar-lowering and conservative fixed-slot schedules; independent norm/R streams and auxiliary proxies; no RTL/PPA/full-model speed or global-optimality proof")
    save_json(out / "audit.json", result)
    print(json.dumps(dict(status=result["status"], witnesses=len(cases), negatives=len(negatives))), flush=True)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for option in ("integer", "repeat", "root", "out"):
        p.add_argument("--" + option, type=Path, required=True)
    p.add_argument("--range", dest="range_root", type=Path)
    p.add_argument("--norm-stage", default="norm03")
    p.add_argument("--binding", type=Path)
    a = p.parse_args()
    execute(a.integer, a.repeat, a.root, a.range_root, a.out, a.binding, a.norm_stage)


if __name__ == "__main__":
    main()
