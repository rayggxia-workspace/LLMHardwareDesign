"""Timed wide-head attention using bounded SRAM windows and verified KV beats."""
from collections import Counter
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
    def __init__(self, projection, *, pipeline=False):
        self.proj = projection
        self.ram = projection.target
        self.clock = projection.clock
        self.pipeline = pipeline
        self.stats = Counter()

    def bind(self, record):
        count, width, q_word, out, scale, key, value = unpack_from("<4HIQQ", record, 16)
        words = width//4
        row_bytes = width*4
        if (width != 256 or not 1 <= count <= 514 or not 0 < scale <= 1 << 30
                or any(record[44:124]) or (key | value) % 64 or
                max(q_word, out)+words > 1024):
            raise ValueError("invalid wide-head attention descriptor")
        proj, ram = self.proj, self.ram
        operand = None
        if self.pipeline:
            from attention_refill import PipelinedOperands
            operand = PipelinedOperands(proj, 544, words, 2, self.stats)

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

            def normalize():
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
                        proj.edge(lambda: proj.write_span(ram, 384, payload, start_av), 64)))

                proj.write_span(ram, 384, padded, lambda:
                                proj.read_span(ram, 384, len(padded)//16, softmax))

            def key_dot(first, n, query, raw, finished, cycles):
                k = np.frombuffer(raw, dtype="<i4").astype(np.int64).reshape(n, width)
                scores[first:first+n] = np.rint((k@query)/65536).clip(-(1 << 31), (1 << 31)-1)
                proj.edge(finished, cycles)

            def qk(query, first):
                if first == count:
                    normalize()
                    return
                n = min(4, count-first)
                prefetch(key, first, n, lambda raw:
                         key_dot(first, n, query, raw, lambda: qk(query, first+n), 256))

            def start_query(raw):
                query = np.frombuffer(raw, dtype="<i4").astype(np.int64)
                if operand is None:
                    qk(query, 0)
                else:
                    def consume(first, n, word, finished):
                        operand.read(word, n*words, lambda data: key_dot(first, n, query, data, finished, 128))
                    operand.replay(key, count, consume, normalize)

            def output_av():
                data = np.rint(accum/65536).clip(-(1 << 31), (1 << 31)-1).astype("<i4")
                proj.write_span(ram, out, data.tobytes(), done)

            def value_dot(raw, n, probability, finished):
                v = np.frombuffer(raw, dtype="<i4").astype(np.int64).reshape(n, width)
                accum[:] += probability @ v
                proj.edge(finished, n*32)

            def av(first):
                if first == count:
                    output_av()
                    return
                n = min(4, count-first)

                def read_probability(raw):
                    probability = np.frombuffer(raw, dtype="<i4")[:n].astype(np.int64)
                    prefetch(value, first, n, lambda values: value_dot(values, n, probability, lambda: av(first+n)))

                proj.read_span(ram, 384+first//4, 1, read_probability)

            def start_av():
                if operand is None:
                    av(0)
                else:
                    def consume(first, n, word, finished):
                        def read_probability(raw):
                            offset = first % 4
                            probability = np.frombuffer(raw, dtype="<i4")[offset:offset+n].astype(np.int64)
                            operand.read(word, n*words, lambda values: value_dot(values, n, probability, finished))
                        operand.read(384+first//4, 1, read_probability)
                    operand.replay(value, count, consume, output_av)

            proj.read_span(ram, q_word, words, start_query)
        return run
