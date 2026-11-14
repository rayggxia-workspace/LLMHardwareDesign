"""Native DMA providers sharing one finite write lane and callback-backed DDR."""

from bisect import bisect_right
from collections import Counter
from struct import unpack_from

from native_tlm_timing import Transfer
from native_tlm_pipeline import span, stream


class CommittedMemory:
    """Read immutable images or bytes committed to the compiled write allocation."""

    def __init__(self, images, write_regions):
        self.images = images
        self.regions = sorted(write_regions)
        self.bases = [base for base, _, _ in self.regions]
        self.committed = {}
        self.pending = set()
        end = 0
        for base, size, tag in self.regions:
            if base < end or size <= 0 or (base | size) % 64 or tag < 0:
                raise ValueError("invalid compiled DDR write extent")
            end = base + size

    def binding(self, address):
        if address % 64:
            raise ValueError("unaligned DDR beat")
        index = bisect_right(self.bases, address) - 1
        if index >= 0:
            base, size, tag = self.regions[index]
            if address < base + size:
                return tag + (address - base) // 64
        return None

    def __call__(self, address):
        if self.binding(address) is None:
            return self.images(address)
        if address not in self.committed:
            raise ValueError(f"DDR read before the compiled write committed at {address:#x}")
        return self.committed[address]

    def begin_write(self, address, tag, payload):
        expected = self.binding(address)
        if (expected is None or tag != expected or len(payload) != 64 or
                address in self.pending or address in self.committed):
            raise ValueError("unbound or duplicate native DDR write")
        self.pending.add(address)

        def commit():
            self.pending.remove(address)
            self.committed[address] = payload

        return commit


class NativeDMA:
    def __init__(self, clock, dram, memory, *, core_ps, pipeline=False):
        self.clock, self.dram, self.memory, self.core_ps = clock, dram, memory, core_ps
        self.writer = None
        self.pipeline = pipeline
        self.stats = Counter()

    def next_edge(self, action):
        self.clock.after(self.core_ps - self.clock.now % self.core_ps, action)

    def provider(self, sram, *, size, store=False, channel=None, down_sram=None):
        if down_sram is not None and (size != 8192 or not store or len(down_sram) != 3):
            raise ValueError("native Down store requires exactly three source SRAMs")

        def bind(record):
            word, base = unpack_from("<H6xQ", record, 16)
            tag, = unpack_from("<Q", record, 32)
            if (base % 64 or word + size // 16 > 1024 or size <= 0 or size % 64 or
                    any(record[18:24]) or any(record[(40 if store else 32):124]) or
                    (down_sram is not None and (word != 0 or tag != base // 64))):
                raise ValueError("invalid native DMA descriptor extent")

            def execute(done):
                def beat(offset, complete=None):
                    if offset == size:
                        if store:
                            self.writer = None
                        done()
                        return
                    address = base + offset
                    s_word = word + offset // 16
                    if store:
                        gather(offset, address, s_word, [], complete)
                    else:
                        self.dram.submit(Transfer(address), lambda: read_return(offset, address, s_word, complete),
                                         channel=channel)

                def read_return(offset, address, s_word, complete):
                    payload = self.memory(address)
                    self.stats["read_returns"] += 1
                    if complete:
                        self.next_edge(lambda: span(sram, s_word, 4, self.next_edge,
                                                   lambda _: complete(), payload))
                    else:
                        self.next_edge(lambda: fill(offset, s_word, payload, 0))

                def fill(offset, s_word, payload, lane):
                    if lane == 4:
                        beat(offset + 64)
                        return
                    count = sram.beat_words(s_word + lane, 4 - lane)
                    end = lane + count
                    sram.access_beat(s_word + lane, count, lambda _: self.next_edge(
                        lambda: fill(offset, s_word, payload, end)), payload[16 * lane:16 * end])

                def gather(offset, address, s_word, parts, complete):
                    lanes = sum(len(part) // 16 for part in parts)
                    if lanes < 4:
                        def received(payload):
                            parts.append(payload)
                            self.next_edge(lambda: gather(offset, address, s_word, parts, complete))

                        linear = s_word + lanes
                        if down_sram is None:
                            count = sram.beat_words(linear, 4 - lanes)
                            if complete:
                                span(sram, linear, 4-lanes, self.next_edge, received)
                            else:
                                sram.access_beat(linear, count, received)
                        else:
                            group, lane = divmod(linear, 2)
                            source = down_sram[group % 3]
                            word = 2 * (group // 3) + lane
                            count = source.beat_words(word, min(2 - lane, 4 - lanes))
                            source.access_beat(word, count, received)
                        return
                    submit_write(offset, address, b"".join(parts), complete)

                def submit_write(offset, address, payload, complete):
                    commit = self.memory.begin_write(address, tag + offset // 64, payload)

                    def write_return():
                        commit()
                        self.stats["write_commits"] += 1
                        self.next_edge(complete or (lambda: beat(offset + 64)))

                    self.dram.submit(Transfer(address, payload), write_return, channel=channel)

                if store:
                    if self.writer is not None:
                        raise ValueError("native DDR write lane is already held by another descriptor")
                    self.writer = record
                if self.pipeline:
                    self.next_edge(lambda: stream(size//64, 8, lambda i, ack: beat(64*i, ack),
                                                  lambda: beat(size)))
                else:
                    self.next_edge(lambda: beat(0))

            return execute
        return bind
