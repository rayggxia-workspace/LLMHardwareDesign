"""Compile and execute Qwen3's first two Gather calls on the PR #260 timeline."""
import argparse
import hashlib
import json
from pathlib import Path
from struct import pack_into, unpack_from
from zlib import crc32

import assemble_cases
from compile_scope_loops import expand
from export_tlm_mother_program import instructions
from link_native_program import deploy_algo1_result
from make_lc_kernel import kernel
from native_program_runtime import parse_pm_image
from native_tlm_local import run_page
from native_tlm_timing import Clock, Dram, Images, S128, Scheduler, Transfer
from prepare_native_embedding_dispatch import graph_inputs, SITE, TOPOLOGY
import numpy as np
from run import compile_event_graph


ABI = 8
TARGET = 3
TABLE = 1 << 20


def weight_image(checkpoint, output, hidden, vocab):
    row, = (line.split() for line in (checkpoint / "weights.index").read_text().splitlines()
            if line.startswith("model.embed_tokens.weight "))
    rows, columns, exponent, offset = map(int, row[1:])
    if (rows, columns, exponent) != (vocab, hidden, -15):
        raise ValueError("unexpected frozen Qwen3 S16 embedding geometry or exponent")
    raw = np.memmap(checkpoint / "weights.bin", dtype="<i2", mode="r",
                    offset=offset, shape=(rows, columns))
    with output.open("xb") as f:
        for start in range(0, rows, 1024):
            (raw[start:start+1024].astype("<i4") * 2).tofile(f)
    return raw


def deploy(hidden, vocab, output):
    row_bytes = hidden * 4
    descriptor_base = TABLE + row_bytes * vocab
    graph, hardware = graph_inputs(TABLE, vocab, index_bits=32, index_offset=8192, target=TARGET)
    graph["values"]["table"]["shape"] = [vocab, hidden]
    graph["values"]["embedding"]["shape"] = [1, hidden]
    hardware["event_model"]["windows"]["result"]["bytes"] = row_bytes
    plan = compile_event_graph(graph, hardware, budget=0)

    def encode(command):
        source, = command["read"]
        destination, = command["write"]
        spec = command["indexed_read"]
        if (command["op"], source["address"], destination["address"], destination["bytes"],
                spec["table_address"], spec["rows"], spec["row_words"]) != (
                "INDEXED_LOAD", 8192, 0, row_bytes, TABLE, vocab, row_bytes // 16):
            raise ValueError("compiler selected a different Qwen3 embedding contract")
        rec = bytearray(128)
        pack_into("<IHHIIQIHHHH", rec, 0, 3, 128, 4, ABI, TOPOLOGY, TABLE, vocab, 8192, 0, 32, row_bytes)
        pack_into("<I", rec, 124, crc32(rec[:124]))
        return bytes(rec)

    manifest = deploy_algo1_result(plan, {"embedding-row": ("destination_commit_ack", encode)},
                                   output, base=descriptor_base, topology=TOPOLOGY,
                                   assembler=assemble_cases, expand=expand, local_kernel=kernel,
                                   service_routes={TARGET: ((3, ABI, 4),)})
    return manifest


def embedding(sram, ddr, memory, row_bytes):
    """Read the indexed S32 row through DDR and retire only after SRAM commits."""
    def bind(record):
        table, rows, offset, dest, bits, encoded_bytes = unpack_from("<QIHHHH", record, 16)
        if (table, offset, dest, bits, encoded_bytes) != (TABLE, 8192, 0, 32, row_bytes):
            raise ValueError("invalid model-specific embedding descriptor")

        def execute(done):
            def indexed(index_word):
                token, = unpack_from("<i", index_word)
                if not 0 <= token < rows:
                    raise ValueError("token outside embedding table")

                def transfer(beat):
                    if beat * 64 == row_bytes:
                        done()
                        return
                    address = table + row_bytes * token + 64 * beat

                    def commit():
                        words = memory(address)

                        def store(offset):
                            if offset == 4:
                                transfer(beat + 1)
                                return
                            start = 4 * beat + offset
                            count = sram.beat_words(start, 4 - offset)
                            sram.access_beat(start, count, lambda _: store(offset + count),
                                             words[offset * 16:(offset + count) * 16])

                        store(0)

                    ddr.submit(Transfer(address), commit, channel=0)

                transfer(0)

            sram.access(512, indexed)
        return execute
    return bind


def run(checkpoint, library, ini, output):
    meta = dict(line.split(maxsplit=1) for line in
                (checkpoint / "metadata.txt").read_text().splitlines())
    if meta["family"] != "qwen3":
        raise ValueError("expected Qwen3")
    hidden, vocab = int(meta["hidden"]), int(meta["vocab"])
    tokens = json.loads((checkpoint / "export_receipt.json").read_text())["prompt_ids"][:2]
    if len(tokens) != 2 or any(not 0 <= token < vocab for token in tokens):
        raise ValueError("two valid prompt IDs are required")
    output.mkdir()
    raw16 = weight_image(checkpoint, output / "embedding.s32", hidden, vocab)
    stage = output / "deploy"
    manifest = deploy(hidden, vocab, stage)
    desc = (stage / "descriptors.bin").read_bytes()
    base = manifest["descriptor_base"]
    mother = (stage / "mother.bin").read_bytes()
    local = (stage / next(iter(manifest["local_images"].values()))).read_bytes()
    (output / "mother.padded").write_bytes(mother.ljust((len(mother) + 63) & -64, b"\0"))
    (output / "local.padded").write_bytes(local.ljust((len(local) + 63) & -64, b"\0"))
    (output / "prompt.bin").write_bytes(np.asarray(tokens, dtype="<i4").tobytes().ljust(64, b"\0"))
    prompt_address = base + 4096
    mother_address = base + 8192
    local_address = base + 24576
    images_table = output / "ddr-initial.tsv"
    images_table.write_text("5\n{} {} embedding.s32\n{} {} deploy/descriptors.bin\n"
                            "{} 64 prompt.bin\n{} {} mother.padded\n{} {} local.padded\n".format(
                                TABLE, hidden * 4 * vocab, base, len(desc), prompt_address,
                                mother_address, (len(mother) + 63) & -64,
                                local_address, (len(local) + 63) & -64))
    memory = Images(images_table)
    mc, _, mc_raw = parse_pm_image((output / "mother.padded").read_bytes(), stage / "mother.bin",
                                   base=mother_address, count=len(mother), crc=crc32(mother),
                                   role="mother", topology=TOPOLOGY)
    _, _, lc_raw = parse_pm_image((output / "local.padded").read_bytes(), stage / "local-0.bin",
                                  base=local_address, count=len(local), crc=crc32(local),
                                  role="local", topology=TOPOLOGY)
    clock = Clock()
    ddr = Dram(clock, library, ini, output, credits=32, core_ps=3334)
    sram = S128(clock, core_ps=3334, port_bits=512)
    scheduler = Scheduler(clock, ddr, memory, core_ps=3334, pm_write_bits=512)
    scheduler.install_pm(local_address, len(lc_raw), mother=False)
    scheduler.bind_local(TARGET, lc_raw)
    scheduler.install_pm(mother_address, len(mc_raw), mother=True)
    mc_page = {"instructions": instructions(mc_raw), "targets": mc["target_mask"],
               "entry_pc": unpack_from("<I", mc_raw, 16)[0],
               "max_steps": unpack_from("<I", mc_raw, 52)[0]}

    def instruction(_):
        elapsed = []
        clock.after(3 * sram.core_ps, lambda: elapsed.append(True))
        clock.until(lambda: bool(elapsed))

    calls = []
    for position, token in enumerate(tokens):
        ready = []

        def receive_token():
            payload = memory(prompt_address)[4 * position:4 * position + 4]
            sram.access(512, lambda _: ready.append(True), payload.ljust(16, b"\0"))

        ddr.submit(Transfer(prompt_address), receive_token, channel=0)
        clock.until(lambda: bool(ready))
        run_page(mc_page, topology=TOPOLOGY, descriptor_base=base, descriptor_bytes=len(desc),
                 scheduler=scheduler, providers={(TARGET, 3, ABI, 4): embedding(sram, ddr, memory, hidden * 4)},
                 instruction=instruction,
                 timing=lambda key, issue, dispatch, done:
                 calls.append({"position": position, "target": key[0], "issue_ps": issue,
                               "dispatch_ps": dispatch, "destination_commit_ps": done}))
        actual = b"".join(sram.words[word] for word in range(hidden // 4))
        if actual != (raw16[token].astype("<i4") * 2).tobytes():
            raise ValueError("SRAM row differs from the frozen checkpoint")
        calls[-1]["token"] = token
        calls[-1]["row_sha256"] = hashlib.sha256(actual).hexdigest()
    if len(calls) != 2 or not all(c["issue_ps"] < c["dispatch_ps"] < c["destination_commit_ps"] for c in calls):
        raise ValueError("expected two completed Gather calls")
    (output / "receipt.json").write_text(json.dumps(
        {"scope": "Qwen3 embedding component; model-specific TLM descriptor ABI",
         "calls": calls, "ddr": dict(ddr.stats)}, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("checkpoint", "library", "ini", "output"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
