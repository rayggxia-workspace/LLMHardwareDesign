"""Timed wide-head attention using bounded SRAM windows and verified KV beats."""
from functools import lru_cache
from struct import unpack_from

import numpy as np
from check_softmax import coefficients, reference
from native_tlm_timing import Transfer

from qwen3_short_plan import align


@lru_cache(maxsize=1)
def lut():
    return coefficients()


class WideAttention:
    def __init__(self, projection):
        self.proj = projection
        self.ram = projection.target
        self.clock = projection.clock

    def bind(self, record):
        count, width, q_word, out, scale, key, value = unpack_from("<4HIQQ", record, 16)
        words = width//4
        row_bytes = width*4
        if (width != 256 or not 1 <= count <= 514 or not 0 < scale <= 1 << 30
                or any(record[44:124]) or (key | value) % 64 or
                max(q_word, out)+words > 1024):
            raise ValueError("invalid wide-head attention descriptor")
        proj, ram = self.proj, self.ram

        def run(done):
            scores = np.empty(count, dtype="<i4")
            accum = np.zeros(width, dtype=np.int64)

            def prefetch(base, first, n, callback):
                beats = n*row_bytes//64
                issued = committed = 0
                ready = {}
                writing = False

                def accept():
                    nonlocal issued
                    while issued < beats and issued-committed < 8:
                        index = issued
                        issued += 1
                        address = base+first*row_bytes+index*64
                        proj.dram.submit(Transfer(address), lambda i=index,a=address: complete(i,a), channel=1)

                def complete(index, address):
                    ready[index] = proj.memory(address)
                    drain()

                def ack():
                    nonlocal committed, writing
                    committed += 1
                    writing = False
                    if committed == beats:
                        proj.read_span(ram, 544, n*words, callback)
                    else:
                        accept()
                        drain()

                def drain():
                    nonlocal writing
                    if not writing and committed in ready:
                        writing = True
                        proj.write_span(ram, 544+4*committed, ready.pop(committed), ack)

                accept()

            def qk(query, first):
                if first == count:
                    scaled = np.rint(scores.astype(np.float64)*scale/(1 << 30)).clip(
                        -(1 << 31), (1 << 31)-1).astype("<i4")
                    padded = scaled.tobytes().ljust(align(count*4, 16), b"\0")

                    def softmax(raw):
                        values = np.frombuffer(raw, dtype="<i4")[:count].tolist()
                        exponents, prob = reference(values, lut())
                        exponent = np.asarray(exponents, dtype="<i4").tobytes().ljust(len(padded), b"\0")
                        payload = np.asarray(prob, dtype="<i4").tobytes().ljust(len(padded), b"\0")
                        proj.write_span(ram, 384, exponent, lambda:
                            proj.read_span(ram, 384, len(padded)//16, lambda _:
                            proj.edge(lambda: proj.write_span(ram, 384, payload, lambda: av(0)), 64)))

                    proj.write_span(ram, 384, padded, lambda:
                                    proj.read_span(ram, 384, len(padded)//16, softmax))
                    return

                n = min(4, count-first)

                def loaded(raw):
                    k = np.frombuffer(raw, dtype="<i4").astype(np.int64).reshape(n, width)
                    scores[first:first+n] = np.rint((k@query)/65536).clip(-(1 << 31), (1 << 31)-1)
                    proj.edge(lambda: qk(query, first+n), 256)

                prefetch(key, first, n, loaded)

            def av(first):
                if first == count:
                    data = np.rint(accum/65536).clip(-(1 << 31), (1 << 31)-1).astype("<i4")
                    proj.write_span(ram, out, data.tobytes(), done)
                    return
                n = min(4, count-first)

                def loaded(raw, probability):
                    v = np.frombuffer(raw, dtype="<i4").astype(np.int64).reshape(n, width)
                    accum[:] += probability @ v
                    proj.edge(lambda: av(first+n), n*32)

                def read_probability(raw):
                    probability = np.frombuffer(raw, dtype="<i4")[:n].astype(np.int64)
                    prefetch(value, first, n, lambda values: loaded(values, probability))

                proj.read_span(ram, 384+first//4, 1, read_probability)

            proj.read_span(ram, q_word, words, lambda raw:
                           qk(np.frombuffer(raw, dtype="<i4").astype(np.int64), 0))
        return run
