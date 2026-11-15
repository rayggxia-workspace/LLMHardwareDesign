"""Qwen3 S32 RMS provider with a descriptor-defined vector length."""
from math import isqrt
from struct import unpack_from

from native_tlm_u import UArithmetic, rne


class RMS(UArithmetic):
    def bind(self, record, *, gamma_bank=None, shifted_input=False):
        source, gamma, target, words, epsilon = unpack_from("<4HI", record, 16)
        shift = record[28] if shifted_input else 0
        if (words not in (16, 24, 32, 64, 256, 384, 512, 640, 768) or max(source, gamma, target) + words > 1024
                or gamma_bank is None and gamma < source + words and source < gamma + words
                or target not in (source, gamma) and (abs(target-source) < words or abs(target-gamma) < words)
                or not epsilon or (shifted_input and not 1 <= shift <= 8)
                or any(record[29 if shifted_input else 28:124])):
            raise ValueError("invalid RMS SRAM spans or epsilon")

        def begin(done):
            extra = 0
            squares = 0

            def scan(i):
                if i == words:
                    self.leaf("n_begin", 2, lambda: stats(0))
                    return

                def inspected(values):
                    nonlocal extra
                    while any(not -32768 <= rne(value << shift, extra) <= 32767 for value in values):
                        extra += 1
                    scan(i + 1)

                self.read(source + i, inspected)

            def stats(i):
                if i == words:
                    eps = max(1, rne(epsilon, 2 * extra))
                    divisor = isqrt((squares << 14)//words + (eps << 16))
                    raw_factor = (1 << 38) // divisor
                    factor = raw_factor if shifted_input else rne(raw_factor, extra)
                    self.leaf("n_finalize", 168, lambda: self.leaf(
                        "n_read_factor", 2, lambda: apply(0, factor)))
                    return

                def accumulated(values):
                    nonlocal squares
                    squares += sum(rne(value << shift, extra)**2 for value in values)
                    self.leaf("n_stats", 6, lambda: stats(i + 1))

                self.read(source + i, accumulated)

            def apply(i, factor):
                if i == words:
                    done()
                    return

                def multiply(values):
                    shift_product = 13+extra if shifted_input else 13
                    scaled = [rne((value << shift) * factor, shift_product) for value in values]

                    def gamma_ready(weights):
                        result = [rne(value * weight, 17) for value, weight in zip(scaled, weights)]
                        self.leaf("e_product_packets", 9, lambda: self.write(
                            target + i, result, lambda: apply(i + 1, factor)))

                    def read_gamma():
                        if gamma_bank is None:
                            self.read(gamma + i, gamma_ready)
                        else:
                            gamma_bank.access(gamma+i, lambda data: self.edge(
                                lambda: gamma_ready(unpack_from("<4i", data))))
                    self.leaf("e_product_packets", 9, read_gamma)

                self.read(source + i, multiply)

            scan(0)

        return self.service(begin)
