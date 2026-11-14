"""ATT1 data flow using the resident S128 aperture and committed K/V reads."""

from collections import Counter
from functools import lru_cache
from pathlib import Path
from struct import pack, unpack, unpack_from
import sys

from native_tlm_timing import Transfer
from native_tlm_pipeline import span
from native_tlm_u import rne, s32

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "native_s32_n"))
from check_softmax import coefficients, reference


@lru_cache(maxsize=1)
def softmax_lut():
    return coefficients()


class Attention:
    def __init__(self, clock, dram, memory, aperture, *, kv_window=1, pipeline=False, value_fetch="legacy"):
        if not 1 <= kv_window <= 32:
            raise ValueError("KV read window must be between 1 and 32 beats")
        self.clock, self.dram, self.memory, self.aperture = clock, dram, memory, aperture
        self.sram = aperture.target
        self.kv_window = kv_window
        if value_fetch not in ("legacy", "selected", "paired"):
            raise ValueError("unknown AV fetch mode")
        self.value_fetch = value_fetch
        self.pipeline = pipeline
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
                        if self.pipeline:
                            self.aperture.edge(lambda: span(
                                self.sram, destination, len(payload)//16, self.aperture.edge,
                                lambda _: acknowledged(), payload))
                        else:
                            self.aperture.edge(lambda: write(destination, payload, acknowledged))

                issue()

            def tiled(count, tile, load, consume, finish):
                """Two disjoint half windows, with at most one refill active."""
                def start(index, bank):
                    if index == count:
                        finish()
                        return
                    size = min(tile, count-index)
                    load(index, size, bank, lambda: compute(index, size, bank))

                def compute(index, size, bank):
                    next_index = index + size
                    next_bank = 1-bank
                    waiting = 2 if next_index < count else 1

                    def ready():
                        nonlocal waiting
                        waiting -= 1
                        if waiting == 0:
                            if next_index == count:
                                finish()
                            else:
                                compute(next_index, min(tile, count-next_index), next_bank)

                    if next_index < count:
                        load(next_index, min(tile, count-next_index), next_bank, ready)
                    consume(index, size, bank, ready)

                start(0, 0)

            def qk(first, *, tile_ready=None, bank=0, refill_only=False):
                if first == count:
                    softmax()
                    return
                n = min(4 if self.pipeline else 8, count - first)
                destination = work + 128*bank

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
                            "<" + "i" * len(values), *values), tile_ready or (lambda: qk(first+n))), 128)

                    read(query, 32, lambda q: read(destination, 32*n, lambda keys: dot(q, keys)))

                if self.pipeline and not refill_only:
                    loaded()
                    return
                base = k_base + first*512
                if self.kv_window == 1 and not self.pipeline:
                    read_memory(base, 8*n, work, loaded)
                else:
                    prefetch(8*n, lambda i: (base + 64*i, destination + 4*i, None),
                             tile_ready if refill_only else loaded)

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
                                            lambda: start_av(0)), 64)))

                scale(0)

            def start_av(group):
                paired = self.value_fetch == "paired"
                selected = self.value_fetch != "legacy"
                lanes = 16 if paired else 8
                row_words = lanes // 4
                tile = 32 if paired else (128 if self.pipeline else 256) // row_words
                sums = [0] * lanes

                def load(first, n, bank, ready):
                    destination = work + 128 * bank
                    group_address = v_base + (group // 4) * 128
                    pick = group % 4

                    def plan(index):
                        if selected:
                            row, beat = index, pick // 2
                        else:
                            row, beat = divmod(index, 2)
                        address = group_address + (first + row) * 512 + 64 * beat
                        dst = destination + row_words * row if beat == pick // 2 else None
                        return address, dst, None if paired else (pick % 2) * 32

                    beats = n if selected else 2 * n
                    self.stats["av_read_requests"] += beats
                    self.stats["av_legacy_read_requests"] += 2 * n * (lanes // 8)
                    prefetch(beats, plan, ready)

                def consume(first, n, bank, ready):
                    destination = work + 128 * bank

                    def step_slice(half, complete):
                        def dot(probs, values):
                            probability = unpack("<" + "i" * (len(probs) // 4), probs)
                            for row, weight in enumerate(probability[:n]):
                                for lane, value in enumerate(unpack_from("<8i", values, 32 * row)):
                                    sums[8 * half + lane] += weight * value
                            self.stats["av_dot_groups"] += 1
                            self.aperture.edge(save, n)

                        def inputs(probs):
                            if not paired:
                                read(destination, row_words * n, lambda values: dot(probs, values))
                                return
                            rows = []

                            def next_row(row):
                                if row == n:
                                    dot(probs, b"".join(rows))
                                else:
                                    def returned(data):
                                        rows.append(data)
                                        next_row(row + 1)
                                    read(destination + row * row_words + 2 * half, 2, returned)
                            next_row(0)

                        def execute_slice():
                            read(score + first // 4, (n + 3) // 4, inputs)

                        def snapshot_io(payload, finished):
                            self.stats["av_checkpoint_ops"] += 1
                            image = []
                            base = work + 128 + 7 * half

                            def received(data):
                                image.append(data)
                                word(len(image))

                            def word(index):
                                if index == 7:
                                    self.aperture.edge(lambda: finished(b"".join(image)), 4)
                                elif payload is None:
                                    read(base + index, 1, received)
                                else:
                                    write(base + index, payload[16 * index:16 * (index + 1)],
                                          lambda: word(index + 1))
                            self.aperture.edge(lambda: word(0), 4)

                        def save():
                            if not paired or first + n == count:
                                complete()
                                return
                            # Model payload and handshakes for the existing S80 context image.
                            image = b"".join(value.to_bytes(10, "little", signed=True)
                                             for value in sums[8 * half:8 * half + 8])
                            snapshot_io(image + bytes(32), lambda _: complete())

                        def restored(image):
                            sums[8 * half:8 * half + 8] = [
                                int.from_bytes(image[i:i + 10], "little", signed=True)
                                for i in range(0, 80, 10)]
                            execute_slice()

                        if paired and first:
                            snapshot_io(None, restored)
                        else:
                            execute_slice()

                    step_slice(0, (lambda: step_slice(1, ready)) if paired else ready)

                def finish():
                    output = pack(f"<{lanes}i", *(s32(rne(value, 16)) for value in sums))
                    next_group = group + lanes // 8
                    write(out + 2 * group, output, done if next_group == 16 else lambda: start_av(next_group))

                def serial(first):
                    if first == count:
                        finish()
                    else:
                        n = min(tile, count - first)
                        load(first, n, 0, lambda: consume(first, n, 0, lambda: serial(first + n)))

                if self.pipeline and not paired:
                    tiled(count, tile, load, consume, finish)
                else:
                    serial(0)

            if self.pipeline:
                tiled(count, 4,
                      lambda i, _, b, ack: qk(i, tile_ready=ack, bank=b, refill_only=True),
                      lambda i, _, b, ack: qk(i, tile_ready=ack, bank=b), softmax)
            else:
                qk(0)
        return execute
