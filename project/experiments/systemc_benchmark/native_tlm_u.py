"""Resident U arithmetic. Cycle accounting is a service model for RTL calibration."""

from collections import Counter
from math import isqrt
from struct import pack, unpack, unpack_from


def rne(value, shift):
    if shift <= 0:
        return value << -shift
    denominator = 1 << shift
    quotient, remainder = divmod(value, denominator)
    return quotient + (2 * remainder > denominator or
                       (2 * remainder == denominator and quotient & 1))


def s32(value):
    return min((1 << 31) - 1, max(-(1 << 31), value))


class UArithmetic:
    def __init__(self, clock, sram):
        self.clock, self.sram = clock, sram
        self.stats = Counter()
        self.busy = False

    def edge(self, action, cycles=1):
        period = self.sram.core_ps
        self.clock.after(period * cycles - self.clock.now % period, action)

    def read(self, address, done):
        self.sram.access(address, lambda data: self.edge(lambda: done(unpack("<4i", data))))

    def write(self, address, values, done):
        if any(not -(1 << 31) <= n < 1 << 31 for n in values):
            raise ValueError("native E service reported S32 clipping")
        self.sram.access(address, lambda _: self.edge(done), pack("<4i", *values))

    def leaf(self, opcode, cycles, done):
        self.stats[opcode] += 1
        self.edge(done, cycles)

    def service(self, begin):
        def run(done):
            if self.busy:
                raise ValueError("overlapping resident U services lack a certified lease")
            self.busy = True

            def terminal():
                self.busy = False
                done()

            self.edge(lambda: begin(terminal))
        return run

    def add(self, record):
        left, right, dst, words = unpack_from("<4H", record, 16)
        if (not words or max(left, right, dst) + words > 1024 or any(record[24:124]) or
                any(0 < abs(src - dst) < words for src in (left, right))):
            raise ValueError("invalid resident ADD2 descriptor")

        def begin(done):
            def word(index):
                if index == words:
                    done()
                    return

                def rhs(a, b):
                    self.leaf("e_add_packets", 9, lambda: self.write(
                        dst + index, [x + y for x, y in zip(a, b)],
                        lambda: word(index + 1)))

                self.read(left + index, lambda a: self.read(right + index, lambda b: rhs(a, b)))

            word(0)
        return self.service(begin)

    def rms(self, record):
        x, gamma, dst, reserved, epsilon, baseline, eps_shift, factor_shift, gamma_shift = (
            unpack_from("<HHHHIbbbb", record, 16))
        if ((x, gamma) not in ((0, 512), (512, 0)) or dst not in (x, gamma) or
                reserved or any(record[32:124]) or not epsilon or not -32 <= baseline <= 31 or
                not all(-63 <= shift <= 63 for shift in (factor_shift, gamma_shift))):
            raise ValueError("unsupported native S32 Q16 RMS descriptor")

        def begin(done):
            extra, squares = 0, 0

            def scan(index):
                if index == 512:
                    eps = max(1, rne(epsilon, 2 * extra - eps_shift))
                    if not 0 < eps < 1 << 32:
                        raise ValueError("RMS epsilon exceeds native N range")
                    self.leaf("n_begin", 2, lambda: stats(0, eps))
                    return

                def inspect(values):
                    nonlocal extra
                    while any(not -32768 <= rne(v, baseline + extra) <= 32767 for v in values):
                        extra += 1
                        if baseline + extra > 31:
                            raise ValueError("native RMS range scan overflow")
                    scan(index + 1)

                self.read(x + index, inspect)

            def stats(index, eps):
                if index == 512:
                    factor = rne((1 << 38) // isqrt((squares << 5) + (eps << 16)), extra)
                    # N mean divide, root, factor divide and ReadFactor stages.
                    self.leaf("n_finalize", 168, lambda: self.leaf(
                        "n_read_factor", 2, lambda: apply(0, factor)))
                    return

                def accumulate(values):
                    nonlocal squares
                    squares += sum(rne(v, baseline + extra)**2 for v in values)
                    self.leaf("n_stats", 6, lambda: stats(index + 1, eps))

                self.read(x + index, accumulate)

            def apply(index, factor):
                if index == 512:
                    done()
                    return

                def scale(values):
                    normalized = [rne(v * factor, factor_shift) for v in values]
                    if any(not -(1 << 31) <= v < 1 << 31 for v in normalized):
                        raise ValueError("native E RMS factor product clipped")
                    self.leaf("e_product_packets", 9, lambda: self.read(
                        gamma + index, lambda weights: weighted(normalized, weights)))

                def weighted(values, weights):
                    self.leaf("e_product_packets", 9, lambda: self.write(
                        dst + index, [rne(v * g, gamma_shift) for v, g in zip(values, weights)],
                        lambda: apply(index + 1, factor)))

                self.read(x + index, scale)

            scan(0)
        return self.service(begin)

    def rope(self, record):
        source, cosine, sine, dst = unpack_from("<4H", record, 16)
        cos, neg, neg_align, sin, sin_align, out, src_exp, dst_exp, native_exp, coeff_exp = (
            unpack_from("<10b", record, 24))
        windows = sorted((source, cosine, sine, dst))
        if (windows[-1] > 992 or any(b - a < 32 for a, b in zip(windows, windows[1:])) or
                any(record[34:124]) or not all(-63 <= s <= 63 for s in (cos, neg, neg_align, sin, sin_align, out)) or
                coeff_exp != -14 or src_exp + coeff_exp + cos != native_exp or neg + neg_align or
                src_exp + coeff_exp + sin + sin_align != native_exp or native_exp + out != dst_exp):
            raise ValueError("invalid native resident RoPE descriptor")

        def begin(done):
            def word(index):
                if index == 32:
                    done()
                    return
                addresses = (source + index, source + (index ^ 16), cosine + index, sine + index)
                operands = []

                def gather():
                    if len(operands) == len(addresses):
                        rotate()
                        return

                    def received(values):
                        operands.append(values)
                        gather()

                    self.read(addresses[len(operands)], received)

                def rotate():
                    x, pair, c, s = operands
                    result = []
                    for value, other, c_gain, s_gain in zip(x, pair, c, s):
                        if index < 16:
                            other = s32(rne(s32(rne(-other, neg)), neg_align))
                        real = s32(rne(value * c_gain, cos))
                        rot = s32(rne(s32(rne(other * s_gain, sin)), sin_align))
                        result.append(s32(rne(s32(real + rot), out)))
                    operations = [("e_product_packets", 9)]
                    if index < 16:
                        operations.append(("e_product_packets", 9))
                        if neg_align:
                            operations.append(("e_convert_packets", 7))
                    operations.append(("e_product_packets", 9))
                    if sin_align:
                        operations.append(("e_convert_packets", 7))
                    operations.append(("e_add_packets", 9))
                    if out:
                        operations.append(("e_convert_packets", 7))

                    def packet(i):
                        if i == len(operations):
                            self.write(dst + index, result, lambda: word(index + 1))
                            return
                        op, cycles = operations[i]
                        self.leaf(op, cycles, lambda: packet(i + 1))

                    packet(0)

                gather()

            word(0)
        return self.service(begin)
