"""Independently decode the image bundle and check it against the task IR."""
import argparse
from collections import Counter
import json
import pathlib
import sys

from task_ir import HERE, TARGET, decode_ir, fields, require

sys.path.insert(0, str(HERE.parent / "control_image_v0_1"))
import image

ROLES = ("mother", "local0", "local1")


def service_summary(parsed):
    result = []
    for instruction in parsed["program"]:
        opcode = instruction["op"]
        if opcode in ("L_RX", "L_TX"):
            transfer = parsed["records"]["transfer"][instruction["c"]]
            result.append((opcode, transfer["edge_id"], transfer["peer_block"], instruction["b"]))
    return result


def verify_local(parsed, buffer, transfers, ready):
    target = f"LC{buffer.block}"
    records = parsed["records"]
    objects = records["object"]
    require(len(objects) == 1 and objects[0]["base_bytes"] == buffer.address and
            objects[0]["object_version"] == TARGET["object_version"],
            target + ".object", "RAW16 storage differs from the task graph")
    program = parsed["program"]
    counts = Counter(i["op"] for i in program)
    expected = {"L_OPEN": 1, "L_DROP": 1, "L_END": 1, "L_RX": 1,
                "L_WAIT": 2 if buffer.block == 0 else 1}
    expected.update({"L_TX": 1} if buffer.block == 0 else {"L_MOVI": 1, "L_REPORT": 1})
    require(counts == expected, target + ".program", "unexpected operations or object lifecycle")
    require(service_summary(parsed) == transfers, target + ".transfer",
            "edge, direction, peer or credit differs from the task graph")
    require([i["x"] for i in program if i["op"] == "L_WAIT"] ==
            [1 << token for _, _, _, token in transfers],
            target + ".wait", "service completion masks differ from the task graph")
    if ready is not None:
        registers = [0] * TARGET["register_count"]
        for ins in program:
            if ins["op"] == "L_MOVI":
                registers[ins["a"]] = ins["x"]
            elif ins["op"] == "L_REPORT":
                require((ins["a"], ins["b"], registers[ins["b"]]) ==
                        (ready.event_id, ready.local_register, ready.value),
                        target + ".ready", "event identity, register or scalar differs")


def verify(data, package):
    graph = decode_ir(data)
    fields(package, "schema manifest manifest_sha256 ir_sha256 target_sha256 images_hex", "bundle")
    require(package["schema"] == "control-ir-build/0.1", "bundle.schema", "unknown build format")
    require(package["ir_sha256"] == image.digest(data), "bundle.ir_sha256", "input provenance mismatch")
    require(package["target_sha256"] == image.digest((HERE / "target.json").read_bytes()),
            "bundle.target_sha256", "target registry provenance mismatch")
    manifest = package["manifest"]
    require(isinstance(manifest, dict) and package["manifest_sha256"] == image.manifest_digest(manifest),
            "bundle.manifest", "manifest integrity mismatch")
    require(manifest.get("bundle") == graph.name, "bundle.manifest", "wrong graph name")
    require(isinstance(package["images_hex"], dict) and set(package["images_hex"]) == set(ROLES),
            "bundle.images_hex", "expected exactly the three controller images")
    require(all(isinstance(value, str) for value in package["images_hex"].values()),
            "bundle.images_hex", "image values must be hexadecimal strings")
    images = {key: bytes.fromhex(value) for key, value in package["images_hex"].items()}
    parsed = image.validate_bundle(manifest, images)
    require(tuple(parsed[key]["header"]["program_image_id"] for key in ROLES) == graph.image_ids,
            "bundle.images", "image identities differ from the task graph")

    relay, destination = graph.buffers
    ingress, forward = graph.transfers
    verify_local(parsed["local0"], relay,
                 [("L_RX", ingress.edge, TARGET["host"], ingress.receive_token),
                  ("L_TX", forward.edge, destination.block, forward.send_token)], None)
    verify_local(parsed["local1"], destination,
                 [("L_RX", forward.edge, relay.block, forward.receive_token)], graph.ready)

    mother = parsed["mother"]
    ops = [ins["op"] for ins in mother["program"]]
    require(ops[:3] == ["G_CALL", "G_EVENT", "G_CALL"] and ops[-1:] == ["G_END"] and
            all(op == "G_WAIT" for op in ops[3:-1]),
            "mother.program", "expected READY-gated producer launch and completion drain")
    calls = [(i["a"], i["b"]) for i in mother["program"] if i["op"] == "G_CALL"]
    require(calls == [(destination.block, destination.completion_token),
                      (relay.block, relay.completion_token)],
            "mother.call", "target order or completion credit differs from the task graph")
    event = mother["program"][1]
    require((event["a"], event["b"]) == (graph.ready.mother_register, graph.ready.event_id),
            "mother.event", "READY binding or destination register differs")
    bindings = mother["records"]["event_binding"]
    require(len(bindings) == 1 and
            (bindings[0]["source_block"], bindings[0]["event_id"], bindings[0]["message_kind"]) ==
            (destination.block, graph.ready.event_id, 0),
            "mother.binding", "READY source does not match the declared consumer")
    token = {item.name: item.completion_token for item in graph.buffers}
    wait_masks = [i["x"] for i in mother["program"] if i["op"] == "G_WAIT"]
    require(wait_masks == [sum(1 << token[name] for name in group) for group in graph.wait_groups],
            "mother.wait", "completion masks or grouping differ from the task graph")
    return images, dict(graph=graph.name, mother_ops=ops, wait_masks=wait_masks,
                        s_byte_addresses=[item.address for item in graph.buffers],
                        ready_scalar=graph.ready.value, mother_register=graph.ready.mother_register)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ir", type=pathlib.Path)
    parser.add_argument("bundle", type=pathlib.Path)
    args = parser.parse_args()
    try:
        _, report = verify(args.ir.read_bytes(), json.loads(args.bundle.read_text(encoding="utf-8")))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"{exc}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
