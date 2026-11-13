"""Service-2 native projection with live K128 windows and bounded weight records."""

from collections import Counter
from struct import pack, unpack, unpack_from

from native_tlm_timing import Transfer
from native_tlm_u import rne


def accumulate(weights, activation, shift, prefix, head16):
    steps = 8 if head16 else 1
    scales = unpack_from("<" + "H" * (steps * 8), weights, 1024)
    payload = unpack_from("<1024b", weights)
    if not head16 and any(weights[1040:]):
        raise ValueError("nonzero ordinary projection record padding")
    for step in range(steps):
        chunks = range(step, step + 1) if head16 else range(8)
        for lane in range(8):
            total = 0
            for chunk in chunks:
                start = chunk * 128 + lane * 16
                total += sum(a * b for a, b in zip(payload[start:start + 16],
                                                  activation[chunk * 16:chunk * 16 + 16]))
            bits = scales[8 * step + lane]
            exponent = bits >> 10
            if not 0 < bits < 0x7c00:
                raise ValueError("invalid projection weight scale")
            scaled = rne(total * ((bits & 1023) + (1024 if exponent else 0)),
                         25 - max(exponent, 1) - shift)
            prefix[lane] += scaled
            if not (-(1 << 31) <= scaled < 1 << 31 and -(1 << 31) <= prefix[lane] < 1 << 31):
                raise ValueError("native projection overflow")


class Projection:
    def __init__(self, clock, dram, memory, source, target, *, source_word, scratch_word,
                 scratch_sram=None):
        self.clock, self.dram, self.memory = clock, dram, memory
        self.source, self.target = source, target
        self.source_word, self.scratch_word = source_word, scratch_word
        self.scratch_sram = source if scratch_sram is None else scratch_sram
        self.stats = Counter()
        self.busy = False

    def edge(self, action, cycles=1):
        period = self.target.core_ps
        self.clock.after(cycles * period - self.clock.now % period, action)

    def provider(self, record, *, packed_tile=None):
        weight0, weight1, columns, first, stride, groups, context, full_k, start, end, ways, flags = (
            unpack_from("<QQIIHBBHHHBB", record, 48))
        input_s, out, out1, scratch, snapshot, reserved, bias0, bias1 = unpack_from("<6HQQ", record, 84)
        bases = (weight0,) if ways == 1 else (weight0, weight1)
        outputs = (out,) if ways == 1 else (out, out1)
        spans = sorted([(input_s, 16), *((word, 2 * groups) for word in outputs)])
        if (any(base % 64 for base in bases) or stride < 8 or stride % 8 or first % 8 or
                not 1 <= groups <= 16 or context + groups * ways > 16 or
                first + (groups - 1) * stride >= columns or ways not in (1, 2) or
                flags > 1 or start or end != full_k or not full_k or full_k % 128 or
                sum(spans[-1]) > 1024 or any(a + size > b for (a, size), (b, _) in zip(spans, spans[1:])) or
                (ways == 1 and (weight1 or out1)) or reserved or bias0 or bias1 or any(record[112:124])):
            raise ValueError("unsupported native service-2 projection extent")
        overlaps_source = self.scratch_sram is self.source and not (
            self.scratch_word + 16 <= self.source_word or
            self.source_word + full_k // 4 <= self.scratch_word)
        overlaps_target = self.scratch_sram is self.target and any(
            word < self.scratch_word + 16 and self.scratch_word < word + width for word, width in spans)
        if packed_tile is None and (
                ways != 1 or scratch or snapshot or self.source_word + full_k // 4 > 1024 or
                not 0 <= self.scratch_word <= 1008 or overlaps_source or overlaps_target):
            raise ValueError("unbound projection feeder windows")
        head16 = bool(flags)
        size = 1152 if head16 else 1088
        tiles = full_k // 128

        def execute(done):
            if self.busy:
                raise ValueError("P projection already owns the feeder and M contexts")
            self.busy = True
            prefixes = [[0] * 8 for _ in range(groups * ways)]

            def tile(k):
                if k == tiles:
                    write_output(0)
                    return
                if packed_tile is not None:
                    packed_tile(k, lambda payload, shift: stage(k, payload, shift))
                    return
                start_word = self.source_word + k * 32

                def scan(data):
                    peak = max(abs(value) for value in unpack("<128i", data))
                    shift = next(s for s in range(18) if peak <= 32767 << s)

                    def convert(raw):
                        packed = pack("<128h", *(rne(v, shift) for v in unpack("<128i", raw)))
                        self.write_span(self.scratch_sram, self.scratch_word, packed, lambda: self.read_span(
                            self.scratch_sram, self.scratch_word, 16, lambda staged: stage(k, staged, shift)))

                    self.edge(lambda: self.read_span(self.source, start_word, 32, convert))

                self.read_span(self.source, start_word, 32, scan)

            def stage(k, packed, shift):
                self.write_span(self.target, input_s, packed, lambda: self.read_span(
                    self.target, input_s, 16, lambda data: run_records(k, unpack("<128h", data), shift)))

            def run_records(k, activation, shift):
                slots = {}
                next_fetch, next_run, executing = 0, 0, False

                def advance():
                    nonlocal next_fetch, executing
                    while len(slots) < 4 and next_fetch < groups * ways:
                        entry = next_fetch
                        next_fetch += 1
                        slots[entry] = None
                        group, way = divmod(entry, ways)
                        index = ((first + group * stride) // 8) * tiles + k
                        address = bases[way] + size * index
                        self.fetch(address, size, lambda data, e=entry: ready(e, data))
                    if next_run == groups * ways:
                        self.edge(lambda: tile(k + 1))
                    elif not executing and slots[next_run] is not None:
                        executing = True
                        # W-first stream is 8 x 128 B for K128. The completion
                        # includes a modeled scale/result drain per M group.
                        self.edge(finish_group, 8 + 8 * (8 if head16 else 1))

                def ready(group, data):
                    slots[group] = data
                    advance()

                def finish_group():
                    nonlocal next_run, executing
                    data = slots.pop(next_run)
                    accumulate(data, activation, shift, prefixes[next_run], head16)
                    self.stats["weight_records_consumed"] += 1
                    next_run += 1
                    executing = False
                    advance()

                advance()

            def write_output(index):
                if index == groups * ways:
                    self.busy = False
                    done()
                    return
                group, way = divmod(index, ways)
                self.write_span(self.target, outputs[way] + 2 * group, pack("<8i", *prefixes[index]),
                                lambda: write_output(index + 1))

            self.edge(lambda: tile(0))
        return execute

    def read_span(self, sram, start, words, done):
        parts = []

        def step(offset):
            if offset == words:
                done(b"".join(parts))
                return
            count = sram.beat_words(start + offset, words - offset)

            def returned(data):
                parts.append(data)
                self.edge(lambda: step(offset + count))

            sram.access_beat(start + offset, count, returned)
        step(0)

    def write_span(self, sram, start, data, done):
        def step(offset):
            if offset == len(data):
                done()
                return
            word = start + offset // 16
            count = sram.beat_words(word, (len(data) - offset) // 16)
            end = offset + count * 16
            sram.access_beat(word, count, lambda _: self.edge(lambda: step(end)), data[offset:end])
        step(0)

    def fetch(self, base, size, done):
        parts = []

        def beat():
            offset = len(parts) * 64
            if offset == size:
                done(b"".join(parts))
                return
            address = base + offset

            def returned():
                self.stats["weight_read_returns"] += 1
                parts.append(self.memory(address))
                beat()

            self.dram.submit(Transfer(address), returned, channel=(base >> 11) & 1)
        beat()
