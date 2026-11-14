"""Three-P FFN page. Advance Mid only after all Gate/Up scopes have committed."""

from pathlib import Path
from struct import pack, pack_into, unpack, unpack_from
import sys

from native_tlm_projection import Projection
from native_tlm_u import rne

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "w8a16_g"))
from reference import packet


def quantize(row):
    peak = max(map(abs, row))
    shift = next(s for s in range(18) if peak <= 32767 << s)
    return pack("<128h", *(rne(v, shift) for v in row)), shift


class FFN:
    def __init__(self, clock, dram, memory, u, banks, dma, input_base, *, rtl_weight_fetch=False):
        self.clock, self.u, self.banks = clock, u, banks
        self.pipeline_copy = dma.pipeline
        self.projections = [Projection(clock, dram, memory, u, bank, source_word=0,
                                       scratch_word=512, rtl_weight_fetch=rtl_weight_fetch)
                            for bank in banks]
        self.x = {}
        self.mid = {}
        self.stripe = []
        self.carry = []
        self.groups = 0
        self.mid_count = 0
        self.scope_count = 0
        self.requests = {}
        self.mid_pending = False
        self.mid_barrier_ps = 0
        row = bytearray(128)
        pack_into("<H6xQ", row, 16, 0, input_base)
        ready = []
        dma.provider(u, size=8192)(row)(lambda: ready.append(True))
        clock.until(lambda: bool(ready))

    def provider(self, target):
        projection = self.projections[target]

        def bind(record):
            first, stride, groups = unpack_from("<IHB", record, 68)
            ways = record[82]
            out, out1 = unpack_from("<HH", record, 86)
            if stride != 24 or first % 24 != target*8 or ways not in (1, 2):
                raise ValueError("invalid three-P descriptor stripe")

            def input_tile(k, done):
                if ways == 1:
                    owner = self.banks[k % 3]
                    projection.read_span(owner, 256+16*(k//3), 16,
                                         lambda data: done(data, self.mid[k]))
                    return
                ready = self.x.get(k)
                if ready is not None:
                    projection.read_span(self.u, 512+16*k, 16, lambda data: done(data, ready))
                    return
                if k in self.requests:
                    self.requests[k].append(done)
                    return
                self.requests[k] = [done]

                def convert(raw):
                    data, shift = quantize(unpack("<128i", raw))

                    def committed():
                        self.x[k] = shift
                        for waiter in self.requests.pop(k):
                            projection.read_span(self.u, 512+16*k, 16,
                                                 lambda payload, cb=waiter: cb(payload, shift))

                    projection.write_span(self.u, 512+16*k, data, committed)

                projection.read_span(self.u, 32*k, 32,
                                     lambda _: projection.read_span(self.u, 32*k, 32, convert))

            run = projection.provider(record, packed_tile=input_tile)

            def execute(done):
                if ways == 1 and self.mid_count != 86:
                    raise ValueError("Down opened before all Mid tiles committed")

                def finish():
                    self.scope_count += 1
                    if ways == 2:
                        self.stripe.append((target, first, groups, out, out1))
                    done()

                run(finish)
            return execute
        return bind

    def after_wait(self):
        if not self.stripe:
            return
        if len(self.stripe) != 3 or {row[0] for row in self.stripe} != {0, 1, 2}:
            raise ValueError("Gate/Up needs the three actual P terminals")
        projection = self.projections[0]
        fragments = sorted((first+group*24, target, out+2*group, out1+2*group)
                           for target, first, groups, out, out1 in self.stripe for group in range(groups))
        self.stripe.clear()
        self.mid_pending = True
        start = self.clock.now
        prefetched = {}
        waiting = {}

        def fetch(i):
            _, target, gate, up = fragments[i]
            bank = self.banks[target]

            def received(g, u):
                if i in waiting:
                    waiting.pop(i)(g, u)
                else:
                    prefetched[i] = (g, u)

            projection.read_span(bank, gate, 2, lambda g: projection.read_span(
                bank, up, 2, lambda u: received(g, u)))

        def fragment(i):
            if i == len(fragments):
                self.mid_pending = False
                return
            column, target, gate, up = fragments[i]
            if column != self.groups*8:
                raise ValueError("missing or reordered Gate/Up columns")
            bank = self.banks[target]
            if self.pipeline_copy:
                def copy(g, u):
                    if i+1 < len(fragments):
                        fetch(i+1)
                    projection.write_span(self.banks[0], 720, g, lambda:
                        projection.write_span(self.banks[0], 784, u, lambda: activate(i)))

                if i in prefetched:
                    copy(*prefetched.pop(i))
                else:
                    waiting[i] = copy
                return
            projection.read_span(bank, gate, 2, lambda g: projection.read_span(
                bank, up, 2, lambda u: projection.write_span(self.banks[0], 720, g, lambda:
                    projection.write_span(self.banks[0], 784, u, lambda: activate(i)))))

        def activate(i):
            def product(gate, up):
                values = []
                for j in range(0, 8, 2):
                    pair, error = packet(gate[j:j+2], up[j:j+2], True, 3)
                    if error:
                        raise ValueError("native G32 overflow")
                    values.extend(pair)
                self.groups += 1
                self.carry.extend(values)
                if len(self.carry) == 128:
                    raw = pack("<128i", *self.carry)
                    self.carry.clear()
                    k = self.mid_count

                    def convert(payload):
                        packed, shift = quantize(unpack("<128i", payload))

                        def committed():
                            self.mid[k] = shift
                            self.mid_count += 1
                            fragment(i+1)

                        projection.write_span(self.banks[k % 3], 256+16*(k//3), packed, committed)

                    projection.write_span(self.banks[0], 928, raw, lambda: projection.read_span(
                        self.banks[0], 928, 32, lambda _: projection.read_span(
                            self.banks[0], 928, 32, convert)))
                else:
                    fragment(i+1)

            projection.read_span(self.banks[0], 720, 2, lambda g: projection.read_span(
                self.banks[0], 784, 2, lambda u: projection.edge(
                    lambda: product(unpack("<8i", g), unpack("<8i", u)), 11)))

        if self.pipeline_copy:
            fetch(0)
        fragment(0)
        self.clock.until(lambda: not self.mid_pending)
        self.mid_barrier_ps += self.clock.now - start
