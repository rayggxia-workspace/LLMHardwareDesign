"""Replay compiled Qwen3 short programs using the archived #260 TLM services."""
import argparse
from bisect import bisect_right
from collections import Counter
from hashlib import sha256
import json
from math import tanh
from pathlib import Path
from struct import pack, unpack, unpack_from

from export_tlm_mother_program import instructions
from native_program_runtime import parse_pm_image
from native_tlm_attention import Attention
from native_tlm_dma import CommittedMemory, NativeDMA
from native_tlm_local import run_page
from native_tlm_projection import Projection
from native_tlm_timing import Clock, Dram, Images, S128, Scheduler, Transfer
from native_tlm_u import UArithmetic, rne
from reference import packet
from projection_window import WindowedProjection

from qwen3_gather import embedding
from qwen3_rms import RMS
from qwen3_short_plan import (
    ACT, ADD2, ATT1, ATT_WIDE, BASE_ABI, CONTEXT, COPY, Compiler, DMA, ELEMENT, HEAD_OUT, HIDDEN, LOAD,
    MID, MOE, P, PROJ, PROJ_ABI, RECURRENT, RESIDUAL, ROTARY, STORE, TOPOLOGY, U, VECTOR, VOCAB, align, hash_file,
)


CORE_PS = 3334


class KVMemory(CommittedMemory):
    def __init__(self, images, plan):
        super().__init__(images, [(base, size, base//64)
                                 for base, size in plan["state"] + plan.get("scratch", [])])
        self.history = plan["history"]
        self.row = plan.get("kv_row", 512)
        self.historical = [(base-self.history*self.row, base) for base, _ in plan["state"]]
        self.historical_bases = [lo for lo, _ in self.historical]
        self.bounds = {base for base, _ in plan["state"]}
        self.first_history = self.historical[0][0] if self.historical else 1 << 34
        self.initial = sorted(plan.get("initial", []))
        self.initial_bases = [lo for lo, _ in self.initial]
        self.recurrent_regions = plan.get("recurrent_regions", [])
        self.step = 0
        self.reread = set()
        self.recurrent_reads = set()

    def __call__(self, address):
        i = bisect_right(self.initial_bases, address)-1
        if i >= 0 and address < sum(self.initial[i]):
            return bytes(64)
        if self.history and address >= self.first_history and self.binding(address) is None:
            index = bisect_right(self.historical_bases, address)-1
            if address < self.historical[index][1]:
                return bytes(64)
            raise ValueError(f"read from unbound history or padding {address:#x}")
        data = super().__call__(address)
        if self.step == 1 and self.recurrent_regions and address in self.recurrent_previous:
            self.recurrent_reads.add(address)
        if self.step == 1 and self.binding(address) is not None:
            start = address & -self.row
            if start in self.bounds:
                self.reread.add(address)
        return data

    def check_step(self):
        expected = {base + offset for base in self.bounds
                    for offset in range(0, self.row * (self.step + 1), 64)}
        actual = {a for a in self.committed if (a & -self.row) in self.bounds or
                  (a & -self.row)-self.row in self.bounds}
        if actual != expected or self.pending:
            raise ValueError("KV writeback did not complete all expected DDR beats")
        if self.step == 1 and self.reread != {base + offset for base in self.bounds
                                             for offset in range(0, self.row, 64)}:
            raise ValueError("step two did not read all K/V beats committed in step one")
        if self.recurrent_regions:
            expected_recurrent = {base+off for step, base, size in self.recurrent_regions
                                  if step <= self.step for off in range(0, size, 64)}
            if not expected_recurrent <= self.committed.keys():
                raise ValueError("recurrent state was not committed to DDR")
            if not self.step:
                self.recurrent_previous = expected_recurrent
            elif self.recurrent_reads != self.recurrent_previous:
                raise ValueError("second step did not reread the complete recurrent state")


class Execution:
    def __init__(self, plan, assets, library, ini, output, weight_window=1):
        self.plan = plan
        self.assets = assets
        self.output = output
        self.clock = Clock()
        self.memory = KVMemory(Images(assets / "ddr-initial.tsv"), plan)
        self.dram = Dram(self.clock, library, ini, output, credits=32, core_ps=CORE_PS)
        self.sram = [S128(self.clock, core_ps=CORE_PS, port_bits=512) for _ in range(4)]
        self.scheduler = Scheduler(self.clock, self.dram, self.memory, core_ps=CORE_PS, pm_write_bits=512)
        self.dma = NativeDMA(self.clock, self.dram, self.memory, core_ps=CORE_PS)
        self.hidden = plan.get("hidden", HIDDEN)
        self.vocab = plan.get("vocab", VOCAB)
        self.token_word = plan.get("token_word", 512)
        self.n = [RMS(self.clock, s) for s in self.sram]
        self.e = [UArithmetic(self.clock, s) for s in self.sram]
        self.weight_window = weight_window
        projection = Projection if weight_window == 1 else WindowedProjection
        projection_args = {} if weight_window == 1 else {"weight_window": weight_window}
        self.proj = [projection(self.clock, self.dram, self.memory, self.sram[src], self.sram[P],
                                source_word=word, scratch_word=944, scratch_sram=self.sram[P], **projection_args)
                     for src, word in ((U if self.hidden <= 2048 else MID, self.hidden//4 if self.hidden <= 2048 else 0),
                                       (CONTEXT, 0), (MID, 0))]
        self.attn = Attention(self.clock, self.dram, self.memory, self.proj[0], kv_window=8)
        self.calls = Counter()
        self.service_times = {}
        self.service_group = None
        self.token = None
        self.logits = []
        self.experts = []
        self.residual_saturations = 0
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
            if source > 5 or any(record[17:24]) or any(record[32:48]):
                raise ValueError("invalid projection source")
            return self.proj[min(source, 2)]

        def project(record):
            proj = match(record)
            source = record[16]
            if source < 3:
                return proj.provider(record)
            width, = unpack_from("<H", record, 76)
            if source == 3 and width != 8192:
                raise ValueError("split Mid route requires exactly 8192 coefficients")
            if source in (4, 5) and width not in (4096, 6144, 8192, 9216, 10240):
                raise ValueError("DDR Mid route has an unsupported width")

            def tile(k, done):
                site = CONTEXT if k < 32 else MID
                word = (k % 32) * 32

                def convert(raw):
                    values = unpack("<128i", raw)
                    peak = max(map(abs, values))
                    shift = next(s for s in range(18) if peak <= 32767 << s)
                    packed = pack("<128h", *(rne(v, shift) for v in values))
                    proj.edge(lambda: proj.write_span(self.sram[P], 944, packed,
                              lambda: proj.read_span(self.sram[P], 944, 16,
                              lambda data: done(data, shift))))

                if source == 3 or source == 5 and k < 32:
                    proj.read_span(self.sram[site], word, 32,
                                   lambda _: proj.read_span(self.sram[site], word, 32, convert))
                else:
                    address, = unpack_from("<Q", record, 24)
                    native = bytearray(128)
                    native[16:32] = pack("<H6xQ", 896, address + k*512)
                    self.dma.provider(self.sram[P], size=512, channel=1)(native)(
                        lambda: proj.read_span(self.sram[P], 896, 32,
                                lambda _: proj.read_span(self.sram[P], 896, 32, convert)))
            return proj.provider(record, packed_tile=tile)

        def vocab(record):
            start, = unpack_from("<I", record, 68)
            count = 8 * record[74]
            word, = unpack_from("<H", record, 86)
            if start != len(self.logits) or start + count > ((self.vocab + 7) & -8):
                raise ValueError("word projection missing or out of order")
            proj = match(record)

            def execute(done):
                def projected():
                    def retire(payload):
                        keep = min(count, self.vocab-start)
                        values = unpack(f"<{count}i", payload)[:keep]
                        gain = self.plan.get("logits_scale_q16", 65536)
                        self.logits.extend(rne(value*gain, 16) for value in values)
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

        def activation(record, *, gelu=False, sigmoid=False, scaled=False):
            gate, up, out = unpack_from("<3H", record, 16)
            gain = unpack_from("<I", record, 22)[0] if scaled else 65536
            words = 64 if sigmoid else 32
            if (max(gate, up, out)+words > 1024 or any(record[26 if scaled else 22:124]) or
                    min(abs(gate-up), abs(gate-out), abs(up-out)) < words):
                raise ValueError("invalid G32 component aperture")
            arith = self.e[P]

            def begin(done):
                def word(index):
                    if index == words:
                        done()
                        return

                    def product(g, u):
                        if gelu:
                            values = []
                            for a, b in zip(g, u):
                                x = a/65536
                                y = round(a*0.5*(1+tanh(0.7978845608028654*(x+0.044715*x**3))))
                                values.append(rne(y*b, 16))
                        elif sigmoid:
                            from math import exp
                            values = [round(b/(1+exp(-max(-64, min(64, a/65536))))) for a,b in zip(g,u)]
                        else:
                            g = [rne(x*gain, 16) for x in g]
                            first, failed = packet(g[:2], u[:2], True, 3)
                            second, failed2 = packet(g[2:], u[2:], True, 3)
                            if failed or failed2:
                                raise ValueError("G32 overflow")
                            values = first+second
                        arith.leaf("g_packet", 40 if gelu else 22, lambda: arith.write(
                            out+index, values, lambda: word(index+1)))

                    arith.read(gate+index, lambda g: arith.read(up+index, lambda u: product(g, u)))
                word(0)
            return arith.service(begin)

        def rotary64(record):
            source, cosine, sine, dest, words = unpack_from("<5H", record, 16)
            if words != 16 or any(record[26:124]):
                raise ValueError("invalid 64-dimensional rotary descriptor")
            lane = self.proj[0]
            sram = self.sram[P]

            def execute(done):
                def calculate(x, c, s):
                    a, b, d = (unpack("<64i", buf) for buf in (x, c, s))
                    rotated = [rne(a[i]*b[i], 14) +
                               rne((a[i^32] if i >= 32 else -a[i^32])*d[i], 14)
                               for i in range(64)]
                    lane.edge(lambda: lane.write_span(sram, dest,
                              pack("<64i", *rotated)+bytes(256), done), words*36)

                lane.read_span(sram, source, words,
                               lambda x: lane.read_span(sram, cosine, words,
                               lambda c: lane.read_span(sram, sine, words, lambda s: calculate(x, c, s))))
            return execute

        def pad64(record):
            source, dest = unpack_from("<2H", record, 16)
            if any(record[20:124]):
                raise ValueError("invalid 64-dimensional V staging descriptor")
            proj = self.proj[0]
            sram = self.sram[P]

            def execute(done):
                proj.read_span(sram, source, 16, lambda data:
                               proj.write_span(sram, dest, data+bytes(256), done))
            return execute

        def rotary_partial(record, wide=False):
            source, cosine, sine, dest, width = unpack_from("<5H", record, 16)
            if not 0 < width <= 256 or width % 8 or any(record[26:124]):
                raise ValueError("invalid partial rotary descriptor")
            proj = self.proj[0]
            sram = self.sram[P]
            dimension = 256 if wide or width > 128 else 128
            words = dimension//4

            def execute(done):
                def calculate(x, c, s):
                    a, b, d = (unpack(f"<{dimension}i", buf) for buf in (x, c, s))
                    half = width//2
                    out = [rne(a[i]*b[i], 14) +
                           rne((a[i-half] if i >= half else -a[i+half])*d[i], 14)
                           for i in range(width)]
                    proj.edge(lambda: proj.write_span(sram, dest,
                              pack(f"<{dimension}i", *out, *a[width:]), done), width//4*36)

                proj.read_span(sram, source, words,
                               lambda x: proj.read_span(sram, cosine, words,
                               lambda c: proj.read_span(sram, sine, words, lambda s: calculate(x, c, s))))
            return execute

        def residual(record, site=P, scaled=False, saturating=False):
            local, other, words = unpack_from("<3H", record, 16)
            gain = unpack_from("<I", record, 22)[0] if scaled else 65536
            if not words or max(local, other)+words > 1024 or any(record[26 if scaled else 22:124]):
                raise ValueError("invalid cross-bank residual")
            unit = self.e[U]
            proj = self.proj[0]

            def begin(done):
                def step(i):
                    if i == words:
                        done()
                        return

                    def add(a, b):
                        values = [x+rne(y*gain, 16) for x, y in zip(a, unpack("<4i", b))]
                        if saturating:
                            clipped = [min((1 << 31)-1, max(-(1 << 31), x)) for x in values]
                            self.residual_saturations += sum(a != b for a, b in zip(values, clipped))
                            values = clipped
                        unit.leaf("e_add_packets", 9, lambda: unit.write(local+i, values, lambda: step(i+1)))

                    unit.read(local+i, lambda a: proj.read_span(self.sram[site], other+i, 1,
                                                               lambda b: add(a, b)))
                step(0)
            return unit.service(begin)

        def scale(record, site=U, ranged=False):
            words, gain = unpack_from("<HI", record, 16)
            start = unpack_from("<H", record, 22)[0] if ranged else 0
            if not 0 < words <= 1024-start or any(record[24 if ranged else 22:124]):
                raise ValueError("invalid embedding scale descriptor")
            unit = self.e[site]

            def begin(done):
                def step(i):
                    if i == words:
                        done()
                        return
                    unit.read(start+i, lambda values: unit.leaf("e_product_packets", 9,
                        lambda: unit.write(start+i, [rne(x*gain, 16) for x in values], lambda: step(i+1))))
                step(0)
            return unit.service(begin)

        providers = {(P, PROJ, PROJ_ABI, 2): project,
                     (P, HEAD_OUT, PROJ_ABI, 2): vocab,
                     (U, 3, VECTOR, 4): embedding(self.sram[U], self.dram, self.memory, self.hidden*4,
                                                     self.token_word),
                     (P, ROTARY, VECTOR, 1): rotary64,
                     (P, ROTARY, VECTOR, 2): pad64,
                     (P, ROTARY, VECTOR, 3): rotary_partial,
                     (P, ROTARY, VECTOR, 4): lambda r: rotary_partial(r, wide=True),
                     (U, RESIDUAL, VECTOR, 1): residual,
                     (U, RESIDUAL, VECTOR, 2): lambda r: residual(r, site=MID),
                     (U, RESIDUAL, VECTOR, 3): lambda r: residual(r, scaled=True),
                     (U, RESIDUAL, VECTOR, 4): lambda r: residual(r, site=MID, saturating=True),
                     (U, ELEMENT, VECTOR, 1): scale,
                     (P, ELEMENT, VECTOR, 2): lambda r: scale(r, site=P, ranged=True),
                     (MID, 3, VECTOR, 5): lambda record: self.n[MID].bind(
                         record, gamma_bank=self.sram[CONTEXT]),
                     (P, ACT, VECTOR, 1): activation,
                     (P, ACT, VECTOR, 2): lambda r: activation(r, gelu=True),
                     (P, ACT, VECTOR, 3): lambda r: activation(r, sigmoid=True),
                     (P, ACT, VECTOR, 4): lambda r: activation(r, scaled=True),
                     (P, ATT1, BASE_ABI, 1): self.attn.provider,
                     (P, int.from_bytes(b"RPE1", "little"), BASE_ABI, 1): self.e[P].rope,
                     (U, 3, BASE_ABI, ADD2): self.e[U].add}
        if self.hidden == 2560:
            from attention_wide import WideAttention
            providers[P, ATT_WIDE, VECTOR, 1] = WideAttention(self.proj[0]).bind
        if self.plan["kv_row"] == 256:
            from attention_compact import CompactAttention64
            providers[P, ATT1, BASE_ABI, 2] = CompactAttention64(self.proj[0]).bind
        if self.plan.get("moe"):
            from granite_short import Router
            providers[P, MOE, VECTOR, 1] = Router(self, activation).bind
        if self.plan.get("recurrent"):
            from hybrid_short import Recurrent
            providers[P, RECURRENT, VECTOR, 1] = Recurrent(self).bind
        for site in (U, P, CONTEXT, MID):
            providers[site, 3, VECTOR, 3] = self.n[site].bind
            providers[site, DMA, VECTOR, LOAD] = dma(site, False)
            providers[site, DMA, VECTOR, STORE] = dma(site, True)
        for site in (CONTEXT, MID, U):
            providers[site, COPY, VECTOR, 1] = local_copy(site)
        return providers

    def count_call(self, signature, issue_ps, dispatch_ps, complete_ps):
        if not issue_ps < dispatch_ps <= complete_ps:
            raise ValueError("noncausal CALL completion")
        self.calls[signature] += 1
        totals = self.service_times.setdefault((self.service_group, signature), [0, 0, 0])
        totals[0] += 1
        totals[1] += dispatch_ps - issue_ps
        totals[2] += complete_ps - dispatch_ps

    def pages(self, pages):
        for item in pages:
            parts = item["path"].split("-", 2)
            phase = parts[1] if parts[1] in ("ingress", "head") else "layers"
            self.service_group = f"{parts[0]}-{phase}"
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
                self.sram[U].access(self.token_word, lambda _: ready.append(True), pack("<i12x", token))

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
            residual = self.read(U, 0, self.hidden//4)
            (self.output / f"residual-{step}.bin").write_bytes(residual)
            boundary.append({"step": step, "input_id": input_id,
                             "complete_ps": finish, "sha256": sha256(residual).hexdigest()})
            if decode:
                self.logits.clear()
                self.pages(phase["vocabulary"])
                if len(self.logits) != self.vocab:
                    raise ValueError("full vocabulary missing")
                self.token = max(range(self.vocab), key=self.logits.__getitem__)
                vals = pack(f"<{self.vocab}i", *self.logits)
                (self.output / f"logits-{step}.bin").write_bytes(vals)
                retirements.append({"input": input_id, "selected": self.token,
                                    "time_ps": self.clock.now, "vocab": self.vocab,
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
                  "writes_committed": sum(size for _, size in self.plan["state"])//64,
                  "expert_routes": self.experts,
                  "residual_saturations": self.residual_saturations,
                  "recurrent_writes": sum(size//64 for _, _, size in self.memory.recurrent_regions),
                  "recurrent_cross_step_reads": len(self.memory.recurrent_reads),
                  "cross_step_reads": len(self.memory.reread),
                  "pages": len(self.timing), "calls": [{"signature": k, "count": v} for k, v in sorted(self.calls.items())],
                  "ddr": counts, "timing_calibrated": False, "rtl_qualified": False}
        result["weight_window"] = self.weight_window
        result["projection"] = [dict(p.stats) for p in self.proj]
        result["services"] = [{"group": group, "signature": signature, "count": count,
                               "dispatch_ps": dispatch, "service_ps": service}
                              for (group, signature), (count, dispatch, service) in
                              sorted(self.service_times.items())]
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
    parser.add_argument("--model", choices=("qwen3", "llama", "phi", "gemma", "granite", "qwen35", "falcon"), default="qwen3")
    parser.add_argument("--layers", type=int)
    parser.add_argument("--weight-window", type=int, choices=(1, 2, 4, 8), default=1)
    parser.add_argument("--ffn-context-cache", action="store_true")
    parser.add_argument("--compact-kv64", action="store_true")
    args = parser.parse_args()
    if args.ffn_context_cache and args.model not in ("phi", "gemma", "qwen35", "falcon"):
        parser.error("FFN context cache requires a DDR-backed Mid mapping")
    if args.compact_kv64 and args.model not in ("llama", "granite"):
        parser.error("compact KV requires 64-element attention heads")
    full = {"qwen3": 28, "llama": 16, "phi": 32, "gemma": 34, "granite": 32,
            "qwen35": 32, "falcon": 32}[args.model]
    layers = full if args.layers is None else args.layers
    if not 1 <= layers <= full or args.mode == "decode" and layers != full:
        parser.error("decode must cover the complete model")
    args.output.mkdir()
    assets = args.output / "assets"
    assets.mkdir()
    history = 512 if args.mode == "decode" else 0
    if args.model == "qwen3":
        compiler = Compiler(args.checkpoint, args.frozen, args.packed, args.reference,
                            assets, layers, history, args.mode)
    elif args.model == "llama":
        from llama_short_plan import LlamaCompiler
        compiler = LlamaCompiler(args.checkpoint, args.packed, args.reference,
                                  assets, layers, history, args.mode)
    elif args.model == "phi":
        from phi_short_plan import PhiCompiler
        compiler = PhiCompiler(args.checkpoint, args.packed, args.reference,
                                assets, layers, history, args.mode)
    elif args.model == "gemma":
        from gemma_short_plan import GemmaCompiler
        compiler = GemmaCompiler(args.checkpoint, args.packed, args.reference,
                                  assets, layers, history, args.mode)
    elif args.model == "granite":
        from granite_short import GraniteCompiler
        compiler = GraniteCompiler(args.checkpoint, args.packed, args.reference,
                                   assets, layers, history, args.mode)
    else:
        from hybrid_short import FalconCompiler, Qwen35Compiler
        model = Qwen35Compiler if args.model == "qwen35" else FalconCompiler
        compiler = model(args.checkpoint, args.packed, args.reference, assets, layers, history, args.mode)
    if args.ffn_context_cache:
        compiler.ffn_context_cache = True
    if args.compact_kv64:
        compiler.compact_kv64 = True
        compiler.kv_row = 256
        compiler.kv_bytes = align((history+2)*compiler.kv_row, 4096)
    plan = compiler.compile()
    (assets / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    result = Execution(plan, assets, args.library, args.ini, args.output, args.weight_window).run()
    result.update(plan_sha256=hash_file(assets / "plan.json"),
                  model=args.model,
                  ffn_context_cache=args.ffn_context_cache,
                  compact_kv64=args.compact_kv64,
                  workload="serial projection and modeled SRAM COPY candidate; zero historical KV")
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
