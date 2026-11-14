"""Verify the sealed native inputs and recover the exact DDR prompt for audit."""

import argparse
from bisect import bisect_right
from hashlib import sha256
import json
from pathlib import Path
from struct import pack, unpack_from

from native_rtl_retirements import program_binding


def digest(path):
    result = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            result.update(chunk)
    return result.hexdigest()


def verify_seal(directory):
    seal = directory / "proof.sha256"
    members = {}
    for line in seal.read_text(encoding="ascii").splitlines():
        expected, name = line.split("  ", 1)
        if name in members or Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError(f"invalid or duplicate sealed member {name}")
        if digest(directory / name) != expected:
            raise ValueError(f"sealed member changed: {name}")
        members[name] = expected
    return digest(seal), members


def prepare(program, memory, state_path, reference, run_id, output):
    deployment, programs = verify_seal(program)
    memory_seal, memory_files = verify_seal(memory)
    if not {"input-index.tsv", "ddr-writes.tsv"} <= programs.keys() or not {
            "memory-binding.json", "ddr-initial.tsv", "initial-assets.sha256"} <= memory_files.keys():
        raise ValueError("request or memory seal lacks a required table")
    state = json.loads(state_path.read_bytes())
    if state["schema"] != "native-state-rows/1" or len(state["phases"]) != 128:
        raise ValueError("expected all 128 persistent state phases")
    evidence = program_binding(program, deployment, state["phases"])
    binding = json.loads((memory / "memory-binding.json").read_bytes())
    if (binding["write_binding"]["package_proof_sha256"] != deployment or
            binding["write_binding"]["write_table_sha256"] != programs["ddr-writes.tsv"]):
        raise ValueError("initial DDR and writable state target different deployments")

    assets = {}
    for line in (memory / "initial-assets.sha256").read_text(encoding="ascii").splitlines():
        expected, name = line.split("  ", 1)
        if name in assets or digest(Path(name)) != expected:
            raise ValueError(f"invalid or changed initial DDR asset {name}")
        assets[name] = expected
    regions = {}
    count, *rows = (memory / "ddr-initial.tsv").read_text(encoding="ascii").splitlines()
    end = 0
    for row in rows:
        base, size, name = row.split()
        base, size = int(base), int(size)
        if (base < end or size <= 0 or (base | size) % 64 or name not in assets or
                Path(name).stat().st_size != size):
            raise ValueError(f"invalid initial DDR region {row}")
        regions[base] = size, Path(name)
        end = base + size
    if int(count) != len(regions) or len(regions) != binding["readonly_assets"]:
        raise ValueError("initial DDR table count differs from its binding")

    bases = list(regions)
    count, *rows = (program / "input-index.tsv").read_text(encoding="ascii").splitlines()
    if len(rows) != int(count) or len(rows) != 639:
        raise ValueError("expected 512 prompt positions and 127 dependent decode positions")
    prompt = []
    for index, row in enumerate(rows):
        step, page, position, mode, address, _, offset = (int(field, 16) for field in row.split())
        if position != index:
            raise ValueError("request input positions are out of order")
        if index >= 512:
            if (step, page, mode, address, offset) != (index - 511, 0, 2, 0, 8):
                raise ValueError("decode does not consume a preceding retirement")
            continue
        if step or mode != 1 or address % 64 or offset % 4 or not 0 <= offset < 64:
            raise ValueError("invalid compiled prompt DDR binding")
        region = bisect_right(bases, address) - 1
        if region < 0:
            raise ValueError("prompt binding lies outside initial DDR")
        base = bases[region]
        size, image = regions[base]
        relative = address - base + offset
        if relative + 4 > size:
            raise ValueError("prompt binding lies outside its sealed image")
        with image.open("rb") as stream:
            stream.seek(relative)
            prompt.append(unpack_from("<I", stream.read(4))[0])

    receipt = json.loads((reference / "receipt.json").read_bytes())
    tokens_path = reference / "tokens.json"
    if (receipt["schema"] != "qwen-p512d128-fp32-quality/1" or
            digest(tokens_path) != receipt["tokens_sha256"] or
            prompt != json.loads(tokens_path.read_bytes())["prompt"]):
        raise ValueError("compiled DDR prompt differs from the quality reference")
    output.mkdir()
    (output / "prompt.s64le").write_bytes(pack("<512q", *prompt))
    identity = dict(run_id=run_id, deployment_sha256=deployment,
                    checkpoint_sha256=receipt["checkpoint_sha256"],
                    memory_seal_sha256=memory_seal, state_sha256=digest(state_path),
                    expected_pages=evidence["expected_pages"])
    (output / "identity.json").write_text(json.dumps(identity, indent=2) + "\n", encoding="ascii")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("program", "memory", "state", "reference"):
        parser.add_argument(name, type=Path)
    parser.add_argument("run_id")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.program, args.memory, args.state, args.reference, args.run_id, args.output)


if __name__ == "__main__":
    main()
