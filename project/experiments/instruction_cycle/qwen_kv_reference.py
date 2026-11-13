"""Validate the archived Qwen2.5-3B integer KV window around a segment boundary."""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile


RECEIPTS = {
    2: (
        "f3a7c30449ff899d403e67b40d9ea5eaccdca4d4822b050a833d0565b8c781af",
        "e8bd0094282e0fe2b9e454aefa136ce3f606c101d743c599dac274d2d4fb6605",
    ),
    3: (
        "b29ac83bfaad6fb30a687527324039199848501d83bf047adabbc981112f4466",
        "d06b092aa4429a0b4789927b1451190d1406635f522adaa3c44ef0ae0a327ad0",
    ),
}
STEPS = (11, 12, 13)
LAYERS = 36
EXPONENT = -20
CHUNK_SIZE = 1 << 20


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_pinned_json(path, expected):
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, f"SHA-256 mismatch: {path}")
    return json.loads(raw)


def stream_sha256(stream):
    digest = hashlib.sha256()
    size = 0
    for block in iter(lambda: stream.read(CHUNK_SIZE), b""):
        digest.update(block)
        size += len(block)
    return digest.hexdigest(), size


def kv_shape(tokens):
    return [1, 2, tokens, 128]


def read_state(path, expected, rows):
    with path.open("rb") as stream:
        archive_sha, _ = stream_sha256(stream)
        require(archive_sha == expected, f"SHA-256 mismatch: {path}")
        with ZipFile(stream) as archive:
            names = archive.namelist()
            expected_names = {f"next_{layer}_{kind}.npy" for layer in range(LAYERS) for kind in "kv"}
            require(len(names) == len(expected_names) and set(names) == expected_names,
                    "wrong KV archive members")
            for row in rows:
                with archive.open(f"{row['source']}.npy") as tensor:
                    require(tensor.read(8) == b"\x93NUMPY\x01\x00", "unsupported NumPy array header")
                    header_size = int.from_bytes(tensor.read(2), "little")
                    require(0 < header_size <= 4096, "invalid NumPy array header size")
                    header = ast.literal_eval(tensor.read(header_size).decode("ascii").strip())
                    expected_header = {"descr": "<i4", "fortran_order": False, "shape": tuple(row["shape"])}
                    require(header == expected_header, f"wrong S32 layout for {row['source']}")
                    digest, size = stream_sha256(tensor)
                    require(size == 4 * row["logical_elements"] and digest == row["canonical_s32_sha256"],
                            f"KV payload differs from next-step input: {row['source']}")


def check_format(formats, name, shape):
    fmt = formats[name]
    require((fmt["shape"], fmt["bits"], fmt["exponent"]) == (shape, 32, EXPONENT),
            f"wrong S32 handoff format for {name}")


def kv_append(program, nodes, row, prefix):
    past, output = row["input"], row["source"]
    check_format(program["runtime_formats"], past, kv_shape(prefix))
    check_format(program["output_formats"], output, kv_shape(prefix + 1))
    layer = int(output.split("_")[1])
    kernel_prefix = f"/model/model/layers.{layer}/self_attn/"
    result_id = program["outputs"][output]
    concat = nodes[result_id]
    if concat["op"] == "Convert":
        require(len(concat["inputs"]) == 1, f"ambiguous output conversion: {output}")
        concat = nodes[concat["inputs"][0]]
    require(concat["op"] == "Concat" and concat["kernel"].startswith(kernel_prefix)
            and concat["attributes"]["axis"] in (-2, 2) and concat["shape"] == kv_shape(prefix + 1)
            and len(concat["inputs"]) == 2, f"wrong attention append: {output}")
    history, new = concat["inputs"]
    if history != past:
        convert = nodes[history]
        require(convert["op"] == "Convert" and convert["inputs"] == [past]
                and convert["shape"] == kv_shape(prefix), f"wrong append history: {output}")
    require(nodes[new]["shape"] == kv_shape(1), f"wrong new-token append shape: {output}")
    return {**row, "output_ssa": result_id, "concat_ssa": concat["id"],
            "new_token_ssa": new, "output_shape": kv_shape(prefix + 1)}


def adjacent_layer_edges(instructions, nodes, first_layer):
    producer_prefix = f"/model/model/layers.{first_layer}/"
    consumer_prefix = f"/model/model/layers.{first_layer + 1}/input_layernorm/"
    edges = []
    for consumer in instructions:
        if not consumer["kernel"].startswith(consumer_prefix):
            continue
        for name in consumer["inputs"]:
            producer = nodes.get(name)
            if (producer and producer["op"] == "Add" and producer["shape"] == [1, 1, 2048]
                    and producer["kernel"].startswith(producer_prefix)):
                edges.append({"producer_ssa": name, "producer_kernel": producer["kernel"],
                              "consumer_ssa": consumer["id"], "consumer_kernel": consumer["kernel"],
                              "shape": producer["shape"]})
    require(bool(edges), "missing adjacent-layer residual handoff")
    return edges


def audit_step(path, check, ordinal, first_layer):
    raw = (path / "receipt.json").read_bytes()
    receipt = json.loads(raw)
    require(receipt == check, f"step receipt differs from pinned segment: {path}")
    prefix = 512 + ordinal - 1
    require(receipt["step"] == ordinal and receipt["prefix_tokens"] == prefix
            and receipt["query_tokens"] == 1 and receipt["passed"] is True
            and receipt["top1_equal"] is True and len(receipt["outputs"]) == 1 + 2 * LAYERS,
            f"wrong decode step or failed numeric checks: {path}")
    handoff = receipt["handoff"]
    require(handoff["origin"] == "previous emitted integer program outputs"
            and handoff["prefix_tokens"] == prefix and handoff["physical_movement_inferred"] is False,
            f"wrong handoff provenance: {path}")
    rows = handoff["state"]
    by_input = {row["input"]: row for row in rows}
    expected = {f"past_{layer}_{kind}" for layer in range(LAYERS) for kind in "kv"}
    require(handoff["state_count"] == len(rows) == len(expected) and set(by_input) == expected,
            f"missing or duplicate KV entries: {path}")

    program = read_pinned_json(path / "program.json", receipt["program_sha256"])
    require(program["source_sha256"] == receipt["onnx_sha256"] and program["input_ids_shape"] == [1, 1],
            f"wrong source graph or batch/token shape: {path}")
    instructions = program["instructions"]
    nodes = {node["id"]: node for node in instructions}
    require(len(nodes) == len(instructions), f"duplicate integer SSA id: {path}")
    selected = []
    for layer in (first_layer, first_layer + 1):
        for kind in "kv":
            row = by_input[f"past_{layer}_{kind}"]
            require(row["source"] == f"next_{layer}_{kind}" and row["shape"] == kv_shape(prefix)
                    and row["exponent"] == EXPONENT and row["logical_elements"] == 2 * prefix * 128
                    and re.fullmatch("[0-9a-f]{64}", row["canonical_s32_sha256"]),
                    f"wrong KV handoff row: {row['input']}")
            selected.append(kv_append(program, nodes, row, prefix))
    return {"step": ordinal, "prefix_tokens": prefix, "integer_selected_token": receipt["integer_selected_token"],
            "receipt_sha256": hashlib.sha256(raw).hexdigest(),
            "program_sha256": receipt["program_sha256"], "onnx_sha256": receipt["onnx_sha256"],
            "kv": selected, "adjacent_layer_edges": adjacent_layer_edges(instructions, nodes, first_layer)}


def audit_window(root, case=2, first_layer=0):
    """Return logical lineage, verifying archived S32 bytes at the segment boundary."""
    require(case in RECEIPTS and 0 <= first_layer < LAYERS - 1, "unsupported case or adjacent layers")
    root = Path(root)
    parts = [root / f"part-{part}" / f"case-{case}" for part in (0, 1)]
    receipts = [read_pinned_json(path / "receipt.json", digest)
                for path, digest in zip(parts, RECEIPTS[case])]
    earlier, later = receipts
    identity = earlier["identity"]
    require(identity == later["identity"] and identity["tiny"] is False
            and identity["parameter_count"] == 3_085_938_688 and len(identity["prompt"]) == 512
            and identity["generated_token_target"] == 128 and identity["kv_exponent"] == EXPONENT,
            "wrong model, prompt length or KV format in segment receipts")
    for receipt in receipts:
        require(receipt["batch_numeric_passed"] is True and receipt["sequence_numeric_passed"] is True
                and receipt["systemc_time_qualified"] is False and receipt["state_count"] == 2 * LAYERS
                and receipt["live_integer_state_origin"] == "empty-cache emitted integer prefill, then only emitted integer outputs",
                "wrong numeric or timing scope in segment receipts")
    require(later["ancestry"] == [{"receipt_sha256": RECEIPTS[case][0],
                                   "accepted_generated_tokens": 12, "numeric_passed": True}],
            "part-1 ancestry differs from archived part-0")
    history = later["generated_tokens"]
    require(not earlier["ancestry"] and len(earlier["generated_tokens"]) == 12
            and history[:12] == earlier["generated_tokens"], "generated token history differs across segments")
    steps = []
    for ordinal in STEPS:
        part = int(ordinal >= 12)
        check = receipts[part]["checks"][ordinal - 12 * part]
        step = audit_step(parts[part] / f"step-{ordinal:02d}", check, ordinal, first_layer)
        require(step["integer_selected_token"] == history[ordinal], "selected token differs from segment history")
        step["previous_selected_token_from_receipt"] = history[ordinal - 1]
        steps.append(step)
    read_state(parts[0] / "state.npz", earlier["state_sha256"], steps[1]["kv"])
    return {
        "case": case, "layers": [first_layer, first_layer + 1], "steps": steps,
        "parameter_count": identity["parameter_count"], "prompt_tokens": len(identity["prompt"]),
        "prompt_ids_json_sha256": hashlib.sha256(json.dumps(identity["prompt"], separators=(",", ":")).encode()).hexdigest(),
        "weights_manifest_sha256": identity["weights_manifest_sha256"],
        "segment_receipt_sha256": list(RECEIPTS[case]), "segment_boundary_state_sha256": earlier["state_sha256"],
        "transitions": [
            {"source_step": 11, "consumer_step": 12, "evidence": "verified_archived_s32_payload"},
            {"source_step": 12, "consumer_step": 13, "evidence": "pinned_integer_handoff_receipt"},
        ],
        "physical_binding_qualified": False, "timing_qualified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="archived sequence-range-segments-OT8GaRTa directory")
    parser.add_argument("--case", action="append", type=int, choices=tuple(RECEIPTS))
    parser.add_argument("--first-layer", default=0, type=int)
    args = parser.parse_args()
    try:
        cases = [audit_window(args.root, case, args.first_layer) for case in (args.case or [2])]
    except (BadZipFile, KeyError, IndexError, OSError, SyntaxError, TypeError, ValueError) as exc:
        parser.exit(1, f"Qwen KV reference failed: {exc}\n")
    print(json.dumps({"schema": "issue265-qwen-kv-reference/1", "cases": cases}, indent=2))


if __name__ == "__main__":
    main()
