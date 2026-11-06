"""Compile the bounded RAW16/P task IR to a three-controller image bundle."""
import argparse
import json
import os
import pathlib
import sys
import tempfile

from task_ir import HERE, TARGET, decode_ir, require

sys.path.insert(0, str(HERE.parent / "control_image_v0_1"))
import image

SCHEMA = "control-ir-build/0.1"
ROLES = ("mother", "local0", "local1")
SIZE = TARGET["object_bytes"]
S_RESOURCE = 1 << 5


def transfer_record(transfer, *, transmit, peer):
    return dict(direction=int(transmit), format=4, object_id=0, port_id=TARGET["port"],
                peer_block=peer, peer_port=TARGET["port"], peer_object=0,
                count_bytes=SIZE, edge_id=transfer.edge, invocation=TARGET["invocation"],
                fragment=0, object_version=TARGET["object_version"], max_fragment_bytes=SIZE)


def local_image(buffer, ingress, egress, ready, image_id, instruction_version):
    peer = TARGET["host"] if buffer.block == 0 else 0
    transfers = [transfer_record(ingress, transmit=False, peer=peer)]
    program = [dict(op="L_OPEN", a=0), dict(op="L_RX", b=ingress.receive_token, c=0)]
    if ready is not None:
        program.extend([dict(op="L_MOVI", a=ready.local_register, x=ready.value),
                        dict(op="L_REPORT", a=ready.event_id, b=ready.local_register, c=0)])
    program.append(dict(op="L_WAIT", x=1 << ingress.receive_token))
    if egress is not None:
        transfers.append(transfer_record(egress, transmit=True, peer=1))
        program.extend([dict(op="L_TX", b=egress.send_token, c=1),
                        dict(op="L_WAIT", x=1 << egress.send_token)])
    program.extend([dict(op="L_DROP", a=0), dict(op="L_END")])
    task = dict(block_type=0, entry_pc=0, max_steps=len(program),
                required_resources=S_RESOURCE, program_image_id=image_id,
                topology_id=TARGET["topology_id"], native_abi_id=TARGET["native_abi_id"],
                input_object_mask=1, output_object_mask=int(egress is not None))
    obj = dict(object_id=0, base_bytes=buffer.address, capacity_bytes=SIZE, length_bytes=SIZE,
               format=4, object_version=TARGET["object_version"], native_abi_id=TARGET["native_abi_id"])
    return image.assemble_image("local", program,
                                dict(task=[task], object=[obj], transfer=transfers),
                                image_id, S_RESOURCE, instruction_version=instruction_version)


def compile_ir(data, *, instruction_version=image.compact.LEGACY_VERSION):
    graph = decode_ir(data)
    require((image.ABI, image.TOPOLOGY, image.PROFILE_ID) ==
            (TARGET["native_abi_id"], TARGET["topology_id"], TARGET["capacity_profile_id"]),
            "target", "assembler registry mismatch")
    relay, destination = graph.buffers
    ingress, forward = graph.transfers
    ready = graph.ready
    mother_id, relay_id, destination_id = graph.image_ids

    program = [dict(op="G_CALL", a=destination.block, b=destination.completion_token, c=0),
               dict(op="G_EVENT", a=ready.mother_register, b=ready.event_id),
               dict(op="G_CALL", a=relay.block, b=relay.completion_token, c=0)]
    tokens = {item.name: item.completion_token for item in graph.buffers}
    program.extend(dict(op="G_WAIT", x=sum(1 << tokens[name] for name in group))
                   for group in graph.wait_groups)
    program.append(dict(op="G_END"))
    binding = dict(event_id=ready.event_id, source_block=destination.block, message_kind=0)
    images = {
        "mother": image.assemble_image("mother", program, {"event_binding": [binding]}, mother_id,
                                       instruction_version=instruction_version),
        "local0": local_image(relay, ingress, forward, None, relay_id, instruction_version),
        "local1": local_image(destination, forward, None, ready, destination_id, instruction_version),
    }
    manifest = dict(schema="control-image-bundle/0.1", bundle=graph.name,
                    topology_id=image.TOPOLOGY, native_abi_id=image.ABI,
                    capacity_profile_id=image.PROFILE_ID,
                    images={key: dict(bytes=len(images[key]), sha256=image.digest(images[key]),
                                      program_image_id=image_id)
                            for key, image_id in zip(ROLES, graph.image_ids)})
    image.validate_bundle(manifest, images)
    return dict(schema=SCHEMA, manifest=manifest, manifest_sha256=image.manifest_digest(manifest),
                ir_sha256=image.digest(data), target_sha256=image.digest((HERE / "target.json").read_bytes()),
                images_hex={role: data.hex() for role, data in images.items()})


def write_bundle(path, bundle):
    payload = json.dumps(bundle, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
            temporary = pathlib.Path(file.name)
            file.write(payload)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--instruction-version", type=int, choices=image.compact.VERSIONS,
                        default=image.compact.LEGACY_VERSION,
                        help="1 for 128-bit instructions or 2 for compact 64-bit instructions")
    args = parser.parse_args()
    try:
        if args.input.resolve() == args.output.resolve():
            raise ValueError("output must differ from the input IR")
        bundle = compile_ir(args.input.read_bytes(), instruction_version=args.instruction_version)
        write_bundle(args.output, bundle)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"{exc}\n")
    print(f"Wrote {args.output} with manifest SHA-256 {bundle['manifest_sha256']}")


if __name__ == "__main__":
    main()
