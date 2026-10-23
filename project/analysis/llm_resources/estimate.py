"""Offline budget accounting for <=4B W8A8 workloads; no model or EDA execution."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROFILE_COMMIT = "3fa0b45070c7ce4587240589d48703d02a1b5246"
PROFILE_BLOB = "6ceb6b8b6d4698792a75be782a7278aaab5ee3c5"
PROFILE_PATH = "project/experiments/block_candidate/candidate.json"


class InputError(ValueError):
    """Invalid input, distinct from an accounted resource shortfall."""


def ceildiv(a, b):
    return (a + b - 1) // b


def _unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise InputError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def read_json(path):
    def reject_constant(value):
        raise InputError(f"non-finite JSON number: {value}")
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"),
                          object_pairs_hook=_unique_object, parse_constant=reject_constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputError(f"{Path(path).name}: {exc}") from exc


def validate_schema(value, rule, where="$"):
    """Validate the JSON-Schema subset used in schema.json, without dependencies."""
    if "anyOf" in rule:
        for choice in rule["anyOf"]:
            try:
                validate_schema(value, choice, where)
                return
            except InputError:
                pass
        raise InputError(f"{where}: no allowed type/shape matched")
    checks = {
        "null": lambda x: x is None,
        "object": lambda x: isinstance(x, dict),
        "array": lambda x: isinstance(x, list),
        "string": lambda x: isinstance(x, str),
        "integer": lambda x: type(x) is int,
        "number": lambda x: type(x) in (int, float) and math.isfinite(x),
    }
    kind = rule.get("type")
    if kind and not checks[kind](value):
        raise InputError(f"{where}: expected {kind}")
    if "const" in rule and (type(value) is not type(rule["const"]) or value != rule["const"]):
        raise InputError(f"{where}: expected constant {rule['const']!r}")
    if "enum" in rule and not any(type(value) is type(v) and value == v for v in rule["enum"]):
        raise InputError(f"{where}: outside enum {rule['enum']!r}")
    if type(value) in (int, float):
        if not math.isfinite(value):
            raise InputError(f"{where}: non-finite number")
        for key, compare in (("minimum", lambda x, y: x < y),
                             ("maximum", lambda x, y: x > y),
                             ("exclusiveMinimum", lambda x, y: x <= y)):
            if key in rule and compare(value, rule[key]):
                raise InputError(f"{where}: violates {key}={rule[key]}")
    if isinstance(value, str) and len(value) < rule.get("minLength", 0):
        raise InputError(f"{where}: empty string")
    if isinstance(value, dict):
        properties = rule.get("properties", {})
        missing = set(rule.get("required", [])) - value.keys()
        extra = value.keys() - properties.keys()
        if missing:
            raise InputError(f"{where}: missing {sorted(missing)}")
        if extra and rule.get("additionalProperties") is False:
            raise InputError(f"{where}: unknown fields {sorted(extra)}")
        for key, item in value.items():
            if key in properties:
                validate_schema(item, properties[key], f"{where}.{key}")
    if isinstance(value, list):
        if len(value) < rule.get("minItems", 0) or len(value) > rule.get("maxItems", math.inf):
            raise InputError(f"{where}: invalid item count")
        if rule.get("uniqueItems") and len(set(map(lambda x: json.dumps(x, sort_keys=True), value))) != len(value):
            raise InputError(f"{where}: duplicate items")
        for index, item in enumerate(value):
            validate_schema(item, rule.get("items", {}), f"{where}[{index}]")


def validate_input(config):
    validate_schema(config, read_json(HERE / "schema.json"))
    model, scene = config["model"], config["scenario"]
    if model["int8_parameters"] + sum(p["parameters"] for p in model["auxiliary_parameters"]) != model["total_parameters"]:
        raise InputError("model: INT8 plus auxiliary parameter counts must equal total")
    ops = model["linear_ops"]
    if (ops is None) == (model["linear_macs_per_token"] is None):
        raise InputError("model: choose exactly one of linear_ops and linear_macs_per_token")
    if ops is not None:
        if model["linear_outputs_per_token"] is not None:
            raise InputError("model: shape-derived outputs must not be overridden")
        if len({op["name"] for op in ops}) != len(ops):
            raise InputError("model.linear_ops: names must be unique")
        if any(op["active_instances"] > op["instances"] for op in ops):
            raise InputError("model.linear_ops: active_instances exceeds total instances")
        storage = sum(op["instances"] * op["input_features"] * op["output_features"] for op in ops)
        if storage > model["int8_parameters"]:
            raise InputError("model.linear_ops: unique matrix weights exceed INT8 parameter inventory")
        if model["kind"] == "dense" and any(op["active_instances"] != op["instances"] for op in ops):
            raise InputError("dense model: active_instances must equal instances")
    elif model["linear_macs_per_token"] > model["int8_parameters"]:
        raise InputError("aggregate mode assumes each active matrix weight used once; exceeds total INT8 weights")
    for group in model["attention"]:
        if group["query_heads"] % group["kv_heads"]:
            raise InputError("attention: query_heads must be divisible by kv_heads")
    peak = scene["cached_tokens"] + scene["input_tokens"] + scene["output_tokens"]
    if model["max_context_tokens"] is not None and peak > model["max_context_tokens"]:
        raise InputError("scenario: reserved context exceeds model.max_context_tokens")
    if scene["phase"] == "decode" and scene["output_tokens"] < 2:
        raise InputError("decode budget requires >=2 outputs (the first comes from prefill)")
    for transfer in config["transfers"]:
        if transfer["logical_bits"] > transfer["storage_bits"]:
            raise InputError("transfer: logical bits exceed storage container")
        if transfer["logical_bits"] == 33 and transfer["storage_bits"] != 64:
            raise InputError("candidate i33 transport requires an i64 container")
    return config


def validate_candidate(candidate):
    if not isinstance(candidate, dict) or candidate.get("schema") != "block-candidate/1":
        raise InputError("candidate: expected block-candidate/1")
    scalar_fields = ("data_link_bits", "beat_bytes", "packet_header_bytes",
                     "endpoint_fifo_bytes", "s_bank_bytes", "s_bank_count")
    for key in scalar_fields:
        if type(candidate.get(key)) is not int or candidate[key] < 0:
            raise InputError(f"candidate.{key}: expected nonnegative integer")
    if candidate["data_link_bits"] < 8 or candidate["data_link_bits"] % 8:
        raise InputError("candidate: link width must be a positive multiple of 8")
    if candidate["beat_bytes"] == 0:
        raise InputError("candidate: beat_bytes must be positive")
    if candidate["s_bank_bytes"] == 0:
        raise InputError("candidate: S bank capacity must be positive")
    blocks = candidate.get("blocks")
    if (not isinstance(blocks, list) or not all(isinstance(b, dict) and isinstance(b.get("id"), str) for b in blocks) or
            {b.get("id") for b in blocks} != {"M", "V", "A", "R", "D"} or len(blocks) != 5):
        raise InputError("candidate: exactly M/V/A/R/D templates required")
    for block in blocks:
        for key in ("instances", "native_mul8", "rq_mul8", "private_bytes", "rom_bytes", "rx", "tx"):
            if type(block.get(key)) is not int or block[key] < 0:
                raise InputError(f"candidate.{block['id']}.{key}: invalid count")
    if next(b for b in blocks if b["id"] == "M")["native_mul8"] == 0:
        raise InputError("candidate: M must have a positive INT8 multiplier count")
    graph = candidate.get("logical_bindings_hybrid")
    if not isinstance(graph, dict) or not graph:
        raise InputError("candidate: logical_bindings_hybrid required")
    if any(not isinstance(v, list) or any(not isinstance(n, str) or n not in graph for n in v)
           for v in graph.values()):
        raise InputError("candidate: malformed logical graph")
    if (candidate["endpoint_fifo_bytes"] - candidate["packet_header_bytes"]) // candidate["beat_bytes"] < 1:
        raise InputError("candidate: FIFO cannot hold header plus a payload beat")
    return candidate


def inventory(candidate, matrix_count):
    private = rom = fifo_count = multipliers = total_blocks = 0
    for block in candidate["blocks"]:
        count = matrix_count if block["id"] == "M" else block["instances"]
        total_blocks += count
        private += count * block["private_bytes"]
        rom += count * block["rom_bytes"]
        fifo_count += count * (block["rx"] + block["tx"])
        multipliers += count * (block["native_mul8"] + block["rq_mul8"])
    banks = candidate["s_bank_count"]
    fifo_count += 2 * banks
    bank_bytes = banks * candidate["s_bank_bytes"]
    fifos = fifo_count * candidate["endpoint_fifo_bytes"]
    return {"block_instances": total_blocks + banks, "matrix_instances": matrix_count,
            "signed8_multipliers_including_RQ": multipliers, "private_bytes": private,
            "shared_bank_bytes": bank_bytes, "rom_bytes": rom,
            "fifo_count": fifo_count, "fifo_bytes": fifos,
            "all_declared_memory_bytes": private + bank_bytes + rom + fifos}


def packet(payload, candidate):
    if payload == 0:
        return {"packets": 0, "wire_bytes": 0, "ideal_link_cycles": 0}
    beat, header, fifo = (candidate[k] for k in ("beat_bytes", "packet_header_bytes", "endpoint_fifo_bytes"))
    maximum = (fifo - header) // beat * beat
    chunks, tail = divmod(payload, maximum)
    packets = chunks + bool(tail)
    wire = chunks * (header + maximum) + (header + ceildiv(tail, beat) * beat if tail else 0)
    link_bytes = candidate["data_link_bits"] // 8
    cycles = chunks * ceildiv(header + maximum, link_bytes)
    if tail:
        cycles += ceildiv(header + ceildiv(tail, beat) * beat, link_bytes)
    return {"packets": packets, "wire_bytes": wire, "ideal_link_cycles": cycles}


def scale_storage(elements, spec):
    return None if spec is None else ceildiv(elements, spec["group_elements"]) * spec["bytes_per_group"]


def causal_pairs(cached, rows, window):
    def prefix(n):
        if window is None or n <= window:
            return n * (n + 1) // 2
        return window * (window + 1) // 2 + (n - window) * window
    return prefix(cached + rows) - prefix(cached)


def compute(config, candidate):
    """Pure accounting. No files, subprocesses, network, model weights or simulator."""
    validate_input(config)
    validate_candidate(candidate)
    model, scene, hw, accounting = (config[k] for k in ("model", "scenario", "hardware", "accounting"))
    precision, placement = config["precision"], config["placement"]
    unresolved, violations = [], []
    batch, prompt = scene["batch"], scene["input_tokens"]
    prefill = scene["phase"] == "prefill"
    rows = prompt if prefill else 1
    peak_context = scene["cached_tokens"] + prompt + scene["output_tokens"]
    decode_context = peak_context - 1
    target = scene["target_tokens_per_second"]
    tokens_per_step = batch * rows
    deadline = tokens_per_step / target if target is not None else None
    if deadline is not None and (not math.isfinite(deadline) or deadline <= 0):
        raise InputError("target step duration overflows or underflows; check units")
    if deadline is None:
        unresolved.append("scenario.target_tokens_per_second")
    if model["max_context_tokens"] is None:
        unresolved.append("model.max_context_tokens")
    if precision["quantization_contract"] is None:
        unresolved.append("precision.quantization_contract (numeric quality/correctness not qualified)")
    if model["kind"] == "moe":
        unresolved.append("MoE routing/distinct expert union across rows not supplied; active counts/passes are assumptions")

    ops = model["linear_ops"]
    if ops is None:
        linear = model["linear_macs_per_token"] * batch * rows
        outputs = model["linear_outputs_per_token"]
        outputs = None if outputs is None else outputs * batch * rows
        active_weights = model["linear_macs_per_token"]
        unresolved.append("model.linear_ops absent: aggregate envelope, no graph/tensor coverage")
    else:
        linear = outputs = active_weights = 0
        for op in ops:
            op_rows = batch * (prompt if prefill and op["prefill_rows"] == "all" else 1)
            active = op["active_instances"]
            active_weights += active * op["input_features"] * op["output_features"]
            linear += op_rows * active * op["input_features"] * op["output_features"]
            outputs += op_rows * active * op["output_features"]
    weight_scales = scale_storage(model["int8_parameters"], accounting["weight_scale"])
    aux = 0
    for item in model["auxiliary_parameters"]:
        if item["storage_bits"] is None:
            unresolved.append(f"auxiliary parameter format: {item['name']}")
        else:
            aux += item["parameters"] * item["storage_bits"] // 8
    for key, value in (("weight_scale", weight_scales), ("weight_padding_bytes", accounting["weight_padding_bytes"])):
        if value is None:
            unresolved.append("accounting." + key)
    weight_known = model["int8_parameters"] + aux + (weight_scales or 0) + (accounting["weight_padding_bytes"] or 0)

    kv_payload = kv_scales = kv_writes = kv_read_basis = attention_macs = 0
    for group in model["attention"]:
        layers, heads, dim = group["layers"], group["kv_heads"], group["head_dim"]
        cap = min(peak_context, group["window_tokens"] or peak_context)
        pairs = (causal_pairs(scene["cached_tokens"], prompt, group["window_tokens"]) if prefill
                 else min(decode_context, group["window_tokens"] or decode_context))
        per_row = 2 * layers * heads * dim * precision["kv_bits"] // 8
        scale = accounting["kv_scale"]
        per_row_scale = (0 if scale is None else 2 * layers * heads *
                         ceildiv(dim, scale["group_elements"]) * scale["bytes_per_group"])
        kv_payload += batch * cap * per_row
        kv_scales += batch * cap * per_row_scale
        kv_writes += batch * rows * (per_row + per_row_scale)
        kv_read_basis += batch * pairs * (per_row + per_row_scale)
        attention_macs += 2 * batch * layers * group["query_heads"] * dim * pairs
    if model["attention"] and accounting["kv_scale"] is None:
        unresolved.append("accounting.kv_scale (capacity/traffic below exclude unknown scale bytes)")
    state = batch * sum(s["elements_per_sequence"] * s["storage_bits"] // 8 +
                        s["extra_bytes_per_sequence"] for s in model["recurrent_states"])
    if state:
        unresolved.append("recurrent execution, wide arithmetic and conversion service not modeled")

    backing = {"shared": 0, "external": 0}
    for name, amount in (("weights", weight_known), ("kv", kv_payload + kv_scales), ("recurrent", state)):
        location = placement[name]
        if location == "unknown":
            unresolved.append("placement." + name)
        else:
            backing[location] += amount
    for location in ("shared", "external"):
        value = accounting[location + "_workspace_bytes"]
        if value is None:
            unresolved.append("accounting." + location + "_workspace_bytes")
        else:
            backing[location] += value
    shared_capacity = candidate["s_bank_count"] * candidate["s_bank_bytes"] - hw["shared_reserve_bytes"]
    if shared_capacity < 0:
        raise InputError("hardware.shared_reserve_bytes exceeds shared bank capacity")
    if backing["shared"] > shared_capacity:
        violations.append("shared_backing_accounted_bytes_exceed_capacity")
    if hw["external_capacity_bytes"] is None:
        unresolved.append("hardware.external_capacity_bytes")
    elif backing["external"] > hw["external_capacity_bytes"]:
        violations.append("external_backing_accounted_bytes_exceed_capacity")

    external_traffic = 0
    traffic_incomplete = any(
        placement[name] == "unknown" and amount > 0
        for name, amount in (("weights", weight_known), ("kv", kv_payload + kv_scales), ("recurrent", state)))
    weight_traffic = kv_traffic = state_traffic = None
    if placement["weights"] == "external":
        # Missing layout/auxiliary transfers preclude a complete traffic ledger.
        traffic_incomplete = True
        active_scale = scale_storage(active_weights, accounting["weight_scale"])
        if accounting["weight_read_passes"] is None:
            unresolved.append("accounting.weight_read_passes")
        else:
            weight_traffic = (active_weights + (active_scale or 0)) * accounting["weight_read_passes"]
            external_traffic += weight_traffic
            unresolved.append("weight transfer padding and auxiliary parameter traffic not scheduled")
    if placement["kv"] == "external" and model["attention"]:
        traffic_incomplete |= accounting["kv_scale"] is None
        factor = accounting["kv_read_multiplier"]
        if factor is None:
            traffic_incomplete = True
            external_traffic += kv_writes
            unresolved.append("accounting.kv_read_multiplier (no inter-query reuse assumed by basis only)")
        else:
            kv_traffic = kv_read_basis * factor + kv_writes
            external_traffic += kv_traffic
    if placement["recurrent"] == "external" and state:
        passes = accounting["recurrent_read_write_passes"]
        if passes is None:
            traffic_incomplete = True
            unresolved.append("accounting.recurrent_read_write_passes")
        else:
            state_traffic = 2 * state * rows * passes
            external_traffic += state_traffic
    bw = hw["external_effective_bytes_per_second"]
    if bw is None:
        unresolved.append("hardware.external_effective_bytes_per_second")
    has_rate_bound = external_traffic > 0 or not traffic_incomplete
    required_bw = None if deadline is None or not has_rate_bound else external_traffic / deadline
    if required_bw is not None and bw is not None and required_bw > bw:
        violations.append("accounted_external_traffic_exceeds_effective_bandwidth")

    tile = config["mapping"]["matrix_tile"]
    tile_ram = (tile["operand_copies"] * (tile["rows"] * tile["reduction"] +
                tile["reduction"] * tile["columns"]) +
                tile["accumulator_copies"] * tile["rows"] * tile["columns"] * 4 + tile["reserved_bytes"])
    matrix_template = next(b for b in candidate["blocks"] if b["id"] == "M")
    if tile_ram > matrix_template["private_bytes"]:
        violations.append("matrix_tile_accounted_bytes_exceed_private_RAM")
    frequency, utilization = hw["clock_hz"], hw["matrix_utilization"]
    if frequency is None:
        unresolved.append("hardware.clock_hz")
    if utilization is None:
        unresolved.append("hardware.matrix_utilization")
    capacity = (None if frequency is None or utilization is None else
                matrix_template["native_mul8"] * frequency * utilization)
    if capacity is not None and (not math.isfinite(capacity) or capacity <= 0):
        raise InputError("matrix rate overflows or underflows; check units")
    min_matrices = None if capacity is None or deadline is None else max(1, math.ceil(linear / capacity / deadline))
    rq_ii = hw["rq_initiation_interval_cycles"]
    if rq_ii is None or outputs is None or matrix_template["rq_mul8"] == 0:
        unresolved.append("RQ service unavailable: II/output count/channel count not fully specified")
    scans = []
    for count in hw["matrix_counts"]:
        rq_cycles = (None if rq_ii is None or outputs is None or matrix_template["rq_mul8"] == 0 else
                     math.ceil(outputs * rq_ii / (matrix_template["rq_mul8"] * count)))
        scans.append({"inventory": inventory(candidate, count),
                      "linear_compute_seconds_lower_bound": None if capacity is None else linear / (capacity * count),
                      "linear_target_violated": None if min_matrices is None else count < min_matrices,
                      "RQ_steady_service_cycles_proxy": rq_cycles,
                      "RQ_target_violated_under_II_assumption":
                          None if rq_cycles is None or frequency is None or deadline is None else
                          rq_cycles / frequency > deadline,
                      "topology_status": "unmapped; candidate graph not replicated by inventory scaling"})

    graph = candidate["logical_bindings_hybrid"]
    transfers = []
    edge_bytes, tx_bytes = {}, {}
    for transfer in config["transfers"]:
        path = transfer["path"]
        if any(src not in graph or dst not in graph[src] for src, dst in zip(path, path[1:])):
            raise InputError(f"transfer {transfer['name']}: edge absent from candidate graph")
        payload = math.prod(transfer["shape"]) * transfer["storage_bits"] // 8 + transfer["metadata_bytes"]
        packed = packet(payload, candidate)
        messages = transfer["messages_per_step"]
        wire_step = None if messages is None else packed["wire_bytes"] * messages * (len(path) - 1)
        if messages is not None:
            for src, dst in zip(path, path[1:]):
                edge_bytes[(src, dst)] = edge_bytes.get((src, dst), 0) + packed["wire_bytes"] * messages
                tx_bytes[src] = tx_bytes.get(src, 0) + packed["wire_bytes"] * messages
        fraction = hw["link_effective_fraction"]
        transfers.append({"name": transfer["name"], "payload_bytes": payload, "path": path,
                          **packed, "hop_summed_wire_bytes_per_step": wire_step,
                          "single_link_seconds_lower_bound_per_message":
                              None if frequency is None or fraction is None else
                              packed["wire_bytes"] / (candidate["data_link_bits"] / 8 * frequency * fraction)})
        if messages is None:
            unresolved.append(f"transfer {transfer['name']}: messages_per_step")
    if hw["link_effective_fraction"] is None:
        unresolved.append("hardware.link_effective_fraction")
    link_capacity = (None if frequency is None or hw["link_effective_fraction"] is None else
                     candidate["data_link_bits"] / 8 * frequency * hw["link_effective_fraction"])
    def service_entry(amount, capacity):
        required = None if deadline is None else amount / deadline
        return {"accounted_wire_bytes_per_step": amount, "required_bytes_per_second": required,
                "capacity_bytes_per_second": capacity,
                "lower_bound_exceeds_capacity": None if required is None or capacity is None else required > capacity}
    template_tx = {b["id"]: b["tx"] for b in candidate["blocks"]}
    tx_entries = {}
    for node, amount in sorted(tx_bytes.items()):
        ports = 1 if node.startswith("S") else template_tx[node]
        tx_entries[node] = service_entry(amount, None if link_capacity is None else ports * link_capacity)
    transport = {
        "scope": "one instance per named compute node in reference graph; never extrapolated to scaled inventories",
        "complete_model_transfer_schedule": False,
        "all_listed_message_counts_known": bool(config["transfers"]) and all(t["messages_per_step"] is not None for t in config["transfers"]),
        "edges": [{"source": src, "destination": dst, **service_entry(amount, link_capacity)}
                  for (src, dst), amount in sorted(edge_bytes.items())],
        "shared_TX": tx_entries,
        "qualification": "sums only listed transfers; RX mux, S 1RW arbitration and physical paths remain unresolved",
    }
    unresolved.extend(["full operator/precision coverage and physical qualification",
                       "nonlinear/attention wide lowering, bank arbitration, complete transfer schedule",
                       "static routing, pin/track/via budgets, clocks, deadlock and cycle-level execution"])
    return {
        "schema_version": "llm-resource-report/1",
        "status": "analytical_partial; no full-model feasibility certificate",
        "model": {"name": model["name"], "kind": model["kind"],
                  "total_parameters": model["total_parameters"], "source": model["source"]},
        "scenario": {**scene, "reserved_context_tokens": peak_context,
                     "decode_evaluated_context_tokens": None if prefill else decode_context,
                     "tokens_per_step": tokens_per_step, "target_step_seconds": deadline},
        "storage": {"int8_weight_payload_bytes": model["int8_parameters"],
                    "auxiliary_parameter_accounted_bytes": aux, "weight_scale_bytes": weight_scales,
                    "weight_accounted_bytes_lower_bound": weight_known,
                    "kv_payload_bytes": kv_payload, "kv_scale_accounted_bytes": kv_scales,
                    "recurrent_bytes": state, "backing_accounted_bytes": backing,
                    "shared_capacity_bytes": shared_capacity,
                    "matrix_tile_accounted_bytes": tile_ram,
                    "shared_capacity_excludes_private_ROM_and_endpoint_FIFOs": True},
        "work": {"linear_MACs_per_step": linear, "linear_output_elements_per_step": outputs,
                 "active_matrix_weight_elements_per_step_pass": active_weights,
                 "attention_logical_MACs_per_step": attention_macs,
                 "attention_MACs_not_added_to_W8A8_timing": True},
        "external": {"linear_weight_accounted_bytes_per_step": weight_traffic,
                     "KV_read_basis_bytes_no_inter_query_reuse": kv_read_basis,
                     "KV_accounted_bytes_per_step": kv_traffic,
                     "KV_append_accounted_bytes_per_step": kv_writes,
                     "recurrent_accounted_bytes_per_step": state_traffic,
                     "total_accounted_bytes_per_step_lower_bound": external_traffic,
                     "listed_policy_traffic_incomplete": traffic_incomplete,
                     "required_bytes_per_second_lower_bound": required_bw,
                     "service_seconds_lower_bound": None if bw is None or not has_rate_bound else external_traffic / bw,
                     "qualification": "only listed policy terms; not a complete model transfer schedule"},
        "matrix_instances_linear_lower_bound": min_matrices,
        "scans": scans, "transfers": transfers, "reference_transport": transport,
        "known_constraint_violations_under_input_assumptions": violations,
        "unresolved": sorted(set(unresolved)),
        "formulas": {
            "weights": "INT8_parameters + ceil(INT8_parameters/group)*scale_bytes + known aux/padding",
            "KV": "sum_groups B*min(reserved_context,window)*2*L*Hkv*(d*KV_bytes+row_scales)",
            "linear": "sum active_instances*rows*K*N; last-only LM head uses B prefill rows",
            "matrix_count": "ceil(linear_MACs/(native_mul8*clock*utilization*target_step_seconds))",
            "external": "declared active-weight passes + declared KV read multiplier/append + declared state passes; omitted terms stay unresolved",
            "prefill_pairs": "sum_i=1..S min(cached+i,window); decode evaluated at reserved_context-1",
            "packets": "split to FIFO-sized messages; each header + ceil(payload/beat)*beat, each hop charged",
        },
    }


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def provenance(input_path, candidate_path):
    raw = candidate_path.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    files = [Path(__file__), HERE / "schema.json", input_path, candidate_path]
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                         text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.SubprocessError):
        commit = None
    records = []
    for path in files:
        matches = False
        try:
            relative = path.resolve().relative_to(ROOT).as_posix()
            if commit:
                data = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=ROOT,
                                      capture_output=True, check=False)
                matches = data.returncode == 0 and data.stdout == path.read_bytes()
        except ValueError:
            pass
        records.append({"name": path.name, "sha256": file_digest(path), "matches_commit": matches})
    return {"commit": commit, "files": records,
            "source_bound": all(f["matches_commit"] for f in records),
            "candidate_git_blob": blob, "matches_PR44_snapshot": blob == PROFILE_BLOB,
            "candidate_source": ({"commit": PROFILE_COMMIT, "path": PROFILE_PATH,
                                  "url": f"https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/{PROFILE_COMMIT}/{PROFILE_PATH}"}
                                 if blob == PROFILE_BLOB else {"status": "custom local candidate; no upstream binding"})}


def main(argv=None):
    # Keep machine-readable JSON UTF-8 on Windows as well as Unix.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--candidate", type=Path, help="override candidate path; source binding recomputed")
    parser.add_argument("--output", type=Path, help="new JSON file only; stdout when omitted")
    args = parser.parse_args(argv)
    try:
        input_path = args.input.resolve()
        config = validate_input(read_json(input_path))
        candidate_path = (args.candidate.resolve() if args.candidate else
                          (input_path.parent / config["hardware"]["candidate_file"]).resolve())
        candidate = read_json(candidate_path)
        result = compute(config, candidate)
        result["provenance"] = provenance(input_path, candidate_path)
        data = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8", newline="\n") as output:
                output.write(data)
        else:
            print(data, end="")
        return 0
    except (InputError, OSError, ValueError, ArithmeticError) as exc:
        print(json.dumps({"status": "invalid_input_or_output", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
