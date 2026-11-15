"""Bind exact half-rotation RoPE regions from sealed Algo1 graphs."""

import argparse
from collections import defaultdict
from functools import lru_cache
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path

from bind_attention_graph import broadcast, sealed_graphs


def bind_rope(graph):
    values, weights = graph["values"], set(graph["weights"])
    graph_inputs, graph_outputs = set(graph["inputs"]), set(graph["outputs"])
    producers, consumers = {}, defaultdict(list)
    for task in graph["tasks"]:
        for output in task["outputs"]:
            if output in producers:
                raise ValueError(f"multiple producers for {output}")
            producers[output] = task
        for port, operand in enumerate(task["inputs"]):
            consumers[operand].append((task, port))

    def tensor(name):
        row = values[name]
        shape = row["shape"]
        if any(type(dim) is not int or dim <= 0 for dim in shape):
            raise ValueError(f"unsupported concrete shape for {name}")
        return dict(tensor=name, shape=shape, dtype=row["dtype"])

    def node(task, op, arity):
        if (task is None or task["op"] != op or task.get("domain") or len(task["inputs"]) != arity
                or len(task["outputs"]) != 1 or (op != "Concat" and task.get("attributes"))):
            raise ValueError(f"expected standard {op} with {arity} inputs")
        return task

    def only_consumer(value, op, arity):
        if value in graph_outputs or len(consumers[value]) != 1:
            raise ValueError(f"RoPE intermediate has an external consumer: {value}")
        task, port = consumers[value][0]
        return node(task, op, arity), port

    def exclusive(value, user, port):
        if value in graph_outputs or consumers[value] != [(user, port)]:
            raise ValueError(f"RoPE intermediate has an external consumer: {value}")

    def static(name):
        return name in weights and name not in graph_inputs and name not in producers

    def slice_bounds(task):
        result = {}
        for role, name in zip(("start", "end", "axis", "step"), task["inputs"][1:], strict=True):
            row = tensor(name)
            data = values[name].get("constant")
            if (not static(name) or row["dtype"] not in {"INT32", "INT64"} or row["shape"] != [1]
                    or not isinstance(data, list) or len(data) != 1 or type(data[0]) is not int):
                raise ValueError(f"Slice {role} is not a sealed integer vector: {name}")
            result[role] = dict(row, value=data)
        return result

    def finite_array(data, shape):
        if not shape:
            return type(data) in (int, float) and isfinite(data)
        return isinstance(data, list) and len(data) == shape[0] and all(
            finite_array(value, shape[1:]) for value in data)

    @lru_cache(maxsize=None)
    def coefficient(name):
        if not static(name):
            raise ValueError(f"RoPE coefficient is not a sealed initializer: {name}")
        row = tensor(name)
        if "constant" in values[name]:
            data = values[name]["constant"]
            if not finite_array(data, row["shape"]):
                raise ValueError(f"embedded coefficient does not match its layout: {name}")
            digest = sha256(json.dumps(data, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
            return dict(row, source="embedded_initializer", constant_sha256=digest)
        return dict(row, source="referenced_initializer")

    def bind(concat):
        node(concat, "Concat", 2)
        negated, low = concat["inputs"]
        negative = node(producers.get(negated), "Neg", 1)
        high, = negative["inputs"]
        low_slice = node(producers.get(low), "Slice", 5)
        high_slice = node(producers.get(high), "Slice", 5)
        source = low_slice["inputs"][0]
        if high_slice["inputs"][0] != source:
            raise ValueError("rotation halves have different source tensors")
        activation = tensor(source)
        shape, dtype = activation["shape"], activation["dtype"]
        if len(shape) < 2 or shape[-1] % 2 or dtype not in {"FLOAT", "FLOAT16", "BFLOAT16", "DOUBLE"}:
            raise ValueError("rotation needs a floating tensor with an even last dimension")
        rank, width = len(shape), shape[-1]
        half = width // 2
        attrs = concat.get("attributes", {})
        if set(attrs) != {"axis"} or type(attrs["axis"]) is not int or attrs["axis"] not in (-1, rank - 1):
            raise ValueError("rotation Concat must use the last axis")
        bounds = [slice_bounds(task) for task in (low_slice, high_slice)]
        for branch, start, ends in zip(bounds, (0, half), ({half}, {width, 2**63 - 1}), strict=True):
            exact = {key: row["value"][0] for key, row in branch.items()}
            if (exact["start"] != start or exact["end"] not in ends
                    or exact["axis"] not in (-1, rank - 1) or exact["step"] != 1):
                raise ValueError("Slice constants do not select the two exact last-axis halves")
        exclusive(low, concat, 1)
        exclusive(high, negative, 0)
        exclusive(negated, concat, 0)

        rotated, = concat["outputs"]
        sine_mul, rotated_port = only_consumer(rotated, "Mul", 2)
        sine = coefficient(sine_mul["inputs"][1 - rotated_port])
        sine_product, = sine_mul["outputs"]
        add, sine_port = only_consumer(sine_product, "Add", 2)
        cosine_product = add["inputs"][1 - sine_port]
        cosine_mul = node(producers.get(cosine_product), "Mul", 2)
        if cosine_mul["inputs"].count(source) != 1:
            raise ValueError("cosine branch must use the original activation once")
        cosine = coefficient(next(value for value in cosine_mul["inputs"] if value != source))
        if cosine["tensor"] == sine["tensor"] or cosine["shape"] != sine["shape"]:
            raise ValueError("cosine and sine need distinct tensors with the same layout")
        if (not cosine["shape"] or cosine["shape"][-1] != width
                or broadcast(cosine["shape"], shape) != shape
                or cosine["dtype"] != dtype or sine["dtype"] != dtype):
            raise ValueError("coefficient layout must broadcast to the activation without changing its lanes")
        exclusive(cosine_product, add, 1 - sine_port)
        output, = add["outputs"]
        for name, expected in [(value, shape[:-1] + [half]) for value in (low, high, negated)] + [
                (value, shape) for value in (rotated, sine_product, cosine_product, output)]:
            row = tensor(name)
            if row["shape"] != expected or row["dtype"] != dtype:
                raise ValueError(f"rotation intermediate shape or dtype mismatch at {name}")
        steps = (low_slice, high_slice, negative, concat, sine_mul, cosine_mul, add)
        return dict(input=activation, output=tensor(output), cosine=cosine, sine=sine,
                    rotate_axis=attrs["axis"], normalized_axis=rank - 1,
                    slices=[dict(node=task["id"], output=tensor(task["outputs"][0]), bounds=branch)
                            for task, branch in zip((low_slice, high_slice), bounds, strict=True)],
                    operations=[task["id"] for task in steps],
                    output_consumers=[dict(operation=user["id"], input=port) for user, port in consumers[output]],
                    graph_output=output in graph_outputs)

    regions, unmatched = [], []
    for task in graph["tasks"]:
        if task["op"] != "Concat":
            continue
        input_ops = {producers.get(operand, {}).get("op") for operand in task["inputs"]}
        if not {"Neg", "Slice"} <= input_ops:
            continue
        try:
            regions.append(bind(task))
        except ValueError as error:
            unmatched.append(dict(operation=task["id"], reason=str(error)))
    return regions, unmatched


def bind_request(request_path, expected_regions=None):
    payload = request_path.read_bytes()
    bindings = []
    for identity, graph in sealed_graphs(request_path, json.loads(payload)):
        regions, unmatched = bind_rope(graph)
        if expected_regions is not None and (len(regions) != expected_regions or unmatched):
            raise ValueError(f"{identity['graph']}: expected {expected_regions} RoPE regions, "
                             f"got {len(regions)} with unmatched rotations {unmatched}")
        bindings.append(dict(identity, rope=regions, unmatched_rotations=unmatched))
    return dict(schema="native-request-rope-bindings/1", request_sha256=sha256(payload).hexdigest(),
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
