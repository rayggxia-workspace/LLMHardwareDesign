"""Bind graph-defined QK, scale, optional additive mask, Softmax and AV regions."""

import argparse
from collections import defaultdict
from hashlib import sha256
from itertools import zip_longest
import json
from math import isfinite
from pathlib import Path


def broadcast(left, right):
    result = []
    for a, b in zip_longest(reversed(left), reversed(right), fillvalue=1):
        if a != b and a != 1 and b != 1:
            raise ValueError(f"incompatible broadcast shapes {left} and {right}")
        result.append(b if a == 1 else a)
    return list(reversed(result))


def bind_attention(graph):
    """Return composable region bindings and reasons for unmatched Softmax nodes."""
    values = graph["values"]
    producers, consumers = {}, defaultdict(list)
    outputs = set(graph["outputs"])
    for task in graph["tasks"]:
        for value in task["outputs"]:
            if value in producers:
                raise ValueError(f"multiple producers for {value}")
            producers[value] = task
        for port, value in enumerate(task["inputs"]):
            consumers[value].append((task, port))

    def tensor(value):
        row = values[value]
        shape = row["shape"]
        if any(type(dim) is not int or dim <= 0 for dim in shape):
            raise ValueError(f"unsupported concrete shape for {value}")
        return dict(tensor=value, shape=shape, dtype=row["dtype"])

    def require(task, operation, arity):
        if (task["op"] != operation or task.get("domain") or len(task["inputs"]) != arity
                or len(task["outputs"]) != 1 or (operation != "Softmax" and task.get("attributes"))):
            raise ValueError(f"unsupported {operation} operation {task['id']}")

    def predecessor(task, operation):
        ports = [value for value in task["inputs"] if producers.get(value, {}).get("op") == operation]
        if len(ports) != 1:
            raise ValueError(f"expected one {operation} input to {task['id']}")
        value, = ports
        other, = (name for name in task["inputs"] if name != value)
        return producers[value], other

    def bind(softmax):
        require(softmax, "Softmax", 1)
        logits, = softmax["inputs"]
        probabilities, = softmax["outputs"]
        previous = producers.get(logits)
        if previous is None:
            raise ValueError("Softmax input has no score producer")
        mask = None
        mask_node = None
        if previous["op"] == "Add":
            mask_node = previous
            require(mask_node, "Add", 2)
            previous, mask = predecessor(mask_node, "Mul")
        scale_node = previous
        require(scale_node, "Mul", 2)
        qk, coefficient = predecessor(scale_node, "MatMul")
        require(qk, "MatMul", 2)
        q, k = qk["inputs"]
        scale = tensor(coefficient)
        constant = values[coefficient].get("constant")
        if scale["shape"] == [1] and isinstance(constant, list) and len(constant) == 1:
            constant = constant[0]
        if scale["shape"] not in ([], [1]) or type(constant) not in (int, float) or not isfinite(constant):
            raise ValueError(f"unsupported static scale tensor {coefficient}")
        scale["value"] = constant

        if len(consumers[probabilities]) != 1 or consumers[probabilities][0][1] != 0:
            raise ValueError("Softmax output must be the exclusive left operand of AV")
        av, _ = consumers[probabilities][0]
        require(av, "MatMul", 2)
        v = av["inputs"][1]
        result, = av["outputs"]
        query, key, value, output = (tensor(name) for name in (q, k, v, result))
        qs, ks, vs = (row["shape"] for row in (query, key, value))
        if min(len(qs), len(ks), len(vs)) < 2 or qs[-1] != ks[-2] or ks[-1] != vs[-2]:
            raise ValueError("incompatible QK or AV contraction dimensions")
        score_shape = broadcast(qs[:-2], ks[:-2]) + [qs[-2], ks[-1]]
        expected = broadcast(score_shape[:-2], vs[:-2]) + [qs[-2], vs[-1]]
        axis = softmax.get("attributes", {}).get("axis")
        if (set(softmax.get("attributes", {})) != {"axis"} or type(axis) is not int
                or axis not in (-1, len(score_shape) - 1)):
            raise ValueError("Softmax must explicitly normalize the last score axis")
        if output["shape"] != expected:
            raise ValueError("AV output shape disagrees with the contractions")
        if mask is not None and broadcast(tensor(mask)["shape"], score_shape) != score_shape:
            raise ValueError("additive mask changes score dimensions")
        steps = [qk, scale_node] + ([mask_node] if mask_node is not None else []) + [softmax, av]
        for step, following in zip(steps, steps[1:]):
            edge, = step["outputs"]
            if (edge in outputs or [user["id"] for user, _ in consumers[edge]] != [following["id"]]):
                raise ValueError(f"intermediate has an external consumer: {edge}")
            if tensor(edge)["shape"] != score_shape:
                raise ValueError(f"score shape mismatch at {edge}")
        dtypes = {tensor(name)["dtype"] for step in steps for name in step["inputs"] + step["outputs"]}
        if len(dtypes) != 1 or query["dtype"] not in {"FLOAT", "FLOAT16", "BFLOAT16", "DOUBLE"}:
            raise ValueError("unsupported Attention dtype combination")
        mask_binding = None if mask is None else dict(tensor(mask), mode="additive", source=(
            "initializer" if mask in graph.get("weights", ()) else "graph_value"))
        return dict(query=query, transposed_key=key, value=value, scale=scale, mask=mask_binding,
                    scores=tensor(qk["outputs"][0]), scaled_scores=tensor(scale_node["outputs"][0]),
                    logits=tensor(logits), probabilities=tensor(probabilities), output=output,
                    softmax_axis=axis, normalized_axis=len(score_shape) - 1,
                    operations=[step["id"] for step in steps],
                    output_consumers=[dict(operation=user["id"], input=port) for user, port in consumers[result]],
                    graph_output=result in outputs)

    bound, unmatched = [], []
    for task in graph["tasks"]:
        if task["op"] == "Softmax":
            try:
                bound.append(bind(task))
            except ValueError as error:
                unmatched.append(dict(operation=task["id"], reason=str(error)))
    return bound, unmatched


def sealed_graphs(request_path, request):
    """Read every hash-verified source graph in the request's execution order."""
    if request.get("schema") != "algo1-request-input/1":
        raise ValueError("unsupported request graph seal")
    workload = request["workload"]
    expected_phases = [("prefill", None), *((("decode", past) for past in
                       range(workload["first_decode_past"], workload["last_decode_past"] + 1)))]
    if len(request["graphs"]) != len(expected_phases) or len(expected_phases) != workload["generated_tokens"]:
        raise ValueError("incomplete sealed request graph sequence")
    for entry, (phase, past) in zip(request["graphs"], expected_phases, strict=True):
        name = f"{phase}.json" if past is None else f"{phase}-{past}.json"
        if (entry["graph"], entry["phase"], entry.get("past")) != (name, phase, past):
            raise ValueError(f"invalid sealed request graph entry for {name}")
        raw = (request_path.parent / name).read_bytes()
        if sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError(f"invalid sealed graph {name}")
        graph = json.loads(raw)
        seal = graph["execution_binding"]
        if (seal["manifest_sha256"] != request["manifest_sha256"]
                or seal["frontend_sha256"] != request["frontend_sha256"]
                or (seal["phase"], seal["past"]) != (phase, past)):
            raise ValueError(f"graph provenance does not match the sealed request for {name}")
        yield dict(graph=name, graph_sha256=entry["sha256"], phase=phase, past=past), graph


def bind_request(request_path, expected_regions=None):
    payload = request_path.read_bytes()
    bindings = []
    for identity, graph in sealed_graphs(request_path, json.loads(payload)):
        regions, unmatched = bind_attention(graph)
        if expected_regions is not None and (len(regions) != expected_regions or unmatched):
            raise ValueError(f"{identity['graph']}: expected {expected_regions} Attention regions, "
                             f"got {len(regions)} with unmatched Softmax nodes {unmatched}")
        bindings.append(dict(identity, attention=regions, unmatched_softmax=unmatched))
    return dict(schema="native-request-attention-bindings/1", request_sha256=sha256(payload).hexdigest(),
                scope="structural", bindings=bindings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-regions", type=int)
    args = parser.parse_args()
    bindings = bind_request(args.request, args.expected_regions)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(bindings, output, separators=(",", ":"))
        output.write("\n")


if __name__ == "__main__":
    main()
