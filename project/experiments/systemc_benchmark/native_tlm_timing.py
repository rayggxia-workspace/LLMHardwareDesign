"""Timed native service execution on finite S128 ports and real DDR callbacks."""

from collections import Counter, defaultdict, deque
from bisect import bisect_right
import ctypes as c
from dataclasses import dataclass
import heapq
from itertools import count
from functools import lru_cache
from mmap import ACCESS_READ, mmap
from struct import unpack_from
from native_tlm_pipeline import span, stream


@dataclass
class Transfer:
    address: int
    payload: bytes | None = None


class Images:
    def __init__(self, table):
        count_line, *rows = table.read_text(encoding="ascii").splitlines()
        self.regions = {}
        end = 0
        for row in rows:
            base, size, name = row.split()
            base, size = int(base), int(size)
            if base < end or size <= 0 or (base | size) % 64:
                raise ValueError("invalid initial DDR region")
            self.regions[base] = size, table.parent / name
            end = base + size
        if int(count_line) != len(self.regions):
            raise ValueError("initial DDR table count mismatch")
        self.bases = list(self.regions)
        self.map_image = lru_cache(maxsize=512)(self.open_image)

    @staticmethod
    def open_image(path):
        with path.open("rb") as source:
            return mmap(source.fileno(), 0, access=ACCESS_READ)

    def __call__(self, address):
        index = bisect_right(self.bases, address) - 1
        if index < 0:
            raise ValueError("DDR read below all images")
        base = self.bases[index]
        size, path = self.regions[base]
        if address + 64 > base + size:
            raise ValueError("DDR read outside its image")
        offset = address - base
        data = self.map_image(path)[offset:offset+64]
        if len(data) != 64:
            raise ValueError("truncated DDR image")
        return data


class Clock:
    def __init__(self):
        self.now = 0
        self.events = []
        self.sequence = count()

    def after(self, delay, callback):
        heapq.heappush(self.events, (self.now + delay, next(self.sequence), callback))

    def until(self, complete):
        while not complete():
            if not self.events:
                raise RuntimeError("native TLM deadlock")
            self.now, _, callback = heapq.heappop(self.events)
            callback()


class Dram:
    def __init__(self, clock, library, config, output, *, credits, core_ps=None):
        if credits <= 0:
            raise ValueError("DDR requires positive finite credits")
        self.clock, self.credits = clock, credits
        self.core_ps = core_ps
        self.issue_history = (deque(), deque())
        self.stats = Counter()
        self.pending = defaultdict(deque)
        self.queue = (deque(), deque())
        self.active = [0, 0]
        self.lib = c.CDLL(str(library))
        callback = c.CFUNCTYPE(None, c.c_uint64, c.c_bool)
        for name, result, arguments in (
                ("open", c.c_void_p, [c.c_char_p, c.c_char_p, callback]),
                ("period_ns", c.c_double, [c.c_void_p]),
                ("offer", c.c_bool, [c.c_void_p, c.c_uint64, c.c_bool]),
                ("tick", None, [c.c_void_p]), ("close", None, [c.c_void_p])):
            function = getattr(self.lib, f"native_dram_{name}")
            function.restype, function.argtypes = result, arguments
        self.callbacks = [callback(lambda address, write, ch=ch: self.returned(ch, address, write))
                          for ch in range(2)]
        self.models = []
        for ch in range(2):
            directory = output / f"channel{ch}"
            directory.mkdir()
            self.models.append(self.lib.native_dram_open(str(config).encode(), str(directory).encode(),
                                                        self.callbacks[ch]))
            period = round(self.lib.native_dram_period_ns(self.models[-1]) * 1000)
            if period != 630:
                raise ValueError("expected the native 630 ps DRAMsim3 configuration")
        self.failure = None
        self.clock.after(630, self.tick)

    def submit(self, transfer, done, *, channel=None):
        address = transfer.address
        if address % 64 or not 0 <= address < 16 * (1 << 30):
            raise ValueError("native DDR beat is outside the channel capacity")
        if channel is None:
            channel = (address >> 6) & 1
        self.queue[channel].append((transfer, done, self.clock.now))
        key = f"channel{channel}_peak_queued"
        self.stats[key] = max(self.stats[key], len(self.queue[channel]))

    def returned(self, channel, address, write):
        key = channel, address, write
        if not self.pending.get(key):
            self.failure = RuntimeError(f"unmatched DRAMsim3 callback: {key}")
            return
        done, admitted = self.pending[key].popleft()
        if not self.pending[key]:
            del self.pending[key]
        self.active[channel] -= 1
        self.stats["callbacks"] += 1
        self.stats["ddr_inflight_ps"] += self.clock.now - admitted
        self.clock.after(0, done)

    def tick(self):
        for channel, model in enumerate(self.models):
            queue = self.queue[channel]
            history = self.issue_history[channel]
            cycle = self.clock.now // self.core_ps if self.core_ps else 0
            if self.core_ps:
                while history and history[0] < cycle - 2:
                    history.popleft()
            blocked = (self.core_ps and
                       (len(history) == 4 or history.count(cycle) == 2))
            if queue and not blocked and self.active[channel] < self.credits:
                transfer, done, queued = queue[0]
                write = transfer.payload is not None
                if self.lib.native_dram_offer(model, transfer.address, write):
                    queue.popleft()
                    self.pending[channel, transfer.address, write].append((done, self.clock.now))
                    self.active[channel] += 1
                    if self.core_ps:
                        history.append(cycle)
                    self.stats["ddr_queue_ps"] += self.clock.now - queued
                    key = f"channel{channel}_peak_active"
                    self.stats[key] = max(self.stats[key], self.active[channel])
                    self.stats["writes" if write else "reads"] += 1
                else:
                    self.stats["dram_backpressure_ticks"] += 1
            elif queue:
                self.stats["dma_issue_throttle_ticks" if blocked else "dma_credit_wait_ticks"] += 1
            self.lib.native_dram_tick(model)
        if self.failure:
            raise self.failure
        self.clock.after(630, self.tick)

    def close(self):
        if self.pending or any(self.queue) or any(self.active):
            raise RuntimeError("DDR closed before drain")
        for model in self.models:
            self.lib.native_dram_close(model)


class S128:
    def __init__(self, clock, *, core_ps, port_bits=128):
        if port_bits not in (128, 512):
            raise ValueError("local SRAM port must be 128 or 512 bits")
        self.clock, self.core_ps = clock, core_ps
        self.words_per_beat = port_bits // 128
        self.words = {}
        self.next_port = 0
        self.responses = deque()
        self.stats = Counter()

    def access(self, word, done, payload=None):
        self.access_beat(word, 1, done, payload)

    def beat_words(self, word, remaining):
        return min(remaining, self.words_per_beat - word % self.words_per_beat)

    def access_beat(self, word, words, done, payload=None):
        if (not 0 <= word < word + words <= 1024 or
                words > self.beat_words(word, words) or
                (payload is not None and len(payload) != 16 * words)):
            raise ValueError("invalid local SRAM beat")
        edge = ((self.clock.now + self.core_ps - 1) // self.core_ps) * self.core_ps
        while self.responses and self.responses[0] <= edge:
            self.responses.popleft()
        start = max(edge, self.next_port)
        if len(self.responses) == 2:
            start = max(start, self.responses.popleft())
        self.stats["port_wait_ps"] += start - edge
        operation = "read" if payload is None else "write"
        self.stats[f"{operation}_beats"] += 1
        self.stats[f"{operation}_bytes"] += words * 16
        for address in range(word, word + words):
            self.stats[f"bank{address % 4}_accesses"] += 1
        self.next_port = start + self.core_ps
        self.responses.append(start + 2 * self.core_ps)

        def complete():
            if payload is None:
                done(self.words[word] if words == 1 else b"".join(
                    self.words[address] for address in range(word, word + words)))
            else:
                for lane in range(words):
                    self.words[word + lane] = payload[16 * lane:16 * (lane + 1)]
                done(payload)

        self.clock.after(start - self.clock.now + 2 * self.core_ps, complete)


class Scheduler:
    def __init__(self, clock, ddr, memory, *, core_ps, pm_write_bits=128, pipeline=False):
        self.clock, self.ddr, self.memory, self.core_ps = clock, ddr, memory, core_ps
        self.pm_write_bytes = pm_write_bits // 8
        self.pipeline_pm = pipeline
        self.serial, self.terminals = count(), {}
        self.local_images = {}
        self.local_targets = set()

    def bind_local(self, target, image):
        entry, count, start = unpack_from("<III", image, 16)
        code = tuple(unpack_from("<Q", image, start + 8 * i)[0] for i in range(count))
        if entry != 0 or code != (0x4100000000000000, 0x4400000000000001, 0x4f00000000000000):
            raise ValueError("unsupported sealed local instruction sequence")
        self.local_images[target] = code

    def install_pm(self, address, image_bytes, *, mother):
        """Model sequential PM transfers and the mother's byte-serial readback."""
        core_ps = self.core_ps
        for offset in range(0, image_bytes, 64):
            returned = []
            self.ddr.submit(Transfer(address + offset), lambda: returned.append(True), channel=1)
            self.clock.until(lambda: bool(returned))
            committed = []
            writes = (min(64, image_bytes - offset) + self.pm_write_bytes - 1) // self.pm_write_bytes
            cycles = writes + 1 if self.pipeline_pm else writes * 2
            self.clock.after(cycles * core_ps, lambda: committed.append(True))
            self.clock.until(lambda: bool(committed))
        if mother:
            scanned = []
            self.clock.after(image_bytes * core_ps, lambda: scanned.append(True))
            self.clock.until(lambda: bool(scanned))

    def submit_local(self, target, slot, addresses, dispatch):
        if target in self.local_targets:
            raise ValueError("local controller accepted overlapping commands")
        self.local_targets.add(target)
        handle = next(self.serial)
        replies = []
        has_image = target in self.local_images
        wait_issued = False
        provider_done = False

        def finish_local():
            self.local_targets.remove(target)
            self.terminals[handle] = True

        def after_cycles(cycles, action):
            edge = ((self.clock.now + self.core_ps - 1) // self.core_ps) * self.core_ps
            self.clock.after(edge - self.clock.now + cycles * self.core_ps, action)

        def maybe_end():
            if wait_issued and provider_done:
                # END fetch/decode, release, then four terminal transport beats.
                after_cycles(8, finish_local)

        def issue_wait():
            nonlocal wait_issued
            wait_issued = True
            maybe_end()

        def terminal():
            nonlocal provider_done
            provider_done = True
            if has_image:
                maybe_end()
            else:
                finish_local()

        def offer_provider():
            run = dispatch(replies)
            if has_image:
                # Local WAIT fetch proceeds while the provider is active.
                after_cycles(3, issue_wait)
            run(terminal)

        def received(address):
            replies.append((address, self.memory(address)))
            if len(replies) == 2:
                # lc_scope_fetch128 scans bytes 0..123 after receiving both beats.
                after_cycles(124, offer_provider)

        def fetch_descriptor():
            for address in addresses:
                self.ddr.submit(Transfer(address), lambda address=address: received(address),
                                channel=(address >> 11) & 1)

        if has_image:
            # Four inbound flits, EXEC fetch/decode and twenty metadata reads.
            after_cycles(4 + 3 + 20 * 2 + 1, fetch_descriptor)
        else:
            fetch_descriptor()
        return handle

    def wait_local(self, handles):
        self.clock.until(lambda: all(handle in self.terminals for handle in handles))

    def local_succeeded(self, handle):
        return self.terminals.pop(handle)


def embedding(sram, ddr, memory, *, pipeline=False):
    """Execute the native one-index gather and commit all 512 destination words."""
    def bind(record):
        table, rows, offset, output, bits = unpack_from("<QIHHH", record, 16)
        if bits not in (32, 64) or offset % (bits // 8) or output not in (0, 512):
            raise ValueError("invalid embedding window")

        def execute(done):
            def index_ready(word):
                index = int.from_bytes(word[offset % 16:offset % 16 + bits // 8], "little", signed=True)
                if index < 0:
                    index += rows
                if not 0 <= index < rows:
                    raise ValueError("embedding index outside its table")
                row = table + 8192 * index

                if pipeline:
                    def edge(action):
                        clock = sram.clock
                        clock.after(sram.core_ps - clock.now % sram.core_ps, action)

                    def load(index, ack):
                        address = row + 64 * index
                        ddr.submit(Transfer(address), lambda: edge(lambda: span(
                            sram, output + 4*index, 4, edge, lambda _: ack(), memory(address))), channel=0)

                    stream(128, 8, load, done)
                    return

                def burst(beat):
                    if beat == 128:
                        done()
                        return
                    address = row + 64 * beat
                    ddr.submit(Transfer(address), lambda: store(beat, memory(address), 0), channel=0)

                def store(beat, payload, index):
                    if index == 4:
                        burst(beat + 1)
                        return
                    start = output + 4 * beat + index
                    end = index + sram.beat_words(start, 4 - index)
                    sram.access_beat(start, end - index, lambda _: store(beat, payload, end),
                                     payload[16 * index:16 * end])

                burst(0)

            sram.access(offset // 16, index_ready)

        return execute
    return bind
