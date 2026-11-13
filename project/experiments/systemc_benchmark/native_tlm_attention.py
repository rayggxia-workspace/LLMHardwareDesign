"""ATT1 data flow using the resident S128 aperture and committed K/V reads."""

from collections import Counter
from functools import lru_cache
from pathlib import Path
from struct import pack, unpack, unpack_from
import sys

from native_tlm_timing import Transfer
from native_tlm_u import rne, s32

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "native_s32_n"))
from check_softmax import coefficients, reference


@lru_cache(maxsize=1)
def softmax_lut():
    return coefficients()


class Attention:
    def __init__(self, clock, dram, memory, aperture, *, kv_window=1):
        if not 1 <= kv_window <= 32:
            raise ValueError("KV read window must be between 1 and 32 beats")
        self.clock, self.dram, self.memory, self.aperture = clock, dram, memory, aperture
        self.sram = aperture.target
        self.kv_window = kv_window
        self.stats = Counter()

    def provider(self, record):
        count, position, query, score, work, out, coefficient, k_base, v_base = (
            unpack_from("<6HIQQ", record, 16))
        score_words = (count + 3) // 4
        windows = sorted(((query, 32), (score, score_words), (work, 256), (out, 32)))
        if (not 1 <= count <= 639 or position != count - 1 or not 0 < coefficient <= 1 << 30 or
                (k_base | v_base) % 64 or abs(k_base - v_base) < count * 512 or any(record[48:124]) or
                any(lo + words > hi for (lo, words), (hi, _) in zip(windows, windows[1:])) or
                sum(windows[-1]) > 1024):
            raise ValueError("invalid native ATT1 extent")

        def execute(done):
            def read_memory(base, beats, bank_word, done, pick=None):
                def step(i):
                    if i == beats:
                        done()
                        return
                    address = base + 64 * i

                    def returned():
                        data = self.memory(address)
                        self.stats["kv_read_returns"] += 1
                        if pick is not None:
                            if i != pick // 2:
                                self.aperture.edge(lambda: step(i + 1))
                                return
                            lane = (pick % 2) * 32
                            data = data[lane:lane+32]
                            dst = bank_word
                        else:
                            dst = bank_word + 4 * i
                        self.aperture.edge(lambda: write(dst, data, lambda: step(i + 1)))

                    self.dram.submit(Transfer(address), returned, channel=1)
                step(0)

            def read(start, words, done):
                self.aperture.read_span(self.sram, start, words, done)

            def write(start, payload, done):
                self.aperture.write_span(self.sram, start, payload, done)

            def prefetch(beats, plan, finished):
                issued = committed = 0
                ready = {}
                draining = False

                def issue():
                    nonlocal issued
                    while issued < beats and issued - committed < self.kv_window:
                        index = issued
                        address, _, _ = plan(index)
                        issued += 1
                        self.stats["kv_window_peak"] = max(self.stats["kv_window_peak"], issued - committed)
                        self.dram.submit(Transfer(address), lambda i=index, a=address: returned(i, a), channel=1)

                def returned(index, address):
                    ready[index] = self.memory(address)
                    self.stats["kv_read_returns"] += 1
                    drain()

                def acknowledged():
                    nonlocal committed, draining
                    committed += 1
                    draining = False
                    if committed == beats:
                        finished()
                    else:
                        issue()
                        drain()

                def drain():
                    nonlocal draining
                    if draining or committed not in ready:
                        return
                    draining = True
                    payload = ready.pop(committed)
                    _, destination, lane = plan(committed)
                    if destination is None:
                        self.aperture.edge(acknowledged)
                    else:
                        if lane is not None:
                            payload = payload[lane:lane+32]
                        self.aperture.edge(lambda: write(destination, payload, acknowledged))

                issue()

            def qk(first):
                if first == count:
                    softmax()
                    return
                n = min(8, count - first)

                def loaded():
                    def dot(q, keys):
                        q = unpack("<128i", q)
                        values = []
                        for row in range(n):
                            key = unpack_from("<128i", keys, 512 * row)
                            partial = rne(sum(a*b for a, b in zip(q, key)), 16)
                            values.append(s32(partial))
                        values.extend([0] * (-n % 4))
                        self.stats["qk_dot_groups"] += 1
                        self.aperture.edge(lambda: write(score + first // 4, pack(
                            "<" + "i" * len(values), *values), lambda: qk(first+n)), 128)

                    read(query, 32, lambda q: read(work, 32*n, lambda keys: dot(q, keys)))

                base = k_base + first*512
                if self.kv_window == 1:
                    read_memory(base, 8*n, work, loaded)
                else:
                    prefetch(8*n, lambda i: (base + 64*i, work + 4*i, None), loaded)

            def softmax():
                def scale(index):
                    if index == score_words:
                        read(score, score_words, lambda _: read(score, score_words, normalized))
                        return

                    def apply(raw):
                        result = pack("<4i", *(s32(rne(x * coefficient, 30))
                                               for x in unpack("<4i", raw)))
                        self.aperture.edge(lambda: write(score+index, result, lambda: scale(index+1)), 9)

                    read(score+index, 1, apply)

                def normalized(payload):
                    scores = unpack("<" + "i" * (4*score_words), payload)[:count]
                    exponents, probability = reference(scores, softmax_lut())
                    exponents.extend([0] * (-count % 4))
                    probability.extend([0] * (-count % 4))
                    # Preserve the in-S exponent spill and probability rewrite.
                    write(score, pack("<" + "i"*len(exponents), *exponents),
                          lambda: read(score, score_words, lambda _: self.aperture.edge(
                              lambda: write(score, pack("<" + "i"*len(probability), *probability),
                                            lambda: av(0, 0, [0]*8)), 64)))

                scale(0)

            def av(group, first, sums):
                if first == count:
                    output = pack("<8i", *(s32(rne(value, 16)) for value in sums))
                    write(out + 2*group, output, done if group == 15 else lambda: av(group+1, 0, [0]*8))
                    return
                n = min(128, count-first)

                def loaded():
                    read(score+first//4, (n+3)//4,
                         lambda probs: read(work, 2*n, lambda values: reduce(probs, values)))

                def refill(index):
                    if index == n:
                        loaded()
                        return
                    address = v_base + (first+index)*512 + (group//4)*128
                    read_memory(address, 2, work + 2*index, lambda: refill(index+1), pick=group%4)

                def reduce(probs, values):
                    probability = unpack("<" + "i"*(len(probs)//4), probs)
                    for row in range(n):
                        for lane, value in enumerate(unpack_from("<8i", values, 32*row)):
                            sums[lane] += probability[row]*value
                    self.stats["av_dot_groups"] += 1
                    self.aperture.edge(lambda: av(group, first+n, sums), n)

                if self.kv_window == 1:
                    refill(0)
                else:
                    pick = group % 4

                    def plan(i):
                        row, beat = divmod(i, 2)
                        address = v_base + (first+row)*512 + (group//4)*128 + 64*beat
                        return address, work + 2*row if beat == pick//2 else None, (pick % 2)*32

                    prefetch(2*n, plan, loaded)

            qk(0)
        return execute
