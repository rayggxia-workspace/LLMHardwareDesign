"""Qwen3 S32 RMS provider with a descriptor-defined vector length."""
from math import isqrt
from struct import unpack_from

from native_tlm_u import UArithmetic, rne


class RMS(UArithmetic):
    def bind(self, record):
        source, gamma, target, words, epsilon = unpack_from("<4HI", record, 16)
        if (words not in (32, 256) or max(source, gamma, target) + words > 1024
                or gamma < source + words and source < gamma + words
                or target not in (source, gamma) or not epsilon or any(record[28:124])):
            raise ValueError("invalid RMS SRAM spans or epsilon")
        stats_shift = 14 - (words.bit_length() - 1)

        def begin(done):
            extra = 0
            squares = 0

            def scan(i):
                if i == words:
                    self.leaf("n_begin", 2, lambda: stats(0))
                    return

                def inspected(values):
                    nonlocal extra
                    while any(not -32768 <= rne(value, extra) <= 32767 for value in values):
                        extra += 1
                    scan(i + 1)

                self.read(source + i, inspected)

            def stats(i):
                if i == words:
                    eps = max(1, rne(epsilon, 2 * extra))
                    divisor = isqrt((squares << stats_shift) + (eps << 16))
                    factor = rne((1 << 38) // divisor, extra)
                    self.leaf("n_finalize", 168, lambda: self.leaf(
                        "n_read_factor", 2, lambda: apply(0, factor)))
                    return

                def accumulated(values):
                    nonlocal squares
                    squares += sum(rne(value, extra)**2 for value in values)
                    self.leaf("n_stats", 6, lambda: stats(i + 1))

                self.read(source + i, accumulated)

            def apply(i, factor):
                if i == words:
                    done()
                    return

                def multiply(values):
                    scaled = [rne(value * factor, 13) for value in values]

                    def gamma_ready(weights):
                        result = [rne(value * weight, 17) for value, weight in zip(scaled, weights)]
                        self.leaf("e_product_packets", 9, lambda: self.write(
                            target + i, result, lambda: apply(i + 1, factor)))

                    self.leaf("e_product_packets", 9,
                              lambda: self.read(gamma + i, gamma_ready))

                self.read(source + i, multiply)

            scan(0)

        return self.service(begin)
