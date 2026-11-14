"""Run a bounded HEAD16 sensitivity sample with pinned checkpoint weights."""

import argparse
from hashlib import sha256
from heapq import heappop
import json
from pathlib import Path
from struct import pack_into, unpack_from
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("assets", type=Path)
    parser.add_argument("memory", type=Path)
    parser.add_argument("library", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("variant", choices=("baseline", "candidate"))
    args = parser.parse_args()
    sys.path.insert(0, str(args.source))
    from native_tlm_timing import Clock, Images, S128
    from native_tlm_projection import Projection
    from run_native_tlm_request import Vocabulary
    from fast_tlm_replay import DramBridge, TICK_PS

    class BatchedClock(Clock):
        def until(self, complete):
            while not complete():
                if self.events:
                    time, order, _ = self.events[0]
                    if (time, order) < (dram.next_tick, dram.tick_order):
                        self.now, _, callback = heappop(self.events)
                        callback()
                        continue
                    limit = time if time == dram.next_tick else time - 1
                elif dram.pending:
                    limit = dram.next_tick + 4096 * TICK_PS
                else:
                    raise RuntimeError("native TLM deadlock")
                dram.advance(limit)

    descriptors = (args.assets / "descriptors.bin").read_bytes()
    x = (args.assets / "x.hex").read_bytes()
    if len(descriptors) != 1187 * 128 or len(x.splitlines()) != 512:
        raise ValueError("expected a sealed full HEAD16 vocabulary")
    clock = BatchedClock()
    args.output.mkdir()
    dram = DramBridge(clock, args.library, args.config, args.output, credits=32, core_ps=3334)
    u, p = (S128(clock, core_ps=3334, port_bits=512) for _ in range(2))
    for word, row in enumerate(x.splitlines(), 512):
        u.words[word] = bytes.fromhex(row.decode("ascii"))[::-1]
    memory = Images(args.memory)
    program = json.loads((args.assets / "program.json").read_bytes())
    image = Path(program["weight_path"])
    model_base, = [base for base, region in memory.regions.items()
                   if region == (program["weight_bytes"], image)]
    proj = Projection(clock, dram, memory, u, p, source_word=512, scratch_word=1008,
                      scratch_sram=p, rtl_weight_fetch=args.variant == "candidate")
    head = Vocabulary(proj)
    # Three consecutive regions of equal length sample the head of the tensor,
    # middle channels/rows, and final vocabulary columns.
    windows = [(0, 16), (585, 601), (1171, 1187)]
    for first, end in windows:
        head.columns = first * 128
        for index in range(first, end):
            completed = []
            record = bytearray(descriptors[index * 128:(index + 1) * 128])
            native_base, = unpack_from("<Q", record, 48)
            if native_base != program["weight_base"]:
                raise ValueError("unexpected native HEAD16 weight address")
            pack_into("<Q", record, 48, model_base)
            head.provider(record)(lambda: completed.append(True))
            clock.until(lambda: bool(completed))
    dram.close()
    counters = dict(dram.stats)
    if counters["reads"] != 48 * 256 * 18 or counters["reads"] != counters["callbacks"]:
        raise ValueError("missing or extra sampled HEAD16 weight beats")
    result = dict(variant=args.variant, tiles=head.tiles, logits_sha256=head.digest.hexdigest(),
                  sampled_argmax=head.best, ddr=counters, descriptors_sha256=sha256(descriptors).hexdigest(),
                  activation_sha256=sha256(x).hexdigest(), core_ps=3334, windows=windows,
                  weight_base=model_base, weight_sha256=program["weight_sha256"])
    (args.output / "profile.json").write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")


if __name__ == "__main__":
    main()
