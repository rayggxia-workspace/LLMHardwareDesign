"""Export exact compact mother instructions for an Algo1 TLM consumer."""

import argparse
from contextlib import ExitStack
from itertools import zip_longest
import json
from pathlib import Path
from struct import unpack_from
import sys

from native_rtl_retirements import program_pages
from prepare_native_whole_request import digest
from replay_tlm_mother import execute

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "block_local_native"))
from native_program_runtime import parse_pm_image


def instructions(raw):
    count, start = unpack_from("<II", raw, 20)
    code = raw[start:start+8*count]
    return [dict(pc=pc, opcode=code[offset+7], encoding=code[offset:offset+8].hex())
            for pc, offset in enumerate(range(0, len(code), 8))]


def export(program, deployment, limit, *, first_step=0, last_step=None):
    proof = program / "proof.sha256"
    if digest(proof) != deployment:
        raise ValueError("unexpected Algo1 deployment")
    sealed = dict(reversed(line.split("  ", 1)) for line in proof.read_text(encoding="ascii").splitlines())

    def asset(name):
        path = program / name
        if Path(name).name != name or digest(path) != sealed.get(name):
            raise ValueError(f"unsealed or modified program asset {name}")
        return path

    base, span, packed = asset("mother-packed.tsv").read_text(encoding="ascii").split()
    base, span = int(base), int(span)
    with ExitStack() as stack:
        table = stack.enter_context(asset("mother-pages.tsv").open())
        targets = stack.enter_context(asset("mother-targets.tsv").open())
        image = stack.enter_context(asset(packed).open("rb"))
        if image.seek(0, 2) != span:
            raise ValueError("wrong packed mother image length")
        for step, page, generation, address, size, crc, mask in program_pages(table, targets):
            if step < first_step:
                continue
            if last_step is not None and step > last_step:
                return
            offset = address - base
            padded = (size + 63) & ~63
            if not 0 <= offset <= span - padded:
                raise ValueError("program page outside packed mother asset")
            image.seek(offset)
            data = image.read(padded)
            if len(data) < 128:
                raise ValueError("truncated native PM header")
            topology, = unpack_from("<I", data, 64)
            record, _, raw = parse_pm_image(data, Path(packed), base=address, count=size,
                                            crc=crc, role="mother", topology=topology)
            if record["target_mask"] != mask:
                raise ValueError("native CALL targets differ from the sealed table")
            entry_pc, = unpack_from("<I", raw, 16)
            max_steps, = unpack_from("<I", raw, 52)
            yield dict(step=step, page=page, generation=generation, program_base=address,
                       program_bytes=size, crc=crc, targets=mask, entry_pc=entry_pc,
                       max_steps=max_steps, instructions=instructions(raw))
            if limit == generation:
                return
        if limit:
            raise ValueError("requested more pages than the deployment contains")


def audit_calls(program, deployment):
    """Check expanded CALL addresses and targets. This audit does not advance time."""
    table = program / "mother-descriptors.tsv"
    sealed = dict(reversed(line.split("  ", 1)) for line in
                  (program / "proof.sha256").read_text(encoding="ascii").splitlines())
    if digest(table) != sealed.get(table.name):
        raise ValueError("descriptor bounds differ from the deployment seal")
    pages = calls = 0
    with table.open(encoding="ascii") as descriptors:
        expected_pages = int(next(descriptors))
        for page, row in zip_longest(export(program, deployment, 0), descriptors):
            if page is None or row is None:
                raise ValueError("descriptor and program page counts differ")
            step, index, base, size = row.split()
            base, size = int(base, 16), int(size)
            if (page["step"], page["page"]) != (int(step, 16), int(index, 16)):
                raise ValueError("descriptor page key differs from program page key")
            offsets = set()

            def issue(target, slot, registers):
                address = registers[0] | (registers[1] << 32)
                offset = address - base
                if (not page["targets"] & (1 << target) or not 0 <= offset < size or
                        offset % 128 or offset in offsets):
                    raise ValueError(f"invalid descriptor CALL in generation {page['generation']}")
                offsets.add(offset)
                return slot

            execute(page["instructions"], issue=issue, wait=lambda handles: None,
                    max_steps=page["max_steps"], entry_pc=page["entry_pc"])
            if len(offsets) * 128 != size:
                raise ValueError(f"incomplete descriptors in generation {page['generation']}")
            pages += 1
            calls += len(offsets)
    if pages != expected_pages:
        raise ValueError("descriptor table header differs from actual page count")
    return dict(scope="untimed mother instruction audit", deployment_sha256=deployment,
                pages=pages, descriptor_calls=calls)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path)
    parser.add_argument("deployment_sha256")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--audit-calls", action="store_true")
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit must be nonnegative")
    if args.audit_calls:
        if args.limit:
            parser.error("--audit-calls requires the entire deployment")
        print(json.dumps(audit_calls(args.program, args.deployment_sha256), indent=2))
        return
    for page in export(args.program, args.deployment_sha256, args.limit):
        print(json.dumps(page, separators=(",", ":")))


if __name__ == "__main__":
    main()
