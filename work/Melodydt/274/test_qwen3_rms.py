"""Execute input and per-head RMS from real Qwen3 checkpoint data."""
import argparse
import json
from pathlib import Path
from struct import pack_into, unpack_from
from zlib import crc32

import assemble_cases
from compile_scope_loops import expand
from export_tlm_mother_program import instructions
from make_lc_kernel import kernel
from native_program_runtime import parse_pm_image
from native_tlm_dma import NativeDMA
from native_tlm_local import run_page
from native_tlm_timing import Clock, Dram, Images, S128, Scheduler
import numpy as np
from qwen3_rms import RMS
from emit_native_mother import emit_mother


TOPOLOGY = 25001
TARGET = 3
ABI = 8
GAMMA_BASE = 0x10000
DESC_BASE = 0x20000
MOTHER_BASE = 0x30000
LOCAL_BASE = 0x40000
GAMMA_WORD = 512


def weights(checkpoint, name):
    row, = (line.split() for line in (checkpoint / "weights.index").read_text().splitlines()
            if line.startswith(name + " "))
    rows, count, exp, offset = map(int, row[1:])
    if rows != 1:
        raise ValueError("RMS gamma must be a vector")
    data = np.memmap(checkpoint / "weights.bin", dtype="<i2", mode="r",
                     offset=offset, shape=(count,)).astype(np.float64) * 2.0**exp
    return data


def descriptors(words, epsilon):
    data = bytearray(256)
    pack_into("<IHHIIH6xQ", data, 0, 0x344C5244, 128, 1, ABI, TOPOLOGY, GAMMA_WORD, GAMMA_BASE)
    pack_into("<IHHII4HI", data, 128, 3, 128, 3, ABI, TOPOLOGY,
              0, GAMMA_WORD, GAMMA_WORD, words, round(epsilon * 2**32))
    for offset in (0, 128):
        pack_into("<I", data, offset + 124, crc32(data[offset:offset + 124]))
    return data


def run(checkpoint, library, ini, output):
    meta = dict(line.split(maxsplit=1) for line in
                (checkpoint / "metadata.txt").read_text().splitlines())
    epsilon = float(meta["eps"])
    if meta["family"] != "qwen3" or not 0 < epsilon < 1:
        raise ValueError("expected frozen Qwen3 geometry and positive epsilon")
    output.mkdir()
    all_receipts = {}
    for label, suffix, count in (
        ("input", "input_layernorm.weight", 1024),
        ("query", "self_attn.q_norm.weight", 128),
        ("key", "self_attn.k_norm.weight", 128),
    ):
        out = output / label
        out.mkdir()
        gamma = weights(checkpoint, "model.layers.0." + suffix)
        if gamma.shape != (count,):
            raise ValueError("unexpected normalization shape")
        data = descriptors(count // 4, epsilon)
        mother, _, _, _ = emit_mother([(TARGET,), (TARGET,)], DESC_BASE, TOPOLOGY,
                                      assemble_cases, expand)
        local = bytearray(kernel())
        pack_into("<I", local, 64, TOPOLOGY)
        files = {
            "gamma.bin": np.rint(gamma * 65536).astype("<i4").tobytes(),
            "descriptors.bin": data,
            "mother.bin": mother, "local.bin": local,
        }
        regions = []
        for (name, payload), address in zip(files.items(), (GAMMA_BASE, DESC_BASE, MOTHER_BASE, LOCAL_BASE)):
            padded = payload.ljust((len(payload) + 63) & -64, b"\0")
            (out / name).write_bytes(padded)
            regions.append(f"{address} {len(padded)} {name}\n")
        (out / "ddr-initial.tsv").write_text("4\n" + "".join(regions))
        memory = Images(out / "ddr-initial.tsv")
        clock = Clock()
        dram = Dram(clock, library, ini, out, credits=32, core_ps=3334)
        sram = S128(clock, core_ps=3334, port_bits=512)
        scheduler = Scheduler(clock, dram, memory, core_ps=3334, pm_write_bits=512)
        rms = RMS(clock, sram)
        dma = NativeDMA(clock, dram, memory, core_ps=3334)
        mc, _, raw = parse_pm_image((out / "mother.bin").read_bytes(), out / "mother.bin",
                                     base=MOTHER_BASE, count=len(mother), crc=crc32(mother),
                                     role="mother", topology=TOPOLOGY)
        _, _, lc = parse_pm_image((out / "local.bin").read_bytes(), out / "local.bin",
                                   base=LOCAL_BASE, count=len(local), crc=crc32(local),
                                   role="local", topology=TOPOLOGY)
        scheduler.install_pm(LOCAL_BASE, len(lc), mother=False)
        scheduler.bind_local(TARGET, lc)
        scheduler.install_pm(MOTHER_BASE, len(raw), mother=True)
        page = {"instructions": instructions(raw), "targets": mc["target_mask"],
                "entry_pc": unpack_from("<I", raw, 16)[0],
                "max_steps": unpack_from("<I", raw, 52)[0]}
        providers = {(TARGET, 0x344C5244, ABI, 1): dma.provider(sram, size=count*4, channel=1),
                     (TARGET, 3, ABI, 3): rms.bind}
        rows = []
        for amplitude in (0.25, 7.0):
            # Boundary vectors exercise declared width and range scan. The gamma is real.
            vector = np.rint(np.sin(np.arange(count) / 17) * amplitude * 65536).astype("<i4")
            payload = vector.tobytes()
            ready = []

            def load(i):
                if i == count // 4:
                    ready.append(True)
                    return
                sram.access(i, lambda _: load(i + 1), payload[i*16:i*16+16])

            load(0)
            clock.until(lambda: bool(ready))
            start = clock.now

            def instruction(_):
                complete = []
                clock.after(3 * sram.core_ps, lambda: complete.append(True))
                clock.until(lambda: bool(complete))

            run_page(page, topology=TOPOLOGY, descriptor_base=DESC_BASE, descriptor_bytes=256,
                     scheduler=scheduler, providers=providers, instruction=instruction)
            actual = np.frombuffer(b"".join(sram.words[GAMMA_WORD+i] for i in range(count//4)),
                                   dtype="<i4").astype(np.float64) / 65536
            floating = vector.astype(np.float64) / 65536
            expected = floating * gamma / np.sqrt((floating**2).mean() + epsilon)
            relative = np.linalg.norm(actual - expected) / np.linalg.norm(expected)
            if not relative <= 0.005:
                raise ValueError(f"{label} fixed-point boundary differs from FP64 RMS: {relative}")
            rows.append({"amplitude": amplitude, "elapsed_ps": clock.now - start,
                         "relative_l2": relative})
        if dram.stats["reads"] != dram.stats["callbacks"]:
            raise ValueError("DDR requests did not drain")
        stats = dict(dram.stats)
        dram.close()
        all_receipts[label] = {"elements": count, "rows": rows, "ddr": stats}
    (output / "receipt.json").write_text(json.dumps({
        "scope": "component-only, real Qwen3 gamma and independent input boundary vectors",
        "cases": all_receipts,
    }, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("checkpoint", "library", "ini", "output"):
        parser.add_argument(key, type=Path)
    run(**vars(parser.parse_args()))
