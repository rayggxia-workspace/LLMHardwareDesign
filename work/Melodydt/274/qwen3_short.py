"""Replay compiled Qwen3 short programs using the archived #260 TLM services."""
import argparse
from bisect import bisect_right
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from struct import pack, unpack, unpack_from

from export_tlm_mother_program import instructions
from native_program_runtime import parse_pm_image
from native_tlm_attention import Attention
from native_tlm_dma import CommittedMemory, NativeDMA
from native_tlm_local import run_page
from native_tlm_projection import Projection
from native_tlm_timing import Clock, Dram, Images, S128, Scheduler, Transfer
from native_tlm_u import UArithmetic
from reference import packet

from qwen3_gather import embedding
from qwen3_rms import RMS
from qwen3_short_plan import (
    ACT, ADD2, ATT1, BASE_ABI, CONTEXT, COPY, Compiler, DMA, HEAD_OUT, HIDDEN, LOAD,
    MID, P, PROJ, PROJ_ABI, STORE, TOPOLOGY, U, VECTOR, VOCAB, hash_file,
)


CORE_PS = 3334


class KVMemory(CommittedMemory):
    def __init__(self, images, plan):
        super().__init__(images, [(base, size, base//64) for base, size in plan["state"]])
        self.history = plan["history"]
        self.historical = [(base-self.history*512, base) for base, _ in plan["state"]]
        self.historical_bases = [lo for lo, _ in self.historical]
        self.bounds = {base for base, _ in plan["state"]}
        self.step = 0
        self.reread = set()

    def __call__(self, address):
        if self.history and address >= self.historical[0][0] and self.binding(address) is None:
            index = bisect_right(self.historical_bases, address)-1
            if address < self.historical[index][1]:
                return bytes(64)
            raise ValueError(f"read from unbound history or padding {address:#x}")
        data = super().__call__(address)
        if self.step == 1 and self.binding(address) is not None:
            start = address & -512
            if start in self.bounds:
                self.reread.add(address)
        return data

    def check_step(self):
        expected = {base + offset for base in self.bounds
                    for offset in range(0, 512 * (self.step + 1), 64)}
        if set(self.committed) != expected or self.pending:
            raise ValueError("KV writeback did not complete all expected DDR beats")
        if self.step == 1 and self.reread != {base + offset for base in self.bounds
                                             for offset in range(0, 512, 64)}:
            raise ValueError("step two did not read all K/V beats committed in step one")


class Execution:
    def __init__(self, plan, assets, library, ini, output):
        self.plan = plan
        self.assets = assets
        self.output = output
        self.clock = Clock()
        self.memory = KVMemory(Images(assets / "ddr-initial.tsv"), plan)
        self.dram = Dram(self.clock, library, ini, output, credits=32, core_ps=CORE_PS)
        self.sram = [S128(self.clock, core_ps=CORE_PS, port_bits=512) for _ in range(4)]
        self.scheduler = Scheduler(self.clock, self.dram, self.memory, core_ps=CORE_PS, pm_write_bits=512)
        self.dma = NativeDMA(self.clock, self.dram, self.memory, core_ps=CORE_PS)
        self.n = [RMS(self.clock, s) for s in self.sram]
        self.e = [UArithmetic(self.clock, s) for s in self.sram]
        self.proj = [Projection(self.clock, self.dram, self.memory, self.sram[src], self.sram[P],
                                source_word=word, scratch_word=944, scratch_sram=self.sram[P])
                     for src, word in ((U, 256), (CONTEXT, 0), (MID, 0))]
        self.attn = Attention(self.clock, self.dram, self.memory, self.proj[0], kv_window=8)
        self.calls = Counter()
        self.token = None
        self.logits = []
        self.timing = []
        self.providers = self.bind_providers()

    def cycles(self, cycles):
        finished = []
        self.clock.after(cycles * CORE_PS, lambda: finished.append(True))
        self.clock.until(lambda: bool(finished))

    def read(self, site, word, count):
        result = []
        self.proj[0].read_span(self.sram[site], word, count, result.append)
        self.clock.until(lambda: bool(result))
        return result[0]

    def bind_providers(self):
        def match(record):
            source = record[16]
            if source >= len(self.proj) or any(record[17:48]):
                raise ValueError("invalid projection source")
            return self.proj[source]

        def project(record):
            return match(record).provider(record)

        def vocab(record):
            start, = unpack_from("<I", record, 68)
            count = 8 * record[74]
            word, = unpack_from("<H", record, 86)
            if start != len(self.logits) or start + count > VOCAB:
                raise ValueError("word projection missing or out of order")
            proj = match(record)

            def execute(done):
                def projected():
                    def retire(payload):
                        self.logits.extend(unpack(f"<{count}i", payload))
                        done()

                    proj.read_span(self.sram[P], word, count//4, retire)
                proj.provider(record)(projected)
            return execute

        def dma(site, write):
            def bind(record):
                address, word, words = unpack_from("<QHH", record, 16)
                if any(record[28:124]) or not words or words % 4:
                    raise ValueError("invalid DMA descriptor size")
                native = bytearray(128)
                value = pack("<H6xQQ", word, address, address//64 if write else 0)
                native[16:16+len(value)] = value
                return self.dma.provider(self.sram[site], size=words*16, store=write, channel=1)(native)
            return bind

        def local_copy(site):
            def bind(record):
                src, from_word, to_word, words = unpack_from("<B3H", record, 16)
                if (src == site or src >= len(self.sram) or not words or
                        max(from_word, to_word)+words > 1024 or any(record[23:124])):
                    raise ValueError("invalid cross-S copy descriptor")
                lane = self.proj[0]

                def execute(done):
                    def chunk(offset):
                        if offset == words:
                            done()
                            return
                        count = min(4, words-offset)
                        lane.read_span(self.sram[src], from_word+offset, count,
                                       lambda data: lane.write_span(self.sram[site], to_word+offset,
                                                                    data, lambda: chunk(offset+count)))
                    chunk(0)
                return execute
            return bind

        def activation(record):
            gate, up, out = unpack_from("<3H", record, 16)
            if (max(gate, up, out)+32 > 1024 or any(record[22:124]) or
                    min(abs(gate-up), abs(gate-out), abs(up-out)) < 32):
                raise ValueError("invalid G32 component aperture")
            arith = self.e[P]

            def begin(done):
                def word(index):
                    if index == 32:
                        done()
                        return

                    def product(g, u):
                        first, failed = packet(g[:2], u[:2], True, 3)
                        second, failed2 = packet(g[2:], u[2:], True, 3)
                        if failed or failed2:
                            raise ValueError("G32 overflow")
                        arith.leaf("g_packet", 22, lambda: arith.write(
                            out+index, first+second, lambda: word(index+1)))

                    arith.read(gate+index, lambda g: arith.read(up+index, lambda u: product(g, u)))
                word(0)
            return arith.service(begin)

        providers = {(P, PROJ, PROJ_ABI, 2): project,
                     (P, HEAD_OUT, PROJ_ABI, 2): vocab,
                     (U, 3, VECTOR, 4): embedding(self.sram[U], self.dram, self.memory, HIDDEN*4),
                     (P, ACT, VECTOR, 1): activation,
                     (P, ATT1, BASE_ABI, 1): self.attn.provider,
                     (P, int.from_bytes(b"RPE1", "little"), BASE_ABI, 1): self.e[P].rope,
                     (U, 3, BASE_ABI, ADD2): self.e[U].add}
        for site in (U, P):
            providers[site, 3, VECTOR, 3] = self.n[site].bind
            providers[site, DMA, VECTOR, LOAD] = dma(site, False)
        providers[P, DMA, VECTOR, STORE] = dma(P, True)
        for site in (CONTEXT, MID, U):
            providers[site, COPY, VECTOR, 1] = local_copy(site)
        return providers

    def count_call(self, signature, issue_ps, dispatch_ps, complete_ps):
        if not issue_ps < dispatch_ps <= complete_ps:
            raise ValueError("noncausal CALL completion")
        self.calls[signature] += 1

    def pages(self, pages):
        for item in pages:
            path = self.assets / item["path"]
            self.scheduler.install_pm(item["address"], item["image_bytes"], mother=True)
            mc, _, raw = parse_pm_image(path.read_bytes(), path, base=item["address"],
                                        count=item["image_bytes"], crc=item["crc"],
                                        role="mother", topology=TOPOLOGY)
            page = dict(targets=mc["target_mask"], instructions=instructions(raw),
                        entry_pc=unpack_from("<I", raw, 16)[0], max_steps=unpack_from("<I", raw, 52)[0])
            start = self.clock.now
            run_page(page, topology=TOPOLOGY, descriptor_base=item["descriptor_base"],
                     descriptor_bytes=item["count"]*128, scheduler=self.scheduler, providers=self.providers,
                     instruction=lambda op: self.cycles(6+(op == 0x10)), timing=self.count_call)
            self.timing.append({"page": item["path"], "start_ps": start, "complete_ps": self.clock.now})

    def run(self):
        addr = self.plan["local"]["address"]
        size = self.plan["local"]["bytes"]
        path = self.assets / "local.bin"
        _, _, raw = parse_pm_image(path.read_bytes(), path, base=addr, count=size,
                                   crc=self.plan["local"]["crc"], role="local", topology=TOPOLOGY)
        retirements, boundary = [], []
        decode = self.plan["mode"] == "decode"
        self.token = self.plan["first_decode_input"]
        # CONTEXT and MID model SRAM ingress controllers for the bounded copies.
        for target in (U, P, CONTEXT, MID):
            self.scheduler.install_pm(addr, size, mother=False)
            self.scheduler.bind_local(target, raw)
        for step, phase in enumerate(self.plan["phases"]):
            print(f"position {phase['position']} started at {self.clock.now} ps", flush=True)
            self.memory.step = step
            ready = []
            input_id = self.token if decode else None

            def feed(token):
                self.sram[U].access(512, lambda _: ready.append(True), pack("<i12x", token))

            if decode:
                feed(input_id)
            else:
                addr = self.plan["prompt"]
                def from_ddr():
                    nonlocal input_id
                    input_id, = unpack_from("<i", self.memory(addr), step*4)
                    feed(input_id)
                self.dram.submit(Transfer(addr), from_ddr, channel=0)
            self.clock.until(lambda: bool(ready))
            self.pages(phase["ingress"])
            for index, layer in enumerate(phase["layers"]):
                self.pages(layer)
                print(f"position {phase['position']} layer {index} complete at {self.clock.now} ps", flush=True)
            self.memory.check_step()
            finish = self.clock.now
            residual = self.read(U, 0, HIDDEN//4)
            (self.output / f"residual-{step}.bin").write_bytes(residual)
            boundary.append({"step": step, "input_id": input_id,
                             "complete_ps": finish, "sha256": sha256(residual).hexdigest()})
            if decode:
                self.logits.clear()
                self.pages(phase["vocabulary"])
                if len(self.logits) != VOCAB:
                    raise ValueError("full vocabulary missing")
                self.token = max(range(VOCAB), key=self.logits.__getitem__)
                vals = pack(f"<{VOCAB}i", *self.logits)
                (self.output / f"logits-{step}.bin").write_bytes(vals)
                retirements.append({"input": input_id, "selected": self.token,
                                    "time_ps": self.clock.now, "vocab": VOCAB,
                                    "logits_sha256": sha256(vals).hexdigest()})
            (self.output / "progress.json").write_text(json.dumps({
                "boundary": boundary, "retirements": retirements, "pages": self.timing
            }, indent=2))
        counts = dict(self.dram.stats)
        if counts["reads"] + counts["writes"] != counts["callbacks"]:
            raise ValueError("DDR callbacks did not reconcile")
        self.dram.close()
        result = {"mode": self.plan["mode"], "layers": self.plan["layers"], "history": self.plan["history"],
                  "boundary": boundary, "retirements": retirements,
                  "writes_committed": len(self.memory.committed), "cross_step_reads": len(self.memory.reread),
                  "pages": len(self.timing), "calls": [{"signature": k, "count": v} for k, v in sorted(self.calls.items())],
                  "ddr": counts, "timing_calibrated": False, "rtl_qualified": False}
        if decode:
            ps = retirements[1]["time_ps"] - retirements[0]["time_ps"]
        else:
            ps = boundary[1]["complete_ps"]
        result.update(interval_ps=ps, tok_s=(1e12 if decode else 2e12)/ps)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("checkpoint", "frozen", "packed", "reference", "library", "ini", "output"):
        parser.add_argument(key, type=Path)
    parser.add_argument("--mode", choices=("decode", "prefill"), required=True)
    parser.add_argument("--layers", type=int, choices=(1, 28), default=28)
    args = parser.parse_args()
    if args.mode == "decode" and args.layers != 28:
        parser.error("decode must cover the complete model")
    args.output.mkdir()
    assets = args.output / "assets"
    assets.mkdir()
    history = 512 if args.mode == "decode" else 0
    plan = Compiler(args.checkpoint, args.frozen, args.packed, args.reference,
                    assets, args.layers, history, args.mode).compile()
    (assets / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    result = Execution(plan, assets, args.library, args.ini, args.output).run()
    result.update(plan_sha256=hash_file(assets / "plan.json"),
                  workload="Qwen3 serial projection and modeled SRAM COPY candidate; zero historical KV")
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
