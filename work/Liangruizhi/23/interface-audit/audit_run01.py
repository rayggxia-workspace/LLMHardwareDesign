"""Independent stdlib audit of real-run records; never imports the runner."""
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess

RUN = Path("D:/Projects/Codex/qwen3-inference-20261022/results/run-01")
REPO = Path("D:/Projects/LLMHardwareDesign-inference")
OUT = Path(__file__).resolve().parent
COMMIT = "d63bc2d37a5f1457a4a170b17afba343fb54998d"
failures = []
counts = Counter()


def check(condition, label):
    counts["assertions"] += 1
    if not condition:
        failures.append(label)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def read(name):
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def committed(path):
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=REPO)


def shapes(q, k, c):
    h, f, hq, hk, d = [c[n] for n in ("hidden_size", "intermediate_size",
        "num_attention_heads", "num_key_value_heads", "head_dim")]
    return {
        "q_projection_pre_norm_rope": [1, q, hq*d],
        "k_projection_pre_norm_rope": [1, q, hk*d],
        "v_projection": [1, q, hk*d],
        "attention_output": [1, q, h],
        "ffn_gate_projection": [1, q, f],
        "ffn_up_projection": [1, q, f],
        "ffn_output": [1, q, h],
        "decoder_output": [1, q, h],
        "swiglu_product_before_down_proj": [1, q, f],
        "attention.query_post_rope": [1, hq, q, d],
        "attention.key_cached_post_rope": [1, hk, k, d],
        "attention.value_cached": [1, hk, k, d],
        "attention.context_before_o_proj": [1, q, hq, d],
        "attention.probabilities": [1, hq, q, k],
    }


def metadata(event, expected, label):
    check(event["shape"] == expected, label + "/shape")
    check(event["numel"] == math.prod(expected), label + "/numel")
    check(event["dtype"] == "torch.float32" and event["itemsize"] == 4, label + "/dtype")
    check(event["logical_bytes"] == math.prod(expected)*4, label + "/bytes")
    check(len(event["stride"]) == len(expected) and all(s >= 0 for s in event["stride"]), label + "/stride")
    upper = event["storage_offset"] + sum((dim-1)*stride for dim, stride in zip(expected, event["stride"]))
    check(event["storage_offset"] >= 0 and (upper+1)*4 <= event["storage_bytes"], label + "/storage_bounds")


def compared(c, label):
    check(c["finite"] and c["match"], label + "/finite_match")
    check(math.isfinite(c["max_abs"]) and c["max_abs"] >= 0 and
          math.isfinite(c["relative_l2"]) and c["relative_l2"] >= 0, label + "/metrics")


def cache_comparison(comparison, length, label, positive, cfg):
    check(comparison["finite"] and comparison["match"] == positive, label + "/finite_match")
    fields = comparison["cache"]["fields"]
    required = {(layer, kind) for layer in range(cfg["num_hidden_layers"]) for kind in ("keys", "values")}
    check(len(fields) == len(required) and {(f["layer"], f["field"]) for f in fields} == required, label + "/all_fields")
    check(not comparison["cache"]["errors"], label + "/no_errors")
    for field in fields:
        dims = [1, cfg["num_key_value_heads"], length, cfg["head_dim"]]
        check(all(field[k] == dims for k in ("shape", "reference_shape", "expected_shape")), label + "/shape")
        check(field["dtype"] == field["reference_dtype"] == "torch.float32" and field["layout_valid"], label + "/layout")
        check(field["finite"] and math.isfinite(field["max_abs"]) and field["max_abs"] >= 0, label + "/error")
        if positive:
            compared(field, label + "/field")
    logit = comparison["logits"]
    check(logit["shape"] == logit["reference_shape"] == [1, cfg["vocab_size"]], label + "/logits_shape")
    check(logit["dtype"] == logit["reference_dtype"] == "torch.float32", label + "/logits_dtype")
    check(logit["finite"] and math.isfinite(logit["max_abs"]), label + "/logits_finite")
    if positive:
        compared(logit, label + "/logits")
    return fields


def prefix_integrity(record, old, label, cfg):
    fields = record["fields"]
    required = {(layer, kind) for layer in range(cfg["num_hidden_layers"]) for kind in ("keys", "values")}
    if old == 0:
        check(record["unchanged"] and not fields and record["empty_prefix"], label + "/empty")
        return 0
    check(record["unchanged"] and len(fields) == len(required) and
          {(f["layer"], f["field"]) for f in fields} == required, label + "/complete")
    for field in fields:
        check(field["prefix_length"] == old and field["shape"] == [1, cfg["num_key_value_heads"], old, cfg["head_dim"]], label + "/shape")
        check(field["unchanged"] and field["sha256"] == field["after_sha256"] and
              len(bytes.fromhex(field["sha256"])) == 32, label + "/hash_equality")
    return len(fields)


def main():
    manifest, start = read("manifest.json"), read("manifest-start.json")
    check(manifest["source_commit"] == COMMIT, "source_commit")
    check(not manifest["source_dirty_at_start"] and manifest["source_unchanged_at_end"] and
          manifest["model_files_unchanged_at_end"], "reported_clean_unchanged")
    check(all(manifest[k] == value for k, value in start.items()), "start_manifest_consistency")
    artifact_hashes = {}
    check(set(manifest["artifacts"]) == {p.name for p in RUN.iterdir() if p.is_file() and p.name != "manifest.json"}, "artifact_set")
    for name, expected in manifest["artifacts"].items():
        artifact_hashes[name] = sha(RUN/name)
        check(artifact_hashes[name] == expected, "artifact_sha/"+name)
    counts["artifact_hashes"] = len(artifact_hashes)
    for path, expected in manifest["source_files"].items():
        check(digest(committed(path)) == expected, "commit_source_sha/"+path)
    counts["git_commit_source_files"] = len(manifest["source_files"])
    frozen = json.loads(committed("project/experiments/qwen3_trace/experiment.json"))
    check(manifest["model_files"] == frozen["model_files"], "frozen_model_files")
    check(manifest["model_id"] == frozen["model_id"] and manifest["revision"] == frozen["revision"], "model_revision")
    model_dir = Path(manifest["local_model_dir"])
    for name, entry in manifest["model_files"].items():
        check((model_dir/name).stat().st_size == entry["bytes"] and sha(model_dir/name) == entry["sha256"], "actual_model_file/"+name)
    counts["actual_model_files_rehashed"] = len(manifest["model_files"])
    for name, entry in manifest["implementation_files"].items():
        upstream = OUT / "upstream" / ("modeling_qwen3.py" if name == "qwen3" else "cache_utils.py")
        check(sha(entry["path"]) == entry["sha256"] == sha(upstream), "official_runtime_sha/"+name)
    counts["runtime_sources_rehashed"] = 2
    cfg = json.loads((model_dir/"config.json").read_text(encoding="utf-8"))
    dimensions = ("hidden_size", "intermediate_size", "num_hidden_layers", "num_attention_heads",
                  "num_key_value_heads", "head_dim", "vocab_size", "rope_theta", "rms_norm_eps",
                  "attention_bias", "hidden_act", "tie_word_embeddings", "sliding_window", "rope_scaling")
    check(all(manifest["model"]["config"][k] == cfg[k] for k in dimensions), "actual_model_config")
    h, f, layers, hq, hkv, d, vocab = [cfg[k] for k in dimensions[:7]]
    parameter_count = vocab*h + layers*(2*h*hq*d+2*h*hkv*d+3*h*f+2*h+2*d)+h
    check(parameter_count == manifest["model"]["independent_parameter_elements"], "parameter_formula")
    check(parameter_count+vocab*h == manifest["model"]["state_dict_elements"] and manifest["model"]["embedding_lm_head_share_storage"], "tied_parameters")
    inputs = read("inputs.json")
    tokens = inputs["token_ids"][0]
    token_hash = digest(b"".join(struct.pack("<q", value) for value in tokens))
    check(token_hash == inputs["token_bytes_sha256"] and len(tokens) == 104, "input_tokens_hash")
    check(inputs["text"] == frozen["input_text"] and not inputs["add_special_tokens"] and
          inputs["teacher_forced"] and not inputs["generation"], "input_contract")

    with gzip.open(RUN/"primary-events.jsonl.gz", "rt", encoding="utf-8") as stream:
        events = [json.loads(line) for line in stream]
    groups = defaultdict(list)
    for event in events:
        groups[(event["schedule"], event["call"])].append(event)
    trace = read("primary-trace.json")
    check(trace["status"] == "PASS" and not trace["failures"], "trace_status")
    check(len(events) == trace["event_count"] == 35*28*14, "total_events")
    check(len(groups) == len(trace["calls"]) == 35, "trace_call_count")
    ranges = {}
    for schedule, widths in (("single_prefill", [32]+[1]*16), ("chunked_prefill", [16,16]+[1]*16)):
        cursor = 0
        for index, width in enumerate(widths):
            ranges[(schedule,index)] = (cursor,cursor+width)
            cursor += width
    check(set(groups) == set(ranges), "exact_trace_schedules")
    trace_by_key = {(c["schedule"],c["call"]): c for c in trace["calls"]}
    check(set(trace_by_key) == set(ranges), "exact_trace_records")
    probabilities = []
    trace_errors = {"reference_logits":0.0,"boundary":0.0,"instrumentation_logits":0.0}
    for key, group in groups.items():
        lo, hi = ranges[key]
        expected = shapes(hi-lo, hi, cfg)
        required = {(layer,stage) for layer in range(layers) for stage in expected}
        check(len(group) == len(required) and {(e["layer"],e["stage"]) for e in group} == required, f"event_coverage/{key}")
        for e in group:
            check((e["start"],e["end"]) == (lo,hi), f"event_range/{key}")
            metadata(e, expected[e["stage"]], f"event/{key}/{e['layer']}/{e['stage']}")
        record = trace_by_key[key]
        check(record["pass"] and (record["start"],record["end"],record["query_tokens"]) == (lo,hi,hi-lo), f"call/{key}")
        check(record["event_validation"] == {"pass":True,"events":392,"failures":[]}, f"event_summary/{key}")
        cache_events = [e for e in group if e["stage"] in ("attention.key_cached_post_rope","attention.value_cached")]
        kv_bytes = sum(e["logical_bytes"] for e in cache_events)
        kv_storage = sum(e["storage_bytes"] for e in cache_events)
        check(kv_bytes == 2*layers*hkv*d*hi*4 == record["logical_kv_bytes"] == record["expected_logical_kv_bytes"], f"kv_bytes/{key}")
        check(kv_storage == record["storage_kv_bytes"], f"kv_storage/{key}")
        checks = record["instrumentation_cache"]
        check(len(checks) == layers and {c["layer"] for c in checks} == set(range(layers)) and
              all(c["key_equal"] and c["value_equal"] for c in checks), f"instrumentation_kv/{key}")
        bindings = record["attention_cache_binding"]
        check(len(bindings) == layers and {c["layer"] for c in bindings} == set(range(layers)), f"all_bindings/{key}")
        allowed = list(range(lo+1,hi+1))
        zero, blocked = struct.pack("<f",0.0), bytes.fromhex("ffff7fff")
        expected_mask_sha = digest(b"".join(zero if col <= row else blocked for row in range(lo,hi) for col in range(hi)))
        for binding in bindings:
            check(all(binding[k] for k in ("key_equal","value_equal","key_storage_shared","value_storage_shared")), f"cache_binding/{key}")
            mask = binding["actual_additive_mask"]
            check(mask["causal_contract"], f"mask_causal/{key}")
            if mask["present"]:
                metadata(mask,[1,1,hi-lo,hi],f"mask/{key}")
                check(mask["allowed_per_query"] == allowed and mask["sha256"] == expected_mask_sha, f"independent_mask/{key}")
            else:
                check(hi-lo == 1, f"no_mask_decode_only/{key}")
            counts["mask_bindings"] += 1
        boundary = record["boundary_comparisons"]
        required_boundary = {f"{layer}/{stage}" for layer in frozen["selected_layers"] for stage in expected if stage != "attention.probabilities"}
        check(set(boundary) == required_boundary, f"boundary_coverage/{key}")
        for field in boundary.values():
            check(field["pass"] and field["finite"] and math.isfinite(field["max_abs"]), f"boundary_report/{key}")
            trace_errors["boundary"] = max(trace_errors["boundary"],field["max_abs"])
        counts["selected_boundary_reports"] += len(boundary)
        for name in ("reference_logits","instrumentation_logits"):
            field = record[name]
            check(field["pass"] and field["finite"] and math.isfinite(field["max_abs"]), f"trace_logits/{key}/{name}")
            trace_errors[name] = max(trace_errors[name],field["max_abs"])
        prob = [e for e in group if e["stage"] == "attention.probabilities"]
        probabilities.append({"schedule":key[0],"call":key[1],"query_tokens":hi-lo,"total_tokens":hi,
            "per_layer_logical_bytes":prob[0]["logical_bytes"],
            "sum_over_28_layers_logical_bytes":sum(e["logical_bytes"] for e in prob)})
    check(len(trace["negative_controls"]) == 3 and all(c["detected"] for c in trace["negative_controls"]), "metadata_mutations")
    counts.update(events=len(events),trace_calls=len(groups),layers=layers,stages_per_layer=14)

    numeric = []
    for case in frozen["cases"]:
        name, prefix, steps = case["name"],case["prefix"],case["steps"]
        n = read(name+"-numeric.json")
        check(n["status"] == "PASS" and not n["failures"], name+"/status")
        used = prefix+steps
        used_token_hash = digest(b"".join(struct.pack("<q", value) for value in tokens[:used]))
        check(n["setup"]["input_ids_sha256"] == used_token_hash, name+"/tokens")
        check(n["setup"]["used_tokens"] == used and n["setup"]["supplied_tokens"] == len(tokens)
              and n["setup"]["ignored_tokens"] == len(tokens)-used, name+"/token_scope")
        check(n["setup"]["prefix"] == prefix and n["setup"]["steps"] == steps, name+"/setup")
        check(n["tolerances"]["atol"] == frozen["atol"] and n["tolerances"]["rtol"] == frozen["rtol"], name+"/tolerance")
        check(set(n["positive_paths"]) == {"single_prefill","chunked_prefill"}, name+"/paths")
        max_logit, max_kv, positive_count = 0.0,0.0,0
        for schedule, records in n["positive_paths"].items():
            widths = ([prefix] if schedule == "single_prefill" else [prefix//2,prefix-prefix//2])+[1]*steps
            check(len(records) == len(widths), name+"/count")
            cursor = 0
            for record, width in zip(records,widths):
                end = cursor+width
                check(record["passed"] and (record["input_start"],record["input_end"],record["prefix_length"]) == (cursor,end,end), name+"/range")
                fields = cache_comparison(record["comparison"],end,name+"/positive",True,cfg)
                counts["positive_numeric_cache_field_reports"] += len(fields)
                counts["positive_prefix_hash_pairs"] += prefix_integrity(record["prefix_integrity"],cursor,name+"/prefix",cfg)
                max_logit = max(max_logit,record["comparison"]["logits"]["max_abs"])
                max_kv = max(max_kv,max(field["max_abs"] for field in fields))
                cursor = end
                positive_count += 1
        negatives = []
        check(len(n["negative_controls"]) == 2 and {r["name"] for r in n["negative_controls"]} == {"wrong_decode_position_zero","swap_one_layer_kv_heads"}, name+"/negative_set")
        for negative in n["negative_controls"]:
            check(negative["passed"] and negative["detected"] and negative["prefix_length"] == prefix+1, name+"/negative_detected")
            cache_comparison(negative["baseline"],prefix,name+"/negative_baseline",True,cfg)
            fields = cache_comparison(negative["comparison"],prefix+1,name+"/negative_comparison",False,cfg)
            prefix_integrity(negative["prefix_integrity"],prefix,name+"/negative_prefix",cfg)
            changed = (["logits"] if not negative["comparison"]["logits"]["match"] else []) + [f"layer_{f['layer']}.{f['field']}" for f in fields if not f["match"]]
            check(changed and changed == negative["changed_fields"],name+"/changed_fields")
            mutation = negative["mutation"]
            if negative["name"] == "wrong_decode_position_zero":
                check(mutation == {"position_ids":[[0]],"cache_position":[prefix],"correct_position_ids":[[prefix]]},name+"/wrong_position")
            else:
                check(mutation["layer"] == layers//2 and mutation["heads"] == [0,1] and mutation["fields"] == ["keys","values"],name+"/swap")
                changed_hashes = mutation["changed_prefix_hashes"]
                check(len(changed_hashes) == 2 and {x["field"] for x in changed_hashes} == {"keys","values"} and
                      all(x["layer"] == layers//2 and x["before_sha256"] != x["after_sha256"] for x in changed_hashes),name+"/swap_hashes")
            negatives.append({"name":negative["name"],"changed_field_count":len(changed),
                "logits_max_abs":negative["comparison"]["logits"]["max_abs"],
                "max_cache_abs":max(f["max_abs"] for f in fields),"detected":True})
        check(n["totals"] == {"positive_checks":positive_count,"positive_passed":positive_count,"negative_controls":2,"negative_passed":2,"failure_records":0},name+"/totals")
        numeric.append({"name":name,"positive_checks":positive_count,
            "used_token_count":used,"used_token_bytes_sha256":used_token_hash,
            "max_logit_abs":max_logit,"max_cache_abs":max_kv,"negative_controls":negatives})
        counts["numeric_positive_checks"] += positive_count
        counts["semantic_negative_controls"] += len(negatives)
    check(read("summary.json")["status"] == "PASS", "run_summary")
    result = {"status":"PASS" if not failures else "FAIL",
        "scope":"Independent archive structure/hash/layout/closed-form byte audit. Numerical error reports and prefix digests checked for consistency, not recomputed from unsaved tensors. No model execution.",
        "run_directory":str(RUN),"source_commit":COMMIT,"manifest_sha256":sha(RUN/"manifest.json"),
        "artifact_sha256":artifact_hashes,"counts":dict(counts),"failures":failures,
        "parameter_formula_elements":parameter_count,"input_token_count":len(tokens),"input_token_bytes_sha256":token_hash,
        "kv_bytes_per_token_all_28_layers":2*layers*hkv*d*4,
        "kv_bytes_at_32_tokens":2*layers*hkv*d*32*4,"kv_bytes_at_48_tokens":2*layers*hkv*d*48*4,
        "probabilities":probabilities,"trace_reported_error_max":trace_errors,"numeric":numeric,
        "limitations":["No raw numerical output or prefix hash recomputation: raw values are not archived.",
                       "Logical tensor bytes are not measured hardware traffic or total live memory peaks.",
                       "Historical clean-worktree state is runner testimony; source files independently checked against recorded Git commit."]}
    path = OUT/"run-01-audit-results.json"
    path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("status","counts","failures","manifest_sha256","trace_reported_error_max","numeric")},indent=2))
    print("result_sha256="+sha(path))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
